"""
DiffEngine for XML comparison.

This module provides the main DiffEngine class that orchestrates XML comparison
using xmldiff, classifies differences into categories (text, formatting, structure),
and supports large file handling with fast_match option.
"""

import difflib
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from lxml import etree
from xmldiff import main
from xmldiff.actions import (
    UpdateTextIn,
    InsertNode,
    DeleteNode,
    MoveNode,
    RenameNode,
    UpdateAttrib,
    InsertAttrib,
    DeleteAttrib,
)

from .models import (
    CompareOptions,
    TextDiff,
    FormatDiff,
    StructureDiff,
    CompareResult,
    DiffType,
)
from .parser_service import XMLParserService


class DiffEngine:
    """
    Main engine for comparing XML documents.
    
    Uses xmldiff to compute differences between XML trees, classifies them into
    text, formatting, and structure categories, and supports optional
    attribute comparison.
    
    Attributes:
        parser_service: Service for parsing XML files with entity handling
    """

    def __init__(self):
        """Initialize the DiffEngine with a parser service."""
        self.parser_service = XMLParserService()

    def diff(
        self,
        original_path: Path,
        revised_path: Path,
        options: Optional[CompareOptions] = None
    ) -> CompareResult:
        """
        Compare two XML files and return structured diff results.
        
        This is the main entry point for XML comparison. It parses both files,
        computes differences using xmldiff, and classifies them into the
        appropriate categories.
        
        Args:
            original_path: Path to the original XML file
            revised_path: Path to the revised XML file
            options: Comparison options (uses defaults if None)
            
        Returns:
            CompareResult containing all differences and statistics
        """
        if options is None:
            options = CompareOptions()

        # Parse both XML files
        left_tree, right_tree = self.parser_service.parse_both_files(
            original_path, revised_path
        )

        # Capture old text values BEFORE running diff (xmldiff mutates the tree)
        old_text_cache = self._capture_text_cache(left_tree)

        # Determine if fast_match should be used for large files
        use_fast_match = options.fast_match or self._should_use_fast_match(
            original_path, revised_path
        )

        # Get raw xmldiff actions
        diff_options = {"fast_match": use_fast_match} if use_fast_match else None
        raw_actions = self._get_raw_diff_actions(
            left_tree, right_tree, diff_options
        )

        # Create result container
        result = CompareResult(
            original_path=original_path,
            revised_path=revised_path,
            options=options,
        )

        # Count total nodes for statistics
        result.statistics.total_nodes = (
            self.parser_service.count_nodes(left_tree) +
            self.parser_service.count_nodes(right_tree)
        ) // 2

        # Process and classify each action
        self._process_actions(
            raw_actions,
            left_tree,
            right_tree,
            result,
            options,
            old_text_cache
        )

        # Calculate match percentage
        result.statistics.match_percentage = self._calculate_match_percentage(
            result.statistics
        )

        return result

    def _should_use_fast_match(
        self,
        original_path: Path,
        revised_path: Path,
        threshold_mb: float = 50.0
    ) -> bool:
        """
        Determine if fast_match should be used based on file sizes.
        
        Args:
            original_path: Path to original file
            revised_path: Path to revised file
            threshold_mb: Size threshold in MB
            
        Returns:
            True if either file exceeds threshold
        """
        return (
            self.parser_service.is_large_file(original_path, threshold_mb) or
            self.parser_service.is_large_file(revised_path, threshold_mb)
        )

    def _get_raw_diff_actions(
        self,
        left_tree: etree.ElementTree,
        right_tree: etree.ElementTree,
        diff_options: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Get raw xmldiff actions between two trees.
        
        Uses formatter=None to get structured action objects instead of
        formatted text output.
        
        Args:
            left_tree: Original XML tree
            right_tree: Revised XML tree
            diff_options: Optional diff options like fast_match
            
        Returns:
            List of xmldiff action objects
        """
        if diff_options:
            return main.diff_trees(
                left_tree,
                right_tree,
                formatter=None,
                diff_options=diff_options
            )
        return main.diff_trees(left_tree, right_tree, formatter=None)

    def _capture_text_cache(
        self,
        tree: etree.ElementTree
    ) -> Dict[str, str]:
        """
        Capture all text content from tree before diff mutates it.
        
        xmldiff.diff_trees mutates the tree in place when applying
        UpdateTextIn actions, so we must capture original text first.
        
        Args:
            tree: XML tree to capture text from
            
        Returns:
            Dict mapping XPath paths to text content
        """
        cache: Dict[str, str] = {}
        root = tree.getroot()

        # Walk only Element nodes (not Comment, ProcessingInstruction)
        # Comment/PI nodes have Cython tag objects that crash getpath()
        for elem in root.iter():
            # Skip non-element nodes (comments, processing instructions)
            # Their tag is a Cython factory, not a string
            if not isinstance(elem.tag, str):
                continue
            try:
                path = tree.getpath(elem)
                if elem.text:
                    cache[path] = str(elem.text)
            except (TypeError, ValueError):
                # Skip elements that can't be pathed
                continue

        return cache

    def _process_actions(
        self,
        actions: List[Any],
        left_tree: etree.ElementTree,
        right_tree: etree.ElementTree,
        result: CompareResult,
        options: CompareOptions,
        old_text_cache: Dict[str, str]
    ) -> None:
        """
        Process and classify xmldiff actions into result categories.
        
        Args:
            actions: List of xmldiff action objects
            left_tree: Original XML tree (may be mutated by xmldiff)
            right_tree: Revised XML tree
            result: CompareResult to populate
            options: Comparison options
            old_text_cache: Mapping of XPaths to original text values
        """
        for action in actions:
            if isinstance(action, UpdateTextIn):
                self._process_text_update(action, left_tree, right_tree, result, options, old_text_cache)
            elif isinstance(action, (InsertNode, DeleteNode, MoveNode, RenameNode)):
                if options.structure_changes:
                    self._process_structure_action(action, left_tree, right_tree, result)
            # Attribute actions are handled separately by AttributeComparator
            # but we count them here for statistics
            elif isinstance(action, (UpdateAttrib, InsertAttrib, DeleteAttrib)):
                result.statistics.attribute_changes += 1

        # Update total statistics
        result.statistics.text_changes = len(result.text_diffs)
        result.statistics.format_changes = len(result.format_diffs)
        result.statistics.added_nodes = sum(
            1 for d in result.structure_diffs if d.change_type == "added"
        )
        result.statistics.deleted_nodes = sum(
            1 for d in result.structure_diffs if d.change_type == "deleted"
        )
        result.statistics.moved_nodes = sum(
            1 for d in result.structure_diffs if d.change_type == "moved"
        )
        result.statistics.total_differences = (
            result.statistics.text_changes +
            result.statistics.format_changes +
            result.statistics.attribute_changes +
            len(result.structure_diffs)
        )

    def _process_text_update(
        self,
        action: UpdateTextIn,
        left_tree: etree.ElementTree,
        right_tree: etree.ElementTree,
        result: CompareResult,
        options: CompareOptions,
        old_text_cache: Dict[str, str]
    ) -> None:
        """
        Process UpdateTextIn action and classify as text or formatting.

        Formatting detection: if normalized text is the same but wrapper
        tag changed (e.g., italic → bold, sup → sub), it's a formatting change.

        Args:
            action: UpdateTextIn action from xmldiff
            left_tree: Original XML tree (may be mutated by xmldiff)
            right_tree: Revised XML tree
            result: CompareResult to populate
            options: Comparison options
            old_text_cache: Mapping of XPaths to original text values
        """
        path = self._normalize_xpath(action.node)

        # Get new text from action - ensure it's a proper Python string
        new_text = str(action.text) if action.text is not None else ""
        new_text = str(new_text)  # Ensure plain Python string, not Cython object

        # Get old text from cache (tree has been mutated by xmldiff) - ensure proper string
        old_text = old_text_cache.get(path, "")
        old_text = str(old_text)  # Ensure plain Python string, not Cython object

        # Check if this is a formatting-only change
        old_normalized = self._normalize_text(old_text)
        new_normalized = self._normalize_text(new_text)
        
        is_formatting = (
            old_normalized == new_normalized and
            old_normalized and  # Not empty
            self._is_formatting_tag_change(path, left_tree, right_tree)
        )
        
        if is_formatting:
            if options.formatting_only:
                old_tag, new_tag = self._get_tag_change_info(path, left_tree, right_tree)
                format_diff = FormatDiff(
                    path=path,
                    old_tag=old_tag or "unknown",
                    new_tag=new_tag or "unknown",
                    content=old_normalized,
                )
                result.format_diffs.append(format_diff)
        else:
            if options.text_corrections:
                # Generate inline diff using difflib
                inline_diff = self._generate_inline_diff(old_text, new_text)
                text_diff = TextDiff(
                    path=path,
                    old_text=old_text,
                    new_text=new_text,
                    inline_diff=inline_diff,
                )
                result.text_diffs.append(text_diff)

    def _process_structure_action(
        self,
        action: Any,
        left_tree: etree.ElementTree,
        right_tree: etree.ElementTree,
        result: CompareResult,
    ) -> None:
        """
        Process structural actions (InsertNode, DeleteNode, MoveNode, RenameNode).
        
        Args:
            action: Structural action from xmldiff
            left_tree: Original XML tree
            right_tree: Revised XML tree
            result: CompareResult to populate
        """
        if isinstance(action, InsertNode):
            path = self._normalize_xpath(action.target)
            tag = str(action.tag) if action.tag is not None else "unknown"
            preview = f"<{tag}>...</{tag}>"
            structure_diff = StructureDiff(
                path=path,
                change_type="added",
                element_tag=tag,
                element_preview=preview,
            )
            result.structure_diffs.append(structure_diff)
            
        elif isinstance(action, DeleteNode):
            path = self._normalize_xpath(action.node)
            element = self._get_element_by_path(left_tree, action.node)
            tag = str(element.tag) if element is not None else "unknown"
            preview = self._get_element_preview(element)
            structure_diff = StructureDiff(
                path=path,
                change_type="deleted",
                element_tag=tag.split("}")[-1] if "}" in tag else tag,
                element_preview=preview,
            )
            result.structure_diffs.append(structure_diff)
            
        elif isinstance(action, MoveNode):
            old_path = self._normalize_xpath(action.node)
            new_path = self._normalize_xpath(action.target)
            element = self._get_element_by_path(left_tree, action.node)
            tag = str(element.tag) if element is not None else "unknown"
            preview = self._get_element_preview(element)
            structure_diff = StructureDiff(
                path=new_path,
                change_type="moved",
                element_tag=tag.split("}")[-1] if "}" in tag else tag,
                element_preview=preview,
                old_path=old_path,
            )
            result.structure_diffs.append(structure_diff)
            
        elif isinstance(action, RenameNode):
            path = self._normalize_xpath(action.node)
            # Get new tag from action
            new_tag = str(action.tag) if action.tag is not None else "unknown"
            # Try to get old tag from action, or extract from element in tree
            old_tag = getattr(action, 'oldtag', None) or getattr(action, 'old_tag', None)
            
            # If not in action, get from element in left tree
            if old_tag is None:
                element = self._get_element_by_path(left_tree, action.node)
                if element is not None:
                    old_tag = str(element.tag)
                    old_tag = old_tag.split("}")[-1] if "}" in old_tag else old_tag
                else:
                    old_tag = "unknown"
            else:
                old_tag = str(old_tag)
            
            # Rename is both structural and formatting
            # Add as structure change
            element = self._get_element_by_path(left_tree, action.node)
            preview = self._get_element_preview(element)
            structure_diff = StructureDiff(
                path=path,
                change_type="renamed",
                element_tag=f"{old_tag} → {new_tag}",
                element_preview=preview,
            )
            result.structure_diffs.append(structure_diff)

    def _normalize_xpath(self, path: str) -> str:
        """
        Normalize XPath path to standard format.
        
        Ensures path starts with / and uses consistent indexing.
        xmldiff paths may or may not start with /.
        
        Args:
            path: Raw XPath from xmldiff
            
        Returns:
            Normalized XPath string
        """
        # Force to plain Python string to handle xmldiff/lxml Cython objects
        path = str(path) if path is not None else ""
        
        if not path:
            return "/"
        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path
        # Clean up any xmldiff-specific path notation
        path = path.replace("[1]", "[1]")  # Keep index notation consistent
        return path

    def _normalize_text(self, text: Optional[Any]) -> str:
        """
        Normalize text for comparison.
        
        Collapses whitespace and strips leading/trailing whitespace.
        Forces coercion to string to handle lxml/xmldiff cython objects.
        
        Args:
            text: Raw text content (may be lxml cython object)
            
        Returns:
            Normalized text string
        """
        if text is None:
            return ""
        # Force to plain Python string - handles lxml cython objects
        text_str = str(text)
        if not text_str:
            return ""
        # Collapse all whitespace to single spaces - ensure all parts are strings
        return " ".join(str(part) for part in text_str.split()).strip()

    def _is_formatting_tag_change(
        self,
        path: str,
        left_tree: etree.ElementTree,
        right_tree: etree.ElementTree,
    ) -> bool:
        """
        Check if text update represents a formatting tag change.
        
        Looks for tag changes like italic → bold, sup → sub, etc.
        
        Args:
            path: XPath to the element
            left_tree: Original XML tree
            right_tree: Revised XML tree
            
        Returns:
            True if tags differ at this path
        """
        left_elem = self._get_element_by_path(left_tree, path)
        right_elem = self._get_element_by_path(right_tree, path)
        
        if left_elem is None or right_elem is None:
            return False
        
        left_tag = str(left_elem.tag)
        right_tag = str(right_elem.tag)
        
        # Strip namespace if present
        left_tag = left_tag.split("}")[-1] if "}" in left_tag else left_tag
        right_tag = right_tag.split("}")[-1] if "}" in right_tag else right_tag
        
        return left_tag != right_tag

    def _get_tag_change_info(
        self,
        path: str,
        left_tree: etree.ElementTree,
        right_tree: etree.ElementTree,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Get old and new tag names for a formatting change.
        
        Args:
            path: XPath to the element
            left_tree: Original XML tree
            right_tree: Revised XML tree
            
        Returns:
            Tuple of (old_tag, new_tag)
        """
        left_elem = self._get_element_by_path(left_tree, path)
        right_elem = self._get_element_by_path(right_tree, path)
        
        def clean_tag(elem):
            if elem is None:
                return None
            tag = str(elem.tag)
            return tag.split("}")[-1] if "}" in tag else tag
        
        return clean_tag(left_elem), clean_tag(right_elem)

    def _get_element_by_path(
        self,
        tree: etree.ElementTree,
        path: str
    ) -> Optional[etree.Element]:
        """
        Get element from tree by path (with fallback).
        
        Handles xmldiff path format and converts to proper XPath.
        
        Args:
            tree: ElementTree to search
            path: Path from xmldiff action
            
        Returns:
            Element if found, None otherwise
        """
        # Normalize path
        xpath = self._normalize_xpath(path)
        
        try:
            elements = tree.xpath(xpath)
            if elements and len(elements) > 0:
                return elements[0]
        except etree.XPathError:
            pass
        
        return None

    def _get_old_text_from_tree(
        self,
        path: str,
        tree: etree.ElementTree
    ) -> str:
        """Get text content from an element in the tree by XPath.
        
        Args:
            path: XPath to the element
            tree: Element tree to search
            
        Returns:
            Text content of the element, or empty string if not found
        """
        try:
            elements = tree.xpath(path)
            if elements and len(elements) > 0:
                elem = elements[0]
                return str(elem.text) if elem.text is not None else ""
        except (etree.XPathError, AttributeError):
            pass
        return ""

    def _get_element_preview(self, element: Optional[etree.Element]) -> str:
        """
        Get a preview string of element content.
        
        Truncates long content for display purposes.
        
        Args:
            element: Element to preview
            
        Returns:
            String preview of element
        """
        if element is None:
            return ""
        
        tag = str(element.tag)
        tag = tag.split("}")[-1] if "}" in tag else tag
        
        text = self._normalize_text(element.text)
        if len(text) > 100:
            text = text[:97] + "..."
        
        if text:
            return f"<{tag}> {text} </{tag}>"
        return f"<{tag}>...</{tag}>"

    def _generate_inline_diff(self, old_text: str, new_text: str) -> str:
        """
        Generate inline diff highlighting using difflib.SequenceMatcher.
        
        Creates HTML with deleted text marked (strikethrough + red)
        and inserted text marked (bold + green).
        
        Args:
            old_text: Original text
            new_text: New text
            
        Returns:
            HTML string with inline diff highlighting
        """
        if not old_text and not new_text:
            return ""
        
        # Force to plain Python strings to handle lxml Cython objects
        old_text = str(old_text)
        new_text = str(new_text)
        
        matcher = difflib.SequenceMatcher(None, old_text, new_text)
        result = []
        
        for opcode, old_start, old_end, new_start, new_end in matcher.get_opcodes():
            if opcode == "equal":
                result.append(str(old_text[old_start:old_end]))
            elif opcode == "delete":
                deleted = str(old_text[old_start:old_end])
                result.append(f'<span class="diff-delete">{deleted}</span>')
            elif opcode == "insert":
                inserted = str(new_text[new_start:new_end])
                result.append(f'<span class="diff-insert">{inserted}</span>')
            elif opcode == "replace":
                deleted = str(old_text[old_start:old_end])
                inserted = str(new_text[new_start:new_end])
                result.append(f'<span class="diff-delete">{deleted}</span>')
                result.append(f'<span class="diff-insert">{inserted}</span>')
        
        return "".join(str(item) for item in result)

    def _calculate_match_percentage(self, stats: Any) -> float:
        """
        Calculate match percentage based on changes vs total nodes.
        
        Args:
            stats: CompareStatistics object
            
        Returns:
            Match percentage (0-100)
        """
        if stats.total_nodes == 0:
            return 100.0
        
        changed_nodes = (
            stats.text_changes +
            stats.format_changes +
            stats.attribute_changes +
            stats.added_nodes +
            stats.deleted_nodes +
            stats.moved_nodes
        )
        
        if changed_nodes == 0:
            return 100.0
        
        match_pct = (1 - (changed_nodes / stats.total_nodes)) * 100
        return max(0.0, min(100.0, round(match_pct, 1)))

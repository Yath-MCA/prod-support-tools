"""
AttributeComparator for XML comparison.

This module provides the AttributeComparator class that walks matched nodes
between two XML trees and compares their attributes, tracking changes to
important attributes like id, rid, href, xlink:href, content-type, and class.
"""

import re
from typing import List, Optional, Set, Dict, Tuple, Any
from lxml import etree

from .models import (
    CompareOptions,
    AttributeDiff,
    CompareResult,
)
from .parser_service import XMLParserService


class AttributeComparator:
    """
    Comparator for XML element attributes.
    
    Walks matched nodes (by XPath) between two XML trees and compares their
    attributes. This is an expensive operation that should only be run when
    explicitly enabled via CompareOptions.include_attributes.
    
    Tracks changes to important attributes commonly used in XML documents:
    - id: Element identifiers
    - rid: Reference identifiers (e.g., in xref elements)
    - href: Hyperlinks
    - xlink:href: XLink hyperlinks
    - content-type: Content type classification
    - class: CSS/styling classes
    
    Attributes:
        parser_service: Service for XML parsing and XPath operations
        important_attributes: Set of attribute names to track specifically
    """

    # Attributes that are commonly significant in XML documents
    IMPORTANT_ATTRIBUTES: Set[str] = {
        "id",
        "rid",
        "href",
        "xlink:href",
        "content-type",
        "contentType",  # Alternative casing
        "class",
        "style",
        "type",
        "name",
        "ref-type",
        "refType",  # Alternative casing
        "symbol",
        "alt",
        "title",
        "lang",
        "xml:lang",
        "xmlns",
        "xmlns:xlink",
    }

    def __init__(self):
        """Initialize the AttributeComparator with a parser service."""
        self.parser_service = XMLParserService()

    def compare_attributes(
        self,
        left_tree: etree.ElementTree,
        right_tree: etree.ElementTree,
        options: CompareOptions,
    ) -> List[AttributeDiff]:
        """
        Compare attributes between two XML trees.
        
        This method walks all elements in both trees by XPath and compares
        their attributes. Only runs if options.include_attributes is True.
        
        Args:
            left_tree: Original XML tree
            right_tree: Revised XML tree
            options: Comparison options (must have include_attributes=True)
            
        Returns:
            List of AttributeDiff objects representing attribute changes
            
        Raises:
            ValueError: If options.include_attributes is False
        """
        if not options.include_attributes:
            raise ValueError(
                "Attribute comparison is disabled. "
                "Set include_attributes=True to enable."
            )

        diffs: List[AttributeDiff] = []

        # Build XPath-indexed dictionaries for both trees
        left_elements = self._index_elements_by_xpath(left_tree)
        right_elements = self._index_elements_by_xpath(right_tree)

        # Get all unique paths from both trees
        all_paths = set(left_elements.keys()) | set(right_elements.keys())

        for path in all_paths:
            left_elem = left_elements.get(path)
            right_elem = right_elements.get(path)

            # Skip if either element doesn't exist (structural change, not attribute)
            if left_elem is None or right_elem is None:
                continue

            # Compare attributes on this matched pair
            path_diffs = self._compare_element_attributes(
                path, left_elem, right_elem
            )
            diffs.extend(path_diffs)

        return diffs

    def compare_and_update_result(
        self,
        left_tree: etree.ElementTree,
        right_tree: etree.ElementTree,
        result: CompareResult,
    ) -> None:
        """
        Compare attributes and update a CompareResult in place.
        
        Convenience method that runs attribute comparison and populates
        the result object directly.
        
        Args:
            left_tree: Original XML tree
            right_tree: Revised XML tree
            result: CompareResult to update with attribute differences
        """
        if not result.options.include_attributes:
            return

        attribute_diffs = self.compare_attributes(
            left_tree, right_tree, result.options
        )
        result.attribute_diffs = attribute_diffs
        result.statistics.attribute_changes = len(attribute_diffs)
        result.statistics.total_differences = (
            result.statistics.text_changes +
            result.statistics.format_changes +
            result.statistics.attribute_changes +
            len(result.structure_diffs)
        )

    def _index_elements_by_xpath(
        self,
        tree: etree.ElementTree
    ) -> Dict[str, etree.Element]:
        """
        Index all elements in tree by their XPath.
        
        Creates a dictionary mapping XPath strings to elements for
        efficient lookup during comparison.
        
        Args:
            tree: ElementTree to index
            
        Returns:
            Dictionary of xpath -> element
        """
        index: Dict[str, etree.Element] = {}
        root = tree.getroot()
        
        # Build index recursively
        self._build_index_recursive(root, "", index, tree)
        
        return index

    def _build_index_recursive(
        self,
        element: etree.Element,
        parent_path: str,
        index: Dict[str, etree.Element],
        tree: etree.ElementTree,
    ) -> None:
        """
        Recursively build XPath index for elements.
        
        Args:
            element: Current element to process
            parent_path: XPath of parent element
            index: Dictionary to populate
            tree: ElementTree (for namespace handling)
        """
        # Get tag without namespace
        tag = element.tag
        if isinstance(tag, str):
            tag = tag.split("}")[-1] if "}" in tag else tag
        else:
            # Processing instruction or comment
            tag = str(tag)

        # Build position-based path
        position = self._get_element_position(element, parent_path, tree)
        if parent_path:
            path = f"{parent_path}/{tag}[{position}]"
        else:
            path = f"/{tag}[{position}]"

        # Normalize and store
        normalized_path = self._normalize_xpath(path)
        index[normalized_path] = element

        # Process children
        for child in element:
            self._build_index_recursive(child, path, index, tree)

    def _get_element_position(
        self,
        element: etree.Element,
        parent_path: str,
        tree: etree.ElementTree,
    ) -> int:
        """
        Get the 1-based position of element among siblings with same tag.
        
        Args:
            element: Element to find position for
            parent_path: XPath of parent
            tree: ElementTree context
            
        Returns:
            1-based position index
        """
        parent = element.getparent()
        if parent is None:
            return 1

        # Get tag without namespace
        tag = element.tag
        if isinstance(tag, str):
            tag = tag.split("}")[-1] if "}" in tag else tag
        else:
            return 1

        # Count siblings with same tag before this element
        position = 1
        for sibling in parent:
            if sibling is element:
                return position
            sibling_tag = sibling.tag
            if isinstance(sibling_tag, str):
                sibling_tag = sibling_tag.split("}")[-1] if "}" in sibling_tag else sibling_tag
            if sibling_tag == tag:
                position += 1

        return position

    def _compare_element_attributes(
        self,
        path: str,
        left_elem: etree.Element,
        right_elem: etree.Element,
    ) -> List[AttributeDiff]:
        """
        Compare attributes between two matched elements.
        
        Detects: modified attributes, added attributes, deleted attributes.
        
        Args:
            path: XPath to the elements
            left_elem: Original element
            right_elem: Revised element
            
        Returns:
            List of AttributeDiff objects for this element pair
        """
        diffs: List[AttributeDiff] = []

        # Get tag name
        tag = left_elem.tag
        if isinstance(tag, str):
            tag = tag.split("}")[-1] if "}" in tag else tag
        else:
            tag = "unknown"

        # Get all attribute names from both elements
        left_attrs = {str(k): str(v) if v is not None else "" for k, v in left_elem.attrib.items()}
        right_attrs = {str(k): str(v) if v is not None else "" for k, v in right_elem.attrib.items()}

        all_attr_names = set(left_attrs.keys()) | set(right_attrs.keys())

        for attr_name in all_attr_names:
            attr_name = str(attr_name)  # Ensure string
            left_val = left_attrs.get(attr_name)
            right_val = right_attrs.get(attr_name)

            # Skip if values are the same (or both None)
            if left_val == right_val:
                continue

            # Create diff record
            attr_diff = AttributeDiff(
                path=path,
                element_tag=tag,
                attribute_name=attr_name,
                old_value=left_val,
                new_value=right_val,
            )
            diffs.append(attr_diff)

        return diffs

    def _normalize_xpath(self, path: str) -> str:
        """
        Normalize XPath to standard format.
        
        Ensures path starts with / and uses consistent indexing format.
        
        Args:
            path: Raw XPath string
            
        Returns:
            Normalized XPath
        """
        # Force to plain Python string to handle xmldiff/lxml Cython objects
        path = str(path) if path is not None else ""
        
        if not path:
            return "/"
        
        # Ensure leading /
        if not path.startswith("/"):
            path = "/" + path
        
        # Remove duplicate slashes
        path = re.sub(r"/+", "/", path)
        
        # Ensure [1] is explicit for elements without index
        # This is complex, so we keep the format as-is from lxml
        
        return path

    def is_important_attribute(self, attr_name: str) -> bool:
        """
        Check if an attribute is considered important/significant.
        
        Args:
            attr_name: Name of the attribute
            
        Returns:
            True if attribute is in the important set
        """
        return attr_name in self.IMPORTANT_ATTRIBUTES

    def get_attribute_summary(self, diffs: List[AttributeDiff]) -> Dict[str, int]:
        """
        Get summary statistics of attribute changes.
        
        Args:
            diffs: List of AttributeDiff objects
            
        Returns:
            Dictionary mapping attribute names to change counts
        """
        summary: Dict[str, int] = {}
        for diff in diffs:
            summary[diff.attribute_name] = summary.get(diff.attribute_name, 0) + 1
        return summary

    def filter_important_diffs(
        self,
        diffs: List[AttributeDiff]
    ) -> List[AttributeDiff]:
        """
        Filter diffs to only include important attributes.
        
        Args:
            diffs: List of all AttributeDiff objects
            
        Returns:
            Filtered list with only important attributes
        """
        return [
            d for d in diffs
            if self.is_important_attribute(d.attribute_name)
        ]

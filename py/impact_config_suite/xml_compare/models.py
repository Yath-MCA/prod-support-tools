"""
Data models for XML comparison.

This module contains dataclasses for configuration options, diff results,
and comparison statistics used throughout the xml_compare package.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Dict, Any


class DiffType(Enum):
    """Classification of difference types."""
    TEXT = auto()
    FORMATTING = auto()
    ATTRIBUTE = auto()
    STRUCTURE = auto()


@dataclass
class CompareOptions:
    """
    Configuration options for XML comparison.
    
    Attributes:
        text_corrections: Include text corrections in comparison
        formatting_only: Include formatting changes detection
        full_compare: Include all comparison details
        include_attributes: Run attribute level comparison (expensive)
        structure_changes: Detect structure changes (add/delete/move)
        generate_statistics: Generate statistics dashboard
        fast_match: Use fast matching for large files (>50MB)
    """
    text_corrections: bool = True
    formatting_only: bool = True
    full_compare: bool = True
    include_attributes: bool = False
    structure_changes: bool = True
    generate_statistics: bool = True
    fast_match: bool = False


@dataclass
class TextDiff:
    """
    Represents a text content difference.
    
    Attributes:
        path: XPath to the element
        old_text: Original text content
        new_text: Revised text content
        inline_diff: Optional inline diff highlighting
    """
    path: str
    old_text: str
    new_text: str
    inline_diff: Optional[str] = None


@dataclass
class FormatDiff:
    """
    Represents a formatting change (tag/style change without text change).
    
    Attributes:
        path: XPath to the element
        old_tag: Original tag name
        new_tag: New tag name
        content: Text content (unchanged)
        old_style: Original style attributes
        new_style: New style attributes
    """
    path: str
    old_tag: str
    new_tag: str
    content: str
    old_style: Optional[str] = None
    new_style: Optional[str] = None


@dataclass
class AttributeDiff:
    """
    Represents an attribute change on an element.
    
    Attributes:
        path: XPath to the element
        element_tag: Tag name of the element
        attribute_name: Name of the changed attribute
        old_value: Original attribute value
        new_value: New attribute value
    """
    path: str
    element_tag: str
    attribute_name: str
    old_value: Optional[str]
    new_value: Optional[str]


@dataclass
class StructureDiff:
    """
    Represents a structural change (insert, delete, move).
    
    Attributes:
        path: XPath to the element
        change_type: Type of structural change ('added', 'deleted', 'moved')
        element_tag: Tag name of the element
        element_preview: Preview of element content
        old_path: Original path (for moves)
    """
    path: str
    change_type: str  # 'added', 'deleted', 'moved'
    element_tag: str
    element_preview: str
    old_path: Optional[str] = None


@dataclass
class CompareStatistics:
    """
    Statistics about the comparison.
    
    Attributes:
        total_differences: Total number of differences found
        text_changes: Count of text corrections
        format_changes: Count of formatting changes
        attribute_changes: Count of attribute modifications
        added_nodes: Count of added nodes
        deleted_nodes: Count of deleted nodes
        moved_nodes: Count of moved nodes
        total_nodes: Total nodes in the document
        match_percentage: Calculated match percentage
    """
    total_differences: int = 0
    text_changes: int = 0
    format_changes: int = 0
    attribute_changes: int = 0
    added_nodes: int = 0
    deleted_nodes: int = 0
    moved_nodes: int = 0
    total_nodes: int = 0
    match_percentage: float = 100.0


@dataclass
class CompareResult:
    """
    Complete result of an XML comparison.
    
    Attributes:
        original_path: Path to original XML file
        revised_path: Path to revised XML file
        generated_time: Timestamp of comparison
        text_diffs: List of text differences
        format_diffs: List of formatting differences
        attribute_diffs: List of attribute differences
        structure_diffs: List of structural differences
        statistics: Comparison statistics
        options: Options used for this comparison
    """
    original_path: Path
    revised_path: Path
    generated_time: datetime = field(default_factory=datetime.now)
    text_diffs: List[TextDiff] = field(default_factory=list)
    format_diffs: List[FormatDiff] = field(default_factory=list)
    attribute_diffs: List[AttributeDiff] = field(default_factory=list)
    structure_diffs: List[StructureDiff] = field(default_factory=list)
    statistics: CompareStatistics = field(default_factory=CompareStatistics)
    options: CompareOptions = field(default_factory=CompareOptions)

    def get_all_diffs(self) -> List[Any]:
        """Return all diffs combined as a single list."""
        return (
            self.text_diffs +
            self.format_diffs +
            self.attribute_diffs +
            self.structure_diffs
        )

"""
XML Parser Service with entity handling.

This module provides XML parsing functionality with proper handling
of HTML entities and malformed XML for robust comparison.
"""

import html as html_lib
import re
from pathlib import Path
from typing import Optional, Tuple

from lxml import etree


class XMLParserService:
    """
    Service for parsing XML files with entity handling.
    
    Handles HTML named entities (like &rsquo;) and escapes stray ampersands
    to ensure lxml can parse files that may contain HTML-isms.
    """

    @staticmethod
    def parse_xml_with_entity_handling(xml_path: Path) -> etree.ElementTree:
        """
        Read XML as text and safely handle HTML named entities.
        
        Converts HTML named entities to Unicode characters and escapes
        stray '&' characters that are not valid XML entities.
        
        Args:
            xml_path: Path to the XML file to parse
            
        Returns:
            ElementTree: Parsed XML tree
            
        Raises:
            etree.XMLSyntaxError: If XML cannot be parsed even with recovery
            FileNotFoundError: If the file does not exist
        """
        if not xml_path.exists():
            raise FileNotFoundError(f"XML file not found: {xml_path}")
        
        raw = xml_path.read_text(encoding="utf-8", errors="replace")
        
        # Convert HTML named entities to Unicode chars (e.g., &rsquo; -> ')
        raw = html_lib.unescape(raw)
        
        # Escape stray '&' that are not valid XML entities
        # Keep only XML 5 predefined entities untouched: amp, lt, gt, quot, apos
        raw = re.sub(
            r"&(?!(amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;))",
            "&amp;",
            raw
        )
        
        parser = etree.XMLParser(recover=True, remove_blank_text=False)
        root = etree.fromstring(raw.encode("utf-8"), parser=parser)
        return etree.ElementTree(root)

    @staticmethod
    def get_file_size_mb(xml_path: Path) -> float:
        """
        Get file size in megabytes.
        
        Args:
            xml_path: Path to the file
            
        Returns:
            float: Size in MB
        """
        return xml_path.stat().st_size / (1024 * 1024)

    @staticmethod
    def is_large_file(xml_path: Path, threshold_mb: float = 50.0) -> bool:
        """
        Check if file exceeds size threshold for fast matching.
        
        Args:
            xml_path: Path to the file
            threshold_mb: Size threshold in MB (default 50)
            
        Returns:
            bool: True if file is larger than threshold
        """
        return XMLParserService.get_file_size_mb(xml_path) > threshold_mb

    @staticmethod
    def count_nodes(tree: etree.ElementTree) -> int:
        """
        Count total nodes in XML tree.
        
        Args:
            tree: ElementTree to count nodes in
            
        Returns:
            int: Total number of elements
        """
        return len(tree.xpath("//*"))

    @staticmethod
    def parse_both_files(
        original_path: Path,
        revised_path: Path
    ) -> Tuple[etree.ElementTree, etree.ElementTree]:
        """
        Parse both original and revised XML files.
        
        Args:
            original_path: Path to original XML
            revised_path: Path to revised XML
            
        Returns:
            Tuple of (original_tree, revised_tree)
        """
        left_tree = XMLParserService.parse_xml_with_entity_handling(original_path)
        right_tree = XMLParserService.parse_xml_with_entity_handling(revised_path)
        return left_tree, right_tree

    @staticmethod
    def get_element_by_xpath(
        tree: etree.ElementTree,
        xpath: str
    ) -> Optional[etree.Element]:
        """
        Safely get element by XPath.
        
        Args:
            tree: ElementTree to search
            xpath: XPath expression
            
        Returns:
            Element if found, None otherwise
        """
        try:
            elements = tree.xpath(xpath)
            if elements and len(elements) > 0:
                return elements[0]
        except etree.XPathError:
            pass
        return None

    @staticmethod
    def get_normalized_text(element: etree.Element) -> str:
        """
        Get normalized text content from element.
        
        Normalizes whitespace and concatenates all text content.
        
        Args:
            element: Element to extract text from
            
        Returns:
            Normalized text string
        """
        if element is None:
            return ""
        text = etree.tostring(element, method="text", encoding="unicode")
        # Normalize whitespace
        text = " ".join(text.split())
        return text.strip()

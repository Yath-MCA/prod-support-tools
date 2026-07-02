#!/usr/bin/env python3
"""
Test script to verify Cython object handling in xml_compare.

This script tests the fixes for the "expected str instance, _cython_3_1_4.cython_function_or_method found" error.
"""

import sys
from pathlib import Path
from xml_compare.parser_service import XMLParserService
from xml_compare.diff_engine import DiffEngine
from xml_compare.models import CompareOptions
import tempfile

# Create test XML files
test_xml1 = """<?xml version="1.0" encoding="UTF-8"?>
<root>
    <element id="1">Original text content</element>
    <element id="2">Another element with <!-- comment --> embedded</element>
    <element id="3">
        Text with   multiple   spaces
        and newlines
    </element>
</root>
"""

test_xml2 = """<?xml version="1.0" encoding="UTF-8"?>
<root>
    <element id="1">Modified text content</element>
    <element id="2">Another element with updated content</element>
    <element id="3">
        Text with single spaces
        and newlines preserved
    </element>
</root>
"""

def test_comparison():
    """Run comparison test to validate the fixes."""
    print("Testing XML comparison with Cython object handling...")
    
    try:
        # Create temporary XML files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            xml1_path = tmppath / "test1.xml"
            xml2_path = tmppath / "test2.xml"
            
            xml1_path.write_text(test_xml1)
            xml2_path.write_text(test_xml2)
            
            print(f"Created test files: {xml1_path}, {xml2_path}")
            
            # Initialize comparison components
            options = CompareOptions(
                text_corrections=True,
                formatting_only=True,
                full_compare=True,
                include_attributes=False,
                structure_changes=True,
                generate_statistics=True
            )
            
            # Run comparison
            diff_engine = DiffEngine()
            print("\nRunning comparison...")
            result = diff_engine.diff(xml1_path, xml2_path, options)
            
            # Print results
            print(f"\n✓ Comparison completed successfully!")
            print(f"  - Total differences: {result.statistics.total_differences}")
            print(f"  - Text changes: {result.statistics.text_changes}")
            print(f"  - Format changes: {result.statistics.format_changes}")
            print(f"  - Text diffs found: {len(result.text_diffs)}")
            
            # Print details of text diffs
            if result.text_diffs:
                print(f"\n  Text Differences:")
                for i, diff in enumerate(result.text_diffs, 1):
                    print(f"    {i}. Path: {diff.path}")
                    print(f"       Old: {diff.old_text[:50]}...")
                    print(f"       New: {diff.new_text[:50]}...")
                    if diff.inline_diff:
                        print(f"       Inline diff exists: {len(diff.inline_diff)} chars")
            
            print("\n✓ All tests passed! The Cython object handling fix is working correctly.")
            return True
            
    except Exception as e:
        print(f"\n✗ Test failed with error:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_comparison()
    sys.exit(0 if success else 1)

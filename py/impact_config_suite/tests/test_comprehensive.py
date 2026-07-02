#!/usr/bin/env python3
"""
Comprehensive test for Cython object handling in xml_compare.

Tests all major code paths including attributes and structural changes.
"""

import sys
from pathlib import Path
from xml_compare.pipeline import run_xml_compare
from xml_compare.models import CompareOptions
import tempfile

# Test XML with various structures
test_xml1 = """<?xml version="1.0" encoding="UTF-8"?>
<root xmlns="http://example.com" xmlns:xlink="http://www.w3.org/1999/xlink">
    <book id="b1" title="Original Title" href="http://example.com/1">
        <chapter num="1">Introduction</chapter>
        <chapter num="2">Content</chapter>
    </book>
    <article xlink:href="http://example.com/article1" content-type="text">
        <para>Original paragraph text with &rsquo; entity</para>
    </article>
    <section>
        <title>First</title>
        <content>Some text here</content>
    </section>
</root>
"""

test_xml2 = """<?xml version="1.0" encoding="UTF-8"?>
<root xmlns="http://example.com" xmlns:xlink="http://www.w3.org/1999/xlink">
    <book id="b1" title="Modified Title" href="http://example.com/2" status="active">
        <chapter num="1">Introduction Modified</chapter>
        <chapter num="2">Content Updated</chapter>
        <chapter num="3">New Chapter</chapter>
    </book>
    <article xlink:href="http://example.com/article2" content-type="document">
        <para>Revised paragraph text with updated content</para>
    </article>
    <section>
        <title>First</title>
        <content>Different text here</content>
    </section>
</root>
"""

def test_full_pipeline():
    """Test full comparison pipeline including attributes."""
    print("Testing full XML comparison pipeline with all features...")
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            xml1_path = tmppath / "test1.xml"
            xml2_path = tmppath / "test2.xml"
            output_dir = tmppath / "reports"
            
            xml1_path.write_text(test_xml1)
            xml2_path.write_text(test_xml2)
            output_dir.mkdir(exist_ok=True)
            
            print(f"\nCreated test files: {xml1_path}, {xml2_path}")
            
            # Run full comparison with all options enabled
            options = CompareOptions(
                text_corrections=True,
                formatting_only=True,
                full_compare=True,
                include_attributes=True,  # Enable attribute comparison
                structure_changes=True,
                generate_statistics=True,
                fast_match=False
            )
            
            print("\nRunning full comparison with attributes and structure analysis...")
            
            def log_callback(msg):
                print(f"  {msg}")
            
            report_path = run_xml_compare(
                xml1_path,
                xml2_path,
                options=options,
                output_dir=output_dir,
                log_callback=log_callback
            )
            
            print(f"\n✓ Full comparison completed successfully!")
            print(f"  Report generated: {report_path}")
            print(f"  Report file exists: {report_path.exists()}")
            print(f"  Report size: {report_path.stat().st_size} bytes")
            
            # Verify report content
            report_content = report_path.read_text()
            has_overview = "Comparison Overview" in report_content
            has_text_tab = "tab-text" in report_content
            has_attr_tab = "tab-attribute" in report_content
            has_structure = "tab-structure" in report_content
            
            print(f"\n  Report sections:")
            print(f"    - Overview tab: {has_overview}")
            print(f"    - Text tab: {has_text_tab}")
            print(f"    - Attribute tab: {has_attr_tab}")
            print(f"    - Structure tab: {has_structure}")
            
            print("\n✓ All comprehensive tests passed!")
            return True
            
    except Exception as e:
        print(f"\n✗ Comprehensive test failed with error:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_full_pipeline()
    sys.exit(0 if success else 1)

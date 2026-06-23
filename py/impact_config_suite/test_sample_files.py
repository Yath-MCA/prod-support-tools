#!/usr/bin/env python3
"""
Test comparison on real XML files from run_sample directory.
"""

import sys
from pathlib import Path
from xml_compare.pipeline import run_xml_compare
from xml_compare.models import CompareOptions
from xml_compare.diff_engine import DiffEngine

def test_sample_files():
    """Run comparison on actual sample XML files."""
    
    # File paths
    sample_dir = Path("run_sample")
    original = sample_dir / "Input_Testing_Newgen.xml"
    revised = sample_dir / "Ouput_Testing_Newgen.xml"
    output_dir = sample_dir / "reports"
    
    # Verify files exist
    if not original.exists():
        print(f"❌ File not found: {original}")
        return False
    if not revised.exists():
        print(f"❌ File not found: {revised}")
        return False
    
    print("=" * 80)
    print("XML COMPARISON TEST - REAL SAMPLE FILES")
    print("=" * 80)
    
    print(f"\n📄 Input Files:")
    print(f"   Original: {original.name} ({original.stat().st_size} bytes)")
    print(f"   Revised:  {revised.name} ({revised.stat().st_size} bytes)")
    
    try:
        # Create output directory
        output_dir.mkdir(exist_ok=True)
        
        # Test with comprehensive options
        options = CompareOptions(
            text_corrections=True,
            formatting_only=True,
            include_attributes=True,
            structure_changes=True,
            generate_statistics=True
        )
        
        print(f"\n🔍 Running comparison...")
        print(f"   Text corrections: {options.text_corrections}")
        print(f"   Formatting changes: {options.formatting_only}")
        print(f"   Attributes: {options.include_attributes}")
        print(f"   Structure changes: {options.structure_changes}")
        
        def log_callback(msg):
            print(f"   → {msg}")
        
        # Run the comparison
        report_path = run_xml_compare(
            original,
            revised,
            options=options,
            output_dir=output_dir,
            log_callback=log_callback
        )
        
        print(f"\n✅ Comparison completed successfully!")
        print(f"\n📊 Report Generated:")
        print(f"   Path: {report_path}")
        print(f"   Size: {report_path.stat().st_size:,} bytes")
        print(f"   Exists: {report_path.exists()}")
        
        # Read and analyze report content
        report_content = report_path.read_text(encoding="utf-8")
        
        # Extract statistics from report (basic parsing)
        print(f"\n📋 Report Content Analysis:")
        sections = {
            "HTML structure": "<!DOCTYPE" in report_content or "<html" in report_content,
            "Overview section": "Overview" in report_content,
            "Text changes": "text" in report_content.lower(),
            "Formatting changes": "format" in report_content.lower(),
            "Structure changes": "struct" in report_content.lower(),
            "Attribute changes": "attribut" in report_content.lower(),
        }
        
        for section, found in sections.items():
            status = "✓" if found else "✗"
            print(f"   {status} {section}")
        
        # Try to get diff statistics from the diff engine directly
        print(f"\n📈 Detailed Statistics:")
        try:
            diff_engine = DiffEngine()
            result = diff_engine.diff(original, revised, options)
            
            print(f"   Total differences: {result.statistics.total_differences}")
            print(f"   Text changes: {len(result.text_diffs)}")
            print(f"   Format changes: {len(result.format_diffs)}")
            print(f"   Attribute changes: {len(result.attribute_diffs)}")
            print(f"   Structure changes: {len(result.structure_diffs)}")
            print(f"   Total nodes (combined): {result.statistics.total_nodes}")
            print(f"   Match percentage: {result.statistics.match_percentage:.1f}%")
            
            if result.text_diffs:
                print(f"\n   📝 Text Differences ({len(result.text_diffs)} total):")
                for i, diff in enumerate(result.text_diffs[:5], 1):
                    old_preview = diff.old_text[:60].replace('\n', ' ')
                    new_preview = diff.new_text[:60].replace('\n', ' ')
                    print(f"      {i}. {diff.path}")
                    print(f"         Old: {old_preview}...")
                    print(f"         New: {new_preview}...")
                    if i >= 5 and len(result.text_diffs) > 5:
                        print(f"      ... and {len(result.text_diffs) - 5} more")
                        break
            
            if result.attribute_diffs:
                print(f"\n   🏷️  Attribute Differences ({len(result.attribute_diffs)} total):")
                for i, diff in enumerate(result.attribute_diffs[:5], 1):
                    print(f"      {i}. {diff.path} - {diff.attribute_name}")
                    print(f"         Old: {diff.old_value}")
                    print(f"         New: {diff.new_value}")
                    if i >= 5 and len(result.attribute_diffs) > 5:
                        print(f"      ... and {len(result.attribute_diffs) - 5} more")
                        break
            
            if result.structure_diffs:
                print(f"\n   🔧 Structure Changes ({len(result.structure_diffs)} total):")
                for i, diff in enumerate(result.structure_diffs[:5], 1):
                    print(f"      {i}. {diff.path} - {diff.change_type}")
                    print(f"         Element: {diff.element_tag}")
                    if i >= 5 and len(result.structure_diffs) > 5:
                        print(f"      ... and {len(result.structure_diffs) - 5} more")
                        break
        
        except Exception as e:
            print(f"   Note: Could not extract detailed stats: {e}")
        
        print(f"\n" + "=" * 80)
        print(f"✅ TEST COMPLETE - NO CYTHON ERRORS!")
        print(f"=" * 80)
        
        # Show report path for opening
        print(f"\n💡 To view the report:")
        print(f"   start {report_path}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sample_files()
    sys.exit(0 if success else 1)

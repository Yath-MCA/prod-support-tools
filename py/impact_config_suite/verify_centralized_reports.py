#!/usr/bin/env python3
"""
Verify that XML comparison reports are saved to centralized location.
"""

from pathlib import Path
from xml_compare.pipeline import run_xml_compare
from xml_compare.models import CompareOptions
from core.run_history import RunHistoryStore

def verify_centralized_storage():
    """Test XML comparison with default output directory (centralized location)."""
    
    # File paths
    sample_dir = Path("run_sample")
    original = sample_dir / "Input_Testing_Newgen.xml"
    revised = sample_dir / "Ouput_Testing_Newgen.xml"
    
    # Verify files exist
    if not original.exists() or not revised.exists():
        print("❌ Sample files not found")
        return False
    
    print("=" * 80)
    print("CENTRALIZED REPORT STORAGE VERIFICATION")
    print("=" * 80)
    
    # Show centralized directory
    centralized_dir = RunHistoryStore.base_dir() / "xml_compare_reports"
    print(f"\n📁 Centralized Storage Location:")
    print(f"   {centralized_dir}")
    
    print(f"\n📄 Sample Files:")
    print(f"   Original: {original.name} ({original.stat().st_size} bytes)")
    print(f"   Revised:  {revised.name} ({revised.stat().st_size} bytes)")
    
    try:
        options = CompareOptions(
            text_corrections=True,
            formatting_only=True,
            include_attributes=True,
            structure_changes=True
        )
        
        print(f"\n🔍 Running comparison (NO explicit output_dir)...")
        print(f"   Expected to use: {centralized_dir}")
        
        def log_callback(msg):
            print(f"   → {msg}")
        
        # Run WITHOUT specifying output_dir - should use centralized location
        report_path = run_xml_compare(
            original,
            revised,
            options=options,
            log_callback=log_callback
        )
        
        print(f"\n✅ Report Generated:")
        print(f"   Path: {report_path}")
        print(f"   Size: {report_path.stat().st_size:,} bytes")
        print(f"   Exists: {report_path.exists()}")
        
        # Verify it's in the centralized location
        if str(report_path).startswith(str(centralized_dir)):
            print(f"\n✅ SUCCESS - Report stored in centralized location!")
            print(f"   Parent directory: {report_path.parent}")
            return True
        else:
            print(f"\n❌ ERROR - Report NOT in centralized location!")
            print(f"   Expected: {centralized_dir}")
            print(f"   Got:      {report_path.parent}")
            return False
            
    except Exception as e:
        print(f"\n❌ Comparison failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_centralized_storage()
    exit(0 if success else 1)

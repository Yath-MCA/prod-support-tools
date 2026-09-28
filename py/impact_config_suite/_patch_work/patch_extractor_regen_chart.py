from pathlib import Path

p = Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite\core\contrib_extractor.py")
text = p.read_text(encoding="utf-8")

# bump SCRIPT_VERSION 12 -> 13
if "SCRIPT_VERSION = 12" not in text:
    raise SystemExit(f"unexpected SCRIPT_VERSION line")
text = text.replace("SCRIPT_VERSION = 12", "SCRIPT_VERSION = 13", 1)

# add import after contrib_phase0 import block
old_imp = """from core.contrib_phase0 import (
    OUT_COMPARE_HTML,
    OUT_XML_ORIGINAL,
    OUT_XML_ORIGINAL_CLEAN,
    OUT_XML_REGEN,
    OUT_XML_STRIP_PI,
    write_phase0_chain,
)
from core import contrib_aff as _contrib_aff
"""
new_imp = """from core.contrib_phase0 import (
    OUT_COMPARE_HTML,
    OUT_XML_ORIGINAL,
    OUT_XML_ORIGINAL_CLEAN,
    OUT_XML_REGEN,
    OUT_XML_STRIP_PI,
    write_phase0_chain,
)
from core import contrib_aff as _contrib_aff
from core.contrib_regen_compare import (
    collect_compare_rows_from_folders,
    write_batch_regen_compare_report,
)
"""
if "from core.contrib_regen_compare import" not in text:
    if old_imp not in text:
        raise SystemExit("import block not found")
    text = text.replace(old_imp, new_imp, 1)

# Wire batch report after issues csv / before PATHS summary
# Find the block after write_issues_csv
marker = '    csv_out = write_issues_csv(client, shortcode, entries, good, report_dir)\n'
if marker not in text:
    raise SystemExit("csv_out marker not found")

insert = '''    csv_out = write_issues_csv(client, shortcode, entries, good, report_dir)

    # Batch regen/compare KPI + cause-chart report (lightweight equality until slot compare)
    regen_compare_out = None
    try:
        cmp_rows = collect_compare_rows_from_folders(good, report_dir=report_dir)
        # Include docs that failed to yield contribs as processing-error rows when folder exists
        failed_rows = [r for r in rows if not r.get("contribs") and r.get("folder")]
        if failed_rows:
            cmp_rows.extend(collect_compare_rows_from_folders(failed_rows, report_dir=report_dir))
        regen_compare_out = write_batch_regen_compare_report(
            client, shortcode, cmp_rows, report_dir
        )
        log(f"[OK] regen_compare={regen_compare_out}")
    except Exception as e:
        log(f"[WARN] regen_compare report skipped: {e}")

'''

if "regen_compare_out = write_batch_regen_compare_report" not in text:
    text = text.replace(marker, insert, 1)

# Add to path_bits and return dict
old_paths = '''    path_bits = [f"contrib={path_for_meta(out)}"]
    if elements_out:
        path_bits.append(f"elements={path_for_meta(elements_out)}")
    path_bits.append(f"issues={path_for_meta(csv_out)}")
'''
new_paths = '''    path_bits = [f"contrib={path_for_meta(out)}"]
    if elements_out:
        path_bits.append(f"elements={path_for_meta(elements_out)}")
    path_bits.append(f"issues={path_for_meta(csv_out)}")
    if regen_compare_out:
        path_bits.append(f"regen_compare={path_for_meta(regen_compare_out)}")
'''
if "regen_compare={path_for_meta(regen_compare_out)}" not in text:
    if old_paths not in text:
        raise SystemExit("path_bits block not found")
    text = text.replace(old_paths, new_paths, 1)

# Add regen_compare_report to return dict (success path)
old_ret = '''        "aff_unique_report": path_for_meta(aff_unique_out) if aff_unique_out else None,
'''
# There may be two return dicts - cancelled and success. Only success has issues_csv nearby.
# Find success return more specifically
success_anchor = '''        "issues_csv": path_for_meta(csv_out),
        "aff_report": path_for_meta(aff_out) if aff_out else None,
        "aff_csv": path_for_meta(aff_csv_out) if aff_csv_out else None,
        "aff_unique_report": path_for_meta(aff_unique_out) if aff_unique_out else None,
'''
success_new = '''        "issues_csv": path_for_meta(csv_out),
        "regen_compare_report": path_for_meta(regen_compare_out) if regen_compare_out else None,
        "aff_report": path_for_meta(aff_out) if aff_out else None,
        "aff_csv": path_for_meta(aff_csv_out) if aff_csv_out else None,
        "aff_unique_report": path_for_meta(aff_unique_out) if aff_unique_out else None,
'''
if "regen_compare_report" not in text:
    if success_anchor not in text:
        raise SystemExit("success return anchor not found")
    text = text.replace(success_anchor, success_new, 1)

# Also add None on cancelled early return for key consistency
cancel_anchor = '''            "aff_unique_report": None,
'''
# carefully - only first cancelled return after cancelled_mid
# Look for the cancelled return block
cancel_block = '''            "aff_report": None,
            "aff_csv": None,
            "aff_unique_report": None,
'''
cancel_new = '''            "aff_report": None,
            "aff_csv": None,
            "aff_unique_report": None,
            "regen_compare_report": None,
'''
if text.count("regen_compare_report") < 2:
    if cancel_block not in text:
        raise SystemExit("cancel return anchor not found")
    text = text.replace(cancel_block, cancel_new, 1)

p.write_text(text, encoding="utf-8")
compile(text, str(p), "exec")
print("extractor wired OK", "SCRIPT_VERSION" in text)
# verify SCRIPT_VERSION
for line in text.splitlines():
    if line.startswith("SCRIPT_VERSION"):
        print(line)
        break

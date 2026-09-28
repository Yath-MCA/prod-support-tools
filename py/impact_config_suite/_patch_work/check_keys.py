from pathlib import Path
t = Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite\core\contrib_extractor.py").read_text(encoding="utf-8")
print("regen_compare_report count", t.count("regen_compare_report"))
for i, line in enumerate(t.splitlines(), 1):
    if "regen_compare" in line:
        print(f"{i}: {line.rstrip()}")
idx = t.find('"issues_csv": path_for_meta(csv_out)')
print("--- around issues_csv success return ---")
print(t[idx:idx+500])

from pathlib import Path
p = Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite\core\element_extractor.py")
t = p.read_text(encoding="utf-8")
old = "            for chunk_start in range(0, total_files or 1 if all_files else 0, chunk_size):"
new = "            for chunk_start in range(0, len(all_files), chunk_size):"
if old not in t:
    raise SystemExit("range marker missing")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("range fixed")

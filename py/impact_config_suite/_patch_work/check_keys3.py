from pathlib import Path
t = Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite\core\contrib_extractor.py").read_text(encoding="utf-8")
for i, line in enumerate(t.splitlines(), 1):
    if "regen_compare_report" in line:
        print(f"{i}: {line.rstrip()}")
compile(t, "contrib_extractor.py", "exec")
print("syntax ok")

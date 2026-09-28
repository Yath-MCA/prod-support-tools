from pathlib import Path
t = Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite\core\contrib_extractor.py").read_text(encoding="utf-8")
for i, line in enumerate(t.splitlines(), 1):
    if "regen_compare_report" in line:
        print(f"{i}: {line.rstrip()}")
        for j in range(max(1,i-3), min(len(t.splitlines()), i+3)+1):
            if j != i:
                print(f"   {j}: {t.splitlines()[j-1].rstrip()}")

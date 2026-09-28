from pathlib import Path
import re

roots = [
    Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite\tests\test_contrib_extractor.py"),
    Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite\tests\test_contrib_aff.py"),
]
for p in roots:
    text = p.read_text(encoding="utf-8")
    orig = text
    # version equality checks
    text = text.replace("ce.SCRIPT_VERSION, 12)", "ce.SCRIPT_VERSION, 13)")
    text = text.replace("SCRIPT_VERSION=12", "SCRIPT_VERSION=13")
    text = text.replace("_elements_v12.html", "_elements_v13.html")
    text = text.replace("_contrib_v12.html", "_contrib_v13.html")
    text = text.replace("aff_unique_v12.html", "aff_unique_v13.html")
    text = text.replace("_aff_v12.html", "_aff_v13.html")
    # docstring mentions
    text = text.replace("SCRIPT_VERSION = 12", "SCRIPT_VERSION = 13")
    if text != orig:
        p.write_text(text, encoding="utf-8")
        print("updated", p.name)
    else:
        print("no change", p.name)

# show remaining v12 hardcodes in those tests
for p in roots:
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if "v12" in line or ", 12)" in line or "= 12" in line:
            print(f"{p.name}:{i}: {line.strip()[:120]}")

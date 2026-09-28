from pathlib import Path

p = Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite\core\contrib_extractor.py")
text = p.read_text(encoding="utf-8")

# Success return: insert after issues_csv
success_old = '''        "issues_csv": path_for_meta(csv_out),
        "aff_report": path_for_meta(aff_out) if aff_out else None,
'''
success_new = '''        "issues_csv": path_for_meta(csv_out),
        "regen_compare_report": path_for_meta(regen_compare_out) if regen_compare_out else None,
        "aff_report": path_for_meta(aff_out) if aff_out else None,
'''
if '"regen_compare_report": path_for_meta(regen_compare_out)' not in text:
    if success_old not in text:
        raise SystemExit("success return block not found")
    text = text.replace(success_old, success_new, 1)
    print("added success key")
else:
    print("success key already present")

# Cancelled early return
cancel_old = '''            "issues_csv": None,
            "aff_report": None,
'''
# check what's actually there
idx = text.find('"cancelled": True')
print("cancelled idx", idx)
print(repr(text[idx:idx+600]))

cancel_marker = '''            "elements_report": None,
            "issues_csv": None,
            "aff_report": None,
            "aff_csv": None,
            "aff_unique_report": None,
'''
cancel_new = '''            "elements_report": None,
            "issues_csv": None,
            "regen_compare_report": None,
            "aff_report": None,
            "aff_csv": None,
            "aff_unique_report": None,
'''
if cancel_marker in text and '"regen_compare_report": None' not in text[idx:idx+800]:
    text = text.replace(cancel_marker, cancel_new, 1)
    print("added cancel key")
elif '"regen_compare_report": None' in text:
    print("cancel key already present")
else:
    # try without elements_report line exactness
    print("WARN cancel marker mismatch")

p.write_text(text, encoding="utf-8")
compile(text, str(p), "exec")
print("done", text.count('"regen_compare_report"'))

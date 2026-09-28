from pathlib import Path

root = Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite")

# --- tab PATHS ---
tab = root / "tabs" / "contrib_extractor_tab.py"
tt = tab.read_text(encoding="utf-8")
old = '''            for key, label in (
                ("report", "contrib"),
                ("elements_report", "elements"),
                ("issues_csv", "issues"),
            ):'''
new = '''            for key, label in (
                ("report", "contrib"),
                ("elements_report", "elements"),
                ("issues_csv", "issues"),
                ("aff_report", "aff"),
                ("aff_csv", "aff_csv"),
                ("aff_unique_report", "aff_unique"),
            ):'''
if old not in tt:
    raise SystemExit("tab PATHS block not found")
tt = tt.replace(old, new, 1)
# comment near PATHS
tt = tt.replace(
    "# Surface output paths (contrib HTML, elements HTML, issues CSV) in the log",
    "# Surface output paths (contrib/elements/aff HTML, issues/aff CSV) in the log",
    1,
)
tab.write_text(tt, encoding="utf-8")
print("patched tab")

# --- existing tests: SCRIPT_VERSION 9 -> 10 where hard-asserted ---
tests = root / "tests" / "test_contrib_extractor.py"
te = tests.read_text(encoding="utf-8")
replacements = [
    (
        '"""SCRIPT_VERSION=9 treats prior version=2/8 (and legacy logic-only) reports as updates."""\n        self.assertEqual(ce.SCRIPT_VERSION, 9)',
        '"""SCRIPT_VERSION=10 treats prior version=2/8/9 (and legacy logic-only) reports as updates."""\n        self.assertEqual(ce.SCRIPT_VERSION, 10)',
    ),
    (
        'self.assertEqual(ce.SCRIPT_VERSION, 9)\n            self.assertEqual(entry.get("version"), 9)',
        'self.assertEqual(ce.SCRIPT_VERSION, 10)\n            self.assertEqual(entry.get("version"), 10)',
    ),
    (
        'self.assertIn("_contrib_v9.html", report_norm)',
        'self.assertIn("_contrib_v10.html", report_norm)',
    ),
    (
        'self.assertIn("v9", html)',
        'self.assertIn("v10", html)',
    ),
    (
        'self.assertIn("_elements_v9.html", str(elements).replace("\\\\", "/"))',
        'self.assertIn("_elements_v10.html", str(elements).replace("\\\\", "/"))',
    ),
    (
        'self.assertIn("_issues_v9.csv", str(issues).replace("\\\\", "/"))',
        'self.assertIn("_issues_v10.csv", str(issues).replace("\\\\", "/"))',
    ),
    (
        'self.assertEqual(loaded["JATS"]["LWW"]["INF"].get("version"), 9)',
        'self.assertEqual(loaded["JATS"]["LWW"]["INF"].get("version"), 10)',
    ),
    (
        '"""SCRIPT_VERSION=9 treats prior version=8 reports as updates."""\n        self.assertEqual(ce.SCRIPT_VERSION, 9)',
        '"""SCRIPT_VERSION=10 treats prior version=8/9 reports as updates."""\n        self.assertEqual(ce.SCRIPT_VERSION, 10)',
    ),
]
# also comments saying v9 meta / v9 HTML / v9 always
te2 = te
for a, b in replacements:
    if a not in te2:
        print("WARN missing:", repr(a[:80]))
    else:
        te2 = te2.replace(a, b, 1)
        print("ok:", repr(a[:60]))

# Add aff meta assertions into process_group test if not present
needle = 'self.assertIn("_issues_v10.csv", str(issues).replace("\\\\", "/"))'
aff_assert = '''
            # v10 aff / author-notes after contrib-group
            self.assertTrue(entry.get("aff_report"))
            aff = Path(entry["aff_report"])
            self.assertTrue(aff.is_absolute())
            self.assertTrue(aff.exists())
            self.assertIn("_aff_v10.html", str(aff).replace("\\\\", "/"))
            self.assertTrue(entry.get("aff_csv"))
            self.assertTrue(Path(entry["aff_csv"]).exists())
            self.assertTrue(entry.get("aff_unique_report"))
            self.assertTrue(Path(entry["aff_unique_report"]).exists())
'''
# The needle uses double-escaped backslash in the source file which is actually single backslash in Python source
needle2 = 'self.assertIn("_issues_v10.csv", str(issues).replace("\\", "/"))'
if needle2 in te2 and 'aff_report' not in te2[te2.find('test_process_group_writes_report_and_meta'):te2.find('test_process_group_writes_report_and_meta')+2500]:
    te2 = te2.replace(needle2, needle2 + aff_assert, 1)
    print("added aff asserts")
elif 'aff_report' in te2:
    print("aff asserts already present?")
else:
    # try find issues assert line
    idx = te2.find('_issues_v10.csv')
    print("issues_v10 idx", idx)
    if idx > 0:
        # find end of that statement
        end = te2.find("\n", te2.find(")", idx)) + 1
        te2 = te2[:end] + aff_assert + te2[end:]
        print("inserted aff asserts at", end)

tests.write_text(te2, encoding="utf-8")
print("patched tests")

from pathlib import Path

replacements = {
    Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite\tests\test_contrib_extractor.py"): [
        ('entry.get("version"), 12)', 'entry.get("version"), 13)'),
        ('self.assertIn("v12", html)', 'self.assertIn("v13", html)'),
        ('"_issues_v12.csv"', '"_issues_v13.csv"'),
        ('INF"].get("version"), 12)', 'INF"].get("version"), 13)'),
    ],
    Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite\tests\test_contrib_aff.py"): [
        ('"_aff_v12.csv"', '"_aff_v13.csv"'),
        ('self.assertIn("v12", html)', 'self.assertIn("v13", html)'),
    ],
}
for p, pairs in replacements.items():
    text = p.read_text(encoding="utf-8")
    for a, b in pairs:
        if a not in text:
            print("MISSING", p.name, a)
        else:
            text = text.replace(a, b)
            print("OK", p.name, a, "->", b)
    p.write_text(text, encoding="utf-8")

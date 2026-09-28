from pathlib import Path

p = Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite\core\contrib_phase0.py")
text = p.read_text(encoding="utf-8")

old_imp = "from typing import Dict, List, Optional"
new_imp = """from typing import Dict, List, Optional

from core.contrib_regen_compare import (
    enrich_compare_stub_html,
    lightweight_compare_row,
)"""
if "from core.contrib_regen_compare import" not in text:
    if old_imp not in text:
        raise SystemExit("import anchor missing")
    text = text.replace(old_imp, new_imp, 1)

old = '''    path_regen.write_text(regen, encoding="utf-8")

    # 7. Compare HTML stub (preview HTML remains in write_doc_outputs)
    path_compare.write_text(
        build_compare_stub_html(
            original_clean=original_clean,
            regen=regen,
            config_note=config_note,
        ),
        encoding="utf-8",
    )

    return {
        "original": path_original,
'''

new = '''    path_regen.write_text(regen, encoding="utf-8")

    # 7. Compare HTML stub + KPI / cause-chart enrich from lightweight equality
    stub = build_compare_stub_html(
        original_clean=original_clean,
        regen=regen,
        config_note=config_note,
    )
    cmp_row = lightweight_compare_row(
        docid=folder.name,
        original_clean=original_clean,
        regen=regen,
    )
    matched = cmp_row.get("pct") == 100.0 and not cmp_row.get("error")
    path_compare.write_text(
        enrich_compare_stub_html(
            stub,
            matched=matched,
            categories=cmp_row.get("categories") or set(),
        ),
        encoding="utf-8",
    )

    return {
        "original": path_original,
'''

if old not in text:
    raise SystemExit("exact block not found")
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")
compile(text, str(p), "exec")
print("phase0 wired OK", p.stat().st_size)

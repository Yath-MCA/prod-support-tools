from __future__ import annotations

import base64
from datetime import datetime
from html import escape
from pathlib import Path
import re

from .diff_engine import DiffRow


STATUS_CLASS = {
    "OK": "ok",
    "Inserted": "inserted",
    "Deleted": "deleted",
    "Tracked Insert": "tracked-insert",
    "Tracked Delete": "tracked-delete",
    "Untracked Change": "untracked",
}


def _safe_file_token(doc_id: str) -> str:
    safe = re.sub(r"[\\/:*?\"<>|]+", "_", doc_id.strip())
    return safe or "document"


def _summary_items(summary: dict) -> str:
    ordered = [
        ("Total CJK (Original)", summary["total_original"]),
        ("Total CJK (Revised)", summary["total_revised"]),
        ("Inserted", summary["inserted"]),
        ("Deleted", summary["deleted"]),
        ("Tracked Insert", summary["tracked_insert"]),
        ("Tracked Delete", summary["tracked_delete"]),
        ("Untracked Changes", summary["untracked_changes"]),
        ("OK", summary["ok"]),
    ]
    return "".join(f"<li><strong>{escape(label)}:</strong> {value}</li>" for label, value in ordered)


def _png_data_uri(image_path: Path) -> str | None:
    if not image_path.exists():
        return None
    data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def _brand_logos_html() -> str:
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    logos = [
        ("IMPACT", assets_dir / "IMPACT_5_4.png"),
        ("Newgen", assets_dir / "Newgen.png"),
    ]

    tags: list[str] = []
    for alt_text, image_path in logos:
        data_uri = _png_data_uri(image_path)
        if data_uri:
            tags.append(f'<img class="brand-logo" alt="{escape(alt_text)}" src="{data_uri}" />')

    if not tags:
        return ""
    return f'<div class="brand-strip">{"".join(tags)}</div>'


def _table_rows(rows: list[DiffRow]) -> str:
    lines = []
    for idx, row in enumerate(rows, start=1):
        css_class = STATUS_CLASS.get(row.status, "")
        lines.append(
            """
            <tr class="data-row {css_class}" data-status="{status}">
              <td>{idx}</td>
              <td>{path}</td>
              <td>{char_index}</td>
              <td>{original}</td>
              <td>{revised}</td>
              <td>{status_text}</td>
            </tr>
            <tr class="detail-row {css_class}" data-status="{status}">
              <td colspan="6">
                <div><strong>Original snippet:</strong> <code>{orig_snippet}</code></div>
                <div><strong>Revised snippet:</strong> <code>{rev_snippet}</code></div>
              </td>
            </tr>
            """.format(
                css_class=css_class,
                status=escape(row.status),
                idx=idx,
                path=escape(row.element_path),
                char_index=row.char_index,
                original=escape(row.original),
                revised=escape(row.revised),
                status_text=escape(row.status),
                orig_snippet=escape(row.original_snippet),
                rev_snippet=escape(row.revised_snippet),
            )
        )
    return "\n".join(lines)


def generate_report(
    doc_id: str,
    original_url: str,
    revised_url: str,
    rows: list[DiffRow],
    summary: dict,
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"report_{_safe_file_token(doc_id)}.html"

    template_path = Path(__file__).resolve().parent / "templates" / "report_template.html"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = """<!DOCTYPE html>
<html><body>
<h1>CJK Integrity Report - {doc_id}</h1>
<p><strong>Generated:</strong> {generated_at}</p>
<p><strong>Original URL:</strong> {original_url}</p>
<p><strong>Revised URL:</strong> {revised_url}</p>
<ul>{summary_items}</ul>
<table><tbody>{table_rows}</tbody></table>
</body></html>"""

    html = template.format(
        doc_id=escape(doc_id),
        generated_at=escape(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        original_url=escape(original_url),
        revised_url=escape(revised_url),
        brand_logos=_brand_logos_html(),
        summary_items=_summary_items(summary),
        table_rows=_table_rows(rows),
    )

    report_path.write_text(html, encoding="utf-8")
    return report_path

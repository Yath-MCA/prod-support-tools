"""Direct-child comment and alpha-text hits under mixed-citation elements."""

from __future__ import annotations

import csv
import html
import os
import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

from patterns.refs import get_ref_tag, is_ignorable_ref_node

_ALPHA_ONLY_RE = re.compile(r"^[A-Za-z]+$")
_MIXED_CITATION_SELECTOR = ".mixed-citation, [data-name='mixed-citation']"


def is_mixed_citation(node: Any) -> bool:
    if not isinstance(node, Tag):
        return False
    data_name = node.get("data-name")
    if data_name == "mixed-citation":
        return True
    classes = node.get("class") or []
    if isinstance(classes, str):
        classes = classes.split()
    return "mixed-citation" in classes


def is_comment_element(node: Any) -> bool:
    if not isinstance(node, Tag):
        return False
    if get_ref_tag(node) == "comment":
        return True
    if node.name == "comment":
        return True
    data_name = node.get("data-name")
    if data_name == "comment":
        return True
    classes = node.get("class") or []
    if isinstance(classes, str):
        classes = classes.split()
    return "comment" in classes


def is_alpha_only_text(text: str) -> bool:
    if text is None:
        return False
    stripped = str(text).strip()
    if not stripped:
        return False
    return bool(_ALPHA_ONLY_RE.match(stripped))


def _node_line(node: Any) -> int | None:
    return getattr(node, "sourceline", None)


def _parent_ref_id(citation: Tag) -> str | None:
    parent = citation.parent
    while parent is not None and isinstance(parent, Tag):
        data_name = parent.get("data-name")
        classes = parent.get("class") or []
        if isinstance(classes, str):
            classes = classes.split()
        if data_name == "ref" or "ref" in classes:
            ref_id = parent.get("id")
            return ref_id if ref_id else None
        parent = parent.parent
    return None


def extract_direct_hits_from_citation(citation: Tag) -> list[dict]:
    hits: list[dict] = []
    if not is_mixed_citation(citation):
        return hits

    for child in list(citation.contents):
        if is_ignorable_ref_node(child):
            continue

        if isinstance(child, NavigableString) and not isinstance(child, Tag):
            raw = str(child)
            if is_alpha_only_text(raw):
                hits.append(
                    {
                        "kind": "alpha_text",
                        "value": raw.strip(),
                        "line": _node_line(child),
                    }
                )
            continue

        if not isinstance(child, Tag):
            continue

        if is_comment_element(child):
            hits.append(
                {
                    "kind": "comment",
                    "value": child.get_text(strip=False),
                    "line": _node_line(child),
                }
            )

    return hits


def extract_direct_hits_from_soup(soup: BeautifulSoup) -> list[dict]:
    hits: list[dict] = []
    for citation in soup.select(_MIXED_CITATION_SELECTOR):
        if not is_mixed_citation(citation):
            continue
        citation_html = str(citation)
        ref_id = _parent_ref_id(citation)
        for hit in extract_direct_hits_from_citation(citation):
            enriched = dict(hit)
            enriched["citation_html"] = citation_html
            if ref_id is not None:
                enriched["ref_id"] = ref_id
            hits.append(enriched)
    return hits


def extract_direct_hits_from_file(path: Path) -> list[dict]:
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    parser = "lxml-xml" if path.suffix.lower() == ".xml" else "lxml"
    try:
        soup = BeautifulSoup(text, parser)
    except Exception:
        soup = BeautifulSoup(text, "lxml")
    return extract_direct_hits_from_soup(soup)


def rollup_by_client(file_results: list[dict]) -> list[dict]:
    """Aggregate per-file hit results into client-wise rollup rows.

    Each input item: ``{path, client, ok, hits: list}`` where hit kinds are
    ``comment`` | ``alpha_text``.

    Returns list of:
    ``{client, files_searched, files_with_hits, comment_hits, alpha_text_hits, total_hits}``
    """
    buckets: OrderedDict[str, dict] = OrderedDict()

    for item in file_results or []:
        client = item.get("client") or "(unknown)"
        if client not in buckets:
            buckets[client] = {
                "client": client,
                "files_searched": 0,
                "files_with_hits": 0,
                "comment_hits": 0,
                "alpha_text_hits": 0,
                "total_hits": 0,
            }
        row = buckets[client]
        row["files_searched"] += 1
        hits = item.get("hits") or []
        if hits:
            row["files_with_hits"] += 1
        for hit in hits:
            kind = hit.get("kind")
            if kind == "comment":
                row["comment_hits"] += 1
            elif kind == "alpha_text":
                row["alpha_text_hits"] += 1
            row["total_hits"] += 1

    return list(buckets.values())


def generate_mixed_citation_direct_hits_report_html(
    target_path: str,
    file_results: list[dict],
    rollup_rows: list[dict],
    **_: Any,
) -> str:
    """Build a dark-friendly HTML report with client rollup + per-file hits."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target_name = os.path.basename(str(target_path)) or str(target_path)

    total_files = len(file_results or [])
    total_hits = sum(len(r.get("hits") or []) for r in (file_results or []))
    files_with_hits = sum(1 for r in (file_results or []) if r.get("hits"))

    rollup_body = ""
    for row in rollup_rows or []:
        rollup_body += f"""
            <tr>
                <td>{html.escape(str(row.get("client", "")))}</td>
                <td>{int(row.get("files_searched", 0))}</td>
                <td>{int(row.get("files_with_hits", 0))}</td>
                <td><span class="badge badge-comment">comment: {int(row.get("comment_hits", 0))}</span></td>
                <td><span class="badge badge-alpha">alpha_text: {int(row.get("alpha_text_hits", 0))}</span></td>
                <td><strong>{int(row.get("total_hits", 0))}</strong></td>
            </tr>
        """

    if not rollup_body:
        rollup_body = '<tr><td colspan="6" class="empty">No clients / no results</td></tr>'

    detail_rows = ""
    sno = 0
    for fr in file_results or []:
        path_str = str(fr.get("path", ""))
        file_name = os.path.basename(path_str) or path_str
        client = str(fr.get("client", ""))
        hits = fr.get("hits") or []
        if not hits:
            continue
        for hit in hits:
            sno += 1
            kind = str(hit.get("kind", ""))
            value = str(hit.get("value", ""))
            line = hit.get("line", "")
            kind_cls = "badge-comment" if kind == "comment" else "badge-alpha"
            detail_rows += f"""
            <tr>
                <td>{sno}</td>
                <td>{html.escape(client)}</td>
                <td title="{html.escape(path_str)}"><strong>{html.escape(file_name)}</strong>
                    <div class="file-path-sub">{html.escape(path_str)}</div></td>
                <td>{html.escape(str(line) if line is not None else "")}</td>
                <td><span class="badge {kind_cls}">{html.escape(kind)}</span></td>
                <td>{html.escape(value)}</td>
            </tr>
            """

    if not detail_rows:
        detail_rows = '<tr><td colspan="6" class="empty">No hits found</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mixed-citation Comment + Alpha Text Report - {html.escape(target_name)}</title>
    <style>
        :root {{
            --bg-main: #0f172a;
            --bg-card: #1e293b;
            --border-color: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #818cf8;
            --success: #10b981;
            --warn: #f59e0b;
        }}
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            margin: 0;
            padding: 40px 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            margin-bottom: 30px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            flex-wrap: wrap;
            gap: 15px;
        }}
        h1 {{ margin: 0; font-size: 1.6rem; color: var(--primary); }}
        h2 {{ color: var(--text-main); margin: 28px 0 12px; font-size: 1.15rem; }}
        .meta {{ color: var(--text-muted); font-size: 0.9rem; margin-top: 5px; }}
        .timestamp {{
            font-size: 0.85rem;
            background: var(--bg-card);
            padding: 5px 12px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            color: var(--text-muted);
        }}
        .badge-bar {{ margin: 12px 0 20px; display: flex; flex-wrap: wrap; gap: 8px; }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 600;
        }}
        .badge-comment {{ background: rgba(129, 140, 248, 0.2); color: #a5b4fc; }}
        .badge-alpha {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; }}
        .badge-stat {{ background: rgba(16, 185, 129, 0.15); color: var(--success); }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 24px;
        }}
        th, td {{
            padding: 10px 14px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
            vertical-align: top;
        }}
        th {{
            background: rgba(15, 23, 42, 0.6);
            color: var(--text-muted);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        tr:last-child td {{ border-bottom: none; }}
        .file-path-sub {{
            color: var(--text-muted);
            font-size: 0.75rem;
            margin-top: 2px;
            word-break: break-all;
        }}
        .empty {{ color: var(--text-muted); text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Mixed-citation Comment + Alpha Text</h1>
                <div class="meta">Target: <strong>{html.escape(str(target_path))}</strong></div>
                <div class="meta">
                    Files searched: <strong>{total_files}</strong> |
                    Files with hits: <strong>{files_with_hits}</strong> |
                    Total hits: <strong>{total_hits}</strong>
                </div>
            </div>
            <div class="timestamp">Generated: {html.escape(timestamp)}</div>
        </header>

        <div class="badge-bar">
            <span class="badge badge-stat">files_searched: {total_files}</span>
            <span class="badge badge-stat">files_with_hits: {files_with_hits}</span>
            <span class="badge badge-comment">comment hits</span>
            <span class="badge badge-alpha">alpha_text hits</span>
        </div>

        <h2>Client rollup</h2>
        <table>
            <thead>
                <tr>
                    <th>Client</th>
                    <th>Files searched</th>
                    <th>Files with hits</th>
                    <th>Comment hits</th>
                    <th>Alpha text hits</th>
                    <th>Total hits</th>
                </tr>
            </thead>
            <tbody>
                {rollup_body}
            </tbody>
        </table>

        <h2>Hit details</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Client</th>
                    <th>File</th>
                    <th>Line</th>
                    <th>Kind</th>
                    <th>Value</th>
                </tr>
            </thead>
            <tbody>
                {detail_rows}
            </tbody>
        </table>
    </div>
</body>
</html>
"""


def write_mixed_citation_direct_hits_csv(
    csv_path: str | Path,
    file_results: list[dict],
    rollup_rows: list[dict],
) -> Path:
    """Write client rollup CSV; returns the written path.

    Header columns:
    client, files_searched, files_with_hits, comment_hits, alpha_text_hits, total_hits
    """
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    header = [
        "client",
        "files_searched",
        "files_with_hits",
        "comment_hits",
        "alpha_text_hits",
        "total_hits",
    ]

    rows = rollup_rows if rollup_rows is not None else rollup_by_client(file_results or [])

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            writer.writerow(
                [
                    row.get("client", ""),
                    int(row.get("files_searched", 0)),
                    int(row.get("files_with_hits", 0)),
                    int(row.get("comment_hits", 0)),
                    int(row.get("alpha_text_hits", 0)),
                    int(row.get("total_hits", 0)),
                ]
            )

    return csv_path

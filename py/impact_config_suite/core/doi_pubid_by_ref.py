"""Six-bucket first-hit DOI / pub-id / URI extraction (in vs out of .ref)."""

from __future__ import annotations

import csv
import html as html_lib
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from core.mixed_citation_direct_hits import is_comment_element

CSV_HEADER = [
    "file_path",
    "file_name",
    "doc_type",
    "client",
    "link_info",
    "identifier",
    "bucket",
    "element_kind",
    "in_ref",
    "under_comment",
    "doi_org_in_href",
    "doi_org_in_text",
    "line",
    "text",
    "href",
    "outer_xml",
]


def _class_tokens(node: Tag) -> list[str]:
    classes = node.get("class") or []
    if isinstance(classes, str):
        return classes.split()
    return list(classes)


def is_ref_element(node: Tag) -> bool:
    if not isinstance(node, Tag):
        return False
    if node.name == "ref":
        return True
    if node.get("data-name") == "ref" or node.get("data-role") == "ref":
        return True
    return "ref" in _class_tokens(node)


def is_inside_ref(node: Tag) -> bool:
    parent = getattr(node, "parent", None)
    while isinstance(parent, Tag):
        if is_ref_element(parent):
            return True
        parent = parent.parent
    return False


def is_pub_id_element(node: Tag) -> bool:
    if not isinstance(node, Tag):
        return False
    if node.name == "pub-id":
        return True
    if node.get("data-name") == "pub-id":
        return True
    return "pub-id" in _class_tokens(node)


def is_ext_link_of_type(node: Tag, link_type: str) -> bool:
    if not isinstance(node, Tag):
        return False
    is_ext = (
        node.name == "ext-link"
        or node.get("data-name") == "ext-link"
        or "ext-link" in _class_tokens(node)
    )
    if not is_ext:
        return False
    return (node.get("ext-link-type") or "") == link_type


def get_href(node: Tag) -> str:
    for key, val in (node.attrs or {}).items():
        if key == "href" or key == "xlink:href" or (
            isinstance(key, str) and key.endswith("}href")
        ):
            return str(val or "")
    return ""


def _under_comment(node: Tag) -> bool:
    parent = node.parent
    return isinstance(parent, Tag) and is_comment_element(parent)


def _row(bucket: int, kind: str, node: Tag, in_ref: bool) -> dict:
    text = node.get_text(" ", strip=True)
    href = get_href(node)
    under = _under_comment(node) if kind in ("doi", "uri") else False
    doi_href = ("doi.org" in href.lower()) if kind == "uri" else False
    doi_text = ("doi.org" in text.lower()) if kind == "uri" else False
    try:
        outer = str(node)
    except Exception:
        outer = ""
    return {
        "bucket": bucket,
        "element_kind": kind,
        "in_ref": in_ref,
        "under_comment": under,
        "doi_org_in_href": doi_href,
        "doi_org_in_text": doi_text,
        "line": getattr(node, "sourceline", "") or "",
        "text": text,
        "href": href,
        "html": outer,
    }


def extract_buckets_from_soup(soup: Any) -> list[dict]:
    """Return up to six first-hit bucket rows in bucket-number order."""
    filled: dict[int, dict] = {}
    for node in soup.descendants:
        if not isinstance(node, Tag):
            continue
        in_ref = is_inside_ref(node)
        if is_pub_id_element(node):
            kind = "pub-id"
            bucket = 1 if in_ref else 2
        elif is_ext_link_of_type(node, "doi"):
            kind = "doi"
            bucket = 3 if in_ref else 4
        elif is_ext_link_of_type(node, "uri"):
            kind = "uri"
            bucket = 5 if in_ref else 6
        else:
            continue
        if bucket not in filled:
            filled[bucket] = _row(bucket, kind, node, in_ref)
    return [filled[k] for k in sorted(filled)]


def extract_buckets_from_file(file_path: Path) -> dict:
    """Parse one file; return {ok, error?, buckets}."""
    file_path = Path(file_path)
    try:
        raw = file_path.read_bytes()
    except Exception as exc:
        return {"ok": False, "error": str(exc), "buckets": []}

    suffix = file_path.suffix.lower()
    parser = "lxml-xml" if suffix == ".xml" else "lxml"
    try:
        text = raw.decode("utf-8", errors="ignore")
        soup = BeautifulSoup(text, parser)
        if soup is None:
            raise ValueError("empty parse")
        return {"ok": True, "error": "", "buckets": extract_buckets_from_soup(soup)}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "buckets": []}


def write_doi_pubid_by_ref_csv(file_results: list[dict], output_path: Path) -> Path:
    output_path = Path(output_path)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for item in file_results:
            if not item.get("ok", True):
                continue
            buckets = item.get("buckets") or []
            if not buckets:
                continue
            path_str = str(item.get("path", ""))
            file_name = os.path.basename(path_str)
            for row in buckets:
                writer.writerow([
                    path_str,
                    file_name,
                    item.get("doc_type", ""),
                    item.get("client", ""),
                    item.get("link_info", ""),
                    item.get("identifier", ""),
                    row.get("bucket", ""),
                    row.get("element_kind", ""),
                    "True" if row.get("in_ref") else "False",
                    "True" if row.get("under_comment") else "False",
                    "True" if row.get("doi_org_in_href") else "False",
                    "True" if row.get("doi_org_in_text") else "False",
                    row.get("line", ""),
                    row.get("text", ""),
                    row.get("href", ""),
                    row.get("html", ""),
                ])
    return output_path


def generate_doi_pubid_by_ref_html(
    file_results: list[dict],
    target_path: str,
    ts: str | None = None,
) -> str:
    ts = ts or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target_name = os.path.basename(target_path)
    total_files = len(file_results)
    files_with_hits = sum(1 for r in file_results if r.get("ok") and r.get("buckets"))
    total_buckets = sum(len(r.get("buckets") or []) for r in file_results if r.get("ok"))

    sections = []
    for idx, item in enumerate(file_results):
        path_str = str(item.get("path", ""))
        name = os.path.basename(path_str)
        meta = " | ".join(
            p for p in [
                item.get("doc_type", ""),
                item.get("client", ""),
                item.get("link_info", ""),
                item.get("identifier", ""),
            ] if p
        )
        if not item.get("ok", True):
            sections.append(
                f'<div class="card error"><h3>{html_lib.escape(name)}</h3>'
                f'<p class="meta">{html_lib.escape(meta)}</p>'
                f'<p>Error: {html_lib.escape(str(item.get("error", "")))}</p></div>'
            )
            continue
        buckets = item.get("buckets") or []
        rows_html = ""
        for row in buckets:
            rows_html += f"""
            <tr>
              <td>{row.get("bucket")}</td>
              <td>{html_lib.escape(str(row.get("element_kind", "")))}</td>
              <td>{"Yes" if row.get("in_ref") else "No"}</td>
              <td>{"Yes" if row.get("under_comment") else "No"}</td>
              <td>{"Yes" if row.get("doi_org_in_href") else "No"}</td>
              <td>{"Yes" if row.get("doi_org_in_text") else "No"}</td>
              <td>{html_lib.escape(str(row.get("line", "")))}</td>
              <td><code>{html_lib.escape(str(row.get("href", "")))}</code></td>
              <td>{html_lib.escape(str(row.get("text", ""))[:200])}</td>
            </tr>
            """
        if not rows_html:
            rows_html = '<tr><td colspan="9">No bucket hits</td></tr>'
        sections.append(f"""
        <div class="card">
          <h3>{html_lib.escape(name)} <span class="badge">{len(buckets)} bucket(s)</span></h3>
          <p class="meta">{html_lib.escape(meta)}</p>
          <p class="path">{html_lib.escape(path_str)}</p>
          <table>
            <thead>
              <tr>
                <th>Bucket</th><th>Kind</th><th>In ref</th><th>Under comment</th>
                <th>doi.org href</th><th>doi.org text</th><th>Line</th><th>Href</th><th>Text</th>
              </tr>
            </thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>
        """)

    body = "\n".join(sections) if sections else "<p>No files scanned.</p>"
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<title>DOI / pub-id by ref — {html_lib.escape(target_name)}</title>
<style>
body{{font-family:Segoe UI,sans-serif;background:#0b0f19;color:#e2e8f0;margin:24px}}
.card{{background:#111827;border:1px solid #374151;border-radius:10px;padding:16px;margin-bottom:16px}}
.card.error{{border-color:#ef4444}}
.meta,.path{{color:#94a3b8;font-size:0.9rem}}
.badge{{background:#6366f1;color:#fff;border-radius:4px;padding:2px 8px;font-size:0.75rem;margin-left:8px}}
table{{width:100%;border-collapse:collapse;margin-top:10px;font-size:0.85rem}}
th,td{{border:1px solid #374151;padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#1f2937}}
code{{color:#38bdf8;word-break:break-all}}
.stats span{{margin-right:16px}}
</style></head><body>
<h1>DOI / pub-id by ref (unique)</h1>
<p>Target: <strong>{html_lib.escape(target_name)}</strong> · Generated: {html_lib.escape(ts)}</p>
<p class="stats">
  <span>Files: {total_files}</span>
  <span>With hits: {files_with_hits}</span>
  <span>Bucket rows: {total_buckets}</span>
</p>
{body}
</body></html>
"""

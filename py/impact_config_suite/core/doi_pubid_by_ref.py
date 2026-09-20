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
    import json
    from pathlib import Path

    ts = ts or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target_name = os.path.basename(target_path)
    scanned_files = len(file_results)

    # Omit empty / no-hit files from the report body (errors still shown).
    visible = []
    for item in file_results:
        if not item.get("ok", True):
            visible.append(item)
            continue
        if item.get("buckets"):
            visible.append(item)

    files_with_hits = sum(1 for r in visible if r.get("ok") and r.get("buckets"))
    total_buckets = sum(len(r.get("buckets") or []) for r in visible if r.get("ok"))

    doc_types = sorted({
        (r.get("doc_type") or "").strip()
        for r in visible if (r.get("doc_type") or "").strip()
    })
    clients = sorted({
        (r.get("client") or "").strip()
        for r in visible if (r.get("client") or "").strip()
    })
    identifiers = sorted({
        (r.get("identifier") or "").strip()
        for r in visible if (r.get("identifier") or "").strip()
    })

    def _opt(values: list[str]) -> str:
        return "".join(
            f'<option value="{html_lib.escape(v)}">{html_lib.escape(v)}</option>'
            for v in values
        )

    sections = []
    for idx, item in enumerate(visible):
        path_str = str(item.get("path", ""))
        name = os.path.basename(path_str)
        try:
            file_uri = Path(path_str).as_uri()
        except Exception:
            file_uri = ""
        js_file_path = json.dumps(path_str)
        doc_type = (item.get("doc_type") or "").strip()
        client = (item.get("client") or "").strip()
        identifier = (item.get("identifier") or "").strip()
        link_info = (item.get("link_info") or "").strip()
        meta_line = " | ".join(p for p in [doc_type, client, link_info, identifier] if p)
        file_id = f"file-{idx}"

        if not item.get("ok", True):
            err_msg = html_lib.escape(str(item.get("error", "")))
            sections.append(f"""
            <div class="file-card error-card"
                 data-filename="{html_lib.escape(name)}"
                 data-doc-type="{html_lib.escape(doc_type)}"
                 data-client="{html_lib.escape(client)}"
                 data-identifier="{html_lib.escape(identifier)}">
                <div class="file-header" onclick="toggleCard('{file_id}')">
                    <div class="file-header-main">
                        <div class="file-title">
                            <span class="toggle-icon">▶</span>
                            <span class="file-badge badge-error">Error</span>
                            <strong>{html_lib.escape(name)}</strong>
                        </div>
                        <div class="file-actions">
                            {"<a class='file-action-btn' href='" + html_lib.escape(file_uri) + "' target='_blank' rel='noopener noreferrer' onclick='event.stopPropagation()'>Open HTML</a>" if file_uri else ""}
                            <button class="file-action-btn" onclick='copyFilePath({js_file_path}, this, event)'>Copy Path</button>
                        </div>
                    </div>
                    <div class="file-path">{html_lib.escape(path_str)}</div>
                    <div class="file-metadata">{html_lib.escape(meta_line)}</div>
                </div>
                <div id="{file_id}" class="file-content" style="display:none;">
                    <div class="error-box"><strong>Parsing Failed:</strong> {err_msg}</div>
                </div>
            </div>
            """)
            continue

        buckets = item.get("buckets") or []
        match_rows = ""
        for m_idx, row in enumerate(buckets):
            kind = str(row.get("element_kind", ""))
            text = str(row.get("text", ""))
            href = str(row.get("href", ""))
            outer = str(row.get("html", ""))
            line = row.get("line", "")
            flags = []
            if row.get("in_ref"):
                flags.append("in-ref")
            if row.get("under_comment"):
                flags.append("under-comment")
            if row.get("doi_org_in_href"):
                flags.append("doi.org@href")
            if row.get("doi_org_in_text"):
                flags.append("doi.org@text")
            flag_html = " ".join(
                f'<span class="match-badge">{html_lib.escape(f)}</span>' for f in flags
            )
            uc = "true" if row.get("under_comment") else "false"
            dh = "true" if row.get("doi_org_in_href") else "false"
            dt = "true" if row.get("doi_org_in_text") else "false"
            match_rows += f"""
            <div class="match-item"
                 data-tag="{html_lib.escape(kind)}"
                 data-text="{html_lib.escape(text)}"
                 data-under-comment="{uc}"
                 data-doi-org-href="{dh}"
                 data-doi-org-text="{dt}">
                <div class="match-header">
                    <div class="match-meta">
                        <span class="match-number">#{m_idx + 1}</span>
                        <span class="match-badge">Bucket {row.get("bucket")}</span>
                        <span class="match-tag-badge">{html_lib.escape(kind)}</span>
                        <span class="match-badge">Line {html_lib.escape(str(line))}</span>
                        {flag_html}
                    </div>
                    <button class="copy-btn" onclick="copySnippet(this)">Copy Markup</button>
                </div>
                <div class="text-section">
                    <span class="section-lbl">Href:</span>
                    <div class="text-box"><code>{html_lib.escape(href)}</code></div>
                </div>
                <div class="text-section">
                    <span class="section-lbl">Inner Text Content:</span>
                    <div class="text-box">{html_lib.escape(text)}</div>
                </div>
                <div class="code-section">
                    <span class="section-lbl">Outer HTML/XML Markup:</span>
                    <div class="code-wrapper"><pre><code>{html_lib.escape(outer)}</code></pre></div>
                </div>
            </div>
            """

        sections.append(f"""
        <div class="file-card"
             data-filename="{html_lib.escape(name)}"
             data-doc-type="{html_lib.escape(doc_type)}"
             data-client="{html_lib.escape(client)}"
             data-identifier="{html_lib.escape(identifier)}">
            <div class="file-header" onclick="toggleCard('{file_id}')">
                <div class="file-header-main">
                    <div class="file-title">
                        <span class="toggle-icon">▼</span>
                        <span class="file-badge badge-success">{len(buckets)} Match(es)</span>
                        <strong>{html_lib.escape(name)}</strong>
                    </div>
                    <div class="file-actions">
                        {"<a class='file-action-btn' href='" + html_lib.escape(file_uri) + "' target='_blank' rel='noopener noreferrer' onclick='event.stopPropagation()'>Open HTML</a>" if file_uri else ""}
                        <button class="file-action-btn" onclick='copyFilePath({js_file_path}, this, event)'>Copy Path</button>
                    </div>
                </div>
                <div class="file-path">{html_lib.escape(path_str)}</div>
                <div class="file-metadata">{html_lib.escape(meta_line)}</div>
            </div>
            <div id="{file_id}" class="file-content">
                <div class="matches-list">{match_rows}</div>
            </div>
        </div>
        """)

    body = "\n".join(sections) if sections else "<div class='no-results'>No files with bucket hits.</div>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>DOI / pub-id by ref — {html_lib.escape(target_name)}</title>
<style>
:root {{
  --bg-main:#0b0f19; --bg-card:#111827; --bg-code:#030712; --bg-input:#1f2937;
  --border:#374151; --text:#f3f4f6; --muted:#9ca3af; --primary:#6366f1;
  --success:#10b981; --error:#ef4444; --tag:#38bdf8;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:Segoe UI,sans-serif; background:var(--bg-main); color:var(--text); }}
.container {{ max-width:1200px; margin:0 auto; padding:24px; }}
header {{ display:flex; justify-content:space-between; gap:16px; margin-bottom:20px; flex-wrap:wrap; }}
.stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin-bottom:16px; }}
.stat-card {{ background:var(--bg-card); border:1px solid var(--border); border-radius:10px; padding:14px; }}
.stat-card .lbl {{ display:block; color:var(--muted); font-size:0.8rem; }}
.stat-card .val {{ font-size:1.4rem; font-weight:700; color:var(--primary); }}
.controls-panel {{
  display:flex; flex-wrap:wrap; gap:12px; align-items:center; justify-content:space-between;
  background:var(--bg-card); border:1px solid var(--border); border-radius:10px; padding:12px 16px; margin-bottom:16px;
}}
.filter-row {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; width:100%; }}
.search-container {{ position:relative; flex:1; min-width:220px; }}
.search-icon {{ position:absolute; left:12px; top:50%; transform:translateY(-50%); color:var(--muted); }}
.search-input {{
  width:100%; padding:10px 12px 10px 36px; border-radius:8px; border:1px solid var(--border);
  background:var(--bg-input); color:var(--text);
}}
.filter-select {{
  background:var(--bg-input); color:var(--text); border:1px solid var(--border);
  border-radius:8px; padding:8px 10px; min-width:140px;
}}
.button-group {{ display:flex; gap:8px; }}
.action-btn, .file-action-btn, .copy-btn {{
  background:rgba(99,102,241,0.15); color:var(--text); border:1px solid var(--primary);
  border-radius:6px; padding:8px 12px; cursor:pointer; font-size:0.85rem;
}}
.copy-btn.copied, .file-action-btn.copied {{ background:rgba(16,185,129,0.2); border-color:var(--success); }}
.file-card {{
  background:var(--bg-card); border:1px solid var(--border); border-radius:12px; margin-bottom:14px; overflow:hidden;
}}
.file-card.error-card {{ border-color:var(--error); }}
.file-header {{ padding:14px 16px; cursor:pointer; }}
.file-header-main {{ display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; }}
.file-title {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
.file-path, .file-metadata {{ color:var(--muted); font-size:0.85rem; margin-top:6px; word-break:break-all; }}
.file-badge {{ font-size:0.7rem; font-weight:700; padding:2px 8px; border-radius:4px; text-transform:uppercase; }}
.badge-success {{ background:rgba(16,185,129,0.2); color:var(--success); }}
.badge-error {{ background:rgba(239,68,68,0.2); color:var(--error); }}
.file-content {{ padding:0 16px 16px; }}
.match-item {{
  border:1px solid var(--border); border-radius:8px; padding:12px; margin-top:10px; background:#0f172a;
}}
.match-header {{ display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap; margin-bottom:8px; }}
.match-meta {{ display:flex; flex-wrap:wrap; gap:6px; align-items:center; }}
.match-number, .match-badge, .match-tag-badge {{
  font-size:0.75rem; padding:2px 8px; border-radius:4px; background:rgba(99,102,241,0.2);
}}
.match-tag-badge {{ color:var(--tag); }}
.section-lbl {{ display:block; color:var(--muted); font-size:0.75rem; margin:8px 0 4px; }}
.text-box, .code-wrapper {{
  background:var(--bg-code); border:1px solid var(--border); border-radius:6px; padding:10px; overflow:auto;
}}
.code-wrapper pre {{ margin:0; white-space:pre-wrap; word-break:break-word; color:#cbd5e1; font-size:0.8rem; }}
.error-box {{ color:#fecaca; background:rgba(239,68,68,0.1); padding:12px; border-radius:8px; }}
.no-results {{ color:var(--muted); padding:24px; text-align:center; }}
.toast {{
  position:fixed; bottom:24px; right:24px; background:var(--bg-card); border:1px solid var(--primary);
  color:var(--text); padding:12px 20px; border-radius:8px; opacity:0; transform:translateY(40px);
  transition:all .25s ease; z-index:1000;
}}
.toast.show {{ opacity:1; transform:translateY(0); }}
</style>
</head>
<body>
<div class="container">
  <header>
    <div>
      <h1>DOI / pub-id by ref (unique)</h1>
      <p>Target: <strong>{html_lib.escape(target_name)}</strong></p>
    </div>
    <div style="color:var(--muted)">Generated: {html_lib.escape(ts)}</div>
  </header>

  <div class="stats-grid">
    <div class="stat-card"><span class="lbl">Files scanned</span><span class="val">{scanned_files}</span></div>
    <div class="stat-card"><span class="lbl">Files with hits</span><span class="val">{files_with_hits}</span></div>
    <div class="stat-card"><span class="lbl">Bucket rows</span><span class="val">{total_buckets}</span></div>
  </div>

  <div class="controls-panel">
    <div class="filter-row">
      <div class="search-container">
        <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
        <input type="text" id="searchInput" class="search-input"
               placeholder="Search matches by kind, text, filename, or markup..."
               oninput="applyFilters()"/>
      </div>
      <select id="filterDocType" class="filter-select" onchange="applyFilters()">
        <option value="">All types (Books/Journals…)</option>
        {_opt(doc_types)}
      </select>
      <select id="filterClient" class="filter-select" onchange="applyFilters()">
        <option value="">All clients</option>
        {_opt(clients)}
      </select>
      <select id="filterIdentifier" class="filter-select" onchange="applyFilters()">
        <option value="">All identifiers</option>
        {_opt(identifiers)}
      </select>
      <select id="filterUnderComment" class="filter-select" onchange="applyFilters()">
        <option value="">All — Under comment</option>
        <option value="true">Yes</option>
        <option value="false">No</option>
      </select>
      <select id="filterDoiOrgHref" class="filter-select" onchange="applyFilters()">
        <option value="">All — doi.org href</option>
        <option value="true">Yes</option>
        <option value="false">No</option>
      </select>
      <select id="filterDoiOrgText" class="filter-select" onchange="applyFilters()">
        <option value="">All — doi.org text</option>
        <option value="true">Yes</option>
        <option value="false">No</option>
      </select>
      <div class="button-group">
        <button class="action-btn" onclick="toggleAll(false)">Collapse All</button>
        <button class="action-btn" onclick="toggleAll(true)">Expand All</button>
      </div>
    </div>
  </div>

  <div id="resultsList">
    {body}
  </div>
</div>

<div id="toast" class="toast"><span id="toastMsg">Copied!</span></div>

<script>
function toggleCard(id) {{
  const content = document.getElementById(id);
  if (!content) return;
  const card = content.parentElement;
  const icon = card.querySelector('.toggle-icon');
  if (content.style.display === 'none') {{
    content.style.display = 'block';
    if (icon) icon.textContent = '▼';
  }} else {{
    content.style.display = 'none';
    if (icon) icon.textContent = '▶';
  }}
}}

function toggleAll(expand) {{
  document.querySelectorAll('.file-card').forEach(card => {{
    if (card.style.display === 'none') return;
    const content = card.querySelector('.file-content');
    const icon = card.querySelector('.toggle-icon');
    if (!content) return;
    content.style.display = expand ? 'block' : 'none';
    if (icon) icon.textContent = expand ? '▼' : '▶';
  }});
}}

function copySnippet(btn) {{
  const matchItem = btn.closest('.match-item');
  const codeEl = matchItem && matchItem.querySelector('.code-wrapper code');
  if (!codeEl) return;
  navigator.clipboard.writeText(codeEl.textContent).then(() => {{
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    showToast('Markup copied to clipboard!');
    setTimeout(() => {{ btn.textContent = 'Copy Markup'; btn.classList.remove('copied'); }}, 2000);
  }}).catch(() => showToast('Failed to copy markup.'));
}}

function copyFilePath(filePath, btn, event) {{
  if (event) event.stopPropagation();
  navigator.clipboard.writeText(filePath).then(() => {{
    const original = btn.textContent;
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    showToast('File path copied to clipboard!');
    setTimeout(() => {{ btn.textContent = original; btn.classList.remove('copied'); }}, 2000);
  }}).catch(() => showToast('Failed to copy file path.'));
}}

function showToast(msg) {{
  const toast = document.getElementById('toast');
  document.getElementById('toastMsg').textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2500);
}}

function applyFilters() {{
  const searchVal = (document.getElementById('searchInput').value || '').toLowerCase().trim();
  const docType = document.getElementById('filterDocType').value;
  const client = document.getElementById('filterClient').value;
  const identifier = document.getElementById('filterIdentifier').value;
  const underComment = document.getElementById('filterUnderComment').value;
  const doiOrgHref = document.getElementById('filterDoiOrgHref').value;
  const doiOrgText = document.getElementById('filterDoiOrgText').value;

  document.querySelectorAll('.file-card').forEach(card => {{
    if (docType && card.getAttribute('data-doc-type') !== docType) {{
      card.style.display = 'none'; return;
    }}
    if (client && card.getAttribute('data-client') !== client) {{
      card.style.display = 'none'; return;
    }}
    if (identifier && card.getAttribute('data-identifier') !== identifier) {{
      card.style.display = 'none'; return;
    }}

    const filename = (card.getAttribute('data-filename') || '').toLowerCase();
    if (card.classList.contains('error-card')) {{
      card.style.display = (!searchVal || filename.includes(searchVal)) ? 'block' : 'none';
      return;
    }}

    let fileVisible = false;
    card.querySelectorAll('.match-item').forEach(item => {{
      const tag = (item.getAttribute('data-tag') || '').toLowerCase();
      const text = (item.getAttribute('data-text') || '').toLowerCase();
      const codeEl = item.querySelector('.code-wrapper code');
      const code = codeEl ? codeEl.textContent.toLowerCase() : '';
      const searchOk = !searchVal || tag.includes(searchVal) || text.includes(searchVal)
        || code.includes(searchVal) || filename.includes(searchVal);
      const flagOk = (!underComment || item.getAttribute('data-under-comment') === underComment)
        && (!doiOrgHref || item.getAttribute('data-doi-org-href') === doiOrgHref)
        && (!doiOrgText || item.getAttribute('data-doi-org-text') === doiOrgText);
      const isMatch = searchOk && flagOk;
      item.style.display = isMatch ? 'block' : 'none';
      if (isMatch) fileVisible = true;
    }});
    card.style.display = fileVisible ? 'block' : 'none';
  }});
}}
</script>
</body>
</html>
"""

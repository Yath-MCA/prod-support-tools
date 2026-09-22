"""Progressive Element Extractor report artifacts (by_docid + index.js)."""
from __future__ import annotations

import html as html_lib
import json
import re
import shutil
import time
from datetime import datetime
from pathlib import Path


def _safe_id(raw: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", (raw or "").strip())[:120]
    return s or "item"


class EEReportStore:
    def __init__(
        self,
        run_folder: Path,
        *,
        kind: str,
        source_path: str,
        flush_every: int = 10,
        flush_interval_s: float = 1.5,
    ):
        self.run_folder = Path(run_folder)
        self.kind = kind
        self.source_path = source_path
        self.flush_every = max(1, int(flush_every))
        self.flush_interval_s = float(flush_interval_s)
        self.run_folder.mkdir(parents=True, exist_ok=True)
        self.by_docid_dir = self.run_folder / "by_docid"
        # Legacy alias — P0 no longer uses partials/
        self.partials_dir = self.run_folder / "partials"
        self._files: list[dict] = []
        self._writes_since_flush = 0
        self._last_flush_monotonic = time.monotonic()
        self._dirty = False
        self._last_status = "running"
        self._last_stats: dict = {}

    def snapshot_run_meta(self, scan_root: Path) -> Path | None:
        scan_root = Path(scan_root)
        for candidate in (scan_root / "meta.json", scan_root.parent / "meta.json"):
            if candidate.is_file():
                dest = self.run_folder / "run_meta.json"
                shutil.copy2(candidate, dest)
                return dest
        return None

    def write_manifest(self, dtd_filter: str, client_filter: str, files: list[dict]) -> Path:
        payload = {
            "source_path": self.source_path,
            "dtd_filter": dtd_filter or "",
            "client_filter": client_filter or "",
            "files": files,
        }
        path = self.run_folder / "manifest.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def match_stats(self) -> tuple[int, int]:
        """Return (files_with_hits, bucket_rows) from in-memory records."""
        files_with = sum(1 for r in self._files if r.get("ok") and r.get("matches"))
        bucket_rows = sum(len(r.get("matches") or []) for r in self._files if r.get("ok"))
        return files_with, bucket_rows

    def write_result(self, file_record: dict) -> Path:
        """Write by_docid/<id>.js once; keep record in memory. Does not flush index."""
        self.by_docid_dir.mkdir(parents=True, exist_ok=True)
        fid = _safe_id(str(file_record.get("id") or file_record.get("path") or "file"))
        record = dict(file_record)
        record["result_ref"] = f"by_docid/{fid}.js"
        path = self.by_docid_dir / f"{fid}.js"
        body = json.dumps(record, ensure_ascii=False)
        path.write_text(
            "window.__EE_DOC__ = window.__EE_DOC__ || {};\n"
            f"window.__EE_DOC__[{json.dumps(fid)}] = {body};\n",
            encoding="utf-8",
        )
        replaced = False
        for i, existing in enumerate(self._files):
            existing_id = _safe_id(str(existing.get("id") or existing.get("path") or "file"))
            if existing_id == fid:
                self._files[i] = record
                replaced = True
                break
        if not replaced:
            self._files.append(record)
        self._writes_since_flush += 1
        self._dirty = True
        return path

    # Compat for older call sites / tests during transition
    def write_partial(self, file_record: dict) -> Path:
        return self.write_result(file_record)

    def _index_payload(self, *, status: str, stats: dict | None = None) -> dict:
        return {
            "version": 1,
            "kind": self.kind,
            "status": status,
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_path": self.source_path,
            "stats": stats if stats is not None else self._last_stats,
            "files": list(self._files),
        }

    def _write_index_js(self, payload: dict) -> Path:
        path = self.run_folder / "index.js"
        body = json.dumps(payload, ensure_ascii=False)
        path.write_text(
            f"window.__EE_INDEX__ = {body};\n"
            "window.__EE_REPORT__ = window.__EE_INDEX__;\n",
            encoding="utf-8",
        )
        return path

    def flush_index(self, *, status: str, stats: dict | None = None) -> Path:
        """Always write index.js from in-memory records (no disk reload)."""
        if stats is not None:
            self._last_stats = dict(stats)
        self._last_status = status
        path = self._write_index_js(self._index_payload(status=status, stats=self._last_stats))
        self._writes_since_flush = 0
        self._last_flush_monotonic = time.monotonic()
        self._dirty = False
        return path

    def maybe_flush_index(self, *, status: str, stats: dict | None = None) -> Path | None:
        """Flush when dirty and (N writes since last flush or interval elapsed)."""
        if not self._dirty:
            return None
        due_n = self._writes_since_flush >= self.flush_every
        due_t = (time.monotonic() - self._last_flush_monotonic) >= self.flush_interval_s
        if not (due_n or due_t):
            return None
        return self.flush_index(status=status, stats=stats)

    def rebuild_report_data(self, *, status: str, stats: dict | None = None) -> Path:
        """Force flush index (compat name used by DOI coordinator)."""
        return self.flush_index(status=status, stats=stats)

    def finalize(self, *, status: str, stats: dict | None = None) -> Path:
        """Final index flush; retain by_docid/."""
        return self.flush_index(status=status, stats=stats)

    def write_shell_html(self, html_name: str, title: str) -> Path:
        return self.write_doi_shell_html(html_name, title)

    def write_doi_shell_html(self, html_name: str, title: str) -> Path:
        path = self.run_folder / html_name
        path.write_text(doi_shell_html(title), encoding="utf-8")
        return path


def doi_shell_html(title: str) -> str:
    """Thin DOI/pub-id report shell; data comes from index.js."""
    safe_title = html_lib.escape(title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{safe_title}</title>
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
.file-metadata {{ color:var(--muted); font-size:0.85rem; margin-top:6px; word-break:break-all; }}
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
.status-pill {{ font-size:0.8rem; color:var(--muted); }}
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
      <p>Target: <strong id="targetName"></strong>
        <span class="status-pill" id="runStatus"></span></p>
    </div>
    <div style="color:var(--muted)" id="generatedAt"></div>
  </header>

  <div class="stats-grid">
    <div class="stat-card"><span class="lbl">Files scanned</span><span class="val" id="statScanned">0</span></div>
    <div class="stat-card"><span class="lbl">Files with hits</span><span class="val" id="statHits">0</span></div>
    <div class="stat-card"><span class="lbl">Bucket rows</span><span class="val" id="statBuckets">0</span></div>
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
      </select>
      <select id="filterClient" class="filter-select" onchange="applyFilters()">
        <option value="">All clients</option>
      </select>
      <select id="filterIdentifier" class="filter-select" onchange="applyFilters()">
        <option value="">All identifiers</option>
      </select>
      <select id="filterProjectShortcode" class="filter-select" onchange="applyFilters()">
        <option value="">All project-shortcodes</option>
      </select>
      <select id="filterElementKind" class="filter-select" onchange="applyFilters()">
        <option value="">All kinds (doi / uri / pub-id)</option>
        <option value="doi">doi</option>
        <option value="uri">uri</option>
        <option value="pub-id">pub-id</option>
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

  <div id="resultsList"><div class="no-results">Waiting for results…</div></div>
</div>

<div id="toast" class="toast"><span id="toastMsg">Copied!</span></div>

<script src="index.js"></script>
<script>
function esc(s) {{
  return String(s == null ? '' : s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}}

function reportData() {{
  return window.__EE_INDEX__ || window.__EE_REPORT__;
}}

function fillSelect(id, values, blankLabel) {{
  const sel = document.getElementById(id);
  const cur = sel.value;
  sel.innerHTML = '<option value="">' + esc(blankLabel) + '</option>';
  (values || []).forEach(v => {{
    const o = document.createElement('option');
    o.value = v; o.textContent = v;
    sel.appendChild(o);
  }});
  if (cur) sel.value = cur;
}}

function fileUri(path) {{
  try {{
    if (!path) return '';
    let p = String(path).replace(/\\\\/g, '/');
    if (/^[A-Za-z]:/.test(p)) p = '/' + p;
    return 'file://' + encodeURI(p);
  }} catch (e) {{ return ''; }}
}}

function renderReport() {{
  const d = reportData();
  if (!d) {{
    document.getElementById('resultsList').innerHTML = '<div class="no-results">No data</div>';
    return;
  }}
  const files = d.files || [];
  const visible = files.filter(f => !f.ok || (f.matches && f.matches.length));
  const hits = visible.filter(f => f.ok && f.matches && f.matches.length);
  const buckets = hits.reduce((n, f) => n + (f.matches || []).length, 0);
  const stats = d.stats || {{}};
  document.getElementById('targetName').textContent = (d.source_path || '').split(/[/\\\\]/).pop() || '';
  document.getElementById('runStatus').textContent = d.status ? '(' + d.status + ')' : '';
  document.getElementById('generatedAt').textContent = 'Generated: ' + (d.generated || '');
  document.getElementById('statScanned').textContent = stats.files_total || stats.files_scanned || files.length;
  document.getElementById('statHits').textContent = stats.files_with_hits != null ? stats.files_with_hits : hits.length;
  document.getElementById('statBuckets').textContent = stats.bucket_rows != null ? stats.bucket_rows : buckets;

  const docTypes = [...new Set(visible.map(f => f.doc_type).filter(Boolean))].sort();
  const clients = [...new Set(visible.map(f => f.client).filter(Boolean))].sort();
  const idents = [...new Set(visible.map(f => f.identifier).filter(Boolean))].sort();
  const shortcodes = [...new Set(visible.map(f => f.project_shortcode).filter(Boolean))].sort();
  fillSelect('filterDocType', docTypes, 'All types (Books/Journals…)');
  fillSelect('filterClient', clients, 'All clients');
  fillSelect('filterIdentifier', idents, 'All identifiers');
  fillSelect('filterProjectShortcode', shortcodes, 'All project-shortcodes');

  if (!visible.length) {{
    document.getElementById('resultsList').innerHTML =
      '<div class="no-results">' + (d.status === 'running' ? 'Waiting for results…' : 'No files with bucket hits.') + '</div>';
    return;
  }}

  let html = '';
  visible.forEach((item, idx) => {{
    const fileId = 'file-' + idx;
    const name = item.name || (item.path || '').split(/[/\\\\]/).pop() || '';
    const metaLine = [item.doc_type, item.client, item.link_info, item.identifier, item.project_shortcode]
      .filter(Boolean).join(' | ');
    const uri = fileUri(item.path);
    if (!item.ok) {{
      html += '<div class="file-card error-card" data-filename="' + esc(name) + '" data-doc-type="' + esc(item.doc_type||'') +
        '" data-client="' + esc(item.client||'') + '" data-identifier="' + esc(item.identifier||'') +
        '" data-project-shortcode="' + esc(item.project_shortcode||'') + '">' +
        '<div class="file-header" onclick="toggleCard(\\'' + fileId + '\\')"><div class="file-header-main"><div class="file-title">' +
        '<span class="toggle-icon">▶</span><span class="file-badge badge-error">Error</span><strong>' + esc(name) + '</strong></div>' +
        '<div class="file-actions">' +
        (uri ? '<a class="file-action-btn" href="' + esc(uri) + '" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()">Open HTML</a>' : '') +
        '<button class="file-action-btn" onclick=\\'copyFilePath(' + JSON.stringify(item.path||'') + ', this, event)\\'>Copy Path</button></div></div>' +
        '<div class="file-metadata">' + esc(metaLine) + '</div></div>' +
        '<div id="' + fileId + '" class="file-content" style="display:none;"><div class="error-box"><strong>Parsing Failed:</strong> ' +
        esc(item.error||'') + '</div></div></div>';
      return;
    }}
    const matches = item.matches || [];
    let matchHtml = '';
    matches.forEach((m, mi) => {{
      const kind = m.element_kind || m.kind || '';
      const flags = [];
      if (m.in_ref) flags.push('in-ref');
      if (m.under_comment) flags.push('under-comment');
      if (m.doi_org_in_href) flags.push('doi.org@href');
      if (m.doi_org_in_text) flags.push('doi.org@text');
      const flagHtml = flags.map(f => '<span class="match-badge">' + esc(f) + '</span>').join(' ');
      matchHtml += '<div class="match-item" data-tag="' + esc(kind) + '" data-text="' + esc(m.text||'') +
        '" data-under-comment="' + (m.under_comment ? 'true' : 'false') +
        '" data-doi-org-href="' + (m.doi_org_in_href ? 'true' : 'false') +
        '" data-doi-org-text="' + (m.doi_org_in_text ? 'true' : 'false') + '">' +
        '<div class="match-header"><div class="match-meta">' +
        '<span class="match-number">#' + (mi+1) + '</span>' +
        '<span class="match-badge">Bucket ' + esc(m.bucket) + '</span>' +
        '<span class="match-tag-badge">' + esc(kind) + '</span>' +
        '<span class="match-badge">Line ' + esc(m.line) + '</span>' + flagHtml +
        '</div><button class="copy-btn" onclick="copySnippet(this)">Copy Markup</button></div>' +
        '<div class="text-section"><span class="section-lbl">Href:</span><div class="text-box"><code>' + esc(m.href||'') +
        '</code></div></div>' +
        '<div class="text-section"><span class="section-lbl">Inner Text Content:</span><div class="text-box">' +
        esc(m.text||'') + '</div></div>' +
        '<div class="code-section"><span class="section-lbl">Outer HTML/XML Markup:</span>' +
        '<div class="code-wrapper"><pre><code>' + esc(m.html||'') + '</code></pre></div></div></div>';
    }});
    html += '<div class="file-card" data-filename="' + esc(name) + '" data-doc-type="' + esc(item.doc_type||'') +
      '" data-client="' + esc(item.client||'') + '" data-identifier="' + esc(item.identifier||'') +
      '" data-project-shortcode="' + esc(item.project_shortcode||'') + '">' +
      '<div class="file-header" onclick="toggleCard(\\'' + fileId + '\\')"><div class="file-header-main"><div class="file-title">' +
      '<span class="toggle-icon">▼</span><span class="file-badge badge-success">' + matches.length + ' Match(es)</span><strong>' +
      esc(name) + '</strong></div><div class="file-actions">' +
      (uri ? '<a class="file-action-btn" href="' + esc(uri) + '" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()">Open HTML</a>' : '') +
      '<button class="file-action-btn" onclick=\\'copyFilePath(' + JSON.stringify(item.path||'') + ', this, event)\\'>Copy Path</button></div></div>' +
      '<div class="file-metadata">' + esc(metaLine) + '</div></div>' +
      '<div id="' + fileId + '" class="file-content"><div class="matches-list">' + matchHtml + '</div></div></div>';
  }});
  document.getElementById('resultsList').innerHTML = html;
  applyFilters();
}}

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
  const projectShortcode = document.getElementById('filterProjectShortcode').value;
  const elementKind = document.getElementById('filterElementKind').value;
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
    if (projectShortcode && card.getAttribute('data-project-shortcode') !== projectShortcode) {{
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
      const kindOk = !elementKind || item.getAttribute('data-tag') === elementKind;
      const isMatch = searchOk && flagOk && kindOk;
      item.style.display = isMatch ? 'block' : 'none';
      if (isMatch) fileVisible = true;
    }});
    card.style.display = fileVisible ? 'block' : 'none';
  }});
}}

renderReport();
setInterval(function() {{
  const d = reportData();
  if (!d || d.status !== 'running') return;
  const s = document.createElement('script');
  s.src = 'index.js?t=' + Date.now();
  s.onload = function() {{ renderReport(); }};
  document.body.appendChild(s);
}}, 1500);
</script>
</body>
</html>
"""

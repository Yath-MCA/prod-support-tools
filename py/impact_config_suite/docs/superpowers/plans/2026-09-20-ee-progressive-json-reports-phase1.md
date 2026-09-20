# Progressive JSON Reports (Phase 1: DOI/pub-id) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** For DOI/pub-id by-ref runs, write a thin HTML shell + progressive `report-data.js` under the run folder using safe partials → merge → cleanup, snapshot `run_meta.json` / `manifest.json`, and open the primary report once when the first result is ready.

**Architecture:** New `core/ee_report_store.py` owns run-folder artifacts (meta snapshot, manifest, partials, merge to `report-data.js`). DOI HTML becomes a shell that loads `report-data.js` and renders client-side (same filters/UX as today). `_write_doi_pubid_by_ref_outputs` coordinates: init store → collect files → per-file partial → rebuild data JS → open once → final merge/CSV. Phase 2+ (detailed extract) is out of this plan.

**Tech Stack:** Python 3, pathlib/json, existing DOI extract helpers, Tk Element Extractor tab, pytest, vanilla JS in HTML shell.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-20-ee-progressive-json-reports-design.md`
- Phase 1 only: DOI / pub-id by-ref
- `report-data.js` exports `window.__EE_REPORT__ = …` (file:// safe)
- Partials under `{run_folder}/partials/`; deleted after successful final merge
- Single writer for `report-data.js` (coordinator / main scan loop — DOI loop stays sequential in Phase 1)
- Open primary HTML once on first partial when `open_report` is True; do not open primary again at end
- Checkbox label: “Open HTML report in browser when first results are ready”
- Work under `py/impact_config_suite`; TDD; commit only when user asks; exclude `config/build_metadata.json`

## File Map

| File | Responsibility |
|------|----------------|
| `core/ee_report_store.py` (create) | Snapshot meta, manifest, write partial, merge, write `report-data.js`, cleanup partials, write DOI shell HTML |
| `core/doi_pubid_by_ref.py` (modify) | Keep CSV + extract; stop embedding full data HTML (shell moved to store) or keep `generate_doi_pubid_by_ref_html` as thin wrapper calling store |
| `tabs/element_extractor_tab.py` (modify) | Wire progressive DOI writer + open-once; checkbox label |
| `tests/test_ee_report_store.py` (create) | Store/merge/cleanup/meta/manifest |
| `tests/test_doi_pubid_by_ref.py` (modify) | Shell + `__EE_REPORT__` / `report-data.js` expectations |

---

### Task 1: `ee_report_store` — meta, partials, merge, `report-data.js` (TDD)

**Files:**
- Create: `py/impact_config_suite/core/ee_report_store.py`
- Test: `py/impact_config_suite/tests/test_ee_report_store.py`

**Interfaces:**
- Produces:
  - `class EEReportStore`
  - `EEReportStore(run_folder: Path, *, kind: str, source_path: str)`
  - `snapshot_run_meta(scan_root: Path) -> Path | None`
  - `write_manifest(dtd_filter: str, client_filter: str, files: list[dict]) -> Path`
  - `write_partial(file_record: dict) -> Path`  # file_record matches schema `files[]` item
  - `rebuild_report_data(*, status: str, stats: dict | None = None) -> Path`
  - `finalize(*, status: str, stats: dict | None = None) -> Path`  # merge + delete partials/
  - `write_shell_html(html_name: str, title: str) -> Path`
  - `partials_dir` property
- Consumes: `core.meta_json_filters.load_meta_for_scan_root` (optional for finding source meta path to copy)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_ee_report_store.py
import json
from pathlib import Path

from core.ee_report_store import EEReportStore


def test_snapshot_run_meta_copies_nearest_meta(tmp_path):
    scan = tmp_path / "JATS"
    scan.mkdir()
    (scan / "meta.json").write_text(json.dumps({"N1": {"client": "TNF", "dtd": "JATS"}}), encoding="utf-8")
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="doi_pubid_by_ref", source_path=str(scan))
    out = store.snapshot_run_meta(scan)
    assert out is not None
    assert out.name == "run_meta.json"
    assert json.loads(out.read_text(encoding="utf-8"))["N1"]["client"] == "TNF"


def test_snapshot_run_meta_none_when_missing(tmp_path):
    scan = tmp_path / "JATS"
    scan.mkdir()
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="doi_pubid_by_ref", source_path=str(scan))
    assert store.snapshot_run_meta(scan) is None
    assert not (run / "run_meta.json").exists()


def test_write_partial_and_finalize_merges_and_cleans(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="doi_pubid_by_ref", source_path=str(tmp_path))
    store.write_shell_html("report.html", "DOI test")
    store.write_manifest("", "TNF", [{"docid": "N1", "path": "a.html"}])
    store.write_partial({
        "id": "f1", "path": "a.html", "name": "a.html",
        "doc_type": "Journals", "client": "TNF", "link_info": "", "identifier": "DOC1",
        "ok": True, "error": "", "matches": [{"bucket": 1, "element_kind": "pub-id"}],
    })
    store.write_partial({
        "id": "f2", "path": "b.html", "name": "b.html",
        "doc_type": "Journals", "client": "TNF", "link_info": "", "identifier": "DOC2",
        "ok": True, "error": "", "matches": [],
    })
    assert (run / "partials").is_dir()
    data_path = store.finalize(status="complete", stats={"files_scanned": 2})
    assert data_path.name == "report-data.js"
    text = data_path.read_text(encoding="utf-8")
    assert text.startswith("window.__EE_REPORT__ = ")
    assert "doi_pubid_by_ref" in text
    assert '"status": "complete"' in text or '"status":"complete"' in text
    assert not (run / "partials").exists()
    # JS must be valid-ish: extract JSON
    payload = json.loads(text.split("=", 1)[1].strip().rstrip(";"))
    assert len(payload["files"]) == 2


def test_rebuild_keeps_partials(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="doi_pubid_by_ref", source_path=str(tmp_path))
    store.write_partial({
        "id": "f1", "path": "a.html", "name": "a.html",
        "doc_type": "", "client": "", "link_info": "", "identifier": "",
        "ok": True, "error": "", "matches": [{"bucket": 5}],
    })
    store.rebuild_report_data(status="running")
    assert (run / "partials").is_dir()
    assert (run / "report-data.js").is_file()
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd C:\_IMPACT\prod-support-tools\py\impact_config_suite
python -m pytest tests/test_ee_report_store.py -v
```

Expected: import error.

- [ ] **Step 3: Implement `core/ee_report_store.py`**

```python
"""Progressive Element Extractor report artifacts (partials → report-data.js)."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def _safe_id(raw: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", raw.strip())[:120]
    return s or "item"


class EEReportStore:
    def __init__(self, run_folder: Path, *, kind: str, source_path: str):
        self.run_folder = Path(run_folder)
        self.kind = kind
        self.source_path = source_path
        self.run_folder.mkdir(parents=True, exist_ok=True)
        self.partials_dir = self.run_folder / "partials"

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

    def write_partial(self, file_record: dict) -> Path:
        self.partials_dir.mkdir(parents=True, exist_ok=True)
        fid = _safe_id(str(file_record.get("id") or file_record.get("path") or "file"))
        path = self.partials_dir / f"{fid}.json"
        path.write_text(json.dumps(file_record, ensure_ascii=False), encoding="utf-8")
        return path

    def _load_partials(self) -> list[dict]:
        if not self.partials_dir.is_dir():
            return []
        rows = []
        for p in sorted(self.partials_dir.glob("*.json")):
            try:
                rows.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return rows

    def _write_report_data_js(self, payload: dict) -> Path:
        path = self.run_folder / "report-data.js"
        body = json.dumps(payload, ensure_ascii=False)
        path.write_text(f"window.__EE_REPORT__ = {body};\n", encoding="utf-8")
        return path

    def rebuild_report_data(self, *, status: str, stats: dict | None = None) -> Path:
        files = self._load_partials()
        payload = {
            "version": 1,
            "kind": self.kind,
            "status": status,
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_path": self.source_path,
            "stats": stats or {},
            "files": files,
        }
        return self._write_report_data_js(payload)

    def finalize(self, *, status: str, stats: dict | None = None) -> Path:
        path = self.rebuild_report_data(status=status, stats=stats)
        if self.partials_dir.exists():
            shutil.rmtree(self.partials_dir, ignore_errors=True)
        return path

    def write_shell_html(self, html_name: str, title: str) -> Path:
        # Minimal placeholder; Task 2 replaces with full DOI UI shell.
        path = self.run_folder / html_name
        path.write_text(
            f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/><title>{title}</title></head>
<body>
<div id="app">Loading report…</div>
<script src="report-data.js"></script>
<script>
function render() {{
  const d = window.__EE_REPORT__;
  document.getElementById('app').textContent = d
    ? (d.status + ' — ' + (d.files || []).length + ' file(s)')
    : 'No data';
}}
render();
setInterval(function() {{
  if (window.__EE_REPORT__ && window.__EE_REPORT__.status === 'running') {{
    const s = document.createElement('script');
    s.src = 'report-data.js?t=' + Date.now();
    s.onload = render;
    document.body.appendChild(s);
  }}
}}, 1500);
</script>
</body></html>
""",
            encoding="utf-8",
        )
        return path
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/test_ee_report_store.py -v
```

- [ ] **Step 5: Commit (only if user requested)**

```bash
git add py/impact_config_suite/core/ee_report_store.py py/impact_config_suite/tests/test_ee_report_store.py
git commit -m "Add EE report store for progressive partials and report-data.js."
```

---

### Task 2: DOI shell HTML that renders `__EE_REPORT__` (filters parity)

**Files:**
- Modify: `py/impact_config_suite/core/ee_report_store.py` (`write_doi_pubid_shell_html` or expand `write_shell_html` when kind is doi)
- Modify: `py/impact_config_suite/core/doi_pubid_by_ref.py` — add helper to map bucket rows → `matches[]`; deprecate/replace monolithic `generate_doi_pubid_by_ref_html` body with shell+data OR keep function as wrapper that only writes via store in tests
- Test: `py/impact_config_suite/tests/test_doi_pubid_by_ref.py`

**Interfaces:**
- Produces: shell HTML containing controls (search, Collapse/Expand, doc-type/client/identifier/flag filters, Copy Markup / Open HTML / Copy Path, Outer HTML/XML) reading from `window.__EE_REPORT__`
- Match objects for DOI: include `bucket`, `element_kind`, `in_ref`, `under_comment`, `doi_org_in_href`, `doi_org_in_text`, `line`, `href`, `text`, `html`

- [ ] **Step 1: Failing test — shell references report-data.js and key UI strings**

```python
def test_doi_shell_html_loads_report_data_js(tmp_path):
    from core.ee_report_store import EEReportStore
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="doi_pubid_by_ref", source_path=str(tmp_path))
    html_path = store.write_doi_shell_html("DOI_PubID_By_Ref_x.html", "DOI / pub-id by ref")
    text = html_path.read_text(encoding="utf-8")
    assert 'src="report-data.js"' in text
    assert "filterUnderComment" in text
    assert "Outer HTML/XML Markup" in text
    assert "Copy Markup" in text
```

- [ ] **Step 2: Implement `write_doi_shell_html`**

Port the existing CSS/JS UX from `generate_doi_pubid_by_ref_html` into a **static** shell that:
- Does not embed file sections in Python
- On load / poll: reads `__EE_REPORT__`, builds file cards from `files[]` where `ok===false` or `matches.length>0`
- Maps DOI `matches` fields to the same badges/filters (`data-under-comment`, etc.)
- Polls by re-inserting `<script src="report-data.js?t=…">` while `status==="running"`

Keep `generate_doi_pubid_by_ref_html(file_results, …)` as a **compat helper for tests** that: creates a temp store under a tmp folder OR builds payload + shell string for in-memory assert — simplest path for Phase 1:

```python
def generate_doi_pubid_by_ref_html(file_results, target_path, ts=None) -> str:
    # Compat: return shell HTML only (data expected beside file when written via store).
    # For unit tests that only check substrings, include marker strings in shell.
    return EEReportStore._doi_shell_template(title=f"DOI / pub-id by ref — {os.path.basename(target_path)}")
```

Update `test_html_omits_empty_files_and_has_controls` to drive **store path**: write partials + shell + finalize, then assert `report-data.js` omits empty matches and shell has controls.

- [ ] **Step 3: Run DOI + store tests**

```bash
python -m pytest tests/test_ee_report_store.py tests/test_doi_pubid_by_ref.py -v
```

- [ ] **Step 4: Commit if requested**

```bash
git commit -m "Add DOI progressive HTML shell bound to report-data.js."
```

---

### Task 3: Wire `_write_doi_pubid_by_ref_outputs` + open-once + checkbox label

**Files:**
- Modify: `py/impact_config_suite/tabs/element_extractor_tab.py`

**Interfaces:**
- Consumes: `EEReportStore`, `extract_buckets_from_file`, `write_doi_pubid_by_ref_csv`
- Produces: progressive artifacts; returns primary HTML path; opens browser once

- [ ] **Step 1: Update checkbox label**

```python
text="Open HTML report in browser when first results are ready",
```

- [ ] **Step 2: Rewrite DOI writer flow**

Pseudocode for `_write_doi_pubid_by_ref_outputs`:

```python
report_name = f"DOI_PubID_By_Ref_{safe_target_name}_{ts}.html"
csv_name = f"DOI_PubID_By_Ref_{safe_target_name}_{ts}.csv"
store = EEReportStore(run_folder, kind="doi_pubid_by_ref", source_path=str(source_path))
store.snapshot_run_meta(source_path if source_path.is_dir() else source_path.parent)
# collect file_list as today…
manifest_files = [{"docid": fp.parent.name, "path": str(fp)} for fp in file_list]
store.write_manifest(dtd_filter if … else "", client_filter if … else "", manifest_files)
report_path = store.write_doi_shell_html(report_name, f"DOI / pub-id by ref — {safe_target_name}")
store.rebuild_report_data(status="running", stats={"files_scanned": 0, "files_total": len(file_list)})

opened = False
open_report = bool(settings.get("open_report", True))
file_results_for_csv = []

for i, fp in enumerate(file_list, 1):
    if self.cancelled: break
    # progress UI as today
    parsed = extract_buckets_from_file(fp)
    meta = self.extractor.get_file_metadata(fp)
    buckets = parsed.get("buckets") or []
    matches = [ {**bucket_fields_as_match(b)} for b in buckets ]
    record = {
        "id": fp.parent.name + "_" + fp.name,
        "path": str(fp.absolute()),
        "name": fp.name,
        "doc_type": meta.get("doc_type", ""),
        "client": meta.get("client", ""),
        "link_info": meta.get("link_info", ""),
        "identifier": meta.get("identifier", ""),
        "ok": parsed.get("ok", False),
        "error": parsed.get("error", ""),
        "matches": matches,
    }
    store.write_partial(record)
    store.rebuild_report_data(
        status="running",
        stats={"files_done": i, "files_total": len(file_list)},
    )
    file_results_for_csv.append({… legacy shape with buckets for CSV …})
    if open_report and not opened:
        webbrowser.open(f"file:///{report_path}")
        opened = True

status = "cancelled" if self.cancelled else "complete"
if self.cancelled and not file_results_for_csv:
    store.finalize(status="cancelled")
    return ""
store.finalize(status=status, stats={…})
write_doi_pubid_by_ref_csv(file_results_for_csv, run_folder / csv_name)
# Do NOT webbrowser.open primary again here — caller must skip if already progressive
return str(Path(report_path).absolute())
```

- [ ] **Step 3: Change DOI completion open**

Where today:

```python
if open_report and report_path:
    webbrowser.open(...)
```

Use a flag from writer, e.g. return `(report_path, opened_early)` or set `self._doi_report_opened_early = True` and skip end open when True.

- [ ] **Step 4: Manual / automated smoke**

```bash
python -m pytest tests/test_ee_report_store.py tests/test_doi_pubid_by_ref.py -v
```

Optional: short script creating tmp tree + calling store loop.

- [ ] **Step 5: Commit if requested**

```bash
git commit -m "Wire DOI/pub-id runs to progressive report-data.js with open-once."
```

---

## Spec coverage (Phase 1)

| Spec item | Task |
|-----------|------|
| Thin HTML + report-data.js | 1–2 |
| run_meta.json / manifest.json | 1, 3 |
| Partials → merge → delete | 1, 3 |
| Single writer | 3 (sequential DOI loop) |
| Open once on first result | 3 |
| Checkbox label | 3 |
| DOI filters/UX parity | 2 |
| Phase 2 extract reports | Deferred |

## Deferred (not this plan)

- Parallel ProcessPool writing partials (safe: workers write only `partials/<id>.json`; coordinator merges)
- Detailed / Unique / mixed HTML migration
- Lazy outer-markup chunks

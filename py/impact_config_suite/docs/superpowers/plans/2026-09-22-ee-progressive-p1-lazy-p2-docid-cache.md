# EE Progressive P1 Lazy Load + P2 Docid Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slim `index.js` and lazy-load match bodies from `by_docid/*.js` on expand (P1); add optional beside-docid `ee_cache/` with same-query skip-parse for DOI/pub-id runs (P2).

**Architecture:** Keep full file records in coordinator memory and in `by_docid/*.js`. On flush, write a **lightweight** `index.js` (`match_count`, `filter_hints`, `result_ref`, meta — no markup). Shell cards render from index; expand injects `<script src="by_docid/….js">` and fills matches. Optional checkbox (default off) writes/reads `{docid_dir}/ee_cache/<slug>.json` using a fixed cache key (`query_type`, `schema_version`, file `mtime`+`size`).

**Tech Stack:** Python 3, Tkinter Element Extractor tab, file:// HTML/JS shell, pytest.

**Spec:** `docs/superpowers/specs/2026-09-22-ee-progressive-by-docid-json-design.md` (P1 + P2 only; P0 already shipped).

## Global Constraints

- Do **not** delete `by_docid/` on finalize (already true in P0).
- Prefer `.js` siblings for `file://` (no `fetch` of JSON required).
- Single writer for `index.js` / `by_docid` (DOI loop stays sequential).
- `ee_cache` writes only when operator opts in (default **off**).
- Do not change DOI six-bucket extract semantics.
- TDD: failing test → implement → green → commit per task.
- Workspace paths relative to `py/impact_config_suite/`.

---

## File structure

| File | Responsibility |
|------|----------------|
| `core/ee_report_store.py` | Slim index payload; keep full records in memory + by_docid |
| `core/ee_report_store.py` (`doi_shell_html`) | Lazy load on expand; filter hints for unloaded cards |
| `core/ee_docid_cache.py` (create) | Cache key, path, read/write/validate for DOI query |
| `tabs/element_extractor_tab.py` | Checkbox + settings; cache hit/miss in DOI loop |
| `tests/test_ee_report_store.py` | Slim index + shell lazy-load strings |
| `tests/test_ee_docid_cache.py` (create) | Hit/miss/invalidation |
| `tests/test_doi_pubid_by_ref.py` | Index has no heavy matches; by_docid retained |

---

### Task 1: Slim index payload (P1 store)

**Files:**
- Modify: `core/ee_report_store.py` (`_index_payload`, add `_slim_file_entry`)
- Test: `tests/test_ee_report_store.py`

**Interfaces:**
- Consumes: existing `write_result` / `_files` (full records with `matches`)
- Produces: `EEReportStore._slim_file_entry(record: dict) -> dict`; `flush_index` writes slim `files[]` only

- [ ] **Step 1: Write the failing test**

Add to `tests/test_ee_report_store.py`:

```python
def test_flush_index_omits_match_bodies(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(
        run, kind="doi_pubid_by_ref", source_path=str(tmp_path),
        flush_every=999, flush_interval_s=999,
    )
    store.write_result({
        "id": "n1_a",
        "path": "a.html",
        "name": "a.html",
        "doc_type": "Journals",
        "client": "TNF",
        "link_info": "",
        "identifier": "DOC1",
        "project_shortcode": "ABC",
        "ok": True,
        "error": "",
        "matches": [
            {
                "bucket": 1,
                "element_kind": "pub-id",
                "under_comment": True,
                "doi_org_in_href": False,
                "doi_org_in_text": True,
                "html": "<pub-id>x</pub-id>",
                "text": "x",
                "href": "",
                "line": 1,
                "in_ref": True,
            }
        ],
    })
    path = store.flush_index(status="complete")
    payload = json.loads(
        path.read_text(encoding="utf-8")
        .split("window.__EE_INDEX__ =", 1)[1]
        .split(";", 1)[0]
        .strip()
    )
    entry = payload["files"][0]
    assert "matches" not in entry
    assert entry["match_count"] == 1
    assert entry["result_ref"] == "by_docid/n1_a.js"
    assert entry["doc_key"] == "n1_a"
    assert entry["filter_hints"]["kinds"] == ["pub-id"]
    assert entry["filter_hints"]["under_comment"] is True
    assert entry["filter_hints"]["doi_org_href"] is False
    assert entry["filter_hints"]["doi_org_text"] is True
    # Full body still on disk for lazy load
    doc_js = (run / "by_docid" / "n1_a.js").read_text(encoding="utf-8")
    assert "<pub-id>x</pub-id>" in doc_js
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ee_report_store.py::test_flush_index_omits_match_bodies -v`  
Expected: FAIL (`matches` still present or missing `filter_hints`)

- [ ] **Step 3: Write minimal implementation**

In `core/ee_report_store.py`, add:

```python
def _slim_file_entry(self, record: dict) -> dict:
    matches = record.get("matches") or []
    kinds = sorted({
        str(m.get("element_kind") or m.get("kind") or "")
        for m in matches
        if (m.get("element_kind") or m.get("kind"))
    })
    fid = _safe_id(str(record.get("id") or record.get("path") or "file"))
    return {
        "id": record.get("id"),
        "doc_key": fid,
        "path": record.get("path", ""),
        "name": record.get("name", ""),
        "doc_type": record.get("doc_type", ""),
        "client": record.get("client", ""),
        "link_info": record.get("link_info", ""),
        "identifier": record.get("identifier", ""),
        "project_shortcode": record.get("project_shortcode", ""),
        "ok": bool(record.get("ok")),
        "error": record.get("error", ""),
        "match_count": len(matches) if record.get("ok") else 0,
        "result_ref": record.get("result_ref") or f"by_docid/{fid}.js",
        "filter_hints": {
            "kinds": kinds,
            "under_comment": any(bool(m.get("under_comment")) for m in matches),
            "doi_org_href": any(bool(m.get("doi_org_in_href")) for m in matches),
            "doi_org_text": any(bool(m.get("doi_org_in_text")) for m in matches),
        },
    }
```

Change `_index_payload` so `"files"` uses `[self._slim_file_entry(r) for r in self._files]` (keep full records in `self._files`).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ee_report_store.py::test_flush_index_omits_match_bodies -v`  
Expected: PASS

Also run: `pytest tests/test_ee_report_store.py tests/test_doi_pubid_by_ref.py -q`  
Expected: update `test_doi_pubid_by_ref.py` / any test that reads `payload["files"][i]["matches"]` — assert matches live in `by_docid` JS instead (do that in Step 4 if failures appear; minimal assert changes only).

- [ ] **Step 5: Commit**

```bash
git add core/ee_report_store.py tests/test_ee_report_store.py tests/test_doi_pubid_by_ref.py
git commit -m "Slim EE index.js to meta and filter hints; keep matches in by_docid."
```

---

### Task 2: Shell lazy-load on expand (P1 UI)

**Files:**
- Modify: `core/ee_report_store.py` (`doi_shell_html` JS)
- Test: `tests/test_ee_report_store.py`

**Interfaces:**
- Consumes: slim index entries with `doc_key`, `result_ref`, `match_count`, `filter_hints`
- Produces: shell JS `loadDoc(docKey, resultRef, cb)`, collapsed-by-default cards, filters using hints until loaded

- [ ] **Step 1: Write the failing test**

```python
def test_doi_shell_has_lazy_load_hooks(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="doi_pubid_by_ref", source_path=str(tmp_path))
    text = store.write_doi_shell_html("r.html", "DOI").read_text(encoding="utf-8")
    assert "function loadDoc(" in text
    assert "window.__EE_DOC__" in text
    assert "data-result-ref" in text
    assert "data-doc-key" in text
    assert "data-loaded" in text
    assert "filter_hints" in text or "filterHints" in text or "data-kinds" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ee_report_store.py::test_doi_shell_has_lazy_load_hooks -v`  
Expected: FAIL (missing `loadDoc`)

- [ ] **Step 3: Write minimal implementation**

Update `doi_shell_html` rendering behavior:

1. File cards include `data-doc-key`, `data-result-ref`, `data-loaded="0"`, and hint attributes:
   - `data-kinds` = comma-joined `filter_hints.kinds`
   - `data-under-comment` / `data-doi-org-href` / `data-doi-org-text` = `"true"` if any match has that flag (from hints), else `"false"` (use `"mixed"` only if you need three-state — prefer any=true for file-level pre-filter).
2. Match list container starts empty; content `display:none` (collapsed).
3. `toggleCard(fileId)`:
   - If expanding and `data-loaded !== "1"`, call `loadDoc(docKey, resultRef, () => { renderMatches(...); data-loaded=1; show; })`.
   - Else toggle display as today.
4. `loadDoc(docKey, resultRef, onDone)`:
   - If `window.__EE_DOC__ && window.__EE_DOC__[docKey]` already present → `onDone(doc)`.
   - Else inject `<script src="resultRef + '?t=' + Date.now()">`, onload read `__EE_DOC__[docKey]`, call `onDone`.
5. `renderMatches` builds the same match-item HTML as today’s loop (from full doc.matches).
6. `toggleAll(true)`: for each visible card, ensure loaded then expand (sequential or parallel script injects OK).
7. `applyFilters`:
   - File-level filters (doc type, client, identifier, shortcode, search on filename): unchanged on card attrs.
   - Kind / under-comment / doi.org filters:
     - If `data-loaded === "0"`: use hint attrs on the **card** (hide card if hints cannot satisfy).
     - If loaded: keep current per-`.match-item` logic.
8. Poll still reloads `index.js` while `status === "running"`; preserve expanded/loaded state by `doc_key` map when re-rendering (optional but preferred): if too heavy for this task, re-render from index and accept collapse on poll — **prefer preserve loaded state** with a `window.__EE_LOADED__ = {}` map of doc_key → full record after first load, and skip re-fetch when re-rendering.

Minimal preserve approach: on successful `loadDoc`, set `window.__EE_LOADED__[docKey] = doc`. `renderReport` after poll rebuilds cards; if `__EE_LOADED__[docKey]` exists, set `data-loaded=1` and optionally keep expanded if previously expanded (track `window.__EE_EXPANDED__` Set).

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_ee_report_store.py tests/test_doi_pubid_by_ref.py -q`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/ee_report_store.py tests/test_ee_report_store.py
git commit -m "Lazy-load DOI report matches from by_docid on expand."
```

---

### Task 3: `ee_docid_cache` module (P2)

**Files:**
- Create: `core/ee_docid_cache.py`
- Create: `tests/test_ee_docid_cache.py`

**Interfaces:**
- Produces:
  - `SCHEMA_VERSION = 1`
  - `DOI_QUERY_TYPE = "doi_pubid_by_ref"`
  - `query_slug(query_type: str, schema_version: int = SCHEMA_VERSION) -> str`
  - `cache_path(source_file: Path, query_type: str = DOI_QUERY_TYPE) -> Path`  
    → `{source_file.parent}/ee_cache/{slug}.json`
  - `build_cache_payload(source_file: Path, *, buckets: list, query_type: str = DOI_QUERY_TYPE) -> dict`
  - `try_load_cache(source_file: Path, *, query_type: str = DOI_QUERY_TYPE) -> dict | None`  
    returns payload if key matches (type, schema, mtime, size); else `None`
  - `write_cache(source_file: Path, payload: dict) -> Path | None`  
    returns path written, or `None` on OSError (read-only share)

Payload shape:

```python
{
  "schema_version": 1,
  "query_type": "doi_pubid_by_ref",
  "query_value": "",
  "mtime": <float>,
  "size": <int>,
  "buckets": [ ... same as extract_buckets_from_file buckets ... ],
}
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ee_docid_cache.py
import json
import time
from pathlib import Path

from core.ee_docid_cache import (
    SCHEMA_VERSION,
    build_cache_payload,
    cache_path,
    try_load_cache,
    write_cache,
)


def test_cache_path_under_docid_ee_cache(tmp_path):
    doc = tmp_path / "N1"
    doc.mkdir()
    f = doc / "a.xml"
    f.write_text("<x/>", encoding="utf-8")
    p = cache_path(f)
    assert p.parent.name == "ee_cache"
    assert p.parent.parent == doc
    assert p.suffix == ".json"


def test_write_and_hit_same_mtime_size(tmp_path):
    doc = tmp_path / "N1"
    doc.mkdir()
    f = doc / "a.xml"
    f.write_text("<x/>", encoding="utf-8")
    buckets = [{"bucket": 1, "element_kind": "doi", "html": "<a/>"}]
    payload = build_cache_payload(f, buckets=buckets)
    out = write_cache(f, payload)
    assert out is not None and out.is_file()
    loaded = try_load_cache(f)
    assert loaded is not None
    assert loaded["buckets"] == buckets
    assert loaded["schema_version"] == SCHEMA_VERSION


def test_miss_when_mtime_changes(tmp_path):
    doc = tmp_path / "N1"
    doc.mkdir()
    f = doc / "a.xml"
    f.write_text("<x/>", encoding="utf-8")
    write_cache(f, build_cache_payload(f, buckets=[]))
    time.sleep(0.05)
    f.write_text("<x/>y", encoding="utf-8")
    assert try_load_cache(f) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ee_docid_cache.py -v`  
Expected: FAIL (import error)

- [ ] **Step 3: Write minimal implementation**

```python
# core/ee_docid_cache.py
from __future__ import annotations
import json
import re
from pathlib import Path

SCHEMA_VERSION = 1
DOI_QUERY_TYPE = "doi_pubid_by_ref"


def query_slug(query_type: str, schema_version: int = SCHEMA_VERSION) -> str:
    raw = f"{query_type}_v{schema_version}"
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", raw)[:80]
    return s or "query"


def cache_path(source_file: Path, query_type: str = DOI_QUERY_TYPE) -> Path:
    source_file = Path(source_file)
    return source_file.parent / "ee_cache" / f"{query_slug(query_type)}.json"


def _stat_key(source_file: Path) -> tuple[float, int]:
    st = Path(source_file).stat()
    return (st.st_mtime, st.st_size)


def build_cache_payload(source_file: Path, *, buckets: list, query_type: str = DOI_QUERY_TYPE) -> dict:
    mtime, size = _stat_key(source_file)
    return {
        "schema_version": SCHEMA_VERSION,
        "query_type": query_type,
        "query_value": "",
        "mtime": mtime,
        "size": size,
        "buckets": buckets,
    }


def try_load_cache(source_file: Path, *, query_type: str = DOI_QUERY_TYPE) -> dict | None:
    path = cache_path(source_file, query_type=query_type)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema_version") != SCHEMA_VERSION:
        return None
    if data.get("query_type") != query_type:
        return None
    try:
        mtime, size = _stat_key(source_file)
    except OSError:
        return None
    if data.get("mtime") != mtime or data.get("size") != size:
        return None
    if not isinstance(data.get("buckets"), list):
        return None
    return data


def write_cache(source_file: Path, payload: dict) -> Path | None:
    path = cache_path(source_file)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path
    except OSError:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ee_docid_cache.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/ee_docid_cache.py tests/test_ee_docid_cache.py
git commit -m "Add ee_docid_cache for optional beside-docid DOI result reuse."
```

---

### Task 4: Wire checkbox + DOI loop cache (P2 UI)

**Files:**
- Modify: `tabs/element_extractor_tab.py` (settings UI ~556–565, settings dict get/set/apply, `_write_doi_pubid_by_ref_outputs`)
- Test: extend `tests/test_ee_docid_cache.py` with a small pure helper test if loop is hard to unit-test; optionally add a thin extract wrapper — prefer testing cache module + manual checklist. Add one integration-style test only if a pure function is extracted.

**Interfaces:**
- Consumes: `try_load_cache`, `build_cache_payload`, `write_cache`
- Produces: settings key `ee_docid_cache: bool` (default `False`); DOI loop skip-parse on hit

- [ ] **Step 1: Add checkbox (no test required for Tk wiring; verify via settings round-trip if existing pattern has tests — otherwise checklist)**

Under `open_report_chk` (row 8), add row 8b or shift rows carefully. Prefer new row **between open_report and Report Content**:

```python
self.ee_docid_cache_var = tk.BooleanVar(value=False)
self.ee_docid_cache_chk = tk.Checkbutton(
    settings_frame,
    text="Cache DOI/pub-id results next to docid (ee_cache) for same-query reuse",
    variable=self.ee_docid_cache_var,
    bg="#1e293b", fg="#e2e8f0", activebackground="#1e293b", activeforeground="white",
    selectcolor="#334155",
    font=("Segoe UI", 9),
)
self.ee_docid_cache_chk.grid(row=8, column=1, columnspan=2, sticky="w", pady=(0, 5))
# Move open_report to stay above, or place cache at row=8.5 — adjust grid so open_report stays row=8 and cache is row=8 with pady, OR use row=9 and bump Report Content down by 1.
```

Concrete layout (recommended):
- row 8: `open_report_chk` (unchanged)
- row 9: new `ee_docid_cache_chk`
- bump existing “Report Content” and everything below by +1

Persist like `open_report`:
- In `_get_settings_dict` / save: `"ee_docid_cache": bool(self.ee_docid_cache_var.get())`
- In load/apply: `self.ee_docid_cache_var.set(bool(entry.get("ee_docid_cache", False)))`
- Pass into DOI settings: `"ee_docid_cache": bool(self.ee_docid_cache_var.get())`

- [ ] **Step 2: Wire DOI loop**

In `_write_doi_pubid_by_ref_outputs`, import cache helpers at top of method (or module) and:

```python
from core.ee_docid_cache import (
    build_cache_payload,
    try_load_cache,
    write_cache,
)

use_docid_cache = bool(settings.get("ee_docid_cache", False))
cache_hits = 0
# ... inside loop, before extract:
buckets = None
parsed = None
if use_docid_cache:
    cached = try_load_cache(fp)
    if cached is not None:
        buckets = cached["buckets"]
        parsed = {"ok": True, "error": "", "buckets": buckets}
        cache_hits += 1
if buckets is None:
    parsed = extract_buckets_from_file(fp)
    buckets = parsed.get("buckets") or []
    if use_docid_cache and parsed.get("ok"):
        write_cache(fp, build_cache_payload(fp, buckets=buckets))
# then build matches from buckets as today
```

At end when `use_docid_cache`: `self._log(f"ee_cache hits: {cache_hits}/{len(file_results)}")`

- [ ] **Step 3: Run regression tests**

Run: `pytest tests/test_ee_docid_cache.py tests/test_ee_report_store.py tests/test_doi_pubid_by_ref.py -q`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tabs/element_extractor_tab.py
git commit -m "Wire optional ee_cache checkbox into DOI/pub-id scan loop."
```

---

### Task 5: Spec status + smoke checklist

**Files:**
- Modify: `docs/superpowers/specs/2026-09-22-ee-progressive-by-docid-json-design.md` status line

- [ ] **Step 1: Update status**

Set:

```markdown
**Status:** P0+P1+P2 implemented (slim index + lazy by_docid load; optional ee_cache)
```

- [ ] **Step 2: Manual smoke (operator)**

1. DOI folder scan without cache checkbox: open report early; cards collapsed; expand one → markup appears; filters work.
2. Large-ish run: `index.js` stays much smaller than sum of `by_docid`.
3. Enable cache; run twice on same unchanged files → second run logs/skips parse (faster); change one XML → that file re-parses.
4. Read-only source: cache write fails silently; scan still completes.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-09-22-ee-progressive-by-docid-json-design.md
git commit -m "Mark by_docid design P1/P2 implemented."
```

---

## Spec coverage (self-review)

| Spec item | Task |
|-----------|------|
| Lightweight `index.js` files[] | Task 1 |
| Lazy load `by_docid` on expand | Task 2 |
| Retain `by_docid/` | Already P0; unchanged |
| Optional `ee_cache/` default off | Tasks 3–4 |
| Cache key query_type + schema + mtime/size | Task 3 |
| Skip parse on hit; still write run index | Task 4 |
| Filters still work | Task 2 hints + loaded match filters |
| No mandatory write into source trees | Task 4 checkbox default off |
| P3/P4 / HTTP server | Out of scope |

**Placeholder scan:** none intentional.  
**Type consistency:** cache stores `buckets`; loop derives `matches` for report.

---

## Out of scope (this plan)

- P3 general XPath/CSS on same store  
- P4 CSV `project_shortcode`  
- Reading prior-run `by_docid/` as cache (only `ee_cache/`)  
- Async/deferred cache copy  
- Parallel ProcessPool writers  

# Element Extractor CSV Metadata + Unique Matches Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add client/meta columns to Element Extractor CSV exports, always emit full + unique CSVs, add an HTML Unique view that keeps the first match per tag+attrs while ignoring `xlink:href`, and fix post-run hang (history lock deadlock + main-thread button reset) so Run / Open Report / history work again.

**Architecture:** Post-process match lists at report time (do not change `parse_and_extract`). Put pure uniqueness helpers in a small module (`core/match_uniqueness.py`) mirroring `mixed_citation_direct_hits.py`. Annotate matches once before HTML/CSV generation; HTML shows All + Unique panels; CSV writes two files with a shared schema including metadata and uniqueness columns. Fix `RunHistoryStore.add_entry` re-entrant lock deadlock (root cause of history not saving and worker never reaching UI reset). Marshal all post-run widget updates through `_ui`.

**Tech Stack:** Python 3, existing `ElementExtractor` / Tkinter tab, pytest, lxml attribute dicts (Clark `{ns}href` keys), `RunHistoryStore` JSON history.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-19-element-extractor-csv-meta-unique-design.md`
- Uniqueness key: same file + same `tag` + attributes equal except drop `xlink:href` and keys ending with `}href`; different `class` ⇒ different; keep first match; do not use line/text in the key.
- CSV columns (exact order): `selector`, `query_type`, `file_path`, `file_name`, `doc_type`, `client`, `link_info`, `identifier`, `instance_no`, `line`, `tag`, `inner_text`, `outer_xml`, `is_unique`, `unique_group_size`
- `is_unique` serialized as strings `True` / `False`; keep original `instance_no` in unique CSV.
- Metadata columns from `get_file_metadata` only: `doc_type`, `client`, `link_info`, `identifier` (no dtd/titles).
- No new GUI checkbox; always build Unique HTML view; dual CSV only when Export CSV Summary is on.
- After run ends, all action-button state changes MUST run on the Tk main thread via `_ui` / `after(0, ...)`. Never call `run_btn` / `cancel_btn` / `open_last_btn` / `next_batch_btn` `.config` from the worker thread.
- Do not change folder scan, filters, mixed-citation, or citation-type reports.
- Work under `C:\_IMPACT\prod-support-tools\py\impact_config_suite`. TDD: failing test first. Commit only when the user asks (unless they already asked to execute with commits).

## File Map

| File | Responsibility |
|------|----------------|
| `core/run_history.py` (modify) | Fix `add_entry` deadlock: unlocked load/save under one lock |
| `core/match_uniqueness.py` (create) | Pure helpers: attr normalize, unique key, annotate, filter, annotate whole selector results |
| `core/element_extractor.py` (modify) | Call annotate before/inside report+CSV; extend `export_csv`; add HTML All/Unique view chrome |
| `tabs/element_extractor_tab.py` (modify) | Annotate once; write dual CSV paths; log both; main-thread `_finish_run_ui` for Run/Cancel/Open Last |
| `tests/test_run_history_store.py` (create) | Prove `add_entry` completes and persists without hanging |
| `tests/test_match_uniqueness.py` (create) | Unit tests for uniqueness helpers |
| `tests/test_element_extractor_csv_unique.py` (create) | CSV meta columns + dual export integration-style tests |
| `docs/element_extractor_docs.md` (modify) | Document CSV columns, dual files, Unique tab |
| `element_extractor_docs.md` (modify if still mirrored) | Keep in sync with docs copy |

---

### Task 0: Fix `RunHistoryStore.add_entry` deadlock (TDD) — do this first

**Files:**
- Modify: `py/impact_config_suite/core/run_history.py`
- Test: `py/impact_config_suite/tests/test_run_history_store.py`

**Root cause:** `add_entry` holds `threading.Lock`, then calls `load_entries()` / `save_entries()` which acquire the same non-reentrant lock → worker hangs after reports are written → history never saved → `finally` UI reset never runs → only Cancel still works.

**Interfaces:**
- Produces: public API unchanged (`load_entries`, `save_entries`, `add_entry`). Internals: `_load_entries_unlocked` / `_save_entries_unlocked` used while lock is held; public methods acquire lock once.

- [ ] **Step 1: Write the failing / hang-detecting test**

```python
# tests/test_run_history_store.py
import threading
from pathlib import Path

import core.run_history as rh
from core.run_history import RunHistoryStore


def test_add_entry_completes_without_deadlock(tmp_path, monkeypatch):
    monkeypatch.setattr(
        RunHistoryStore, "history_file_path", classmethod(lambda cls: tmp_path / "suite_run_history.json")
    )
    # base_dir unused if history_file_path fully patched; still safe:
    monkeypatch.setattr(RunHistoryStore, "base_dir", classmethod(lambda cls: tmp_path))

    done = threading.Event()
    error = {}

    def worker():
        try:
            RunHistoryStore.add_entry({
                "tool_id": "element_extractor",
                "action": "extract",
                "source_path": r"C:\data\doc",
                "output_dir": str(tmp_path),
                "report_path": str(tmp_path / "report.html"),
                "params": {"query_value": "ext-link"},
                "summary": "test",
            })
            done.set()
        except Exception as exc:
            error["e"] = exc
            done.set()

    t = threading.Thread(target=worker)
    t.start()
    finished = done.wait(timeout=5)
    assert finished, "add_entry deadlocked (did not finish within 5s)"
    assert "e" not in error
    entries = RunHistoryStore.load_entries()
    assert len(entries) == 1
    assert entries[0]["tool_id"] == "element_extractor"
    assert entries[0]["report_path"].endswith("report.html")
```

- [ ] **Step 2: Run test — expect hang/fail on current code**

```bash
python -m pytest tests/test_run_history_store.py::test_add_entry_completes_without_deadlock -v --timeout=10
```

If pytest-timeout is unavailable:

```bash
python -m pytest tests/test_run_history_store.py::test_add_entry_completes_without_deadlock -v
```

Expected: assertion `add_entry deadlocked` OR test process hangs until killed (current bug).

- [ ] **Step 3: Fix `core/run_history.py`**

Refactor to unlocked helpers:

```python
@classmethod
def _load_entries_unlocked(cls) -> list[dict]:
    history_path = cls.history_file_path()
    if not history_path.exists():
        return []
    try:
        raw = json.loads(history_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)][: cls.HISTORY_LIMIT]

@classmethod
def _save_entries_unlocked(cls, entries: list[dict]) -> None:
    history_path = cls.history_file_path()
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        json.dumps(entries[: cls.HISTORY_LIMIT], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

@classmethod
def load_entries(cls) -> list[dict]:
    with cls._lock:
        return cls._load_entries_unlocked()

@classmethod
def save_entries(cls, entries: list[dict]) -> None:
    with cls._lock:
        cls._save_entries_unlocked(entries)

@classmethod
def add_entry(cls, entry: dict) -> dict:
    with cls._lock:
        payload = dict(entry)
        payload.setdefault("id", str(uuid.uuid4()))
        payload.setdefault("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        payload.setdefault("tool_id", "")
        payload.setdefault("tool_label", "")
        payload.setdefault("summary", "")
        payload.setdefault("params", {})

        entries = cls._load_entries_unlocked()
        entry_key = (
            str(payload.get("tool_id", "")),
            str(payload.get("action", "")),
            str(payload.get("source_path", "")),
            str(payload.get("output_dir", "")),
            str(payload.get("report_path", "")),
            json.dumps(payload.get("params", {}), sort_keys=True, ensure_ascii=False),
        )
        entries = [
            existing for existing in entries
            if (
                str(existing.get("tool_id", "")),
                str(existing.get("action", "")),
                str(existing.get("source_path", "")),
                str(existing.get("output_dir", "")),
                str(existing.get("report_path", "")),
                json.dumps(existing.get("params", {}), sort_keys=True, ensure_ascii=False),
            ) != entry_key
        ]
        entries.insert(0, payload)
        cls._save_entries_unlocked(entries)
        return payload
```

- [ ] **Step 4: Re-run test — expect PASS within 5s**

```bash
python -m pytest tests/test_run_history_store.py -v
```

- [ ] **Step 5: Commit** (if user requested)

```bash
git add py/impact_config_suite/core/run_history.py py/impact_config_suite/tests/test_run_history_store.py
git commit -m "Fix RunHistoryStore.add_entry deadlock so run history can save."
```

---

### Task 1: Uniqueness helpers (TDD)

**Files:**
- Create: `py/impact_config_suite/core/match_uniqueness.py`
- Test: `py/impact_config_suite/tests/test_match_uniqueness.py`

**Interfaces:**
- Consumes: match dicts shaped like extract output (`tag`, `attributes`, plus other keys left untouched)
- Produces:
  - `attrs_for_uniqueness(attrs: dict) -> dict`
  - `unique_key(match: dict) -> tuple`
  - `annotate_unique_matches(matches: list[dict]) -> list[dict]` (mutates and returns same list; adds `is_unique: bool`, `unique_group_size: int`)
  - `filter_unique_matches(matches: list[dict]) -> list[dict]`
  - `annotate_selector_results(all_selector_results: list) -> list` (for each file’s `matches` list under each selector’s `scan_results`, call `annotate_unique_matches`; skip non-ok / empty)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_match_uniqueness.py
from core.match_uniqueness import (
    attrs_for_uniqueness,
    annotate_unique_matches,
    filter_unique_matches,
    annotate_selector_results,
)

XLINK = "{http://www.w3.org/1999/xlink}href"


def test_attrs_for_uniqueness_drops_xlink_forms():
    attrs = {
        "class": "ext-link",
        "xlink:href": "a",
        XLINK: "b",
        "ext-link-type": "uri",
    }
    out = attrs_for_uniqueness(attrs)
    assert out == {"class": "ext-link", "ext-link-type": "uri"}
    assert "xlink:href" not in out
    assert XLINK not in out


def test_annotate_keeps_first_when_only_href_differs():
    matches = [
        {"tag": "ext-link", "attributes": {"class": "ext-link", XLINK: "http://a"}, "line": 1, "text": "A", "html": "<a/>"},
        {"tag": "ext-link", "attributes": {"class": "ext-link", XLINK: "http://b"}, "line": 2, "text": "B", "html": "<b/>"},
        {"tag": "ext-link", "attributes": {"class": "ext-link", "xlink:href": "http://c"}, "line": 3, "text": "C", "html": "<c/>"},
    ]
    annotate_unique_matches(matches)
    assert [m["is_unique"] for m in matches] == [True, False, False]
    assert all(m["unique_group_size"] == 3 for m in matches)
    assert filter_unique_matches(matches)[0]["line"] == 1


def test_different_class_are_distinct():
    matches = [
        {"tag": "a", "attributes": {"class": "one", XLINK: "u1"}, "line": 1},
        {"tag": "a", "attributes": {"class": "two", XLINK: "u2"}, "line": 2},
    ]
    annotate_unique_matches(matches)
    assert [m["is_unique"] for m in matches] == [True, True]
    assert [m["unique_group_size"] for m in matches] == [1, 1]


def test_annotate_selector_results_is_per_file():
    results = [{
        "query_val": "ext-link",
        "scan_results": {
            "C:/a.xml": {
                "ok": True,
                "matches": [
                    {"tag": "a", "attributes": {XLINK: "1"}, "line": 1},
                    {"tag": "a", "attributes": {XLINK: "2"}, "line": 2},
                ],
            },
            "C:/b.xml": {
                "ok": True,
                "matches": [
                    {"tag": "a", "attributes": {XLINK: "1"}, "line": 9},
                ],
            },
        },
    }]
    annotate_selector_results(results)
    a = results[0]["scan_results"]["C:/a.xml"]["matches"]
    b = results[0]["scan_results"]["C:/b.xml"]["matches"]
    assert [m["is_unique"] for m in a] == [True, False]
    assert a[0]["unique_group_size"] == 2
    assert b[0]["is_unique"] is True and b[0]["unique_group_size"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `py/impact_config_suite`):

```bash
python -m pytest tests/test_match_uniqueness.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'core.match_uniqueness'` (or import error).

- [ ] **Step 3: Implement helpers**

```python
# core/match_uniqueness.py
from __future__ import annotations


def attrs_for_uniqueness(attrs: dict | None) -> dict:
    if not attrs:
        return {}
    out = {}
    for key, value in attrs.items():
        if key == "xlink:href" or (isinstance(key, str) and key.endswith("}href")):
            continue
        out[key] = value
    return out


def unique_key(match: dict) -> tuple:
    tag = match.get("tag", "")
    normalized = attrs_for_uniqueness(match.get("attributes") or {})
    return (tag, frozenset(normalized.items()))


def annotate_unique_matches(matches: list) -> list:
    """Annotate in place: is_unique + unique_group_size. Keep first of each key."""
    if not matches:
        return matches

    groups: dict[tuple, list] = {}
    order: list[tuple] = []
    for match in matches:
        key = unique_key(match)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(match)

    for key in order:
        members = groups[key]
        size = len(members)
        for index, match in enumerate(members):
            match["is_unique"] = index == 0
            match["unique_group_size"] = size
    return matches


def filter_unique_matches(matches: list) -> list:
    return [m for m in matches if m.get("is_unique")]


def annotate_selector_results(all_selector_results: list) -> list:
    for selector_data in all_selector_results or []:
        scan_results = selector_data.get("scan_results") or {}
        for _path, data in scan_results.items():
            if not data.get("ok", True):
                continue
            matches = data.get("matches") or []
            if matches:
                annotate_unique_matches(matches)
    return all_selector_results
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_match_uniqueness.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit** (only if user requested commits during execution)

```bash
git add py/impact_config_suite/core/match_uniqueness.py py/impact_config_suite/tests/test_match_uniqueness.py
git commit -m "Add match uniqueness helpers for Element Extractor reports."
```

---

### Task 2: Extend `export_csv` with metadata + uniqueness columns

**Files:**
- Modify: `py/impact_config_suite/core/element_extractor.py` (`export_csv` ~4867–4909)
- Test: `py/impact_config_suite/tests/test_element_extractor_csv_unique.py`

**Interfaces:**
- Consumes: `annotate_unique_matches` / `annotate_selector_results` from Task 1; `self.get_file_metadata`
- Produces: `export_csv(self, all_selector_results: list, output_path: Path, unique_only: bool = False) -> Path`
  - If matches lack `is_unique`, call `annotate_selector_results` first (idempotent enough for tests).
  - When `unique_only=True`, skip rows where `is_unique` is not True.
  - Header exactly as Global Constraints column list.

- [ ] **Step 1: Write the failing CSV tests**

```python
# tests/test_element_extractor_csv_unique.py
import csv
from pathlib import Path

from core.element_extractor import ElementExtractor
from core.match_uniqueness import annotate_selector_results

XLINK = "{http://www.w3.org/1999/xlink}href"

EXPECTED_HEADER = [
    "selector", "query_type", "file_path", "file_name",
    "doc_type", "client", "link_info", "identifier",
    "instance_no", "line", "tag", "inner_text", "outer_xml",
    "is_unique", "unique_group_size",
]


def _selector_results(file_path: str, matches: list, meta_client: str = ""):
    return [{
        "query_val": "ext-link",
        "query_type": "CSS Selector",
        "scan_results": {
            file_path: {"ok": True, "matches": matches},
        },
    }]


def test_export_csv_header_and_meta_and_unique_flags(tmp_path: Path, monkeypatch):
    extractor = ElementExtractor()
    file_path = str(tmp_path / "doc.xml")

    def fake_meta(path: Path):
        return {
            "doc_type": "Books",
            "client": "TNF",
            "link_info": "pubkittnf",
            "identifier": "D2V085_Melzer190226TNF_FSM",
            "dtd": "BITS",
            "doc_title": "",
            "project_title": "",
        }

    monkeypatch.setattr(extractor, "get_file_metadata", fake_meta)

    matches = [
        {"tag": "ext-link", "attributes": {"class": "x", XLINK: "u1"}, "line": 10, "text": "A", "html": "<a/>"},
        {"tag": "ext-link", "attributes": {"class": "x", XLINK: "u2"}, "line": 11, "text": "B", "html": "<b/>"},
    ]
    results = _selector_results(file_path, matches)
    annotate_selector_results(results)

    full_path = tmp_path / "full.csv"
    unique_path = tmp_path / "unique.csv"
    extractor.export_csv(results, full_path, unique_only=False)
    extractor.export_csv(results, unique_path, unique_only=True)

    with full_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == EXPECTED_HEADER
    assert len(rows) == 3  # header + 2
    assert rows[1][4:8] == ["Books", "TNF", "pubkittnf", "D2V085_Melzer190226TNF_FSM"]
    assert rows[1][-2:] == ["True", "2"]
    assert rows[2][-2:] == ["False", "2"]
    assert rows[1][8] == "1" and rows[2][8] == "2"  # instance_no

    with unique_path.open(encoding="utf-8", newline="") as f:
        urows = list(csv.reader(f))
    assert urows[0] == EXPECTED_HEADER
    assert len(urows) == 2  # header + first only
    assert urows[1][8] == "1"  # original instance_no kept
    assert urows[1][-2] == "True"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_element_extractor_csv_unique.py::test_export_csv_header_and_meta_and_unique_flags -v
```

Expected: FAIL (header mismatch / unexpected keyword `unique_only`).

- [ ] **Step 3: Implement `export_csv`**

Replace `export_csv` in `core/element_extractor.py` with logic equivalent to:

```python
def export_csv(self, all_selector_results: list, output_path: Path, unique_only: bool = False) -> Path:
    import csv
    from core.match_uniqueness import annotate_selector_results

    annotate_selector_results(all_selector_results)

    header = [
        "selector", "query_type", "file_path", "file_name",
        "doc_type", "client", "link_info", "identifier",
        "instance_no", "line", "tag", "inner_text", "outer_xml",
        "is_unique", "unique_group_size",
    ]

    meta_cache: dict[str, dict] = {}

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for selector_data in all_selector_results:
            query_val = selector_data.get("query_val", "")
            query_type = selector_data.get("query_type", "")
            scan_results = selector_data.get("scan_results", {})

            for file_path_str, data in scan_results.items():
                if not data.get("ok", True):
                    continue
                matches = data.get("matches", [])
                if not matches:
                    continue

                if file_path_str not in meta_cache:
                    meta_cache[file_path_str] = self.get_file_metadata(Path(file_path_str))
                meta = meta_cache[file_path_str]

                file_name = os.path.basename(file_path_str)
                for idx, match in enumerate(matches, 1):
                    if unique_only and not match.get("is_unique"):
                        continue
                    writer.writerow([
                        query_val,
                        query_type,
                        file_path_str,
                        file_name,
                        meta.get("doc_type", ""),
                        meta.get("client", ""),
                        meta.get("link_info", ""),
                        meta.get("identifier", ""),
                        idx,
                        match.get("line", ""),
                        match.get("tag", ""),
                        match.get("text", ""),
                        match.get("html", ""),
                        "True" if match.get("is_unique") else "False",
                        match.get("unique_group_size", 1),
                    ])

    return output_path
```

Note: `instance_no` must be the original 1-based index in the full matches list (use `idx` from `enumerate(matches, 1)` even when `unique_only` skips rows — do **not** renumber).

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_element_extractor_csv_unique.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit** (if user requested)

```bash
git add py/impact_config_suite/core/element_extractor.py py/impact_config_suite/tests/test_element_extractor_csv_unique.py
git commit -m "Add CSV metadata and uniqueness columns to Element Extractor export."
```

---

### Task 3: Dual CSV write + logging in the tab

**Files:**
- Modify: `py/impact_config_suite/tabs/element_extractor_tab.py` (~2104–2115)

**Interfaces:**
- Consumes: `export_csv(..., unique_only=False|True)` from Task 2; `annotate_selector_results` (optional here if export/HTML already annotate)
- Produces: two files under `run_folder`:
  - `Element_Extraction_Report_{safe_target_name}_{query_slug}.csv`
  - `Element_Extraction_Unique_{safe_target_name}_{query_slug}.csv`
- Sets `self.last_csv_path` to the full report path (existing behavior); also set `self.last_unique_csv_path` if useful for open-last (optional; if added, initialize in `__init__` next to `last_csv_path`).

- [ ] **Step 1: Replace the CSV block**

Change the `if generate_csv:` block to:

```python
if generate_csv:
    self._set_status("Generating CSV export...")
    from core.match_uniqueness import annotate_selector_results
    annotate_selector_results(all_selector_results)

    csv_report_name = f"Element_Extraction_Report_{safe_target_name}_{query_slug}.csv"
    csv_unique_name = f"Element_Extraction_Unique_{safe_target_name}_{query_slug}.csv"
    csv_report_path = run_folder / csv_report_name
    csv_unique_path = run_folder / csv_unique_name

    self.extractor.export_csv(all_selector_results, csv_report_path, unique_only=False)
    self.extractor.export_csv(all_selector_results, csv_unique_path, unique_only=True)

    self.last_csv_path = str(csv_report_path.absolute())
    self.last_unique_csv_path = str(csv_unique_path.absolute())
    csv_path = self.last_csv_path
    self._log(f"📋 CSV export saved: {run_folder_name}/{csv_report_name}")
    self._log(f"📋 Unique CSV saved: {run_folder_name}/{csv_unique_name}")
```

Also in `__init__` near `self.last_csv_path = None`, add `self.last_unique_csv_path = None`.

- [ ] **Step 2: Sanity-check import path**

Ensure `from core.match_uniqueness import annotate_selector_results` works the same way other tab imports work (`from core.mixed_citation_direct_hits import ...` pattern at top of file is preferred — move import to module top with existing core imports).

- [ ] **Step 3: Manual smoke (optional)** — run a small folder extract with Export CSV on; confirm both files exist and unique row count ≤ full.

- [ ] **Step 4: Commit** (if user requested)

```bash
git add py/impact_config_suite/tabs/element_extractor_tab.py
git commit -m "Write full and unique Element Extractor CSV exports."
```

---

### Task 3b: Post-run button unlock (main-thread UI)

**Files:**
- Modify: `py/impact_config_suite/tabs/element_extractor_tab.py` (`_run_extraction_thread` success paths ~1678–1683 and ~2207–2228; add helper near `_ui`)

**Problem:** After complete, Run / Open Last Report / Rerun stop responding while Cancel still works. Worker thread calls `self.open_last_btn.config(state="normal")` directly; Tk on Windows then mishandles other button events.

**Interfaces:**
- Produces: `_finish_run_ui(self, *, enable_open_last: bool = False) -> None` — intended to run **only** on the main thread (called via `_ui`).
  - Sets `run_btn` to `state="normal"`, text `🚀  RUN ELEMENT EXTRACTION`
  - Sets `cancel_btn` to `state="disabled"`
  - If `enable_open_last` and `self.last_report_path` exists → `open_last_btn` `state="normal"`

- [ ] **Step 1: Add `_finish_run_ui`**

```python
def _finish_run_ui(self, *, enable_open_last: bool = False) -> None:
    """Reset action buttons after a run. Must run on the Tk main thread."""
    self.run_btn.config(state="normal", text="🚀  RUN ELEMENT EXTRACTION")
    self.cancel_btn.config(state="disabled")
    if enable_open_last and self.last_report_path and os.path.exists(self.last_report_path):
        self.open_last_btn.config(state="normal")
```

- [ ] **Step 2: Remove worker-thread `.config` on open_last / run / cancel**

1. Delete bare `self.open_last_btn.config(state="normal")` at the mixed-only success path (~1680) and normal success path (~2207).
2. Replace `finally` reset with:

```python
finally:
    enable_open = bool(self.last_report_path and os.path.exists(self.last_report_path))
    self._ui(lambda eo=enable_open: self._finish_run_ui(enable_open_last=eo))
```

3. Keep `next_batch_btn` updates on `self.after(0, ...)` / `_ui` only (already mostly correct).
4. Schedule auto-open browser from main thread if needed:

```python
# instead of webbrowser.open directly on worker after success:
report_to_open = self.last_report_path
# ... collect other paths ...
self._ui(lambda: self._open_reports_after_run(report_to_open, citation_report_path, ...))
```

Or keep `webbrowser.open` on the worker (usually OK) but **never** touch widgets there. Minimum fix: widget configs only via `_finish_run_ui`; browser open may stay as-is.

- [ ] **Step 3: Manual verify**

Run one extraction to completion → confirm Run is clickable again, Open Last Report opens the HTML, Cancel is disabled, Rerun Last works.

- [ ] **Step 4: Commit** (if user requested)

```bash
git add py/impact_config_suite/tabs/element_extractor_tab.py
git commit -m "Fix Element Extractor post-run buttons via main-thread UI reset."
```

- [ ] **Step 5 (same task / follow-up): Snapshot history settings off the worker thread**

When starting extraction, capture a plain dict of UI settings on the main thread (all filter/option `.get()` values). Pass that dict into `_run_extraction_thread`. Change `_current_run_settings` to merge **snapshot + worker-produced paths** instead of reading `self.*_var.get()` from the worker. Include `unique_csv_path` in `params` when dual CSV exists.

---

### Task 4: HTML All matches + Unique view

**Files:**
- Modify: `py/impact_config_suite/core/element_extractor.py` (`generate_html_report` ~863–1780)

**Interfaces:**
- Consumes: `annotate_selector_results`, `filter_unique_matches`
- Produces: HTML with:
  - Extra stat card: Unique Matches count
  - View tabs: **All matches** | **Unique** (subtitle: first match per tag+attrs, ignoring xlink:href)
  - Two panels; Unique panel uses same file-card markup but only `is_unique` matches; files with zero unique matches after filter are omitted (same as empty match skip today)

- [ ] **Step 1: Annotate at start of `generate_html_report`**

Immediately after docstring / timestamp setup:

```python
from core.match_uniqueness import annotate_selector_results, filter_unique_matches
annotate_selector_results(all_selector_results)

unique_matches = 0
for selector_data in all_selector_results:
    for data in (selector_data.get("scan_results") or {}).values():
        if data.get("ok", True):
            unique_matches += sum(1 for m in (data.get("matches") or []) if m.get("is_unique"))
```

- [ ] **Step 2: Factor file-section building**

Extract the existing per-selector loop body that builds `file_sections` into a nested helper or local function:

```python
def build_file_sections(scan_results, query_val_single, *, unique_only: bool, id_prefix: str) -> str:
    # copy existing loop; when iterating matches:
    #   match_iter = filter_unique_matches(matches) if unique_only else matches
    # use id_prefix in element ids: f"{id_prefix}-file-{file_global_index}" to avoid duplicate DOM ids
    ...
```

Call twice per selector (or once for single-selector page wrapper):

```python
all_sections = build_file_sections(scan_results, query_val_single, unique_only=False, id_prefix="all")
unique_sections = build_file_sections(scan_results, query_val_single, unique_only=True, id_prefix="uniq")
```

For multi-selector mode, wrap each selector’s pair the same way (All/Unique panels inside each selector content, or page-level tabs that swap the whole `selector_sections` — **prefer page-level tabs** wrapping two complete trees to minimize nested UX complexity):

```html
<div class="view-tabs">
  <button class="view-tab active" onclick="showView('all', this)">All matches</button>
  <button class="view-tab" onclick="showView('unique', this)">Unique</button>
</div>
<p class="view-hint" id="unique-hint" style="display:none;">
  First match per tag+attributes within each file, ignoring xlink:href.
</p>
<div id="view-all" class="view-panel">{ALL_TREE}</div>
<div id="view-unique" class="view-panel" style="display:none;">{UNIQUE_TREE}</div>
```

Build `ALL_TREE` with current logic (`unique_only=False`). Build `UNIQUE_TREE` with the same loop filtered.

Add CSS for `.view-tabs` / `.view-tab.active` consistent with existing dark theme (`--primary`).

JS:

```javascript
function showView(name, btn) {
  document.getElementById('view-all').style.display = name === 'all' ? 'block' : 'none';
  document.getElementById('view-unique').style.display = name === 'unique' ? 'block' : 'none';
  document.getElementById('unique-hint').style.display = name === 'unique' ? 'block' : 'none';
  document.querySelectorAll('.view-tab').forEach(el => el.classList.remove('active'));
  btn.classList.add('active');
}
```

- [ ] **Step 3: Add Unique Matches stat card**

In the stats grid after Total Matches:

```html
<div class="stat-card">
  <span class="lbl">Unique Matches</span>
  <span class="val highlight-match">{unique_matches}</span>
</div>
```

- [ ] **Step 4: Add a focused HTML smoke test (optional but recommended)**

In `tests/test_element_extractor_csv_unique.py`:

```python
def test_html_report_contains_unique_view(tmp_path, monkeypatch):
    extractor = ElementExtractor()
    monkeypatch.setattr(extractor, "get_file_metadata", lambda p: {
        "doc_type": "Books", "client": "TNF", "link_info": "pubkittnf",
        "identifier": "ID1", "dtd": "", "doc_title": "", "project_title": "",
    })
    monkeypatch.setattr(extractor, "get_file_title", lambda p: ("filename", Path(p).name))
    matches = [
        {"tag": "a", "attributes": {"class": "x", XLINK: "1"}, "line": 1, "text": "A", "html": "<a/>"},
        {"tag": "a", "attributes": {"class": "x", XLINK: "2"}, "line": 2, "text": "B", "html": "<b/>"},
    ]
    results = [{
        "query_val": "a", "query_type": "CSS Selector", "total_matches": 2,
        "scan_results": {str(tmp_path / "f.xml"): {"ok": True, "matches": matches}},
    }]
    html_out = extractor.generate_html_report(
        str(tmp_path), "CSS Selector", "a", "", "", results, 2, 1, True
    )
    assert 'id="view-unique"' in html_out
    assert "Unique Matches" in html_out
    assert "showView" in html_out
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_match_uniqueness.py tests/test_element_extractor_csv_unique.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit** (if user requested)

```bash
git add py/impact_config_suite/core/element_extractor.py py/impact_config_suite/tests/test_element_extractor_csv_unique.py
git commit -m "Add Unique matches view to Element Extractor HTML report."
```

---

### Task 5: Documentation

**Files:**
- Modify: `py/impact_config_suite/docs/element_extractor_docs.md`
- Modify: `py/impact_config_suite/element_extractor_docs.md` (if content still mirrors the docs copy)

- [ ] **Step 1: Update Generated Reports / CSV section**

Replace the CSV bullet list with:

```markdown
### 3. CSV Export (`Element_Extraction_Report_*.csv` and `Element_Extraction_Unique_*.csv`)
- Spreadsheet-compatible format
- Columns: selector, query_type, file_path, file_name, doc_type, client, link_info, identifier, instance_no, line, tag, inner_text, outer_xml, is_unique, unique_group_size
- Full CSV: one row per match instance
- Unique CSV: first match per tag+attributes within each file, ignoring `xlink:href` / Clark `{…}href` (keeps original `instance_no`)
- Metadata columns match the HTML `TYPE|CLIENT|LINK-INFO|IDENTIFIER` fields (separate columns, not a pipe string)

### HTML Unique view
- Detailed HTML report includes **All matches** and **Unique** tabs
- Unique = first match in each file for the same tag + attributes except `xlink:href`
- Header shows Total Matches and Unique Matches counts
```

- [ ] **Step 2: Commit** (if user requested)

```bash
git add py/impact_config_suite/docs/element_extractor_docs.md py/impact_config_suite/element_extractor_docs.md
git commit -m "Document Element Extractor CSV metadata and Unique report views."
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Fix history deadlock / history records | Task 0 (+ Task 3b step 5 snapshot) |
| CSV meta columns `doc_type`, `client`, `link_info`, `identifier` | Task 2 |
| Dual CSV files + `is_unique` / `unique_group_size` | Tasks 2–3 |
| Keep first; ignore xlink/Clark href; per file; class matters | Task 1 |
| HTML All + Unique; both counts | Task 4 |
| No new checkbox; annotate at report time | Tasks 3–4 |
| Post-run Run / Open Report / Rerun work again | Tasks 0 + 3b |
| Docs | Task 5 |
| Tests listed in spec | Tasks 0–2, 4 |

## Plan self-review notes

- No TBD placeholders; column order and serialization locked.
- `export_csv` and HTML both call annotate; double-annotate is safe (recomputes same flags).
- `instance_no` uses full-list enumerate index even when `unique_only` skips — matches spec join semantics.
- HTML DOM ids use `all-` / `uniq-` prefixes to avoid collisions when both trees are in one page.
- Task 0 is ordered first: history deadlock explains both “history not recorded” and post-run buttons stuck (worker never reaches `finally`). Task 3b still required for remaining cross-thread `.config` calls.

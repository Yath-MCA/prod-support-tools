# meta.json Client/DTD Scan Filters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When Client or DTD filters are set, resolve client/dtd from nearest then root `meta.json` (cached) before falling back to per-doc `impact_config.xml`, without changing report metadata.

**Architecture:** New small module `core/meta_json_filters.py` loads/caches `meta.json` and looks up the docid (`file_path.parent.name`). `ElementExtractor._matches_config_filters` tries that lookup first; on miss, keeps today’s XML path. `get_file_metadata` is untouched.

**Tech Stack:** Python 3, `json` + `pathlib`, existing `ElementExtractor` filter helpers, pytest tmp_path fixtures.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-20-meta-json-scan-filters-design.md`
- Filters only: `client` and `dtd` fields from meta; other fields unused
- Lookup: nearest `{dtd_folder}/meta.json` then ancestor `meta.json` (root); then `impact_config.xml`
- Case-insensitive compare (same as current XML filters)
- Invalid JSON = miss that file, continue; do not raise out of the matcher
- Work under `C:\_IMPACT\prod-support-tools\py\impact_config_suite`; TDD; commit only when user asks
- Do not stage `config/build_metadata.json`

## File Map

| File | Responsibility |
|------|----------------|
| `core/meta_json_filters.py` (create) | Load/cache meta maps; resolve entry for a file path |
| `core/element_extractor.py` (modify) | `_meta_json_cache`; wire `_matches_config_filters`; clear cache |
| `tests/test_meta_json_filters.py` (create) | Unit tests for lookup + filter integration |

---

### Task 1: meta.json load + lookup helper (TDD)

**Files:**
- Create: `py/impact_config_suite/core/meta_json_filters.py`
- Test: `py/impact_config_suite/tests/test_meta_json_filters.py`

**Interfaces:**
- Produces:
  - `load_meta_map(meta_path: Path, cache: dict) -> dict | None`
  - `lookup_meta_entry(file_path: Path, cache: dict) -> dict | None`
- Consumes: none

- [ ] **Step 1: Write failing tests for load + lookup**

```python
# tests/test_meta_json_filters.py
import json
from pathlib import Path

from core.meta_json_filters import load_meta_map, lookup_meta_entry


def test_load_meta_map_caches_by_mtime(tmp_path):
    meta_path = tmp_path / "meta.json"
    meta_path.write_text(json.dumps({"N1": {"client": "TNF", "dtd": "BITS"}}), encoding="utf-8")
    cache = {}
    m1 = load_meta_map(meta_path, cache)
    m2 = load_meta_map(meta_path, cache)
    assert m1 == {"N1": {"client": "TNF", "dtd": "BITS"}}
    assert m2 is m1
    assert str(meta_path.resolve()) in cache


def test_load_meta_map_returns_none_on_bad_json(tmp_path):
    meta_path = tmp_path / "meta.json"
    meta_path.write_text("{not-json", encoding="utf-8")
    assert load_meta_map(meta_path, {}) is None


def test_lookup_prefers_bits_meta_then_root(tmp_path):
    root = tmp_path
    bits = root / "BITS"
    doc = bits / "Nabc"
    doc.mkdir(parents=True)
    (doc / "x.html").write_text("<p/>", encoding="utf-8")
    (bits / "meta.json").write_text(
        json.dumps({"Nabc": {"client": "TNF", "dtd": "BITS"}}), encoding="utf-8"
    )
    (root / "meta.json").write_text(
        json.dumps({"Nabc": {"client": "OTHER", "dtd": "JATS"}}), encoding="utf-8"
    )
    entry = lookup_meta_entry(doc / "x.html", {})
    assert entry["client"] == "TNF"
    assert entry["dtd"] == "BITS"


def test_lookup_falls_through_to_root_when_key_missing_in_bits(tmp_path):
    root = tmp_path
    bits = root / "BITS"
    doc = bits / "Nabc"
    doc.mkdir(parents=True)
    html = doc / "x.html"
    html.write_text("<p/>", encoding="utf-8")
    (bits / "meta.json").write_text(json.dumps({"Nother": {"client": "X", "dtd": "BITS"}}), encoding="utf-8")
    (root / "meta.json").write_text(
        json.dumps({"Nabc": {"client": "PLOS", "dtd": "JATS"}}), encoding="utf-8"
    )
    entry = lookup_meta_entry(html, {})
    assert entry["client"] == "PLOS"
    assert entry["dtd"] == "JATS"


def test_lookup_returns_none_when_no_meta(tmp_path):
    doc = tmp_path / "BITS" / "Nabc"
    doc.mkdir(parents=True)
    html = doc / "x.html"
    html.write_text("<p/>", encoding="utf-8")
    assert lookup_meta_entry(html, {}) is None
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd C:\_IMPACT\prod-support-tools\py\impact_config_suite
python -m pytest tests/test_meta_json_filters.py -v
```

Expected: import error or missing module.

- [ ] **Step 3: Implement `core/meta_json_filters.py`**

```python
"""Load and resolve IMPACT meta.json maps for client/DTD scan filters."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_meta_map(meta_path: Path, cache: dict) -> dict | None:
    """Return parsed docid->meta dict, or None if missing/invalid. Cache by path+mtime."""
    meta_path = Path(meta_path)
    try:
        mtime = meta_path.stat().st_mtime
    except OSError:
        return None

    key = str(meta_path.resolve()) if meta_path.exists() else str(meta_path)
    cached = cache.get(key)
    if cached is not None and cached.get("mtime") == mtime:
        return cached.get("data")

    try:
        raw = meta_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
        cache[key] = {"mtime": mtime, "data": None}
        return None

    if not isinstance(data, dict):
        cache[key] = {"mtime": mtime, "data": None}
        return None

    cache[key] = {"mtime": mtime, "data": data}
    return data


def lookup_meta_entry(file_path: Path, cache: dict) -> dict | None:
    """
    Find meta entry for file_path.parent.name.
    Prefer {parent.parent}/meta.json (BITS|JATS), then walk ancestors for meta.json.
    """
    file_path = Path(file_path)
    doc_dir = file_path.parent
    docid = doc_dir.name
    if not docid:
        return None

    tried: set[str] = set()
    candidates: list[Path] = []

    # Nearest: DTD folder meta (…/BITS/meta.json)
    nearest = doc_dir.parent / "meta.json"
    candidates.append(nearest)

    # Ancestors from project root upward (skip duplicates)
    for ancestor in doc_dir.parents:
        candidates.append(ancestor / "meta.json")

    for meta_path in candidates:
        try:
            resolved = str(meta_path.resolve())
        except OSError:
            resolved = str(meta_path)
        if resolved in tried:
            continue
        tried.add(resolved)
        if not meta_path.is_file():
            continue
        data = load_meta_map(meta_path, cache)
        if not data:
            continue
        entry = data.get(docid)
        if isinstance(entry, dict):
            return entry
    return None
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/test_meta_json_filters.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit (only if user requested)**

```bash
git add py/impact_config_suite/core/meta_json_filters.py py/impact_config_suite/tests/test_meta_json_filters.py
git commit -m "Add meta.json load and docid lookup helpers for scan filters."
```

---

### Task 2: Wire `_matches_config_filters` + cache clear (TDD)

**Files:**
- Modify: `py/impact_config_suite/core/element_extractor.py` (`__init__`, `clear_config_cache`, `_matches_config_filters`)
- Modify: `py/impact_config_suite/tests/test_meta_json_filters.py` (add integration tests)

**Interfaces:**
- Consumes: `lookup_meta_entry(file_path, self._meta_json_cache)`
- Produces: `_matches_config_filters` prefers meta client/dtd; XML fallback unchanged

- [ ] **Step 1: Write failing integration tests**

Append to `tests/test_meta_json_filters.py`:

```python
from core.element_extractor import ElementExtractor


def test_matches_filters_via_bits_meta_without_impact_config(tmp_path):
    bits = tmp_path / "BITS"
    doc = bits / "Nabc"
    doc.mkdir(parents=True)
    html = doc / "x.html"
    html.write_text("<p/>", encoding="utf-8")
    (bits / "meta.json").write_text(
        json.dumps({"Nabc": {"client": "TNF", "dtd": "BITS"}}), encoding="utf-8"
    )
    ee = ElementExtractor()
    assert ee._matches_config_filters(html, "BITS", "TNF") is True
    assert ee._matches_config_filters(html, "BITS", "PLOS") is False
    assert ee._matches_config_filters(html, "JATS", "TNF") is False


def test_matches_filters_falls_back_to_impact_config(tmp_path):
    bits = tmp_path / "BITS"
    doc = bits / "Nabc"
    doc.mkdir(parents=True)
    html = doc / "x.html"
    html.write_text("<p/>", encoding="utf-8")
    (doc / "impact_config.xml").write_text(
        """<?xml version="1.0"?>
        <config>
          <dtd name="BITS"/>
          <client name="TNF"/>
        </config>
        """,
        encoding="utf-8",
    )
    ee = ElementExtractor()
    assert ee._matches_config_filters(html, "BITS", "TNF") is True
    assert ee._matches_config_filters(html, "", "PLOS") is False


def test_matches_filters_empty_filters_true_without_meta(tmp_path):
    doc = tmp_path / "BITS" / "Nabc"
    doc.mkdir(parents=True)
    html = doc / "x.html"
    html.write_text("<p/>", encoding="utf-8")
    ee = ElementExtractor()
    assert ee._matches_config_filters(html, "", "") is True


def test_matches_filters_root_meta_when_bits_key_missing(tmp_path):
    root = tmp_path
    bits = root / "BITS"
    doc = bits / "Nabc"
    doc.mkdir(parents=True)
    html = doc / "x.html"
    html.write_text("<p/>", encoding="utf-8")
    (bits / "meta.json").write_text(json.dumps({}), encoding="utf-8")
    (root / "meta.json").write_text(
        json.dumps({"Nabc": {"client": "lww", "dtd": "bits"}}), encoding="utf-8"
    )
    ee = ElementExtractor()
    assert ee._matches_config_filters(html, "BITS", "LWW") is True


def test_clear_config_cache_clears_meta_cache(tmp_path):
    bits = tmp_path / "BITS"
    doc = bits / "Nabc"
    doc.mkdir(parents=True)
    html = doc / "x.html"
    html.write_text("<p/>", encoding="utf-8")
    (bits / "meta.json").write_text(
        json.dumps({"Nabc": {"client": "TNF", "dtd": "BITS"}}), encoding="utf-8"
    )
    ee = ElementExtractor()
    assert ee._matches_config_filters(html, "", "TNF") is True
    assert ee._meta_json_cache
    ee.clear_config_cache()
    assert ee._meta_json_cache == {}
```

- [ ] **Step 2: Run new tests — expect FAIL**

```bash
python -m pytest tests/test_meta_json_filters.py::test_matches_filters_via_bits_meta_without_impact_config -v
```

Expected: FAIL — currently returns False when no `impact_config.xml`.

- [ ] **Step 3: Wire ElementExtractor**

In `__init__`:

```python
self._meta_json_cache = {}
```

In `clear_config_cache`:

```python
def clear_config_cache(self) -> None:
    """Clear the impact_config.xml and meta.json caches."""
    self._config_cache.clear()
    self._meta_json_cache.clear()
```

Replace `_matches_config_filters` with:

```python
def _matches_config_filters(self, file_path: Path, dtd_filter: str, client_filter: str) -> bool:
    dtd_filter = self._normalize_named_filter(dtd_filter)
    client_filter = self._normalize_named_filter(client_filter)
    if not dtd_filter and not client_filter:
        return True

    file_path = Path(file_path)
    from core.meta_json_filters import lookup_meta_entry

    entry = lookup_meta_entry(file_path, self._meta_json_cache)
    if entry is not None:
        dtd_name = (entry.get("dtd") or "").strip()
        client_name = (entry.get("client") or "").strip()
        if dtd_filter and dtd_name.upper() != dtd_filter.upper():
            return False
        if client_filter and client_name.upper() != client_filter.upper():
            return False
        return True

    config_path = file_path.parent / "impact_config.xml"
    if not config_path.is_file():
        return False

    dtd_name, client_name, _, _, _, _, _ = self._load_impact_config_filters(config_path)
    if dtd_filter and dtd_name.upper() != dtd_filter.upper():
        return False
    if client_filter and client_name.upper() != client_filter.upper():
        return False
    return True
```

Prefer a top-of-file import of `lookup_meta_entry` if the file already has local imports style; avoid circular imports (module has none).

- [ ] **Step 4: Run full meta filter tests + a smoke of search workflow cache clear**

```bash
python -m pytest tests/test_meta_json_filters.py tests/test_search_workflow.py::TestSearchWorkflow::test_clear_config_cache_clears_cache -v
```

(Adjust test class path if the clear-cache test name differs — use `pytest tests/test_search_workflow.py -k clear_config_cache -v`.)

Expected: all selected tests PASS.

- [ ] **Step 5: Commit (only if user requested)**

```bash
git add py/impact_config_suite/core/element_extractor.py py/impact_config_suite/tests/test_meta_json_filters.py
git commit -m "Prefer meta.json for Element Extractor client/DTD scan filters."
```

---

## Spec coverage (self-review)

| Spec requirement | Task |
|---|---|
| Prefer nearest then root meta | Task 1 lookup + Task 2 wire |
| client/dtd fields only | Task 2 compare |
| Fall back to impact_config.xml | Task 2 |
| Empty filters unchanged | Task 2 test |
| Cache + clear | Task 1 cache + Task 2 clear |
| Invalid JSON miss | Task 1 |
| get_file_metadata unchanged | No edits to that method |
| Case-insensitive | Task 2 |

No placeholders. Function names consistent across tasks.

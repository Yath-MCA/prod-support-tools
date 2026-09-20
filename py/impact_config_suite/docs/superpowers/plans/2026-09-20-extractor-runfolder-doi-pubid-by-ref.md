# Timestamp Run Folders + DOI/pub-id by Ref Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prefix Element Extractor run folders with timestamps, and add a checkbox mode that replaces selector extract with a six-bucket first-hit DOI/pub-id/URI report (in/out `.ref`) plus `under_comment` and `doi_org_in_*` flags.

**Architecture:** Shared `format_extraction_run_folder_name(ts, safe_target, query_slug)` used by all run-folder creators. New `core/doi_pubid_by_ref.py` (BeautifulSoup, reuse `is_comment_element` and `.ref` token rules) extracts six first-buckets per file and writes HTML/CSV. Tab gains a “DOI / pub-id by ref (unique)” checkbox that skips normal extract (same gate style as mixed-citation-only).

**Tech Stack:** Python 3, BeautifulSoup, Tkinter Element Extractor tab, pytest, existing `get_file_metadata` / run-history snapshot patterns.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-20-extractor-runfolder-doi-pubid-by-ref-design.md`
- Run folder: `{YYYYMMDD_HHMMSS}_extraction_{safe_target}_{query_slug}` (example `20260919_234603_extraction_BITS_ext-link_ext-link-type_doi`)
- Mode replaces normal selector extract when checkbox is on; `query_slug` = `doi_pubid_by_ref`
- Six first-buckets only; 5b/5c are flags `doi_org_in_href` / `doi_org_in_text` on URI rows (in and out of `.ref`)
- `.ref` ancestor: class token `ref`, `data-name="ref"`, `data-role="ref"`, or tag `ref` (not substring `xref`)
- `under_comment`: direct parent only; reuse `is_comment_element` from `core/mixed_citation_direct_hits.py`
- Work under `C:\_IMPACT\prod-support-tools\py\impact_config_suite`; TDD; commit only if user asked

## File Map

| File | Responsibility |
|------|----------------|
| `core/extraction_run_paths.py` (create) | `format_extraction_run_folder_name(ts, safe_target, query_slug) -> str` |
| `core/doi_pubid_by_ref.py` (create) | Element classification, six-bucket extract, flags, HTML/CSV writers |
| `tabs/element_extractor_tab.py` (modify) | Use folder helper; checkbox; skip-selector gate; wire scan/report/history |
| `tests/test_extraction_run_paths.py` (create) | Folder name format |
| `tests/test_doi_pubid_by_ref.py` (create) | Buckets + flags + reports |
| `docs/element_extractor_docs.md` (+ root mirror) | Document naming + mode |

---

### Task 1: Run folder name helper (TDD)

**Files:**
- Create: `py/impact_config_suite/core/extraction_run_paths.py`
- Modify: `py/impact_config_suite/tabs/element_extractor_tab.py` (both `run_folder_name = f"extraction_..."` sites)
- Test: `py/impact_config_suite/tests/test_extraction_run_paths.py`

**Interfaces:**
- Produces: `format_extraction_run_folder_name(ts: str, safe_target: str, query_slug: str) -> str`

- [ ] **Step 1: Write failing test**

```python
# tests/test_extraction_run_paths.py
from core.extraction_run_paths import format_extraction_run_folder_name


def test_timestamp_prefix_then_extraction():
    name = format_extraction_run_folder_name(
        "20260919_234603", "BITS", "ext-link_ext-link-type_doi"
    )
    assert name == "20260919_234603_extraction_BITS_ext-link_ext-link-type_doi"
    assert name.startswith("20260919_234603_extraction_")
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
python -m pytest tests/test_extraction_run_paths.py -v
```

Expected: `ModuleNotFoundError` or import error.

- [ ] **Step 3: Implement helper**

```python
# core/extraction_run_paths.py
def format_extraction_run_folder_name(ts: str, safe_target: str, query_slug: str) -> str:
    return f"{ts}_extraction_{safe_target}_{query_slug}"
```

- [ ] **Step 4: Replace tab call sites**

In `tabs/element_extractor_tab.py`, import helper and change both places that currently do:

```python
run_folder_name = f"extraction_{safe_target_name}_{query_slug}_{ts}"
```

to:

```python
from core.extraction_run_paths import format_extraction_run_folder_name
run_folder_name = format_extraction_run_folder_name(ts, safe_target_name, query_slug)
```

(Sites: mixed-citation-only path ~1699 and normal extract path ~2000.)

- [ ] **Step 5: Re-run test — PASS**

```bash
python -m pytest tests/test_extraction_run_paths.py -v
```

- [ ] **Step 6: Commit** (if user requested)

```bash
git add py/impact_config_suite/core/extraction_run_paths.py py/impact_config_suite/tests/test_extraction_run_paths.py py/impact_config_suite/tabs/element_extractor_tab.py
git commit -m "Prefix Element Extractor run folders with timestamp."
```

---

### Task 2: Core six-bucket extraction + flags (TDD)

**Files:**
- Create: `py/impact_config_suite/core/doi_pubid_by_ref.py`
- Test: `py/impact_config_suite/tests/test_doi_pubid_by_ref.py`

**Interfaces:**
- Consumes: `is_comment_element` from `core.mixed_citation_direct_hits`; BeautifulSoup
- Produces:
  - `is_ref_element(node) -> bool`
  - `is_inside_ref(node) -> bool`
  - `is_pub_id_element(node) -> bool`
  - `is_ext_link_of_type(node, link_type: str) -> bool`  # "doi" | "uri"
  - `get_href(node) -> str`
  - `extract_buckets_from_soup(soup) -> list[dict]`  # up to 6 rows, document order firsts
  - Each row dict keys: `bucket` (1–6), `element_kind` (`pub-id`|`doi`|`uri`), `in_ref` (bool), `under_comment` (bool), `doi_org_in_href` (bool), `doi_org_in_text` (bool), `line`, `text`, `href`, `html`

Bucket mapping:
1 pub-id in_ref, 2 pub-id out, 3 doi in_ref, 4 doi out, 5 uri in_ref, 6 uri out

- [ ] **Step 1: Write failing tests**

```python
# tests/test_doi_pubid_by_ref.py
from bs4 import BeautifulSoup
from core.doi_pubid_by_ref import extract_buckets_from_soup

SAMPLE = """
<html><body>
  <div class="ref" data-name="ref">
    <span class="pub-id" data-name="pub-id">10.1/AAA</span>
    <span class="pub-id" data-name="pub-id">10.1/BBB</span>
    <a class="ext-link" ext-link-type="doi" href="https://doi.org/10.1/CCC">doi</a>
    <span class="comment" data-name="comment">
      <span class="ext-link" data-name="ext-link" ext-link-type="uri"
            xlink:href="https://doi.org/10.1109/TSMCB.2009.2015956">https://example.com/x</span>
    </span>
    <span class="ext-link" ext-link-type="uri" href="https://example.org/page">see doi.org/manual</span>
  </div>
  <span class="pub-id">10.1/OUT</span>
  <ext-link ext-link-type="doi" href="https://doi.org/10.1/OUTDOI">out</ext-link>
  <comment><ext-link ext-link-type="uri" xlink:href="https://example.com/no">plain</ext-link></comment>
</body></html>
"""


def test_six_buckets_first_only_and_flags():
    soup = BeautifulSoup(SAMPLE, "lxml")
    rows = extract_buckets_from_soup(soup)
    by_bucket = {r["bucket"]: r for r in rows}
    assert set(by_bucket) == {1, 2, 3, 4, 5, 6}
    assert by_bucket[1]["text"].strip() == "10.1/AAA"
    assert by_bucket[2]["text"].strip() == "10.1/OUT"
    assert by_bucket[5]["under_comment"] is True
    assert by_bucket[5]["doi_org_in_href"] is True
    assert by_bucket[5]["doi_org_in_text"] is False
    # second uri-in-ref is NOT kept as bucket 5 (first wins); flags on kept row only
    assert by_bucket[6]["under_comment"] is True
    assert by_bucket[6]["doi_org_in_href"] is False


def test_uri_doi_org_in_text_flag():
    html = '''<div class="ref"><span class="ext-link" ext-link-type="uri"
              href="https://example.org/x">https://doi.org/10.1/TXT</span></div>'''
    rows = extract_buckets_from_soup(BeautifulSoup(html, "lxml"))
    uri = [r for r in rows if r["bucket"] == 5][0]
    assert uri["doi_org_in_href"] is False
    assert uri["doi_org_in_text"] is True
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
python -m pytest tests/test_doi_pubid_by_ref.py -v
```

- [ ] **Step 3: Implement `core/doi_pubid_by_ref.py` (minimal)**

Core algorithm sketch:

```python
from bs4 import BeautifulSoup
from bs4.element import Tag
from core.mixed_citation_direct_hits import is_comment_element

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
    is_ext = node.name == "ext-link" or node.get("data-name") == "ext-link" or "ext-link" in _class_tokens(node)
    if not is_ext:
        return False
    return (node.get("ext-link-type") or "") == link_type

def get_href(node: Tag) -> str:
    for key, val in (node.attrs or {}).items():
        if key == "href" or key == "xlink:href" or (isinstance(key, str) and key.endswith("}href")):
            return str(val or "")
    return ""

def _under_comment(node: Tag) -> bool:
    parent = node.parent
    return isinstance(parent, Tag) and is_comment_element(parent)

def _row(bucket, kind, node, in_ref: bool) -> dict:
    text = node.get_text(" ", strip=True)
    href = get_href(node)
    under = _under_comment(node) if kind in ("doi", "uri") else False
    doi_href = ("doi.org" in href.lower()) if kind == "uri" else False
    doi_text = ("doi.org" in text.lower()) if kind == "uri" else False
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
        "html": str(node),
    }

def extract_buckets_from_soup(soup) -> list[dict]:
    filled = {}
    for node in soup.descendants:
        if not isinstance(node, Tag):
            continue
        in_ref = is_inside_ref(node)
        kind = None
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
```

Adjust tests if `lxml` wraps html differently; prefer asserting on bucket membership and flag values.

- [ ] **Step 4: Run tests — PASS**

```bash
python -m pytest tests/test_doi_pubid_by_ref.py -v
```

- [ ] **Step 5: Commit** (if user requested)

```bash
git add py/impact_config_suite/core/doi_pubid_by_ref.py py/impact_config_suite/tests/test_doi_pubid_by_ref.py
git commit -m "Add DOI/pub-id by-ref six-bucket extraction helpers."
```

---

### Task 3: CSV + HTML report writers

**Files:**
- Modify: `py/impact_config_suite/core/doi_pubid_by_ref.py`
- Test: `py/impact_config_suite/tests/test_doi_pubid_by_ref.py` (extend)

**Interfaces:**
- Produces:
  - `CSV_HEADER = ["file_path","file_name","doc_type","client","link_info","identifier","bucket","element_kind","in_ref","under_comment","doi_org_in_href","doi_org_in_text","line","text","href","outer_xml"]`
  - `write_doi_pubid_by_ref_csv(file_results: list[dict], output_path: Path) -> Path`
  - `generate_doi_pubid_by_ref_html(file_results, target_path, ts) -> str`
- `file_results` item shape: `{path, client, doc_type, link_info, identifier, ok, error?, buckets: list[dict]}`

- [ ] **Step 1: Test CSV header and one data row**

```python
import csv
from pathlib import Path
from core.doi_pubid_by_ref import write_doi_pubid_by_ref_csv, CSV_HEADER

def test_write_csv(tmp_path: Path):
    results = [{
        "path": str(tmp_path / "a.xml"),
        "doc_type": "Books", "client": "TNF", "link_info": "x", "identifier": "ID1",
        "ok": True,
        "buckets": [{
            "bucket": 5, "element_kind": "uri", "in_ref": True,
            "under_comment": True, "doi_org_in_href": True, "doi_org_in_text": False,
            "line": 10, "text": "t", "href": "https://doi.org/10.1/x", "html": "<a/>",
        }],
    }]
    out = tmp_path / "out.csv"
    write_doi_pubid_by_ref_csv(results, out)
    rows = list(csv.reader(out.open(encoding="utf-8", newline="")))
    assert rows[0] == CSV_HEADER
    assert rows[1][6] == "5"
    assert rows[1][9] == "True"
```

Files with `ok` and empty `buckets` contribute **no** CSV rows. Error files: no CSV rows.

- [ ] **Step 2: Implement writers** (HTML: simple dark-theme table per file + bucket badges; mirror style lightly from mixed-citation report if convenient)

- [ ] **Step 3: pytest PASS**

- [ ] **Step 4: Commit** (if requested)

---

### Task 4: Tab checkbox, skip gate, wire scan

**Files:**
- Modify: `py/impact_config_suite/tabs/element_extractor_tab.py`

**Interfaces:**
- Extend skip helper:

```python
def should_skip_selector_extract(mixed_hits: bool, mixed_only: bool, doi_pubid_by_ref: bool = False) -> bool:
    if doi_pubid_by_ref:
        return True
    return bool(mixed_hits) and bool(mixed_only)
```

- Checkbox `doi_pubid_by_ref_var` text: `DOI / pub-id by ref (unique)`
- Snapshot + history fields include `doi_pubid_by_ref`
- When mode on: early path like mixed-only — collect files, parse each with BeautifulSoup (`lxml` / `lxml-xml` by suffix), call `extract_buckets_from_soup`, attach metadata via `self.extractor.get_file_metadata`, write HTML/CSV under `format_extraction_run_folder_name(ts, safe_target, "doi_pubid_by_ref")`, set `last_report_path`, record history, `_finish_run_ui`

- [ ] **Step 1: Add checkbox** next to mixed-citation options (report options row 2)

- [ ] **Step 2: Wire `_snapshot_ui_settings`, `_current_run_settings`, apply-history restore**

- [ ] **Step 3: In `_run_extraction_thread`, after settings load**, if `doi_pubid_by_ref`:

```python
if doi_pubid_by_ref:
    # build run folder with format_extraction_run_folder_name(ts, safe_target, "doi_pubid_by_ref")
    # collect_matching_files / single file
    # for each file: soup = BeautifulSoup(...); buckets = extract_buckets_from_soup(soup)
    # meta = self.extractor.get_file_metadata(path)
    # write html/csv; history; return
```

Mutual exclusion: if both mixed-only and this mode are on, **prefer doi_pubid_by_ref** (document in log) OR disable mixed-only when this is checked — **decision: checking doi_pubid_by_ref unchecks/disables mixed-only** (simple UX).

- [ ] **Step 4: Allow empty query when this mode is on** (same as mixed-only validation in `_start_extraction`)

- [ ] **Step 5: Manual smoke** — one HTML fixture folder; confirm folder name timestamp-first and CSV flags

- [ ] **Step 6: Commit** (if requested)

```bash
git add py/impact_config_suite/tabs/element_extractor_tab.py
git commit -m "Wire DOI/pub-id by-ref mode into Element Extractor tab."
```

---

### Task 5: Documentation

**Files:**
- `docs/element_extractor_docs.md`
- `element_extractor_docs.md`

- [ ] **Step 1: Document** run folder template and the new checkbox / six buckets / flags (`under_comment`, `doi_org_in_href`, `doi_org_in_text`).

- [ ] **Step 2: Commit** (if requested)

---

## Spec coverage checklist

| Spec item | Task |
|-----------|------|
| Timestamp-prefixed run folders | Task 1 |
| Six first-buckets | Task 2 |
| `under_comment`, `doi_org_in_*` | Task 2 |
| HTML + CSV + meta | Task 3 |
| Checkbox replaces extract | Task 4 |
| History / snapshot | Task 4 |
| Docs | Task 5 |

## Plan self-review notes

- No TBD placeholders; mutual exclusion with mixed-only locked (doi mode wins / unchecks mixed-only).
- Bucket numbers and flag names match the spec.
- Folder helper used by mixed-only + normal + new mode.
- CSV omits empty-bucket files’ data rows; HTML still lists scanned files with zero hits.

# Mixed-citation Comment + Alpha Text Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend IMPACT Config Suite Element Extractor to scan HTML/XML, flag direct-child `comment` elements and alphabetic-only text nodes under each `mixed-citation`, and produce a client-wise HTML+CSV rollup (files searched vs files with hits).

**Architecture:** Add focused helpers (prefer `patterns/refs.py` recognition + a small extractor module or methods on `ElementExtractor`) that walk only `mixed-citation.contents`. Reuse existing folder scan, `impact_config.xml` client filters, and report output conventions from Element Extractor. GUI is a new checkbox on `element_extractor_tab.py` mirroring the citation-type report toggle.

**Tech Stack:** Python 3, BeautifulSoup (`lxml` / `lxml-xml`), Tkinter, existing pytest suite under `py/impact_config_suite/tests`.

## Global Constraints

- Match only **direct children** of `mixed-citation` (`class` or `data-name="mixed-citation"`).
- `comment` hit: tag `comment`, class `comment`, or `data-name="comment"` (same style as `patterns/refs.py` `get_ref_tag` / `REF_SEMANTIC_TAGS`).
- `alpha_text` hit: NavigableString whose stripped value matches `^[A-Za-z]+$` only (no digits, punctuation, spaces-only, empty).
- Skip ignorable nodes via `patterns/refs.py` `is_ignorable_ref_node`.
- Client from nearby `impact_config.xml` via existing `_load_impact_config_filters` / `_matches_config_filters`.
- Do not break existing Element Extractor modes/reports.
- Work on local path `C:\_IMPACT\prod-support-tools\py\impact_config_suite` (machine NKW-LD22-202). Do not commit unless asked.
- TDD: failing test first for each behavior; no production code without a failing test.

## File Map

| File | Responsibility |
|------|----------------|
| `core/mixed_citation_direct_hits.py` (create) | Pure extraction + rollup helpers (keep `element_extractor.py` from growing further if practical) |
| `core/element_extractor.py` (modify) | Thin wrappers: scan entrypoints, HTML/CSV report generators, client filter reuse |
| `tabs/element_extractor_tab.py` (modify) | Checkbox + wire scan/report open |
| `tests/test_mixed_citation_direct_hits.py` (create) | Unit tests + fixtures |
| `element_extractor_docs.md` (modify) | Short feature note |

---

### Task 1: Core match helpers (TDD)

**Files:**
- Create: `py/impact_config_suite/core/mixed_citation_direct_hits.py`
- Test: `py/impact_config_suite/tests/test_mixed_citation_direct_hits.py`

**Interfaces:**
- Produces:
  - `is_mixed_citation(node) -> bool`
  - `is_comment_element(node) -> bool`
  - `is_alpha_only_text(text: str) -> bool`
  - `extract_direct_hits_from_citation(citation) -> list[dict]` each dict: `{kind: "comment"|"alpha_text", value: str, line: int|None}`
  - `extract_direct_hits_from_soup(soup) -> list[dict]` adds `citation_html` / `ref_id` when available
  - `extract_direct_hits_from_file(path: Path) -> list[dict]`

- [ ] **Step 1: Write failing tests**

```python
from bs4 import BeautifulSoup
from core.mixed_citation_direct_hits import (
    extract_direct_hits_from_soup,
    is_alpha_only_text,
)

SAMPLE = """
<div class="ref" data-name="ref" id="CIT0014">
  <span class="mixed-citation" data-name="mixed-citation" publication-type="webpage">
    <span class="year" data-name="year">2009</span>.
    <span class="comment" data-name="comment">Retrieved from archive</span>
    SomeAlpha
    <span class="string-name"><span class="comment">nested</span></span>
  </span>
</div>
"""

def test_alpha_only_text_rules():
    assert is_alpha_only_text("SomeAlpha")
    assert not is_alpha_only_text("2009")
    assert not is_alpha_only_text(".")
    assert not is_alpha_only_text("A B")
    assert not is_alpha_only_text("  ")

def test_direct_comment_and_alpha_text_match():
    soup = BeautifulSoup(SAMPLE, "lxml")
    hits = extract_direct_hits_from_soup(soup)
    kinds = sorted(h["kind"] for h in hits)
    assert kinds == ["alpha_text", "comment"]
    assert any(h["kind"] == "comment" and "Retrieved" in h["value"] for h in hits)
    assert any(h["kind"] == "alpha_text" and h["value"] == "SomeAlpha" for h in hits)

def test_nested_comment_excluded():
    soup = BeautifulSoup(SAMPLE, "lxml")
    hits = extract_direct_hits_from_soup(soup)
    assert not any(h.get("value") == "nested" for h in hits)
```

- [ ] **Step 2: Run tests — expect FAIL** (`module not found` / missing funcs)

Run: `cd C:\_IMPACT\prod-support-tools\py\impact_config_suite && .\.venv\Scripts\python.exe -m pytest tests\test_mixed_citation_direct_hits.py -v`

- [ ] **Step 3: Minimal implementation** in `core/mixed_citation_direct_hits.py` using BeautifulSoup; import `is_ignorable_ref_node` / `get_ref_tag` from `patterns.refs` when possible.

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Do not commit** (user did not ask)

---

### Task 2: Client rollup + report generation (TDD)

**Files:**
- Modify: `core/mixed_citation_direct_hits.py` and/or `core/element_extractor.py`
- Test: extend `tests/test_mixed_citation_direct_hits.py`

**Interfaces:**
- Produces:
  - `rollup_by_client(file_results: list[dict]) -> list[dict]`  
    each: `{client, files_searched, files_with_hits, comment_hits, alpha_text_hits, total_hits}`
  - `generate_mixed_citation_direct_hits_report_html(...)` / `..._csv(...)` returning HTML string / writing CSV path
- Consumes: per-file `{path, client, ok, hits: list}`

- [ ] **Step 1: Write failing rollup tests** with two fake clients/files (one with hits, one without)

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement rollup + HTML/CSV** matching Element Extractor report style (badges, dark-friendly table, escape with `html.escape`)

- [ ] **Step 4: Run — expect PASS**

---

### Task 3: Scan integration on ElementExtractor

**Files:**
- Modify: `core/element_extractor.py`
- Test: `tests/test_mixed_citation_direct_hits.py` (file scan with tmp_path + optional stub impact_config.xml)

**Interfaces:**
- Produces:
  - `ElementExtractor.extract_mixed_citation_direct_hits(file_path: Path) -> list`
  - `ElementExtractor.scan_mixed_citation_direct_hits(path: Path, recursive: bool=False, extensions=..., filename_filter=..., dtd_filter=..., client_filter=..., progress_callback=None, cancel_check=None) -> dict`
    Return shape akin to other scans: `{file_path_str: {ok, matches/hits, client, error?}, ...}` plus summary counts

- [ ] **Step 1: Failing test** that writes a temp HTML file and asserts scan finds hits / respects client filter when config present

- [ ] **Step 2: Implement thin wrappers** reusing `_matches_config_filters` and directory walking patterns from `scan_bibr_citations` / `scan_directory`

- [ ] **Step 3: Tests PASS**

---

### Task 4: GUI checkbox + wiring

**Files:**
- Modify: `tabs/element_extractor_tab.py` near existing `citation_type_report_var` (~584)

**Interfaces:**
- New `BooleanVar` e.g. `mixed_citation_direct_hits_var`
- When checked (folder or single file run): after/instead-of normal extract as appropriate, call `scan_mixed_citation_direct_hits`, write HTML+CSV under Documents/`impact-support-log`, set `last_*` path, open if `open_report_var`

- [ ] **Step 1: Add checkbox** label: `Mixed-citation comment + alpha text`
- [ ] **Step 2: Persist** flag in history entry dict like `citation_type_report`
- [ ] **Step 3: Wire scan thread** to generate report; surface status in existing status label
- [ ] **Step 4: Manual smoke** — launch app if feasible OR import tab module without error

---

### Task 5: Docs + verification

**Files:**
- Modify: `element_extractor_docs.md`

- [ ] **Step 1: Document** new mode, match rules, report columns
- [ ] **Step 2: Run full new test module**  
  `.\.venv\Scripts\python.exe -m pytest tests\test_mixed_citation_direct_hits.py -v`
- [ ] **Step 3: Report** files changed, how to use GUI, test results

## Out of scope (v1)

- Nested comment/text inside `string-name` etc.
- Rewriting/fixing citations
- Cloud PR (GitHub not accessible to Cursor cloud agent for this repo)

## Self-review

- Spec coverage: direct comment ✓, alpha text ✓, client rollup ✓, files searched/found ✓, GUI ✓, tests ✓
- No placeholders left in steps
- Alpha rule locked to `[A-Za-z]+` (letters only, no spaces) as agreed

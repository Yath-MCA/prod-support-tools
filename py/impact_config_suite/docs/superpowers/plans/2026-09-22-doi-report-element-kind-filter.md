# DOI Report Element-Kind Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an All / doi / uri / pub-id dropdown to the progressive DOI HTML shell that filters match rows by existing `data-tag` / `element_kind`.

**Architecture:** HTML/JS only in `doi_shell_html` inside `core/ee_report_store.py`. No extract or CSV changes. Same AND pattern as under-comment / doi.org filters.

**Tech Stack:** Progressive DOI shell (vanilla JS), pytest string asserts.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-22-doi-report-element-kind-filter-design.md`
- Select id: `filterElementKind`; values `""` | `doi` | `uri` | `pub-id`
- Filter on `data-tag` already emitted from `element_kind`
- Work under `py/impact_config_suite`; TDD; commit only when user asks

## File Map

| File | Responsibility |
|------|----------------|
| `core/ee_report_store.py` | Add select + `applyFilters` kind check |
| `tests/test_ee_report_store.py` | Assert `filterElementKind` and options |
| `tests/test_doi_pubid_by_ref.py` | Assert id present in shell |

---

### Task 1: Element kind filter in DOI shell (TDD)

**Files:**
- Modify: `py/impact_config_suite/core/ee_report_store.py` (`doi_shell_html`)
- Test: `py/impact_config_suite/tests/test_ee_report_store.py`
- Test: `py/impact_config_suite/tests/test_doi_pubid_by_ref.py` (optional parallel assert)

- [ ] **Step 1: Extend failing assertions**

In `test_doi_shell_html_loads_report_data_js`:

```python
    assert 'id="filterElementKind"' in text
    assert 'value="doi"' in text
    assert 'value="uri"' in text
    assert 'value="pub-id"' in text
```

In `test_html_omits_empty_files_and_has_controls` (shell checks):

```python
    assert 'id="filterElementKind"' in html_out
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd C:\_IMPACT\prod-support-tools\py\impact_config_suite
python -m pytest tests/test_ee_report_store.py::test_doi_shell_html_loads_report_data_js -v
```

Expected: AssertionError missing `filterElementKind`.

- [ ] **Step 3: Add select after project-shortcode (or near flag filters)**

```html
      <select id="filterElementKind" class="filter-select" onchange="applyFilters()">
        <option value="">All kinds (doi / uri / pub-id)</option>
        <option value="doi">doi</option>
        <option value="uri">uri</option>
        <option value="pub-id">pub-id</option>
      </select>
```

- [ ] **Step 4: Extend `applyFilters()`**

Read kind once with other filters:

```javascript
  const elementKind = document.getElementById('filterElementKind').value;
```

Inside match loop, extend `flagOk` (or separate `kindOk`):

```javascript
      const kindOk = !elementKind || item.getAttribute('data-tag') === elementKind;
      const isMatch = searchOk && flagOk && kindOk;
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
python -m pytest tests/test_ee_report_store.py tests/test_doi_pubid_by_ref.py -v
```

- [ ] **Step 6: Commit (only if user requested)**

```bash
git add py/impact_config_suite/core/ee_report_store.py \
  py/impact_config_suite/tests/test_ee_report_store.py \
  py/impact_config_suite/tests/test_doi_pubid_by_ref.py
git commit -m "Add doi/uri/pub-id kind filter to progressive DOI report."
```

---

## Spec coverage

| Requirement | Task |
|-------------|------|
| Fixed All/doi/uri/pub-id select | Task 1 Step 3 |
| Filter on data-tag | Task 1 Step 4 |
| AND with other filters | Task 1 Step 4 |
| No extract/CSV change | File map |
| Tests | Task 1 Steps 1, 5 |

## Follow-up (not this plan)

Analyze progressive report partials → merge → cleanup / status complete after this lands.

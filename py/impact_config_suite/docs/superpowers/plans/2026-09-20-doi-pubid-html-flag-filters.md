# DOI/pub-id HTML Flag Filters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three All/Yes/No dropdown filters (Under comment, doi.org href, doi.org text) to the DOI/pub-id by-ref HTML report, filtering match rows via `data-*` attributes.

**Architecture:** Extend `generate_doi_pubid_by_ref_html` only. Emit `data-under-comment`, `data-doi-org-href`, `data-doi-org-text` on each `.match-item` from existing row booleans; add three `<select>` controls after `#filterIdentifier`; extend `applyFilters()` so flag selects AND with search and meta filters at match level.

**Tech Stack:** Python 3 f-string HTML report, vanilla JS in embedded `<script>`, pytest static HTML assertions.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-20-doi-pubid-html-flag-filters-design.md`
- HTML report only — no CSV, extraction, or Unique-tab changes
- Select ids: `filterUnderComment`, `filterDoiOrgHref`, `filterDoiOrgText`
- Values: `""` (All), `"true"` (Yes), `"false"` (No)
- Match attributes: lowercase `"true"` / `"false"` strings
- Work under `C:\_IMPACT\prod-support-tools\py\impact_config_suite`; TDD; commit only when user asks

## File Map

| File | Responsibility |
|------|----------------|
| `core/doi_pubid_by_ref.py` | Match `data-*`, three selects, `applyFilters()` flag checks |
| `tests/test_doi_pubid_by_ref.py` | Assert select ids + `data-*` from fixture flags |

---

### Task 1: Flag filter selects + match data attributes (TDD)

**Files:**
- Modify: `py/impact_config_suite/core/doi_pubid_by_ref.py` (match-item markup ~312, filter-row ~479–482, `applyFilters` ~553–589)
- Test: `py/impact_config_suite/tests/test_doi_pubid_by_ref.py`

**Interfaces:**
- Consumes: existing bucket row fields `under_comment`, `doi_org_in_href`, `doi_org_in_text` (bool)
- Produces: HTML with `#filterUnderComment` / `#filterDoiOrgHref` / `#filterDoiOrgText` and match `data-under-comment` / `data-doi-org-href` / `data-doi-org-text`

- [ ] **Step 1: Write the failing test**

Replace or extend `test_html_omits_empty_files_and_has_controls` so the hit fixture includes one row with all three flags true, and assert selects + attributes:

```python
def test_html_omits_empty_files_and_has_controls(tmp_path):
    results = [
        {
            "path": str(tmp_path / "hit.xml"),
            "doc_type": "Books", "client": "TNF", "link_info": "L1", "identifier": "DOC1",
            "ok": True,
            "buckets": [
                {
                    "bucket": 1, "element_kind": "pub-id", "in_ref": True,
                    "under_comment": False, "doi_org_in_href": False, "doi_org_in_text": False,
                    "line": 1, "text": "10.1/A", "href": "", "html": "<pub-id>10.1/A</pub-id>",
                },
                {
                    "bucket": 5, "element_kind": "uri", "in_ref": True,
                    "under_comment": True, "doi_org_in_href": True, "doi_org_in_text": True,
                    "line": 2, "text": "see doi.org", "href": "https://doi.org/10.1/x",
                    "html": "<a href='https://doi.org/10.1/x'>see doi.org</a>",
                },
            ],
        },
        {
            "path": str(tmp_path / "empty.xml"),
            "doc_type": "Journals", "client": "Other", "link_info": "", "identifier": "DOC2",
            "ok": True,
            "buckets": [],
        },
    ]
    html_out = generate_doi_pubid_by_ref_html(results, str(tmp_path))
    assert 'class="controls-panel"' in html_out
    assert "Collapse All" in html_out
    assert "Copy Markup" in html_out
    assert "Open HTML" in html_out
    assert "Copy Path" in html_out
    assert "Outer HTML/XML Markup" in html_out
    assert 'id="filterDocType"' in html_out
    assert 'id="filterClient"' in html_out
    assert 'id="filterIdentifier"' in html_out
    assert 'id="filterUnderComment"' in html_out
    assert 'id="filterDoiOrgHref"' in html_out
    assert 'id="filterDoiOrgText"' in html_out
    assert 'data-under-comment="true"' in html_out
    assert 'data-doi-org-href="true"' in html_out
    assert 'data-doi-org-text="true"' in html_out
    assert 'data-under-comment="false"' in html_out
    assert "hit.xml" in html_out
    assert "empty.xml" not in html_out
    assert "Books" in html_out
    assert "TNF" in html_out
    assert "DOC1" in html_out
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd C:\_IMPACT\prod-support-tools\py\impact_config_suite
python -m pytest tests/test_doi_pubid_by_ref.py::test_html_omits_empty_files_and_has_controls -v
```

Expected: FAIL — missing `filterUnderComment` / `data-under-comment="true"` (or similar AssertionError).

- [ ] **Step 3: Add `data-*` on each match-item**

In `generate_doi_pubid_by_ref_html`, where `.match-item` is built, compute string flags and put them on the div:

```python
uc = "true" if row.get("under_comment") else "false"
dh = "true" if row.get("doi_org_in_href") else "false"
dt = "true" if row.get("doi_org_in_text") else "false"
# ...
match_rows += f"""
<div class="match-item"
     data-tag="{html_lib.escape(kind)}"
     data-text="{html_lib.escape(text)}"
     data-under-comment="{uc}"
     data-doi-org-href="{dh}"
     data-doi-org-text="{dt}">
```

Keep existing badges, Copy Markup, Outer HTML/XML Markup blocks unchanged.

- [ ] **Step 4: Add the three filter selects**

Immediately after the `#filterIdentifier` `</select>`, insert:

```html
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
```

(In the Python f-string, escape braces as needed — these selects have no `{`/`}` so they paste as-is.)

- [ ] **Step 5: Extend `applyFilters()` for flag AND at match level**

Replace the match-loop body inside `applyFilters` so flag selects are read once and applied per item:

```javascript
function applyFilters() {
  const searchVal = (document.getElementById('searchInput').value || '').toLowerCase().trim();
  const docType = document.getElementById('filterDocType').value;
  const client = document.getElementById('filterClient').value;
  const identifier = document.getElementById('filterIdentifier').value;
  const underComment = document.getElementById('filterUnderComment').value;
  const doiOrgHref = document.getElementById('filterDoiOrgHref').value;
  const doiOrgText = document.getElementById('filterDoiOrgText').value;

  document.querySelectorAll('.file-card').forEach(card => {
    if (docType && card.getAttribute('data-doc-type') !== docType) {
      card.style.display = 'none'; return;
    }
    if (client && card.getAttribute('data-client') !== client) {
      card.style.display = 'none'; return;
    }
    if (identifier && card.getAttribute('data-identifier') !== identifier) {
      card.style.display = 'none'; return;
    }

    const filename = (card.getAttribute('data-filename') || '').toLowerCase();
    if (card.classList.contains('error-card')) {
      card.style.display = (!searchVal || filename.includes(searchVal)) ? 'block' : 'none';
      return;
    }

    let fileVisible = false;
    card.querySelectorAll('.match-item').forEach(item => {
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
    });
    card.style.display = fileVisible ? 'block' : 'none';
  });
}
```

Note: when search is empty and all flag filters are All, every match is visible (`searchOk` true, `flagOk` true) — same as today’s default. Do **not** keep the old `let fileVisible = !searchVal` shortcut; with flag filters, empty search can still hide rows, so start `fileVisible` at `false` and set true only when a match passes.

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd C:\_IMPACT\prod-support-tools\py\impact_config_suite
python -m pytest tests/test_doi_pubid_by_ref.py -v
```

Expected: all tests PASS (including `test_html_omits_empty_files_and_has_controls`).

- [ ] **Step 7: Commit (only if user requested)**

```bash
git add py/impact_config_suite/core/doi_pubid_by_ref.py py/impact_config_suite/tests/test_doi_pubid_by_ref.py
git commit -m "Add Under comment / doi.org flag filters to DOI/pub-id HTML report."
```

Do not stage `config/build_metadata.json`.

---

## Spec coverage (self-review)

| Spec requirement | Task |
|---|---|
| Three All/Yes/No selects after Identifier | Task 1 Step 4 |
| Select ids / option values | Task 1 Steps 1, 4 |
| `data-*` on match items | Task 1 Step 3 |
| Match-level filter; hide file if no matches | Task 1 Step 5 |
| AND with search + meta | Task 1 Step 5 |
| Error cards ignore flag filters | Task 1 Step 5 |
| Yes/No = true/false; always-false kinds count as No | Task 1 Steps 3, 5 |
| Tests for ids + true/false attrs | Task 1 Step 1 |
| No CSV / extraction changes | File map / Global Constraints |

No placeholders remaining. Attribute and select ids are consistent across test and implementation steps.

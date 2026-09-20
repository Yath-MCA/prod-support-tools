# DOI / pub-id HTML report — flag filters

**Date:** 2026-09-20  
**Status:** Approved for planning  
**Scope:** `generate_doi_pubid_by_ref_html` in `core/doi_pubid_by_ref.py` (+ tests)  
**Out of scope:** CSV export, extraction/bucket logic, Element Extraction Unique HTML, badge label renames

## Problem

The DOI / pub-id by-ref HTML report already computes and displays match flags:

- `under_comment` → badge `under-comment`
- `doi_org_in_href` → badge `doi.org@href`
- `doi_org_in_text` → badge `doi.org@text`

Operators can filter by doc type, client, and identifier, and search match text/markup, but cannot narrow the report to rows with or without those flags.

## Decision

Add three separate dropdowns (All / Yes / No), filter at **match-item** level (hide non-matching rows; hide file card when no rows remain), AND with existing search and meta filters. Implement via `data-*` attributes on each match plus extended `applyFilters()` JS.

## UI

Place three `<select class="filter-select">` controls in the existing `.filter-row`, after `#filterIdentifier`:

| Element id | First option (empty value) | Other options |
|---|---|---|
| `filterUnderComment` | All — Under comment | Yes (`true`), No (`false`) |
| `filterDoiOrgHref` | All — doi.org href | Yes (`true`), No (`false`) |
| `filterDoiOrgText` | All — doi.org text | Yes (`true`), No (`false`) |

Each select calls `applyFilters()` on `onchange` (same as existing selects). Default for all three: empty (All). Layout continues to use flex-wrap; no second filter strip.

## Match markup

On each `.match-item`, emit boolean attributes from the existing row fields (lowercase string `"true"` / `"false"`):

- `data-under-comment`
- `data-doi-org-href`
- `data-doi-org-text`

Existing badges and Outer HTML/XML Markup are unchanged.

## Filter behavior

`applyFilters()` remains a single AND pipeline:

1. **File meta** (unchanged): if doc type / client / identifier select is set and card `data-*` does not match → hide card and return.
2. **Error cards** (unchanged): search against filename only; flag filters do not apply.
3. **Match rows:** for each `.match-item`:
   - search must match (kind, text, markup, filename) when search is non-empty;
   - if `filterUnderComment` is non-empty, `data-under-comment` must equal it;
   - if `filterDoiOrgHref` is non-empty, `data-doi-org-href` must equal it;
   - if `filterDoiOrgText` is non-empty, `data-doi-org-text` must equal it.
4. Show the match when all applicable checks pass; show the file card only if at least one match is visible (or error-card rules above).

**Yes / No semantics:** Yes means the flag is true; No means the flag is false. Rows where a flag is never set true (e.g. pub-id for doi.org flags) count as false and appear when that filter is No.

## Testing

Extend HTML report tests (e.g. `test_html_omits_empty_files_and_has_controls` or a sibling) to assert:

- presence of `#filterUnderComment`, `#filterDoiOrgHref`, `#filterDoiOrgText`;
- a fixture match that sets flags emits the corresponding `data-*=\"true\"` (and unset flags emit `false`) on the match item.

No new unit tests for browser JS behavior beyond static HTML/attribute assertions (consistent with current report tests).

## Success criteria

- Operators can filter the live report to Under comment / doi.org href / doi.org text = All, Yes, or No independently.
- Flag filters compose with search and Books/Journals / Client / Identifier filters.
- Empty-hit files remain omitted from the report body (unchanged).
- Extraction and CSV outputs are unchanged.

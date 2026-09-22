# DOI report — element kind filter (doi / uri / pub-id)

**Date:** 2026-09-22  
**Status:** Approved for planning  
**Parent:** Progressive DOI HTML shell (`ee_report_store.doi_shell_html`)  
**Scope:** Match-level filter on existing `element_kind`  
**Out of scope:** Extract/bucket logic; CSV; progressive partials lifecycle (follow-up analysis)

## Problem

Operators need to narrow DOI/pub-id by-ref report rows by link kind the same way they filter under-comment / doi.org href / doi.org text. Kind is already stored (`doi`, `uri`, `pub-id` from `ext-link-type` / pub-id) and shown as `data-tag`, but there is no dedicated dropdown.

Example still classified as **uri** (with doi.org flags when applicable):

```html
<ext-link ext-link-type="uri" xlink:href="https://doi.org/10.1111/gec3.12444">https://doi.org/10.1111/gec3.12444</ext-link>
```

## Decision

**Approach 1:** One fixed select filtering on existing match `data-tag` / `element_kind`. No new extract flags.

## UI

Add `#filterElementKind` in the controls filter row:

| Option label | Value |
|--------------|-------|
| All kinds (doi / uri / pub-id) | `""` |
| doi | `doi` |
| uri | `uri` |
| pub-id | `pub-id` |

`onchange="applyFilters()"` like sibling selects.

## Filter behavior

Extend `applyFilters()` AND chain at match level:

- If `filterElementKind` is non-empty, require `item.getAttribute('data-tag') === kindValue`.
- Compose with search, under-comment, doi.org href/text, and file meta filters.
- Hide file card when no match rows remain visible.

## Data / extract

Unchanged. Matches already emit `element_kind` into `report-data.js` and `data-tag` in the shell.

## Testing

- Shell HTML contains `id="filterElementKind"` and the three kind options.
- Optional: static assert `applyFilters` references `filterElementKind` (same style as other filter tests).

## Follow-up (not this spec)

After implementation: analyze progressive report process (partials → merge → cleanup / status complete) separately.

## Success criteria

- Operators can filter to doi-only, uri-only, or pub-id-only rows in the live progressive report.
- No changes to extraction or CSV in this slice.

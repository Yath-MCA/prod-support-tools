# Element Extractor: CSV Metadata + Unique Matches

**Date:** 2026-09-19  
**Status:** Approved for planning  
**Scope:** `py/impact_config_suite` Element Extractor (`core/element_extractor.py`, `tabs/element_extractor_tab.py`, docs, tests)

## Problem

1. **CSV missing client/meta:** The HTML detailed report shows per-file metadata as `TYPE|CLIENT|LINK-INFO|IDENTIFIER` (e.g. `Books|TNF|pubkittnf|D2V085_Melzer190226TNF_FSM`) via `get_file_metadata` / `format_metadata_line`. The CSV export (`export_csv`) only writes selector/path/line/tag/text/outer_xml — so spreadsheet users cannot see client or related meta that the HTML already has.

2. **No unique-return view:** A single query often returns multiple elements in the same document that differ only by `xlink:href` (including lxml Clark notation `{http://www.w3.org/1999/xlink}href`). Users need a first-of-group unique set alongside the full match list, in both HTML and CSV.

## Goals

- Add CSV columns for `doc_type`, `client`, `link_info`, `identifier` (same fields as the HTML metadata line; not a single pipe string; no extra `dtd` / title columns).
- Always produce both full and unique views (no new “unique only” checkbox).
- Unique = keep the **first** match in each group within a file.
- Uniqueness key (per selector/query run, per file): same `tag` + all attributes equal **except** ignore `xlink:href` / keys ending with `}href`. Different `class` values remain different.
- HTML: **All matches** + **Unique** tab/section.
- CSV when export is enabled: full file + unique file, and uniqueness columns on both for Excel filtering.

## Non-goals

- Changing folder scan, filters, folder index, mixed-citation direct hits, or citation-type reports.
- Deduplicating across files.
- Ignoring attributes other than `xlink:href` / `}href`.
- Client-side-only uniqueness (JS) without Python parity for CSV.

## Chosen approach

**Post-process at report time** after scan results exist:

1. Annotate each match with `is_unique` and `unique_group_size`.
2. Drive HTML All / Unique and both CSV outputs from that annotation.
3. Do not collapse matches inside `parse_and_extract` (full list must remain available).

Rejected alternatives: dedup during parse (breaks always-both views); HTML-only JS filter (CSV would need a second implementation).

## Architecture

```
scan_results[file]["matches"]  (unchanged extraction)
        ↓
annotate_unique_matches (per file, per selector)
        ↓
    ├── HTML All matches (all annotated)
    ├── HTML Unique (is_unique only)
    ├── CSV full  (+ metadata + is_unique + unique_group_size)
    └── CSV unique (same columns; unique rows only)
```

Metadata for CSV rows comes from existing `get_file_metadata(Path)` (same source as HTML). Missing `impact_config.xml` → empty strings for the four columns.

## Components

| Piece | Responsibility |
|--------|----------------|
| `_attrs_for_uniqueness(attrs)` | Copy attributes; drop `xlink:href` and keys ending with `}href`. |
| `_unique_key(match)` | `(tag, frozenset(normalized_attrs.items()))`. |
| `annotate_unique_matches(matches)` | Stable order: first of each key → `is_unique=True`; later dups → `False`; set `unique_group_size` on every member of a group. Same list length. |
| `filter_unique_matches(matches)` | Representatives only. |
| `export_csv` | Extend headers; resolve metadata once per file path; write uniqueness columns. |
| CSV call site | Write `Element_Extraction_Report_*.csv` (all) and `Element_Extraction_Unique_*.csv` (unique). Same column schema on both. |
| `generate_html_report` | Tabs/sections **All matches** and **Unique**; badges for total and unique counts. |
| Tab / logging | No new checkbox. When CSV export is on, log both paths. History settings unchanged. |

## CSV schema

Fixed column order for both CSV files:

`selector`, `query_type`, `file_path`, `file_name`, `doc_type`, `client`, `link_info`, `identifier`, `instance_no`, `line`, `tag`, `inner_text`, `outer_xml`, `is_unique`, `unique_group_size`

- Keep original `instance_no` from the full match list in the unique CSV so rows can be joined back to the full CSV.
- Serialize `is_unique` as the strings `True` / `False` for Excel readability.

## HTML UX

- Two views: **All matches** (current behavior) and **Unique**.
- Unique subtitle/helper text: first match per tag+attrs, ignoring `xlink:href`.
- Unique view uses the same file-card / match-detail layout as All, filtered to representatives.
- Header stats show both total match count and unique match count.

## Uniqueness rules (normative)

Within one selector result set and one file path:

1. Build key = `(tag, frozenset(_attrs_for_uniqueness(attributes).items()))`.
2. Walk matches in list order; first occurrence of a key is the representative (`is_unique=True`).
3. Later matches with the same key are duplicates (`is_unique=False`).
4. After grouping, set `unique_group_size` to the group size on every member.
5. Do not compare line numbers or inner text for the key.
6. Different files never share a group.
7. Different selectors/queries are already separate result sets.

Edge cases:

- No attributes / no href: still group by tag + remaining attrs.
- Non-element xpath rows (`text_match` / `xpath_result`): participate with empty attrs.
- Singleton group: `is_unique=True`, `unique_group_size=1`.
- Parse-error files: unchanged (error cards; no CSV rows).

## Error handling

- Metadata lookup failures or missing config → blank meta cells; do not fail the export.
- Annotation must not drop matches; only add fields.
- If CSV export is disabled, skip both CSV files (HTML Unique tab still generated).

## Testing

- Normalize drops both `xlink:href` and `{http://www.w3.org/1999/xlink}href`.
- Three matches same tag/attrs except different hrefs → one unique, `unique_group_size=3`, first kept.
- Different `class` → two uniques.
- Different files → no cross-file collapse.
- CSV headers include the four meta columns; values match `get_file_metadata` for a fixture with `impact_config.xml`.
- Unique CSV row count equals count of `is_unique=True` in the full CSV; ≤ full row count.

## Documentation

Update `docs/element_extractor_docs.md` (and root `element_extractor_docs.md` if still mirrored) for:

- New CSV columns
- Dual CSV outputs
- HTML Unique tab and uniqueness definition

## File touch list (implementation)

- `core/element_extractor.py` — uniqueness helpers, HTML Unique view, CSV schema + dual write
- `tabs/element_extractor_tab.py` — wire dual CSV paths / logging
- `tests/` — new or extended unit tests for uniqueness + CSV meta
- `docs/element_extractor_docs.md` (+ mirror if applicable)

## Success criteria

- Spreadsheet of full CSV shows `client` / meta for files that show metadata in HTML.
- HTML Unique and unique CSV show the same first-of-group set for href-only attribute differences.
- Full match list remains available in HTML All and the full CSV.
- Existing scans and filters behave as today.

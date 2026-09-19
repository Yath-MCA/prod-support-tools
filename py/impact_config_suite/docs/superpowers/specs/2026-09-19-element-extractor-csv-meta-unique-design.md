# Element Extractor: CSV Metadata + Unique Matches

**Date:** 2026-09-19  
**Status:** Approved for planning  
**Scope:** `py/impact_config_suite` Element Extractor (`core/element_extractor.py`, `tabs/element_extractor_tab.py`, docs, tests)

## Problem

1. **CSV missing client/meta:** The HTML detailed report shows per-file metadata as `TYPE|CLIENT|LINK-INFO|IDENTIFIER` (e.g. `Books|TNF|pubkittnf|D2V085_Melzer190226TNF_FSM`) via `get_file_metadata` / `format_metadata_line`. The CSV export (`export_csv`) only writes selector/path/line/tag/text/outer_xml — so spreadsheet users cannot see client or related meta that the HTML already has.

2. **No unique-return view:** A single query often returns multiple elements in the same document that differ only by `xlink:href` (including lxml Clark notation `{http://www.w3.org/1999/xlink}href`). Users need a first-of-group unique set alongside the full match list, in both HTML and CSV.

3. **Post-run buttons stuck:** After an extraction “completes” (reports on disk), only **Cancel** remains usable; **Run**, **Open Last Report**, and history actions do not respond. Primary cause: worker hangs in `RunHistoryStore.add_entry` (see #4) so `finally` never re-enables Run. Secondary cause: any remaining worker-thread Tk `.config()` calls (e.g. `open_last_btn.config(...)`) which are unsafe on Windows.

4. **Run history not recorded (and can hang the worker):** `RunHistoryStore.add_entry` acquires `threading.Lock`, then calls `load_entries()` / `save_entries()` which try to acquire the **same non-reentrant lock** → deadlock. Confirmed via timed thread join. Secondary issue: `_current_run_settings` reads many Tk `StringVar`s from the worker thread, which can yield incomplete or wrong history fields even after the lock is fixed.

## Goals

- Add CSV columns for `doc_type`, `client`, `link_info`, `identifier` (same fields as the HTML metadata line; not a single pipe string; no extra `dtd` / title columns).
- Always produce both full and unique views (no new “unique only” checkbox).
- Unique = keep the **first** match in each group within a file.
- Uniqueness key (per selector/query run, per file): same `tag` + all attributes equal **except** ignore `xlink:href` / keys ending with `}href`. Different `class` values remain different.
- HTML: **All matches** + **Unique** tab/section.
- CSV when export is enabled: full file + unique file, and uniqueness columns on both for Excel filtering.
- After any run ends (success, cancel, or error), restore action buttons on the **main thread** only so Run / Open Last Report / history actions work again.
- Fix `RunHistoryStore.add_entry` lock deadlock so history persists; snapshot run settings for history without reading Tk vars from the worker thread.

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
| `_finish_run_ui(...)` (tab) | Single main-thread helper: re-enable Run, disable Cancel, enable Open Last Report when `last_report_path` exists; never call widget `.config` from the worker thread. |
| `RunHistoryStore` | Fix re-entrant lock bug in `add_entry` (unlocked load/save internals or `RLock`); keep public API unchanged. |

## Run history (normative)

- `add_entry` must not deadlock: while holding the store lock, call unlocked load/save helpers (preferred) or use `threading.RLock`.
- Element Extractor: build the history payload from values already captured on the main thread before the worker starts (path, queries, filters, report options), plus paths/counts produced by the worker (`report_path`, `csv_path`, unique csv path, match counts). Do not call `.get()` on Tk variables inside `_current_run_settings` from the worker.
- After a successful write, `_update_history_ui` on the main thread must show the new entry at the top of Saved Runs.
- Include unique CSV path in `params` when dual CSV is written (`unique_csv_path`).

## Post-run UI (normative)

- All Tk widget mutations from `_run_extraction_thread` (and helpers it calls) MUST go through `_ui` / `self.after(0, ...)`.
- Replace direct `self.open_last_btn.config(...)` in the success and mixed-only success paths with a scheduled finish helper.
- `finally` already resets Run/Cancel via `_ui`; fold Open Last Report enable into that same callback when a report path was set, so one atomic main-thread update restores the action row.
- Do not leave Cancel enabled after a completed run.

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

- `core/run_history.py` — fix `add_entry` lock deadlock
- `core/element_extractor.py` — uniqueness helpers, HTML Unique view, CSV schema + dual write
- `tabs/element_extractor_tab.py` — dual CSV; main-thread UI finish; history payload snapshot
- `tests/` — uniqueness + CSV meta; `RunHistoryStore.add_entry` does not hang and persists
- `docs/element_extractor_docs.md` (+ mirror if applicable)

## Success criteria

- Spreadsheet of full CSV shows `client` / meta for files that show metadata in HTML.
- HTML Unique and unique CSV show the same first-of-group set for href-only attribute differences.
- Full match list remains available in HTML All and the full CSV.
- Existing scans and filters behave as today.
- After a completed run, **Run** and **Open Last Report** work; **Cancel** is disabled until the next run starts.
- Completed runs appear in Saved Runs with correct source/query/report path; `RunHistoryStore.add_entry` returns without hanging.

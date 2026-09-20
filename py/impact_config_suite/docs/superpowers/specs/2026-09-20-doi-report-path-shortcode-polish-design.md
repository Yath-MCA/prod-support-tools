# DOI report UI polish — path hide + project-shortcode

**Date:** 2026-09-20  
**Status:** Approved  
**Parent:** `2026-09-20-ee-progressive-json-reports-design.md`  
**Scope:** DOI / pub-id progressive HTML shell + file records (Phase 1 polish)  
**Out of scope for this addendum:** Detailed extract / Unique migration; opening browser on first hit; empty-metadata hide

## Decisions (validated)

### 1. Remove visible file path

- Do **not** render `class="file-path"` on file cards.
- Keep `path` on each file object in `report-data.js` so **Copy Path** and **Open HTML** still work.

### 2. Add `project_shortcode`

- Populate from `run_meta.json` entry for the docid: field `project-shortcode` (also accept `project_shortcode`).
- Show in `class="file-metadata"` pipe line after identifier:  
  `doc_type | client | link_info | identifier | project_shortcode` (omit blanks).
- Add filter `#filterProjectShortcode` (All / distinct values), AND with existing meta filters via `data-project-shortcode`.

### 3. Meta fallbacks when writing file records

- Prefer `get_file_metadata` for doc_type / client / link_info / identifier when present.
- Fall back to run_meta `type` / `client` / `file-id` when XML meta is empty.
- Always prefer run_meta for `project_shortcode`.

## Deferred to Phase 2

- Add `project_shortcode` column to DOI / pub-id **CSV** export (header + rows).
- Continue progressive JSON rollout for other Element Extractor HTML reports (see parent Phase 2).

## Optional (not in this polish)

- Hide `file-metadata` when the joined line is empty.
- Open browser on first file **with matches**, not first scanned file.
- Prefer run_meta for client/type whenever present (even if XML also has values).

## Testing

- Shell HTML: no `class="file-path"`; has `filterProjectShortcode` and `file-metadata`.
- File records in `report-data.js` include `project_shortcode` when run_meta has it (covered by writer + store integration / manual run).

## Success criteria

- Operators use Copy Path / Open HTML instead of a path line.
- Operators can filter and see project-shortcode in the DOI progressive report.
- CSV shortcode lands in Phase 2, not this polish.

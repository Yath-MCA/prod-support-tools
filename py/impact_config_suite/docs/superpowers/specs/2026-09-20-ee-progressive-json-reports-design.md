# Element Extractor progressive JSON reports

**Date:** 2026-09-20  
**Status:** Approved for planning  
**Scope:** All Element Extractor HTML reports (phased rollout)  
**Out of scope:** Changing extract/query semantics; CSV schema redesign (CSV may still be written at end from merged data); Document Manager / other tabs

## Problem

Today each run builds a large HTML file **after** the full scan: markup, meta, and UI are embedded in one document. Operators wait until completion to open anything. Concurrent workers cannot safely share one growing HTML/JSON file without races. `meta.json` already knows client/DTD/docids, but the run folder does not snapshot it for the report pipeline.

## Goals

1. Thin HTML shell + data file(s) in the **same run folder** as today (`impact-support-log/{ts}_extraction_…/`).
2. Progressive visibility: open the primary report when the **first** file result exists; scan continues.
3. Safe concurrency: parallel parse OK; **no** multi-writer overwrite of a shared results file.
4. Snapshot `meta.json` into the run folder when available.
5. Partials merge into one final data artifact; **no leftover partials** after a successful finish.
6. One shared report renderer schema usable by DOI/pub-id, detailed extract, Unique, and later sibling EE HTML reports.

## Non-goals

- Serving reports over HTTP (unless a later phase needs it).
- Replacing CSV mid-run.
- Opening every secondary report (citation / mixed) mid-scan.

## Architecture

### Run folder layout (after a successful run)

```
{run_folder}/
  index.html              # or existing report filename = thin shell
  report-data.js          # window.__EE_REPORT__ = { ... }  (final merged)
  run_meta.json           # optional snapshot of source meta.json
  manifest.json           # docids + html/xml paths chosen for this run
  *.csv                   # unchanged timing: end of run from merged data
  # partials/             # EXISTS ONLY WHILE RUNNING — deleted after merge
```

During the run only:

```
{run_folder}/partials/<safe_id>.json
```

### Why `report-data.js` (not fetch of `.json`)

Reports open as `file://`. Sibling `<script src="report-data.js">` works without a local server; `fetch("report-data.json")` often does not.

### Concurrency model

1. **Main / coordinator** creates the run folder, writes shell + empty `report-data.js` (`status: "running"`), copies `run_meta.json`, writes `manifest.json`.
2. Workers (threads or `ProcessPoolExecutor`) parse files and either:
   - return results to the coordinator, which writes `partials/<id>.json`, **or**
   - write only their own `partials/<id>.json` (never the shared `report-data.js`).
3. Coordinator periodically (or on each completion) rebuilds `report-data.js` from known partials / in-memory merge for live UI.
4. On finish or cancel: merge all partials → final `report-data.js` with `status: "complete"|"cancelled"` → **delete `partials/`**.
5. Crash mid-run may leave partials; next successful merge for that folder or a cleanup helper may remove them — normal complete path leaves none.

### Progressive open

- Reuse existing **Open HTML report…** checkbox (default on).
- When checked: open the **primary** report **once** when the first partial/result is written (`status: "running"`).
- Do **not** open that same primary report again at completion (avoids duplicate tabs).
- Secondary HTML (citation-type, mixed-citation, etc.): keep current end-of-run open behavior unless later specified; mid-run open is primary only.
- Shell polls/reloads `report-data.js` while `status === "running"` (interval ~1–2s or on focus); stops when complete/cancelled.

### `run_meta.json`

- If scan root (or parent) has `meta.json`, copy/snapshot into the run folder as `run_meta.json` at run start.
- Used to build the filtered docid set and for audit; report filter dropdowns may still derive from result rows.
- If no meta: omit `run_meta.json`; discovery falls back to existing collect path.

### `manifest.json`

Minimal list of work items for the run, e.g.:

```json
{
  "source_path": "...",
  "dtd_filter": "JATS",
  "client_filter": "TNF",
  "files": [
    { "docid": "N…", "path": "…/N…/file.html" }
  ]
}
```

### Report data schema (shared)

```json
{
  "version": 1,
  "kind": "doi_pubid_by_ref | extract | extract_unique | mixed_citation | …",
  "status": "running | complete | cancelled",
  "generated": "ISO or local timestamp",
  "source_path": "",
  "stats": { },
  "files": [
    {
      "id": "stable-id",
      "path": "",
      "name": "",
      "doc_type": "",
      "client": "",
      "link_info": "",
      "identifier": "",
      "ok": true,
      "error": "",
      "matches": [ { "… kind-specific fields …" } ]
    }
  ]
}
```

Kind-specific match fields stay inside `matches[]` (DOI buckets/flags vs tag/text/html for extract). Outer markup may later move to lazy chunks; **phase 1** may keep markup inline in match objects for parity with current HTML.

### Phased rollout

| Phase | Deliverable |
|-------|-------------|
| 1 | Shared shell + schema + partials/merge/cleanup + progressive open for **DOI / pub-id by-ref** |
| 2 | Detailed extract HTML (+ Unique panel/data) on the same shell/schema |
| 3 | Mixed-citation / citation-type EE HTML reports |

CSV and history `report_path` continue to point at the primary HTML path.

## UI / checkbox copy

Update Open HTML checkbox label to reflect early open, e.g.  
“Open HTML report in browser when first results are ready”  
(behavior: once on first result; no second open of primary at end).

## Testing

- Unit: merge partials → single `report-data.js`; `partials/` removed after merge.
- Unit: concurrent-style writes of distinct partials then merge loses no rows.
- Unit: no `meta.json` → no `run_meta.json`; run still completes.
- Integration/smoke: DOI mode with open_report writes shell early; status transitions running → complete.
- Regression: file:// shell loads `report-data.js` without fetch.

## Success criteria

- Primary report can be opened before the scan finishes and shows growing results.
- Parallel extract does not drop results due to shared-file overwrite.
- Successful runs leave no `partials/` residue.
- All EE HTML report kinds can migrate onto the same shell/schema over phases without changing extract logic.

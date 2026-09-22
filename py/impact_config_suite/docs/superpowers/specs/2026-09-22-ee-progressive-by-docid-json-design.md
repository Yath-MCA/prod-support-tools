# Recommended design — progressive EE results (JSON index + by_docid)

**Date:** 2026-09-22  
**Status:** P0 implemented (index.js + retained by_docid/; periodic flush; shell filters unchanged)  
**Applies to:** Element Extractor reports (start: DOI/pub-id; then general XPath/CSS extract)  
**Supersedes (for I/O strategy):** full rewrite of `report-data.js` after every file; delete-all-partials-on-finish as the only retention model

## Goals

1. Fast progressive UI while scanning (open early, grow results).  
2. Durable per-document result JSON for lookup and **same-query reuse**.  
3. Avoid O(n²) merge cost and giant single-payload rewrites.  
4. Keep run artifacts under the log/run folder; optional copy next to docid.  
5. Safe concurrency: many parsers, **one writer**.

## Recommended layout (run folder)

```
{run_folder}/                          # impact-support-log/{ts}_extraction_…
  index.html                           # thin shell
  index.js                             # window.__EE_INDEX__  (status, stats, file list)
  manifest.json                        # catalog + pointers (not match bodies)
  by_docid/<docid>__<safe_file>.js     # window.__EE_DOC__['…'] = { …file record… }
  # OR .json if serving via local HTTP; prefer .js for file://
  run_meta.json                        # optional snapshot of meta.json
  report.csv                           # end of run (unchanged timing)
```

**Optional (checkbox, default off):** also write  
`{docid_dir}/ee_cache/<query_slug>.json`  
mirroring the by_docid payload for that document.

Do **not** require deleting `by_docid/` on success. Keep it for reuse and audit.

## Manifest vs by_docid

| File | Contains |
|------|----------|
| `manifest.json` | Query, filters, list of `{ docid, path, result_ref, status, mtime, size }` — **pointers only** |
| `by_docid/*.js` | Full file record: meta, matches (markup, flags, kind, …) |
| `index.js` | `status`, `stats`, lightweight `files[]` (meta + match counts + `result_ref`) for the shell |

Manifest does **not** inline all partial JSON bodies.

## Progressive flow

1. **Start:** create run folder; write shell + empty `index.js` (`status: "running"`); write `manifest.json` skeleton; snapshot `run_meta.json` if present.  
2. **Per file (worker):** parse (or load cache — see below); return record to coordinator.  
3. **Coordinator (single writer):**  
   - Write `by_docid/<id>.js` once.  
   - Append/update in-memory index entry.  
   - Flush `index.js` every **N files** or every **~1–2s** (not every file).  
4. **First result:** open primary HTML once if “Open when first results ready.”  
5. **Stop:** set `status: "complete"|"cancelled"`; final `index.js` flush; write CSV from in-memory/by_docid; **retain** `by_docid/`.

No full “load all partials → rewrite mega report-data.js” on every file.

## Shell rendering

- Load `index.js` (poll while `running`).  
- Render file cards from index (meta, counts, badges).  
- On expand / “Load markup”: inject `<script src="by_docid/….js">` (file://-safe) or fetch if HTTP.  
- Filters (kind, doi.org flags, client, project-shortcode, …) operate on loaded match data; for unloaded docs, either lazy-load or filter on index fields only until expanded.

## Same XPath / query reuse (docid cache)

When “cache next to docid” (or run `by_docid` from a prior run with same query) is enabled:

**Cache key** (store inside JSON):

- `query_type`, `query_value` (normalized)  
- `schema_version`  
- source file `mtime` + `size` (or content hash if cheap later)

**On scan:** if cache hit → skip parse, use cached matches; still register in this run’s manifest/index.

Invalidation: any key mismatch → re-parse and overwrite cache.

## Dual location policy

| Location | Default | Purpose |
|----------|---------|---------|
| Run `by_docid/` | **Always** | Progressive report + audit |
| Docid `ee_cache/` | **Optional** | Next same-query reuse beside the document |

Prefer not writing into source trees unless the operator opts in (permissions / read-only shares).

## Concurrency

- Parallel parse: OK (`ProcessPool` / threads).  
- JSON/index writes: **main coordinator only**.  
- Workers never rewrite shared `index.js`.

## Speed checklist (must-haves)

1. Periodic index flush (not per-file full merge).  
2. Lazy load of markup-heavy payloads.  
3. Query cache reuse when key matches.  
4. Optional async/deferred copy to docid folder.  
5. Omit zero-hit files from progressive **UI** (still optional in manifest as scanned).

## Phased rollout

| Phase | Deliverable |
|-------|-------------|
| P0 | DOI/pub-id: switch from per-file full `report-data.js` rebuild to `index.js` + retained `by_docid/`; periodic flush; keep shell filters |
| P1 | Lazy load matches on expand; stop deleting partials/by_docid |
| P2 | Optional docid `ee_cache/` + same-query skip-parse |
| P3 | General Element Extractor (XPath/CSS) on same store |
| P4 | CSV `project_shortcode` + any remaining meta columns |

## Out of scope (initial)

- Mandatory write into every docid folder  
- HTTP report server (optional later)  
- Changing extract semantics / six-bucket DOI rules  

## Success criteria

- Large runs no longer rewrite one growing mega-JS after every file.  
- After complete, operator can open `by_docid/<docid>…` JSON/JS directly.  
- Manifest lists all result refs; bodies live in by_docid files.  
- Same query + unchanged file can skip re-parse when cache enabled.  
- Progressive open + filters still work.

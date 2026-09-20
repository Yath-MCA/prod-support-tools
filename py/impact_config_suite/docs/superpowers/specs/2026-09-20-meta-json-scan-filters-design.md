# meta.json for client/DTD scan filters

**Date:** 2026-09-20  
**Status:** Approved for planning  
**Scope:** Element Extractor client/DTD **folder-scan filtering** via `_matches_config_filters`  
**Out of scope:** Report/CSV/`get_file_metadata` (still `impact_config.xml`); generating or maintaining `meta.json`; Document Manager / other tools unless they already call `_matches_config_filters`

## Problem

On large DTD-organized trees (e.g. `…/FOOTNOTES/…/BITS|JATS/<docid>/…`), applying Client or DTD filters opens each doc’s `impact_config.xml`. Operators already have aggregated metadata:

```
root/documents.json
root/meta.json
root/BITS/meta.json
root/JATS/meta.json
```

Example entry (BITS/JATS `meta.json`):

```json
"N00013009-f0f8-49df-81b6-0bad52d03d80": {
  "file-id": "9781041023784_reverted_impact",
  "math-info": "",
  "client": "TNF",
  "project-shortcode": "IPT",
  "type": "Books",
  "dtd": "BITS"
}
```

Reading one JSON map (cached) is far cheaper than parsing tens of thousands of XML configs for filter decisions.

## Decision

Use **Approach 1:** Prefer `meta.json` inside `_matches_config_filters` when a client and/or DTD filter is set. Leave `get_file_metadata` and report/CSV meta on `impact_config.xml`. Fall back to today’s XML path when meta is missing or the docid is absent.

## Lookup order

**Docid key:** `file_path.parent.name`.

When both filters are empty: behavior unchanged (return True; no meta required).

When either filter is set:

1. **Nearest meta:** `{file_path.parent.parent}/meta.json` when that parent is the DTD folder (typical `…/BITS/<docid>/file` → `BITS/meta.json`). Load with cache keyed by absolute path + mtime.
2. If that file does not exist **or** docid is not a key in the map → walk ancestors upward for the next `meta.json` (typically `root/meta.json`), skipping a re-read of the same path already tried.
3. If an entry is found: compare `client` and/or `dtd` fields to the active filters (case-insensitive, same semantics as current XML compare).
4. If still no usable entry → existing path: `file_path.parent / "impact_config.xml"` via `_load_impact_config_filters`. Missing XML still means filter fail (unchanged).

**Invalid / unreadable JSON:** treat that file as a miss; continue to the next source. Do not abort the scan.

## Field mapping (filters only)

| Filter | meta.json field |
|--------|-----------------|
| Client | `client` |
| DTD | `dtd` |

Other meta fields (`type`, `file-id`, `project-shortcode`, `math-info`) are **not** used in this change.

## Caching

- Cache parsed `meta.json` dicts by absolute path string + `st_mtime` (same idea as `_config_cache`).
- Clear with existing config-cache clear hooks if present, or extend `clear_config_cache` to clear meta caches too so long-running GUI sessions pick up regenerated meta files after explicit clear / restart.

## Integration points

- Primary: `ElementExtractor._matches_config_filters`.
- Callers (folder scan, folder index refresh filters, mixed-citation client filter, etc.) inherit behavior automatically — no duplicate filter logic.
- Optional small module or private helpers for load/resolve to keep `element_extractor.py` readable; not a new UI control.

## Testing

tmp_path fixtures:

1. Client filter matches via `BITS/meta.json` with **no** `impact_config.xml`.
2. Docid missing from BITS meta but present in `root/meta.json` → match.
3. Missing from both metas → fall back to `impact_config.xml` client/dtd.
4. Empty client+DTD filters → all files pass; meta not required.
5. Case-insensitive client/dtd comparison.
6. Corrupt nearest `meta.json` → fall through to root or XML without raising.

## Success criteria

- With client/DTD filters on a BITS/JATS tree that has `meta.json`, scans do not need per-doc XML solely to accept/reject by client/DTD when the docid is in meta.
- Reports still show TYPE|CLIENT|… from `impact_config.xml` as today.
- No `meta.json` / no key → same filter outcome as today via XML fallback.

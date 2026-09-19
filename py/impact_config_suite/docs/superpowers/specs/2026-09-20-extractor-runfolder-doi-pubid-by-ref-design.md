# Element Extractor: Timestamp-Prefixed Run Folders + DOI/pub-id by Ref Mode

**Date:** 2026-09-20  
**Status:** Approved for planning  
**Scope:** `py/impact_config_suite` Element Extractor (`tabs/element_extractor_tab.py`, new scan/report helper, docs, tests)

## Problems

1. **Run folder timestamp position:** Folders are named `extraction_{target}_{query}_{ts}` (e.g. `extraction_BITS_ext-link_…_20260919_234603`). Operators want the timestamp **first** for sortability: `20260919_234603_extraction_BITS_ext-link_…`.

2. **DOI / pub-id discovery by parent:** Need a dedicated scan (not the generic Unique tab) that, per document, keeps the **first** hit in each of six buckets: `pub-id` / `ext-link[ext-link-type=doi]` / `ext-link[ext-link-type=uri]` × inside ancestor `.ref` vs outside `.ref`. Some clients wrap URI/DOI links under a direct-parent `comment`; that must be flagged. URI rows also need flags when `doi.org` appears in href and/or text.

## Goals

- Rename all Element Extractor run folders to `{YYYYMMDD_HHMMSS}_extraction_{safe_target}_{query_slug}`.
- Add checkbox mode that **replaces** normal selector extract for that run.
- Per file, emit up to six first-match buckets (document order).
- Columns/flags: `under_comment`, `doi_org_in_href`, `doi_org_in_text` (see normative rules).
- HTML + CSV outputs with existing file metadata fields (`doc_type`, `client`, `link_info`, `identifier`).

## Non-goals

- Changing generic Unique-tab logic (tag+attrs ignoring `xlink:href`).
- Splitting URI-in-ref into separate first-buckets for 5b/5c (those are **flags only**).
- Changing mixed-citation or citation-type report content (only shared folder naming if they share the template).

## Chosen approach

Dedicated mode module (same pattern as mixed-citation-only) plus a shared run-folder name helper. Rejected: six hard-coded multi-selectors + post-filter; extending generic Unique only.

## Task 1 — Run folder naming

**Template (all extract modes that create a run folder):**

```text
{YYYYMMDD_HHMMSS}_extraction_{safe_target}_{query_slug}
```

**Example:** `20260919_234603_extraction_BITS_ext-link_ext-link-type_doi`

- `ts` format remains `%Y%m%d_%H%M%S`.
- Optional month parent folder (`org_by_month`) unchanged: `output/{YYYY-MM}/{run_folder_name}/`.
- Apply everywhere the tab currently builds `extraction_{…}_{ts}` (normal extract, mixed-only, and this new mode).

## Task 2 — DOI / pub-id by ref mode

### UI

- New checkbox, e.g. **“DOI / pub-id by ref (unique)”**.
- When checked: **skip** normal CSS/XPath/Tag selector extract (same control pattern as mixed-citation-only).
- Query field may be unused for extract; folder `query_slug` can be a fixed token such as `doi_pubid_by_ref`.

### Six first-buckets (per file / docid)

| # | Element | Parent |
|---|---------|--------|
| 1 | `pub-id` (CSS `.pub-id` / tag `pub-id`) | inside ancestor with class or `data-name` `ref` (treat as `.ref`) |
| 2 | same | **not** inside such a `.ref` ancestor |
| 3 | `ext-link[ext-link-type="doi"]` | inside `.ref` |
| 4 | same | outside `.ref` |
| 5 | `ext-link[ext-link-type="uri"]` | inside `.ref` |
| 6 | same | outside `.ref` |

- **First** = earliest in document order within that bucket.
- Empty bucket → no row for that bucket.
- A single element belongs to **one** type bucket and **one** parent bucket only.

### Flags / columns (not extra buckets)

| Flag | Applies to | Rule |
|------|------------|------|
| `under_comment` | doi/uri `ext-link` rows | Direct parent is comment: tag `comment`, or class/`data-name` `comment`. Nested deeper → `False`. |
| `doi_org_in_href` | URI rows (buckets 5 and 6) | Case-insensitive substring `doi.org` in href (`xlink:href` or Clark `{…}href` or `href`). |
| `doi_org_in_text` | URI rows (buckets 5 and 6) | Case-insensitive substring `doi.org` in element text content. |

- Labels **5b** / **5c** in operator language map to `doi_org_in_href` / `doi_org_in_text` on URI-in-ref rows; the **same flags** apply to URI-out-ref rows.
- `pub-id` rows: `under_comment` = `False` (or blank); doi.org flags blank/`False`.
- Both href and text may be true on the same URI row.

### Recognition notes

- Match HTML-ish and XML: class-based (`class="ext-link"`, `data-name="ext-link"`) and element names (`ext-link`, `pub-id`, `comment`, `ref`).
- `ext-link-type` attribute equals `doi` or `uri` (case-sensitive as in source unless existing extractor normalizes otherwise — prefer exact match used by CSS `ext-link-type="doi"`).
- `.ref` ancestor: walk parents; treat as in-ref if any ancestor has tag `ref`, or `data-name="ref"`, or CSS class token `ref` (split on whitespace). Do not treat class names that merely contain the substring `ref` (e.g. `xref`) as `.ref`.

### Outputs

- HTML report summarizing per-file six buckets + flags.
- CSV with stable columns, including at least: file path/name, meta (`doc_type`, `client`, `link_info`, `identifier`), `bucket` (1–6 or named), `element_kind` (`pub-id`/`doi`/`uri`), `in_ref`, `under_comment`, `doi_org_in_href`, `doi_org_in_text`, line, text, href/outer markup as useful.
- Reuse `get_file_metadata` for meta columns.

### History

- Persist checkbox in run history like other report options.
- Snapshot settings on main thread (existing pattern).

## Architecture

```
Checkbox on
    → skip selector extract
    → scan files (existing collect/filter path)
    → doi_pubid_by_ref.extract_per_file
    → HTML + CSV under {ts}_extraction_…/doi_pubid_by_ref run folder
```

## Components

| Piece | Responsibility |
|--------|----------------|
| Run folder helper | Single place to format `{ts}_extraction_{target}_{slug}` |
| Checkbox + gate | Skip normal extract when mode on |
| `core/doi_pubid_by_ref.py` | Bucket + flag extraction; pure helpers + report writers |
| Tab | Wire scan, progress, history, open report |
| Tests | Naming, six firsts, comment direct-child, doi.org href/text in and out of ref |

## Error handling

- Parse failure: record file error; no buckets.
- No hits in any bucket: include file in HTML summary with zero hits; no CSV data rows (or one summary row — prefer **no data rows**, count in HTML only).
- Missing `impact_config.xml`: blank meta cells.

## Testing

- Folder name starts with timestamp, then `_extraction_`.
- Fixture with all six bucket types → six firsts; later duplicates ignored.
- Comment-wrapped URI (HTML span + XML `<comment>`) → `under_comment=True`.
- URI with `doi.org` in href only / text only / both → flags set correctly inside and outside `.ref`.
- Mode on → selector extract not invoked.

## Success criteria

- New runs sort by time when listing folders alphabetically.
- One checkbox produces the six-bucket report instead of selector extract.
- Operators can filter CSV on `under_comment` and `doi_org_in_*` without extra buckets.

## File touch list (implementation)

- `tabs/element_extractor_tab.py` — folder rename; checkbox; mode gate
- `core/doi_pubid_by_ref.py` (create) — extract + reports
- `tests/test_doi_pubid_by_ref.py` (create)
- `docs/element_extractor_docs.md` (+ root mirror if kept)

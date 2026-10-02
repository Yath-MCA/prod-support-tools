# Footnotes Group Report (BITS) — Design

Date: 2026-10-02  
Status: approved (v2 extensions)  
Suite: impact_config_suite  
Approach: 1 (enrich meta + dedicated report)  
Report version: 2

## Goal

For **BITS books only**, discover unique `fn-group` and `ref-list` structural patterns (CSS-like selectors with volatile `id` dropped), keyed by **client × DTD basename × kind × placement**, and persist `dtd_basename` into both `meta.json` and `documents.json`.

Also roll up **ID patterns by area category** (reuse ID Pattern Extractor normalizer) and expose Open File / Copy Path actions in the HTML report.

## Non-goals

- Do not change Analyses / book_analyzer xref HTML.
- Do not scan JATS articles in v1/v2.
- Do not hard-fail on client/DTD mismatch or multiple book-end fn-groups (soft warning only).
- Do not hard-code OHO|OXMEDO|LSE until those clients appear in the corpus.

## Locked decisions

| Decision | Choice |
|----------|--------|
| Outcome | Enrich meta **and** dedicated report |
| Uniqueness | Path + stable attrs (`book-part-type`, `content-type`, `class`); **always drop `id`** |
| Tool home | Sibling of DTD Report / Sectional |
| Scope | BITS books only |
| Persist | `dtd_basename` on meta.json **and** documents.json embedded `meta` |
| Placement | `chapter-end` \| `book-end` \| `front-matter` \| `other` for fn-group **and** ref-list |
| Soft map | `BITS-book-oasis2-1.dtd` → OSO\|OHO\|OXMEDO; `BITS.dtd` → LSE\|TNF |
| Exclude | `fn-group[content-type="table-fn"]` skipped entirely |
| Book-end | Under `.book-back` only (never `.book-body`); expect **one** fn-group per book |

## Architecture

1. Load project (`documents.json` + `meta.json`); filter BITS books first.
2. Parse DOCTYPE → `dtd_basename` (`NO_DTD` if missing).
3. Optionally write `dtd_basename` into meta.json and documents.json `meta`.
4. Parse XML → `fn-group` / `ref-list` (skip `table-fn`) → pattern + placement + id_pattern + area.
5. Soft-warn when a doc has **>1** book-end `fn-group`.
6. Roll up structural unique rows + parallel ID-pattern unique rows → HTML / CSV / TSV.

## Pattern rules

- CSS-like ancestor chain; keep `book-part-type`, `content-type`, `class`; omit `id`.
- Structural uniqueness: `(client, dtd_basename, kind, placement, pattern_xpath)`.
- ID uniqueness (parallel): `(client, dtd_basename, kind, area_category, id_pattern)`.

Examples:

- TNF chapter-end: `.book-body .book-part[book-part-type="chapter"] .back .fn-group[content-type="endnotes"]`
- Book-end: `.book-back … .fn-group[content-type="endnotes"]` (must include `.book-back`, not `.book-body`)

## Placement semantics

| Kind + placement | Path | Cardinality |
|------------------|------|-------------|
| `fn-group` + chapter-end | `.book-body` … `.back .fn-group` | Multiple OK |
| `fn-group` + book-end | `.book-back` only | **One** expected; else `multiple_book_end_fn_group` |
| `fn-group` + front-matter | `.front-matter` … | as found |
| `ref-list` | same ancestor rules | as found |

## Filters

- Skip `fn-group` with `content-type="table-fn"` (count in KPI `table-fn skipped`).

## ID pattern + area

- `id_pattern` via `IDPatternExtractor.normalize_id_to_pattern`.
- `area_category` via `_determine_area` with Books keys `front` / `body` / `back` (fallback `unknown`).

## Meta enrich

- Field: `dtd_basename` (`BITS.dtd`, `BITS-book-oasis2-1.dtd`, `NO_DTD`).
- Leave folder-level `dtd: "BITS"` unchanged.
- Soft DTD-family mismatch warning by client.

## Modules

- `core/fn_group_report.py` — enrich + scan + writers
- `tabs/fn_group_report_tab.py` — GUI (Open HTML / Folder / Unique CSV / Detail TSV / ID Patterns CSV)
- `tests/test_fn_group_report.py`
- Nav: Configuration → **Footnotes Group Report**

## Outputs

Under `Documents/impact-support-log/{ts}_fn_group_reports/`:

- `summary.html` — structural patterns + ID patterns + scanned docs (Open File / Copy Path)
- `unique_patterns.csv`
- `unique_id_patterns.csv`
- `detail.tsv`

## Testing

- Drop `id`; keep stable attrs.
- Exclude `table-fn`.
- Two chapter-end endnotes → one unique key; under `.book-body`.
- Book-end under `.book-back` only; multi book-end → soft warning.
- ID pattern + area (`fn-group-{nnn}`, `workid-{work}-…`, body/front).
- Enrich writes both JSON files.
- HTML contains Open File / Copy Path.

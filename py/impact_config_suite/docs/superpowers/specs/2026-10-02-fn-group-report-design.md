# Footnotes Group Report (BITS) — Design

Date: 2026-10-02  
Status: approved  
Suite: impact_config_suite  
Approach: 1 (enrich meta + dedicated report)

## Goal

For **BITS books only**, discover unique `fn-group` and `ref-list` structural patterns (CSS-like selectors with volatile `id` dropped), keyed by **client × DTD basename × kind × placement**, and persist `dtd_basename` into both `meta.json` and `documents.json`.

## Non-goals

- Do not change Analyses / book_analyzer xref HTML.
- Do not scan JATS articles in v1.
- Do not hard-fail on client/DTD mismatch (soft warning only).
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

## Architecture

1. Load project (`documents.json` + `meta.json`) via same collect pattern as Sectional/DTD Report.
2. Filter to BITS books (`dtd == "BITS"` and/or `type == "Books"` / folder under `BITS/`).
3. Parse DOCTYPE (reuse `core.dtd_report.parse_doctype_text` / `dtd_basename`); use `NO_DTD` when missing.
4. Optionally write `dtd_basename` into meta.json and documents.json `meta` (default on).
5. Parse XML → all `fn-group` and `ref-list` → normalize pattern + classify placement.
6. Roll up unique rows → HTML + CSV + detail TSV under `impact-support-log/{ts}_fn_group_reports/`.

## Pattern rules

- CSS-like ancestor chain from document root to target element.
- Keep discriminating attrs: `book-part-type`, `content-type`, `class` on ancestors and on the target.
- Always omit `id` (and other volatile attrs).
- Uniqueness key: `(client, dtd_basename, kind, placement, pattern_xpath)` where `kind ∈ {fn-group, ref-list}`.

Examples:

- TNF / `BITS.dtd`: `.book-body .book-part[book-part-type="chapter"] .back .fn-group[content-type="endnotes"]`
- OSO / oasis: same path with `[content-type="footnotes"]`; also front-matter nested groups

## Placement

| Placement | Signal |
|-----------|--------|
| `chapter-end` | Under `book-part` … `/back/{fn-group\|ref-list}` |
| `book-end` | Under `book-back` |
| `front-matter` | Under `front-matter` / `front-matter-part` |
| `other` | Else |

## Meta enrich

- Field: `dtd_basename` (e.g. `BITS.dtd`, `BITS-book-oasis2-1.dtd`, `NO_DTD`).
- Leave folder-level `dtd: "BITS"` unchanged.
- Soft warning column when client’s expected DTD family ≠ observed basename.

## Modules

- `core/fn_group_report.py` — enrich + scan + writers
- `tabs/fn_group_report_tab.py` — GUI
- `tests/test_fn_group_report.py`
- Nav: Configuration → **Footnotes Group Report** (beside DTD Report)

## Outputs

- Summary HTML (filters: client / DTD / kind / placement)
- Unique patterns CSV
- Detail TSV (one row per occurrence)
- Errors/skips for missing/unparseable XML

## Testing

- Normalize drops `id`, keeps `content-type` / `book-part-type`.
- Two chapter-end endnotes groups → one unique key.
- `book-back/ref-list` → `book-end`.
- Enrich writes both JSON files; oasis SYSTEM → `BITS-book-oasis2-1.dtd`.

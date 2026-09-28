# Sectional Report — Design

Date: 2026-09-28  
Status: draft for review  
Suite: impact_config_suite  
Approach: A (new tool)

## Goal

Add an **Extract → Sectional Report** tool that, for each XML file, counts FRONT / BODY / REF / OTHER section roots and, under each section, counts four DOI/URI-shaped queries. Produce a per-file summary TSV, a sectional HTML report, and a **client-unique** rollup keyed by tag + type attribute (not href).

## Non-goals

- Do not change DOI Extractor whole-file behavior.
- Do not key uniqueness on `href` / `xlink:href`.
- Do not read `<?Manuscript_Number?>`; identity comes from project `meta.json`.

## Placement

- Navigation: Configuration category, new tool **Sectional Report** (beside Element Extractor / Contrib Extract).
- Modules:
  - `core/sectional_report.py` — extract + writers
  - `tabs/sectional_report_tab.py` — GUI
  - `tests/test_sectional_report.py`
- Register in `tools_app.py` (`TOOL_REGISTRY` + `DEFAULT_NAVIGATION`).

## Input / identity

- Project root with JATS (or BITS) tree + `meta.json` (same load path pattern as Contrib Extract).
- Per row identity: **Docid** (meta key) + **File_id** when present; also client / shortcode for rollups.
- UI: project root, optional shortcode filter, Run, Open report folder.

## Section roots

| Section | Roots |
|--------|--------|
| FRONT | all `<front>` |
| BODY | all `<body>` |
| REF | `<ref-list>` under `<back>` |
| OTHER | direct children of `<back>` except `<ref-list>` (queries run under those nodes) |

Section count columns = number of those roots (OTHER = count of those back children).

## Queries (scoped under each section root)

Relative XPath (prefix with `.`):

| Subsection key | Query | Type key for unique |
|----------------|-------|---------------------|
| doi_id | `.//*[@pub-id-type='doi']` | tag + `pub-id-type=doi` |
| extlink_doi | `.//ext-link[@ext-link-type='doi']` | `ext-link` + `ext-link-type=doi` |
| extlink_uri | `.//ext-link[@ext-link-type='uri']` | `ext-link` + `ext-link-type=uri` |
| uri | `.//uri` | tag `uri` (no type attr) |

Hits may record text for display samples; **unique key never includes href**.

## Outputs

Session folder under `Documents/impact-support-log/{timestamp}_sectional_reports/` (same family as other extract reports).

1. **Per-file TSV** — one row per file:  
   `Docid | File_id | FRONT | BODY | REF | OTHER | doi_id | extlink_doi | extlink_uri | uri`  
   - FRONT…OTHER = section root counts  
   - four query columns = **sums across all four sections**

2. **HTML report** — KPI strip; main tabs **FRONT | BODY | REF | OTHER**; each tab has the same four subsections (counts + sample hits without depending on href).

3. **Client unique** — per client table, rows keyed by:  
   `(section, tag, type_attr, type_value)`  
   columns: count, sample docids (and optional shortcode list). Written as HTML (+ CSV/TSV sibling if cheap).

## Testing

- Synthetic XML: front/body/back with ref-list + app-group; assert section counts and scoped query counts.
- OTHER excludes ref-list hits from REF.
- Client unique merges same tag+type across docs; href differences do not split buckets.
- Missing meta file_id still emits Docid.

## Open points (fixed by this review)

- Manuscript_Number PI: **out** → meta Docid/File_id.
- Client unique: **tag + type attr + section**.
- TSV: summary totals; detail in HTML tabs.

## Approval

Awaiting user review of this spec before implementation / plan.

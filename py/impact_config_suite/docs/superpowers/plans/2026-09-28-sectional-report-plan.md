# Sectional Report — Implementation Plan

Date: 2026-09-28  
Suite: impact_config_suite  
Spec: docs/superpowers/specs/2026-09-28-sectional-report-design.md

## Approach

New Configuration tool **Sectional Report** (Approach A). Does not change DOI Extractor.

## Modules

1. `core/sectional_report.py` (REPORT_VERSION=1)
   - `extract_file(xml_path)` — lxml etree; section roots FRONT/BODY/REF/OTHER; relative queries
   - Unique key `(section, tag, type_attr, type_value)` — never href
   - `run_sectional_report(project_root, shortcodes?, report_dir?)` via `contrib_extractor.load_project` or folder `*.xml` scan
   - Writers: TSV, sectional HTML (tabs), client unique HTML+CSV
   - `REPORT_ROOT` override (same pattern as contrib)

2. `tabs/sectional_report_tab.py`
   - Project/folder entry, optional shortcode filter, folder-mode checkbox
   - Run / Cancel / Open report folder / Open last HTML
   - Progress + log

3. `tools_app.py`
   - Import + `TOOL_CLASS_BY_ID["sectional_report"]`
   - `DEFAULT_NAVIGATION` Configuration: `{id: sectional_report, label: Sectional Report}`

4. `tests/test_sectional_report.py`
   - Synthetic XML with front/body/back(ref-list + app-group)
   - REF vs OTHER scoping
   - TSV headers / row sums
   - Client unique merges without href

## Outputs

`Documents/impact-support-log/{timestamp}_sectional_reports/`

- Per-file TSV: Docid | File_id | FRONT | BODY | REF | OTHER | doi_id | extlink_doi | extlink_uri | uri
- HTML with FRONT|BODY|REF|OTHER tabs and four subsections each
- Client unique HTML + CSV

## Verification

```
python -m unittest tests.test_sectional_report -v
```

Smoke: `from tabs.sectional_report_tab import SectionalReportTab`

## Constraints

- Python-only local edits; no git commit unless asked
- Do not break DOI / Contrib extractors
- Identity from meta.json Docid + File_id only (no Manuscript_Number PI)

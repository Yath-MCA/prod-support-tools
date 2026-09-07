# Implementation Report: DOI Extractor

## Summary
Added a new "DOI Extractor" tool to `impact_config_suite`. `core/doi_extractor.py`
reuses `ElementExtractor.scan_directory`/`parse_and_extract` (the existing
element-extraction engine) with a fixed XPath covering all four known
DOI-bearing tag shapes (`article-id`, `pub-id`, `object-id` with
`pub-id-type="doi"`, and `ext-link` with `ext-link-type="doi"`), then layers
DOI normalization (URL-prefix stripping, `xlink:href` fallback), offline
syntax validation, and HTML+CSV reporting on top. `tabs/doi_extractor_tab.py`
mirrors `IDPatternExtractorTab`'s UI, registered as a 5th tool in the
existing "Extractor Tools" category.

## Assessment vs Reality

| Metric | Predicted (Plan) | Actual |
|---|---|---|
| Complexity | Medium (5 files) | Matched -- 3 created, 2 updated |
| Confidence | 9/10 | Confirmed, with one real discovery mid-implementation (see Deviations) |
| Files Changed | 5 | 5 |

## Tasks Completed

| # | Task | Status | Notes |
|---|---|---|---|
| 1 | `core/doi_extractor.py` -- normalization + validation | Done | |
| 2 | `core/doi_extractor.py` -- match extraction + `scan_directory` | Done | Deviated -- see below |
| 3 | `core/doi_extractor.py` -- HTML/CSV report + `run_extraction` | Done | |
| 4 | `tests/test_doi_extractor.py` | Done | 14 tests, all pass |
| 5 | `tabs/doi_extractor_tab.py` | Done | |
| 6 | Register in `tools_app.py` + `config/tools_navigation.json` | Done | |

## Validation Results

| Level | Status | Notes |
|---|---|---|
| Static Analysis | Pass | `python -c "import core.doi_extractor; import tabs.doi_extractor_tab; import tools_app"` succeeds |
| Unit Tests | Pass | `python -m unittest tests.test_doi_extractor -v` -> 14 passed |
| Build | Pass | N/A for Python; import + module load succeeded |
| Integration | Pass | End-to-end `run_extraction` against a temp file with all 4 DOI shapes: correct HTML/CSV output, correct summary counts |
| Manual GUI | Partial | `python main.py` launches without crashing with the new tab registered (`TOOL_CLASS_BY_ID['doi_extractor']` resolves); the actual click-through (Run button, report opening) was not walked through interactively in this environment -- same limitation noted in the prior metadata-harvester report |
| Edge Cases | Pass | Empty/whitespace input -> `None`; `doi:` and URL-prefix variants stripped correctly; object-id sub-DOI suffix (`.g010`) validates as `True`; garbage text -> invalid; duplicate `(tag, doi)` deduped; file with zero DOI matches correctly appears in "files without a DOI" |

## Files Changed

| File | Action |
|---|---|
| `core/doi_extractor.py` | CREATED |
| `tabs/doi_extractor_tab.py` | CREATED |
| `tests/test_doi_extractor.py` | CREATED |
| `tools_app.py` | UPDATED (+1 import, +1 `TOOL_CLASS_BY_ID` entry) |
| `config/tools_navigation.json` | UPDATED (+1 entry in "Extractor Tools") |

## Deviations from Plan

1. **`DOIExtractor.scan_directory` needed an extra file-discovery step not anticipated in the plan.** During Task 2/4 validation, a test asserting a file with zero DOI matches appears in the results with `"dois": []` failed with a `KeyError` -- `ElementExtractor.scan_directory` (element_extractor.py:584-589) only adds an entry to its returned `scan_results` dict for files that either matched or errored; files that parsed cleanly with zero matches are silently omitted entirely. Since "files without a DOI" is a core feature of this tool's report (explicitly in scope per the plan), I added a small `_discover_all_files` helper that mirrors `ElementExtractor.scan_directory`'s own file-discovery/extension-filter logic (and reuses its `_matches_filename_filter` static method directly rather than re-implementing that regex logic) purely to backfill the omitted zero-match files as `{"ok": True, "dois": []}`. This does not modify `ElementExtractor` itself and does not duplicate the actual parsing/matching logic -- only the lightweight "which files exist in this folder" glob, which was unavoidable given the constraint discovered.
2. **No git branch/commit**, consistent with the prior metadata-harvester session -- the repository is still on `main` with the same pre-existing unrelated dirty-tree changes, left untouched.

## Issues Encountered
The file-discovery gap above (Deviation 1) was the only issue, caught immediately by the plan's own Task 4 validation step and fixed before moving on -- no broken state was carried forward.

## Tests Written

| Test File | Tests | Coverage |
|---|---|---|
| `tests/test_doi_extractor.py` | 14 | `normalize_doi` (bare text, ext-link href fallback, href-matches-text, `doi:` prefix, URL prefix stripping, empty/whitespace input), `is_valid_doi` (valid, object-id sub-DOI suffix, invalid, empty), `extract_dois_from_matches` (dedup by `(tag, doi)`, different tags not deduped), end-to-end `scan_directory` (all 4 shapes found, zero-match file correctly reported empty), end-to-end `run_extraction` (HTML+CSV files created, correct summary counts, correct CSV row count) |

## Next Steps
- [ ] Manually walk the plan's Manual Validation checklist in a real desktop session: launch `python main.py`, open "Extractor Tools" > "DOI Extractor", point it at a folder of real IMPACT documents containing the 4 example DOI shapes, confirm the report and "Files without a DOI" section render as expected
- [ ] Code review via `/code-review`
- [ ] If a 5th DOI-bearing tag shape is found in real documents later, extend `DOIExtractor.DOI_XPATH` (a single named constant) rather than redesigning

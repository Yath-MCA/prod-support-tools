# Implementation Report: Metadata Harvester Tab (Crossref + ROR/OpenAlex)

## Summary
Ported the two standalone FastAPI+SQLite harvester services from
`fetchCrossRef` into `impact_config_suite` as a new `Metadata Harvester`
GUI tab, mirroring `SearchTab`'s embedded-uvicorn-in-a-thread pattern. The
tab runs one combined FastAPI app (Swagger at `/docs`) exposing both a
paid-token Crossref DOI/affiliation harvester (`/crossref/*`) and a
free-tier ROR+OpenAlex alphabetical geo harvester (`/geo/*`), started and
stopped from the GUI, with harvest-trigger controls, a live log pane, and
Run History integration (Crossref token deliberately excluded from history
and logs).

## Assessment vs Reality

| Metric | Predicted (Plan) | Actual |
|---|---|---|
| Complexity | Large (17 files created, 3 updated) | Matched exactly |
| Confidence | 8/10 | Confirmed -- backend ported with zero logic changes beyond table renames; only friction was environment/tooling, not design |
| Files Changed | 17 created, 3 updated | 18 created (added `httpx2` note to requirements, no extra file), 3 updated |

## Tasks Completed

| # | Task | Status | Notes |
|---|---|---|---|
| 1 | `metadata_harvester/service/config.py` | Done | |
| 2 | Geo DB layer | Done | Tables renamed `geo_location_registry`/`geo_harvest_progress` |
| 3 | Geo sources (base/ror/openalex) | Done | Ported unchanged, import path only |
| 4 | Geo scheduler | Done | Ported unchanged |
| 5 | Geo routes | Done | |
| 6 | Crossref DB + harvester | Done | Table renamed `crossref_location_registry`; `init_db()` moved out of import-time per plan's GOTCHA |
| 7 | Crossref routes | Done | |
| 8 | Tests (geo + crossref) | Done | 23 tests total (13 geo + 10 crossref/db), all pass, zero live network calls |
| 9 | Combined FastAPI app | Done | |
| 10 | Tab service lifecycle | Done | |
| 11 | Tab harvest-trigger sections | Done | |
| 12 | Tab registration (`tools_app.py` + nav config) | Done | |
| 13 | Dependencies | Done | Deviated -- see below (extra `httpx2` requirement discovered) |

## Validation Results

| Level | Status | Notes |
|---|---|---|
| Static Analysis | Pass | `python -c "from metadata_harvester.service.app import app"` and `python -c "import tools_app"` both succeed cleanly |
| Unit Tests | Pass | `pytest tests/test_metadata_harvester_geo.py tests/test_metadata_harvester_crossref.py -v` -> 23 passed |
| Build | Pass | N/A for Python; import + module load succeeded |
| Integration | Pass | `TestClient` smoke test: `/health` 200, `/geo/stats` 200 `[]`, `/crossref/locations` 200 `[]`, `POST /geo/harvest/start-all` with no email -> 400 as designed |
| Edge Cases | Pass | Missing email -> 400 (geo) / 422 (crossref, invalid email format); org with no `locations` -> skipped; OpenAlex prefix mismatch -> filtered; duplicate `(source, source_id)` -> no-op; duplicate raw affiliation -> no-op |
| Manual GUI | Partial | `python main.py` launches without crashing (verified process stays alive 5s+, then closed cleanly) and `tools_app.CommonToolsApp.TOOL_CLASS_BY_ID["metadata_harvester"]` resolves correctly. Full interactive checklist (clicking Start Service, triggering a live harvest, verifying Run History JSON) was **not walked through manually** in this session -- there is no way to interact with a native Tkinter window from this environment. Recommend the user do a quick manual pass per the plan's Manual Validation checklist. |

## Files Changed

| File | Action |
|---|---|
| `metadata_harvester/__init__.py` | CREATED |
| `metadata_harvester/gui.py` | CREATED |
| `metadata_harvester/service/__init__.py` | CREATED |
| `metadata_harvester/service/app.py` | CREATED |
| `metadata_harvester/service/config.py` | CREATED |
| `metadata_harvester/service/crossref/__init__.py` | CREATED |
| `metadata_harvester/service/crossref/db.py` | CREATED |
| `metadata_harvester/service/crossref/harvester.py` | CREATED |
| `metadata_harvester/service/crossref/routes.py` | CREATED |
| `metadata_harvester/service/geo/__init__.py` | CREATED |
| `metadata_harvester/service/geo/db.py` | CREATED |
| `metadata_harvester/service/geo/scheduler.py` | CREATED |
| `metadata_harvester/service/geo/sources/__init__.py` | CREATED |
| `metadata_harvester/service/geo/sources/base.py` | CREATED |
| `metadata_harvester/service/geo/sources/ror.py` | CREATED |
| `metadata_harvester/service/geo/sources/openalex.py` | CREATED |
| `metadata_harvester/service/geo/routes.py` | CREATED |
| `tests/test_metadata_harvester_geo.py` | CREATED |
| `tests/test_metadata_harvester_crossref.py` | CREATED |
| `tools_app.py` | UPDATED (+1 import, +1 `TOOL_CLASS_BY_ID` entry, +1 `DEFAULT_NAVIGATION` category, +4 `shutdown(wait=True)` call sites) |
| `config/tools_navigation.json` | UPDATED (+1 `"Metadata"` category) |
| `requirements.txt` | UPDATED (+`pydantic-settings`, `email-validator`, `loguru`, `pytest`, `responses`, `httpx2`) |

## Deviations from Plan

1. **`httpx2` added as a dependency**, not anticipated in the plan. This
   suite's installed `starlette` version requires `httpx2` (not the more
   common `httpx`) for `starlette.testclient.TestClient` to work at all --
   discovered only when the crossref `TestClient`-based tests were run.
   Without it, `from fastapi.testclient import TestClient` raises
   `RuntimeError` at import time.
2. **No branch/commit created.** The repository was on `main` with a dirty
   working tree containing unrelated in-progress changes (modified
   `core/element_extractor.py`, `core/citation_pattern_extractor.py`, a
   deleted `data_transfer/README.md`, some test files, and untracked
   `patterns/refs.py`). Per explicit user confirmation, this implementation
   was done in place on the existing working tree with no git operations at
   all -- those pre-existing changes were left untouched.
3. **Full pre-existing `tests/` suite could not be run to completion** in
   this session -- it exceeded the available command time budget twice
   (>180s each), showing all-passing dots (no `F`/`E` markers) up through
   roughly 100 tests before being cut off, with no indication of a failure
   caused by this change. This appears to be a slow test suite (matplotlib/
   lxml/xmldiff-heavy), not a hang introduced by the harvester tab. A full
   run should be completed by whoever has more time budget or CI access.
   Separately, running the full repository (not just `tests/`) fails
   *collection* entirely due to a **pre-existing, unrelated** issue: a
   duplicate test module basename (`test_copy_api.py`) between
   `_archive/temp/recovered_py_source/search_service/` and
   `search_service/`, which predates this change.

## Issues Encountered
- The `httpx2` dependency gap (see Deviation 1) -- resolved by installing
  it and adding it to `requirements.txt`.
- No other issues; the ported backend logic required zero debugging beyond
  the table renames and import-path updates already scoped in the plan.

## Tests Written

| Test File | Tests | Coverage |
|---|---|---|
| `tests/test_metadata_harvester_geo.py` | 13 | DB dedup/progress/counts, scheduler heap balancing and skip-logic, ROR/OpenAlex parsing and error handling (all HTTP mocked via `responses`) |
| `tests/test_metadata_harvester_crossref.py` | 10 | `naive_geo_parser` edge cases (0/1/2/3/5+ comma parts, empty, `None`), DB dedup and country filter, `TestClient`-based endpoint smoke tests (no live network) |

## Next Steps
- [ ] Manually walk the plan's Manual Validation checklist in a real desktop session: launch `python main.py`, open the "Metadata Harvester" tab, start the service, trigger a real geo harvest, confirm Run History never contains the Crossref token
- [ ] Code review via `/code-review`
- [ ] Consider fixing the pre-existing duplicate-basename test-collection issue (`test_copy_api.py`) separately -- unrelated to this feature but blocks whole-repo `pytest` runs
- [ ] Optionally add `metadata_harvester/README.md` mirroring `search_service/README.md` (explicitly optional per the plan's Completion Checklist)

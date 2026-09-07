# Plan: Metadata Harvester Tab (Crossref + ROR/OpenAlex)

## Summary
Port the two standalone FastAPI+SQLite harvester services built in
`fetchCrossRef` (a paid-Crossref-token DOI/affiliation harvester, and a
free-tier ROR+OpenAlex alphabetical geo harvester) into `impact_config_suite`
as a single new GUI tab, `Metadata Harvester`, following the exact pattern
`SearchTab` already uses to embed a FastAPI service inside this Tkinter app.

## User Story
As an IMPACT support engineer already living inside `impact_config_suite`,
I want to run both metadata harvesters from the same desktop tool I use for
everything else, so that I don't need a separate terminal, a separate
`uvicorn` process, and a separate mental model just for these two scripts.

## Problem → Solution
Today: two independent FastAPI apps (`fetchCrossRef/app.py` and
`fetchCrossRef/agent/app/main.py`), each launched manually via
`uvicorn ... --reload` in its own terminal, with no discoverability inside
the team's actual daily tool.
→
One `Metadata Harvester` tab inside `impact_config_suite`, embedding both
backends behind one FastAPI app (still with Swagger at `/docs`), started
and stopped the same way `SearchTab` starts/stops its own embedded service,
with harvest-trigger controls and run history built in.

## Metadata
- **Complexity**: Large (10+ files, new package, cross-cutting registration in 2 existing files)
- **Source PRD**: N/A
- **PRD Phase**: N/A
- **Estimated Files**: 17 created, 3 updated

---

## UX Design

### Before
```
┌─────────────────────────────────────────────┐
│ Terminal 1: cd fetchCrossRef; uvicorn app:app │
│ Terminal 2: cd fetchCrossRef/agent;            │
│             uvicorn app.main:app               │
│ Browser: http://127.0.0.1:8000/docs (x2, diff  │
│          ports, manually remembered)           │
└─────────────────────────────────────────────┘
```

### After
```
┌───────────────────────────────────────────────────┐
│ impact_config_suite (already running)              │
│  → Tools ▸ Metadata ▸ Metadata Harvester tab       │
│      [Service Port: 7100] [START SERVICE] [STOP]   │
│      ● Service Running   [OPEN SWAGGER IN BROWSER] │
│      ── Crossref (paid) ─────────────────────────  │
│      Token: ******  Email: [...] [Start Harvest]   │
│      ── ROR + OpenAlex (free) ───────────────────  │
│      Email: [...] Workers: [6] [Start Harvest]     │
│      ── Log ──────────────────────────────────────│
│      [scrolling status/progress text]              │
└───────────────────────────────────────────────────┘
```

### Interaction Changes
| Touchpoint | Before | After | Notes |
|---|---|---|---|
| Starting a harvest | Open terminal, activate venv, run `uvicorn` | Click a tab, click Start Service | Matches `SearchTab` exactly |
| Triggering Crossref harvest | `curl -X POST .../harvest/start -d '{...}'` | Fill token+email fields, click button | Token field masked (`show="*"`) |
| Triggering geo harvest | `curl -X POST .../harvest/start-all -d '{...}'` | Fill email+workers, click button | |
| Checking progress | `curl .../stats` | Log pane auto-polls and prints stats | |
| API docs | Remembered port + `/docs` | "Open Swagger in Browser" button | |
| Run history | None | Recorded in the suite's existing Run History (start/stop/trigger events, never the token) | |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 | `tabs/search_tab.py` | 1-373 (whole file) | **The** pattern to mirror -- embeds a FastAPI app in a background thread with `uvicorn.Server`, health-check polling, thread-safe UI updates via a queue, `shutdown(wait=True)`, and Run History integration. Copy this file's shape almost verbatim. |
| P0 | `tools_app.py` | 12-50 | `TOOL_CLASS_BY_ID` registry -- new tab MUST be added here or it's invisible to the config loader (see GOTCHA below) |
| P0 | `tools_app.py` | 51-88 | `DEFAULT_NAVIGATION` -- fallback nav structure, must add the new category/tool here too |
| P0 | `tools_app.py` | 154-174 | `_normalize_navigation_config` -- silently drops any `tools_navigation.json` tool id not in `TOOL_CLASS_BY_ID` (no error, just vanishes) |
| P0 | `tools_app.py` | 620-621, 721-733, 753-793 | Every place `self.search_tab` is tracked and `.shutdown(wait=True)` is called on close/restart/reload -- the new tab needs the identical treatment |
| P1 | `core/run_history.py` | 1-102 (whole file) | `RunHistoryStore.add_entry/load_entries/search_entries` -- how every tab records history |
| P1 | `config/tools_navigation.json` | 1-57 (whole file) | Live nav config (overrides `DEFAULT_NAVIGATION`); categories are plain `{name, tools:[{id,label}]}` |
| P1 | `cjk_checker/gui.py` | 1-24 | Precedent for a **package with its own `gui.py`** exposing the `ttk.Frame` tab class, imported via relative import (`from .pipeline import ...`) -- mirrors the `metadata_harvester/` package this plan creates |
| P2 | `requirements.txt` | 1-29 (whole file) | Already has `fastapi`, `uvicorn`, `pydantic`, `requests` (for the existing `search_service`) -- only 3 packages need adding |
| P2 | `search_service/app/app.py` | all | Existing embedded-FastAPI-app example for path/structure reference |
| P2 (source to port) | `../../../_IMPACT/OTHER_LIVE_PROJECTS/fetchCrossRef/app.py` | 1-208 | Crossref paid-token harvester -- the exact logic being ported into `metadata_harvester/service/crossref/` |
| P2 (source to port) | `../../../_IMPACT/OTHER_LIVE_PROJECTS/fetchCrossRef/agent/app/*.py` | all | Geo (ROR+OpenAlex) harvester package -- already split into `config.py`/`db.py`/`scheduler.py`/`sources/` in a prior session; port near-verbatim into `metadata_harvester/service/geo/` |

## External Documentation
No external research needed -- feature uses established internal patterns
(`SearchTab`'s embedded-uvicorn approach) plus already-validated external
API knowledge from the prior `fetchCrossRef` implementation session (ROR,
OpenAlex, Crossref REST APIs all already integrated and smoke-tested there).

---

## Patterns to Mirror

### EMBEDDED_UVICORN_LIFECYCLE
```python
// SOURCE: tabs/search_tab.py:174-242
config = uvicorn.Config(
    search_app,
    host="127.0.0.1",
    port=port,
    log_level="warning",
    access_log=False,
)
self.server = uvicorn.Server(config)
self.server_thread = threading.Thread(
    target=self._run_server, name="impact-search-service", daemon=True
)
self.server_thread.start()
...
def _stop_service(self):
    ...
    if self.server:
        self.server.should_exit = True
    threading.Thread(target=self._wait_for_stop, daemon=True).start()
```

### THREAD_SAFE_UI_QUEUE
```python
// SOURCE: tabs/search_tab.py:25-29, 304-322
self._ui_queue = queue.SimpleQueue()
self.after(50, self._drain_ui_queue)

def _schedule(self, callback, *args):
    self._ui_queue.put((callback, args))

def _drain_ui_queue(self):
    try:
        while True:
            callback, args = self._ui_queue.get_nowait()
            callback(*args)
    except queue.Empty:
        pass
    if self._ui_polling:
        self.after(50, self._drain_ui_queue)
```
Any background thread (server thread, health-check thread, harvest-poll
thread) MUST go through `self._schedule(...)`, never touch a Tkinter widget
directly -- this is how `SearchTab` stays thread-safe.

### TAB_REGISTRATION
```python
// SOURCE: tools_app.py:33-50
TOOL_CLASS_BY_ID = {
    "analyses": AnalysesTab,
    ...
    "search": SearchTab,
    ...
}
```
New entry: `"metadata_harvester": MetadataHarvesterTab`.

### NAV_CONFIG_ENTRY
```json
// SOURCE: config/tools_navigation.json:19-25
{
  "name": "Auto Download",
  "tools": [
    { "id": "data_transfer", "label": "Data Transfer" },
    { "id": "document_manager", "label": "Document Manager" }
  ]
}
```
New category to add: `{"name": "Metadata", "tools": [{"id": "metadata_harvester", "label": "Metadata Harvester"}]}`.

### SHUTDOWN_WIRING
```python
// SOURCE: tools_app.py:620-621, 726-727, 766-767, 791-792
previous_search_tab = getattr(self, "search_tab", None)
self.search_tab = self.tool_views.get(("Analysis", "search"), previous_search_tab)
...
old_search_tab = getattr(self, "search_tab", None)
if old_search_tab is not None:
    old_search_tab.shutdown(wait=True)
...
if self.search_tab is not None:
    self.search_tab.shutdown(wait=True)
```
Add the identical 4 call sites for `self.metadata_harvester_tab`.

### RUN_HISTORY_PATTERN
```python
// SOURCE: tabs/search_tab.py:334-372
def _history_entry(self, action: str) -> dict:
    return {
        "tool_id": self.history_tool_id,
        "tool_label": self.history_tool_label,
        "action": action,
        "summary": f"{action} | port {port}",
        "source_path": "", "output_dir": "", "report_path": service_url,
        "params": {"port": port, "service_url": service_url},
    }

def _record_history(self, action: str) -> None:
    RunHistoryStore.add_entry(self._history_entry(action))
```
**GOTCHA**: `params` must never include the Crossref token -- only
non-secret fields (email, workers, limits, port).

### PACKAGE_WITH_OWN_GUI
```python
// SOURCE: cjk_checker/gui.py:1-15
from __future__ import annotations
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from .pipeline import run_cjk_compare, run_cjk_compare_from_files

class CJKIntegrityTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent)
        ...
```
`metadata_harvester/gui.py` follows this exact shape, importing its FastAPI
app via `from .service.app import app as metadata_harvester_app`.

### FASTAPI_ROUTE_PORTING (from fetchCrossRef, already validated)
```python
// SOURCE: fetchCrossRef/agent/app/main.py:47-58
@app.post("/harvest/start-all", status_code=202)
def start_harvest_all(payload: HarvestAllRequest, background_tasks: BackgroundTasks):
    email = payload.contact_email or settings.contact_email
    if not email:
        raise HTTPException(status_code=400, detail="contact_email is required ...")
    num_workers = payload.num_workers or settings.num_workers
    background_tasks.add_task(run_harvest, DEFAULT_SOURCES, email, num_workers)
    return {"status": "queued", ...}
```
Port near-verbatim; only the route **prefix** changes (mounted under
`/geo` via an `APIRouter`) since it now shares an app with the Crossref
routes.

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `metadata_harvester/__init__.py` | CREATE | Package marker |
| `metadata_harvester/gui.py` | CREATE | `MetadataHarvesterTab`, mirrors `SearchTab` |
| `metadata_harvester/service/__init__.py` | CREATE | Package marker |
| `metadata_harvester/service/app.py` | CREATE | Combined FastAPI app; mounts crossref + geo routers, `/health`, `/docs` |
| `metadata_harvester/service/config.py` | CREATE | Unified `Settings` (env prefix `METADATA_HARVESTER_`), one shared `db_path` |
| `metadata_harvester/service/crossref/__init__.py` | CREATE | Package marker |
| `metadata_harvester/service/crossref/db.py` | CREATE | Ported from `fetchCrossRef/app.py` `init_db`/insert logic; table renamed `crossref_location_registry` |
| `metadata_harvester/service/crossref/harvester.py` | CREATE | Ported `harvest_crossref_task` + `naive_geo_parser` |
| `metadata_harvester/service/crossref/routes.py` | CREATE | `POST /crossref/harvest/start`, `GET /crossref/locations` (APIRouter, prefix `/crossref`) |
| `metadata_harvester/service/geo/__init__.py` | CREATE | Package marker |
| `metadata_harvester/service/geo/db.py` | CREATE | Ported from `fetchCrossRef/agent/app/db.py`; tables renamed `geo_location_registry`/`geo_harvest_progress` |
| `metadata_harvester/service/geo/scheduler.py` | CREATE | Ported from `fetchCrossRef/agent/app/scheduler.py`, unchanged |
| `metadata_harvester/service/geo/sources/__init__.py` | CREATE | Ported from `fetchCrossRef/agent/app/sources/__init__.py` |
| `metadata_harvester/service/geo/sources/base.py` | CREATE | Ported unchanged |
| `metadata_harvester/service/geo/sources/ror.py` | CREATE | Ported unchanged |
| `metadata_harvester/service/geo/sources/openalex.py` | CREATE | Ported unchanged |
| `metadata_harvester/service/geo/routes.py` | CREATE | `POST /geo/harvest/start-all`, `GET /geo/progress`, `GET /geo/stats`, `GET /geo/locations` (APIRouter, prefix `/geo`) |
| `tools_app.py` | UPDATE | Import + register `MetadataHarvesterTab`; add 4 `shutdown(wait=True)` call sites |
| `config/tools_navigation.json` | UPDATE | Add `"Metadata"` category with `metadata_harvester` tool |
| `requirements.txt` | UPDATE | Add `pydantic-settings`, `email-validator`, `loguru` |
| `tests/test_metadata_harvester_geo.py` | CREATE | Ported from `fetchCrossRef/agent/tests/test_db.py` + `test_scheduler.py` + `test_sources.py` (13 tests), import paths updated |
| `tests/test_metadata_harvester_crossref.py` | CREATE | New: `naive_geo_parser` unit tests, `FastAPI TestClient` smoke test for `/crossref/locations` |

## NOT Building
- No unification of the two SQLite schemas into one shared table -- Crossref
  dedups on raw affiliation string, geo dedups on `(source, source_id)`;
  forcing a shared shape would be a lossy, unrequested redesign. Two tables,
  one `.db` file.
- No live results grid/table widget in the tab -- the log pane shows
  progress text; browsing actual harvested rows stays in Swagger (`/docs`)
  or a future `/export` endpoint, not built here.
- No change to how `SearchTab` or any other existing tab works, beyond the
  4 mechanical `shutdown()` call-site additions needed for the new tab.
- No retry/backoff tuning, no auth on the embedded API, no Postgres -- same
  non-goals the original `fetchCrossRef` plan already established.
- No deletion of the original `fetchCrossRef` project -- it stays as the
  reference/standalone version; this plan is an additive port, not a move
  that deletes the source.

---

## Step-by-Step Tasks

### Task 1: Scaffold `metadata_harvester/service/config.py`
- **ACTION**: Create unified settings.
- **IMPLEMENT**: `Settings(BaseSettings)` with `db_path: str = "metadata_harvester.db"`, `contact_email: Optional[EmailStr] = None`, `num_workers: int = 6`, `request_timeout_seconds: float = 30.0`, `ror_max_pages: int = 5`, `ror_page_delay_seconds: float = 0.15`, `log_dir/log_level`. `env_prefix="METADATA_HARVESTER_"`.
- **MIRROR**: `fetchCrossRef/agent/app/config.py` (already validated working code)
- **IMPORTS**: `pydantic.EmailStr`, `pydantic_settings.BaseSettings, SettingsConfigDict`
- **GOTCHA**: `EmailStr` needs `email-validator` installed or Pydantic raises `ImportError` at import time, not at request time -- add to `requirements.txt` in Task 12.
- **VALIDATE**: `python -c "from metadata_harvester.service.config import settings; print(settings)"`

### Task 2: Port geo DB layer
- **ACTION**: Create `metadata_harvester/service/geo/db.py`
- **IMPLEMENT**: Copy `fetchCrossRef/agent/app/db.py` verbatim, rename table `location_registry` -> `geo_location_registry` and `harvest_progress` -> `geo_harvest_progress` in the `CREATE TABLE` and all SQL referencing them; import settings from `metadata_harvester.service.config`.
- **MIRROR**: `fetchCrossRef/agent/app/db.py` (all functions: `get_conn`, `init_db`, `get_alpha_counts`, `is_letter_completed`, `mark_progress`, `record_exists`, `insert_record`)
- **IMPORTS**: `from metadata_harvester.service.config import settings`, `from metadata_harvester.service.geo.sources.base import LocationRecord`
- **GOTCHA**: Keep the module-level `ALPHABET`/`db_lock` -- the scheduler imports `db.ALPHABET`.
- **VALIDATE**: none yet (covered by Task 8 tests)

### Task 3: Port geo sources
- **ACTION**: Create `metadata_harvester/service/geo/sources/{__init__,base,ror,openalex}.py`
- **IMPLEMENT**: Copy `fetchCrossRef/agent/app/sources/*.py` verbatim, only updating the `from app.config import settings` import to `from metadata_harvester.service.config import settings`.
- **MIRROR**: `fetchCrossRef/agent/app/sources/base.py`, `ror.py`, `openalex.py` -- no logic changes, these are already tested and smoke-tested against live APIs.
- **IMPORTS**: `requests`, `loguru.logger`
- **GOTCHA**: none new -- same as original port.
- **VALIDATE**: none yet (covered by Task 8 tests)

### Task 4: Port geo scheduler
- **ACTION**: Create `metadata_harvester/service/geo/scheduler.py`
- **IMPLEMENT**: Copy `fetchCrossRef/agent/app/scheduler.py` verbatim, update `from app import db` -> `from metadata_harvester.service.geo import db`, `from app.sources.base import Source` -> `from metadata_harvester.service.geo.sources.base import Source`.
- **MIRROR**: `fetchCrossRef/agent/app/scheduler.py`
- **IMPORTS**: `heapq`, `threading`, `loguru.logger`
- **GOTCHA**: none.
- **VALIDATE**: none yet (covered by Task 8 tests)

### Task 5: Geo routes
- **ACTION**: Create `metadata_harvester/service/geo/routes.py`
- **IMPLEMENT**: `APIRouter()` with the 4 routes from `fetchCrossRef/agent/app/main.py` (`/harvest/start-all`, `/progress`, `/stats`, `/locations`), unchanged logic, just moved out of `main.py`/`app.py` into a router that the combined app mounts under prefix `/geo`. Keep `DEFAULT_SOURCES` registry here, imported by the route handler.
- **MIRROR**: `fetchCrossRef/agent/app/main.py:44-116` (routes only, not the `FastAPI()` app instance itself)
- **IMPORTS**: `fastapi.APIRouter, BackgroundTasks, HTTPException, Query`, `metadata_harvester.service.geo.db`, `.scheduler.run_harvest`, `.sources.DEFAULT_SOURCES`, `metadata_harvester.service.config.settings`
- **GOTCHA**: Route paths inside the router should be relative (`"/harvest/start-all"` not `"/geo/harvest/start-all"`) -- the `/geo` prefix is applied once at `app.include_router(geo_router, prefix="/geo")` in Task 9.
- **VALIDATE**: covered by Task 9's TestClient smoke check

### Task 6: Port crossref DB + harvester
- **ACTION**: Create `metadata_harvester/service/crossref/db.py` and `harvester.py`
- **IMPLEMENT**: `db.py` -- port `init_db`/insert logic from `fetchCrossRef/app.py:48-66,157-165`, table renamed `crossref_location_registry`, using `sqlite3.connect(settings.db_path)` (same shared DB file as geo, different table -- no `init_db()`-at-import-time; call it explicitly from `app.py` startup, see Task 9 GOTCHA). `harvester.py` -- port `naive_geo_parser` and `harvest_crossref_task` from `fetchCrossRef/app.py:80-174`, updated to call the renamed table via the new `db.py`.
- **MIRROR**: `fetchCrossRef/app.py` (full file -- this is the validated, live-tested reference)
- **IMPORTS**: `sqlite3`, `requests`, `loguru.logger`, `metadata_harvester.service.config.settings`
- **GOTCHA**: The original `fetchCrossRef/app.py` called `init_db()` at **module import time** (line 66) -- do NOT copy that here; the combined `app.py` (Task 9) must call both `crossref.db.init_db()` and `geo.db.init_db()` explicitly once, in a controlled place, so import order doesn't matter and tests can each use their own temp DB via monkeypatched `settings.db_path`.
- **VALIDATE**: covered by Task 8 tests

### Task 7: Crossref routes
- **ACTION**: Create `metadata_harvester/service/crossref/routes.py`
- **IMPLEMENT**: `APIRouter()` with `POST /harvest/start` (payload: `crossref_token`, `user_agent_email: EmailStr`, `rows_per_request`, `max_total_records`) and `GET /locations` (optional `country` filter), ported from `fetchCrossRef/app.py:179-207`.
- **MIRROR**: `fetchCrossRef/app.py:71-76` (Pydantic schema), `:179-207` (routes)
- **IMPORTS**: `fastapi.APIRouter, BackgroundTasks, Query`, `pydantic.BaseModel, EmailStr`, `.db`, `.harvester.harvest_crossref_task`
- **GOTCHA**: Same relative-path note as Task 5 -- no `/crossref` prefix inside this file.
- **VALIDATE**: covered by Task 9

### Task 8: Port geo tests
- **ACTION**: Create `tests/test_metadata_harvester_geo.py`
- **IMPLEMENT**: Combine the 13 tests from `fetchCrossRef/agent/tests/test_db.py`, `test_scheduler.py`, `test_sources.py` into one file (or three, matching the suite's flat `tests/` convention -- see `tests/test_xml_compare.py` etc., all flat, no subpackages), updating imports from `app.*` to `metadata_harvester.service.geo.*`, and `from app.config import settings` -> `from metadata_harvester.service.config import settings`.
- **MIRROR**: `fetchCrossRef/agent/tests/test_db.py`, `test_scheduler.py`, `test_sources.py` (all 13 tests already pass against this exact logic)
- **IMPORTS**: `pytest`, `responses`
- **GOTCHA**: `responses` is not currently in `requirements.txt` -- add in Task 12. Check whether it's already installed in this suite's `.venv` before assuming; if genuinely absent, it must ship as a dev-only addition (this codebase's `requirements.txt` doesn't currently separate dev/prod, so add it there -- consistent with how `pytest` itself is used without a visible entry, implying tooling deps are managed ad hoc in this repo; note as a risk, not a blocker).
- **VALIDATE**: `pytest tests/test_metadata_harvester_geo.py -v` -> 13 passed

### Task 9: Combined FastAPI app
- **ACTION**: Create `metadata_harvester/service/app.py`
- **IMPLEMENT**:
  ```python
  from fastapi import FastAPI
  from metadata_harvester.service.crossref import db as crossref_db
  from metadata_harvester.service.crossref.routes import router as crossref_router
  from metadata_harvester.service.geo import db as geo_db
  from metadata_harvester.service.geo.routes import router as geo_router

  app = FastAPI(title="Metadata Harvester", version="1.0.0")
  crossref_db.init_db()
  geo_db.init_db()
  app.include_router(crossref_router, prefix="/crossref", tags=["crossref"])
  app.include_router(geo_router, prefix="/geo", tags=["geo"])

  @app.get("/health")
  def health():
      return {"status": "ok"}
  ```
- **MIRROR**: `search_service/app/app.py` (how the existing embedded service structures its top-level `app` object)
- **IMPORTS**: as shown
- **GOTCHA**: Both `init_db()` calls run at **app construction time** (not deferred), so the first `uvicorn.Config(app, ...)` in the tab's start handler already has both tables ready before any request lands -- matches how `search_app` is already a ready-made module-level object in `search_service/app/app.py`.
- **VALIDATE**: `from fastapi.testclient import TestClient; from metadata_harvester.service.app import app; c = TestClient(app); assert c.get("/health").status_code == 200`

### Task 10: `metadata_harvester/gui.py` -- service lifecycle half
- **ACTION**: Create `MetadataHarvesterTab.__init__`, `_build_ui` (service controls only), `_start_service`, `_stop_service`, `_run_server`, `_check_health`, `_wait_for_stop`, `_handle_server_ready/_failure/_exit`, `_schedule`, `_drain_ui_queue`, `shutdown`.
- **IMPLEMENT**: Copy `SearchTab`'s equivalent methods near-verbatim, swapping `search_app` for `from metadata_harvester.service.app import app as metadata_harvester_app`, default port `7100` (not `7000`, to avoid colliding with `SearchTab` if both are started at once), health endpoint `/health` (already exists on the combined app), and "OPEN SWAGGER IN BROWSER" opening `f"http://127.0.0.1:{port}/docs"` instead of `/ui`.
- **MIRROR**: `tabs/search_tab.py:1-333` (everything except the two harvest-specific sections and `_history_entry`)
- **IMPORTS**: `queue, socket, threading, time, tkinter as tk, webbrowser, requests, uvicorn`, `from core.run_history import RunHistoryStore`, `from .service.app import app as metadata_harvester_app`
- **GOTCHA**: `metadata_harvester/gui.py` uses a **relative** import (`from .service.app import ...`) since it's a package, unlike `search_tab.py` which is a flat module inside `tabs/` importing the top-level `search_service` package -- this mirrors `cjk_checker/gui.py`'s relative-import style instead.
- **VALIDATE**: manual -- launch the suite, open the tab, click Start/Stop, confirm status circle and Swagger link work

### Task 11: `metadata_harvester/gui.py` -- harvest-trigger half
- **ACTION**: Add two `tk.LabelFrame` sections (Crossref, Geo) to `_build_ui`, plus their trigger handlers and history recording.
- **IMPLEMENT**: Crossref section: `Entry(show="*")` for token, `Entry` for email, `Entry` for rows/max, "Start Crossref Harvest" button -> `requests.post(f"http://127.0.0.1:{port}/crossref/harvest/start", json={...})` in a background thread, logged via `self._schedule(self._log, ...)`. Geo section: `Entry` for email, `Entry` for workers, "Start Geo Harvest" button -> `requests.post(f".../geo/harvest/start-all", json={...})`, same threading/logging approach. Add a periodic poll thread (every ~3s while a harvest is active) hitting `/geo/stats` and logging count deltas.
- **MIRROR**: `tabs/data_transfer_tab.py:198-224` (`_log` helper + launching a background thread from a button handler) combined with `tabs/search_tab.py:300-322` (`_schedule`/`_drain_ui_queue` for thread-safety)
- **IMPORTS**: (already imported above) `requests`
- **GOTCHA**: **Never** put the raw Crossref token into `_history_entry`'s `params` dict or into any `_log(...)` line -- log only "Crossref harvest started" + email, never the token value. This is the single most important gotcha in this plan (secret-handling).
- **VALIDATE**: manual -- with the service running, fill in a real ROR/OpenAlex-only harvest (no token needed) and confirm log lines appear; confirm the Crossref section's button is disabled/shows a validation message if the token field is empty (client-side check mirroring the server's own 400 for missing email)

### Task 12: Register the tab
- **ACTION**: Update `tools_app.py` and `config/tools_navigation.json`
- **IMPLEMENT**: In `tools_app.py`: add `from metadata_harvester.gui import MetadataHarvesterTab`; add `"metadata_harvester": MetadataHarvesterTab` to `TOOL_CLASS_BY_ID`; add a `"Metadata"` category with one tool to `DEFAULT_NAVIGATION["categories"]`; add the 4 `shutdown(wait=True)` call sites for `self.metadata_harvester_tab` alongside every existing `self.search_tab` one (lines ~620-621, ~726-727, ~766-767, ~791-792). In `config/tools_navigation.json`: add the matching `"Metadata"` category block.
- **MIRROR**: TAB_REGISTRATION, NAV_CONFIG_ENTRY, SHUTDOWN_WIRING patterns above
- **IMPORTS**: n/a (just the one new import line)
- **GOTCHA**: Update **both** `TOOL_CLASS_BY_ID` (code) and `tools_navigation.json` (config) -- the config loader silently drops unknown tool ids (see Mandatory Reading, `tools_app.py:154-174`), so if only the JSON is updated the tab never appears, with no error printed.
- **VALIDATE**: launch `python main.py`, confirm a "Metadata" tab-category appears with "Metadata Harvester" inside it

### Task 13: Dependencies
- **ACTION**: Update `requirements.txt`
- **IMPLEMENT**: Add `pydantic-settings`, `email-validator`, `loguru` (all three already proven necessary in the `fetchCrossRef` build). `fastapi`, `uvicorn`, `pydantic`, `requests` are already present.
- **MIRROR**: `requirements.txt:16-20` (existing "Search Service" dependency block -- add a new "Metadata Harvester" comment block near it)
- **IMPORTS**: n/a
- **GOTCHA**: none
- **VALIDATE**: `pip install -r requirements.txt` in the suite's `.venv` succeeds; `python -c "import metadata_harvester.service.app"` succeeds

---

## Testing Strategy

### Unit Tests

| Test | Input | Expected Output | Edge Case? |
|---|---|---|---|
| `naive_geo_parser("City, State, Country")` | 3-part string | `("City", "State", "Country")` | No |
| `naive_geo_parser("Country")` | 1-part string | `(None, None, "Country")` | Yes -- single part |
| `naive_geo_parser("")` / `None` | empty/`None` | `(None, None, None)` | Yes -- empty input |
| geo `insert_record` dedup | same `(source, source_id)` twice | 2nd call returns `False`, row count stays 1 | Yes -- duplicate |
| geo scheduler heap priority | seeded uneven letter coverage | least-covered letter processed first | Yes -- concurrent-ish access via threads |
| ROR/OpenAlex parsing | mocked HTTP responses (`responses` lib) | correctly parsed `LocationRecord`s | Yes -- malformed/missing fields |
| `TestClient(app).get("/health")` | none | `200 {"status": "ok"}` | No |
| `TestClient(app).post("/geo/harvest/start-all", json={})` | missing email | `400` | Yes -- validation |

### Edge Cases Checklist
- [x] Empty input (`naive_geo_parser("")`, missing `contact_email`)
- [ ] Maximum size input -- not applicable (no fixed-size buffers)
- [x] Invalid types (malformed ROR/OpenAlex JSON responses, missing fields)
- [x] Concurrent access (heap scheduler with multiple worker threads -- already covered by ported tests)
- [x] Network failure (ROR/OpenAlex HTTP error handling -- already covered by ported tests)
- [ ] Permission denied -- not applicable (local SQLite file, no auth layer per NOT-Building)

---

## Validation Commands

### Static Analysis
```bash
python -c "import metadata_harvester.service.app"
```
EXPECT: No import errors (confirms `email-validator`/`pydantic-settings`/`loguru` installed and wired correctly)

### Unit Tests
```bash
pytest tests/test_metadata_harvester_geo.py tests/test_metadata_harvester_crossref.py -v
```
EXPECT: All tests pass (13 geo tests ported + new crossref tests)

### Full Test Suite
```bash
pytest
```
EXPECT: No regressions in the suite's existing test files (`test_xml_compare.py`, `test_search_workflow.py`, etc.)

### Manual Validation (GUI, no automated harness for Tkinter in this repo)
- [ ] `python main.py` launches without error
- [ ] "Metadata" category + "Metadata Harvester" tab visible and selectable
- [ ] Click "START SERVICE" -> status circle turns green, "OPEN SWAGGER IN BROWSER" enables
- [ ] Click "OPEN SWAGGER IN BROWSER" -> `/docs` opens showing both `crossref` and `geo` tagged route groups
- [ ] Fill in Geo section (email + workers=1), click "Start Geo Harvest" -> log pane shows growing counts within ~10s (requires outbound network to `api.ror.org`/`api.openalex.org`)
- [ ] Crossref section's token field renders masked (dots, not plaintext)
- [ ] Click "STOP SERVICE" -> status circle turns red, buttons reset
- [ ] Close the whole app (`X` button) while the service is running -> no hang, no traceback (confirms `shutdown(wait=True)` wiring)
- [ ] Open History > View Run History -> harvester start/stop/trigger entries appear, **token value not present anywhere in the JSON**

---

## Acceptance Criteria
- [ ] All 13 tasks completed
- [ ] All validation commands pass
- [ ] Tests written and passing (ported geo tests + new crossref tests)
- [ ] No import errors
- [ ] Matches UX design (service controls + two harvest sections + log pane)
- [ ] Crossref token never appears in logs or Run History

## Completion Checklist
- [ ] Code follows discovered patterns (`SearchTab` lifecycle, `RunHistoryStore` usage, `TOOL_CLASS_BY_ID`/nav-json dual registration)
- [ ] Error handling matches codebase style (`messagebox.showerror`/`showwarning`, HTTP 400 for validation)
- [ ] Logging follows codebase conventions (`loguru` server-side, `Text` widget console client-side)
- [ ] Tests follow test patterns (flat `tests/` directory, `test_*.py` naming)
- [ ] No hardcoded values beyond the deliberate default port `7100`
- [ ] Documentation updated -- a short `metadata_harvester/README.md` mirroring `search_service/README.md`'s existence (not scoped as a task above; add if time allows, not required for acceptance)
- [ ] No unnecessary scope additions (no schema unification, no results grid, no auth)
- [ ] Self-contained -- no questions needed during implementation

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `responses` (test mocking lib) not yet installed in this suite's environment | Medium | Low | Add to `requirements.txt`; `pip install` before running new tests |
| Suite's `.venv` Python version/OS differs from `fetchCrossRef`'s (both were Windows/py3.13 in the original build, but not confirmed identical here) | Low | Medium | Task 1's static-analysis validation catches this immediately |
| Two embedded services (`SearchTab` port 7000, this tab's port 7100) running simultaneously in the same Tkinter process -- untested combination | Medium | Medium | Both already use daemon threads + independent `uvicorn.Server` instances; no shared global state between them, so this should be safe, but call it out explicitly in manual validation |
| Live network calls to `api.ror.org`/`api.openalex.org`/`api.crossref.org` may be blocked from wherever this suite actually runs (corporate network) | Medium | Medium | Same risk existed and was already resolved in the original `fetchCrossRef` build (this sandbox could reach both); if this suite runs on a more locked-down machine, the harvest buttons will simply log HTTP errors gracefully (already handled server-side) rather than crash |

## Notes
- This plan is an **additive port**, not a deletion -- `fetchCrossRef` and
  `fetchCrossRef/agent` remain in place as the original/reference
  implementations unless the user later asks to remove them.
- The two harvester backends were already fully implemented, unit-tested
  (13 tests, 0 live network calls), and live-smoke-tested against real
  ROR/OpenAlex/Crossref APIs in the prior session -- this plan is pure
  mechanical porting + GUI wrapping, not new backend design, which is why
  confidence is high despite the "Large" complexity rating (the size is in
  file count, not in unknowns).

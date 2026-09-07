# Plan: DOI Extractor

## Summary
Add a new "DOI Extractor" tool to `impact_config_suite` that scans a folder
of local XML/HTML files and pulls out every DOI value, regardless of which
of the four tag shapes it appears in (`article-id`, `pub-id`, `object-id`
with `pub-id-type="doi"`, or `ext-link` with `ext-link-type="doi"`). It
reuses the existing `ElementExtractor.scan_directory`/`parse_and_extract`
engine (the "extract elements from XML/HTML files" method already in the
suite) with a fixed XPath, then layers DOI-specific normalization,
validation, and reporting on top -- mirroring `IDPatternExtractor`'s
scan-analyze-report pipeline and `IDPatternExtractorTab`'s UI exactly.

## User Story
As an IMPACT support engineer, I want to point the suite at a folder of
document XML/HTML files and get a report of every DOI found (article DOI,
sub-object DOIs like figure/table DOIs, and DOIs embedded in `ext-link`s),
so that I can verify DOI presence/correctness without opening each file by
hand.

## Problem → Solution
Today: no way to bulk-extract DOI values from a folder of documents; doing
it via the generic Element Extractor tab requires manually typing an XPath
and gives no DOI-specific normalization (stripping `https://doi.org/`
prefixes), validation, or per-file DOI/no-DOI reporting.
→
A new "DOI Extractor" entry alongside the other Extractor Tools (Element
Extractor, Word Extractor, ID Pattern Extractor, Citation Pattern
Extractor), pre-configured with the right XPath, that produces an HTML +
CSV report of every DOI found per file, flags malformed DOIs, and lists
files with zero DOIs found.

## Metadata
- **Complexity**: Medium (5 files, ~400-600 lines)
- **Source PRD**: N/A
- **PRD Phase**: N/A
- **Estimated Files**: 5 (3 created, 2 updated)

---

## UX Design

### Before
```
┌───────────────────────────────────────────────────┐
│ Tools ▸ Extractor Tools ▸ Element Extractor        │
│   Query Type: [XPath ▾]                            │
│   Query Value: [ manually type the DOI XPath ]     │
│   -- no DOI normalization, no validity check,      │
│      no "files missing a DOI" list                 │
└───────────────────────────────────────────────────┘
```

### After
```
┌───────────────────────────────────────────────────┐
│ Tools ▸ Extractor Tools ▸ DOI Extractor            │
│   Scan Root Path: [...................] [Browse]  │
│   Filename Filter: [*_original.xml (optional)]     │
│   [x] Recursive Search                             │
│   Report Output Folder: [.............] [Browse]   │
│   [x] Open HTML report automatically               │
│   Run History: [search] [saved runs ▾] [Apply]...  │
│   [progress bar] Status: ...                       │
│   [🚀 RUN DOI EXTRACTION] [❌ Cancel] [📂 Open Last]│
│   ── Activity log ────────────────────────────────│
│   Report: File | Tag | DOI | Valid | Line          │
│   + "Files without a DOI" section                  │
└───────────────────────────────────────────────────┘
```

### Interaction Changes
| Touchpoint | Before | After | Notes |
|---|---|---|---|
| Finding DOIs in a folder | Manual XPath in Element Extractor, raw HTML dump per match | One click, pre-built XPath, normalized DOI + validity column | |
| Spotting malformed DOIs | Not possible without manual inspection | `Valid` column (regex `^10\.\d{4,9}/\S+$`) flags them | |
| Spotting documents with no DOI at all | Not possible | Dedicated "Files without a DOI" report section | |
| Re-running a previous scan | Not applicable | Run History search/apply/rerun, same as ID Pattern Extractor | |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 | `core/element_extractor.py` | 374-523 | `parse_and_extract` -- the exact "extract elements" method being reused, specifically the `query_type == "XPath"` branch (408-467) which returns `{line, tag, attributes, text, html}` dicts. `attributes` is `dict(elem.attrib)` from lxml, so a namespaced attribute like `xlink:href` appears as the Clark-notation key `{http://www.w3.org/1999/xlink}href`, not `href` |
| P0 | `core/element_extractor.py` | 525-597 | `scan_directory` -- walks a folder (respecting `recursive`, `extensions`, `filename_filter`), calls `parse_and_extract` per file with in-memory caching, returns `(scan_results, total_matches, total_files)` where `scan_results` is `{abs_file_path: {"ok": bool, "matches": [...], "error": str}}`. This is called directly, not re-implemented |
| P0 | `core/id_pattern_extractor.py` | 1193-1271 | `run_extraction` -- the exact scan → analyze → generate-HTML → export-CSV → return-paths pipeline shape to mirror, including the timestamped `run_folder` convention (`output_dir/{prefix}_{YYYYMMDD_HHMMSS}/`) |
| P0 | `core/id_pattern_extractor.py` | 1147-1191 | `export_csv`/`export_element_csv` -- plain `csv.writer` pattern, one header row + data rows |
| P0 | `core/id_pattern_extractor.py` | 455-1145 | `generate_html_report` -- the dark-theme HTML report template (CSS variables, stat cards, table, detail section) to mirror stylistically for the DOI report |
| P0 | `tabs/id_pattern_extractor_tab.py` | 1-748 (whole file) | **The** tab to mirror almost verbatim: settings frame (path/browse, filters, recursive checkbox, output dir/browse, open-report checkbox), Run History frame (search/saved-runs-combo/apply/rerun/open, all via `RunHistoryStore`), progress bar + status line, run/cancel/open-last buttons, console log with right-click context menu, background-thread extraction call |
| P1 | `core/run_history.py` | 10-102 (whole file) | `RunHistoryStore.add_entry/load_entries/save_entries/recent_for_tool/history_file_path` -- exact API used by the tab for history |
| P1 | `tools_app.py` | 20-21, 34-50, 176 | Import + `TOOL_CLASS_BY_ID` registration pattern; line 176's `_normalize_navigation_config` silently drops any `tools_navigation.json` tool id not registered here (same gotcha as the metadata-harvester port) |
| P1 | `config/tools_navigation.json` | 41-49 | The existing `"Extractor Tools"` category -- the new tool is a 5th sibling here, not a new category |
| P2 | `requirements.txt` | 8, 11 | `lxml`/`beautifulsoup4` already present -- no new dependencies needed |
| P2 | `tests/test_citation_pattern_matrix.py` | 1-60 | This codebase's test convention for extractor cores: plain `unittest`, `sys.path.insert(0, str(ROOT))` boilerplate, inline HTML/XML fixtures written to `tempfile` dirs |

## External Documentation
No external research needed -- feature uses established internal patterns
(`ElementExtractor.scan_directory`, `IDPatternExtractor.run_extraction`,
`IDPatternExtractorTab`) and a well-known, stable DOI syntax
(`10.NNNN(N*)/suffix`, per the DOI Handbook -- `^10\.\d{4,9}/\S+$` is a
widely-used pragmatic validation regex, not something needing a live
lookup).

---

## Patterns to Mirror

### REUSE_ELEMENT_EXTRACTOR (the core ask -- do not re-implement file walking)
```python
// SOURCE: core/element_extractor.py:525-597 (signature + return shape)
def scan_directory(self, dir_path: Path, query_type: str, query_val: str,
                   attr_name: str = "", attr_val: str = "", recursive: bool = False,
                   extensions: list = None, filename_filter: str = None,
                   dtd_filter: str = None, client_filter: str = None,
                   month_filter: str = "All Time", custom_month: str = "",
                   progress_callback=None):
    ...
    return scan_results, total_matches, total_files
    # scan_results: {abs_file_path: {"ok": bool, "matches": [...], "error": str}}
    # each match: {"line": int, "tag": str, "attributes": dict, "text": str, "html": str}
```
`DOIExtractor.scan_directory` calls this directly with
`query_type="XPath", query_val=DOI_XPATH`, and does NOT duplicate the
folder-walking/caching/filename-filter logic -- that is the entire point
of the "we already have an extract-elements method" instruction.

### RUN_EXTRACTION_PIPELINE
```python
// SOURCE: core/id_pattern_extractor.py:1193-1270
def run_extraction(self, root_path: str, output_dir: str, ..., progress_callback=None) -> Dict[str, Any]:
    output_dir_obj = Path(output_dir)
    output_dir_obj.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_folder = output_dir_obj / f"id_pattern_{ts}"
    run_folder.mkdir(parents=True, exist_ok=True)
    ...
    html_path = run_folder / f"id_pattern_report_{ts}.html"
    csv_path = run_folder / f"id_pattern_matrix_{ts}.csv"
    ...
    return {"html_path": ..., "csv_path": ..., "run_folder": ..., "total_docs": ..., ...}
```
`DOIExtractor.run_extraction` follows this exact shape with a
`doi_extractor_{ts}` run folder, `doi_report_{ts}.html`,
`doi_matches_{ts}.csv`.

### TAB_SETTINGS_AND_HISTORY_UI
```python
// SOURCE: tabs/id_pattern_extractor_tab.py:60-344 (whole _build_ui)
```
Copy this structure verbatim, removing the Document Type / Client Filter
comboboxes (lines 137-171 -- not applicable, DOI extraction isn't scoped to
IMPACT `impact_config.xml`-grouped documents, it scans any XML/HTML by
extension) and adding one `Filename Filter` entry instead (optional,
directly passed through to `scan_directory`'s existing `filename_filter`
param, e.g. `*_original.xml`).

### BACKGROUND_THREAD_EXTRACTION
```python
// SOURCE: tabs/id_pattern_extractor_tab.py:605-747 (_start_extraction, _run_extraction_thread)
```
Same validate-inputs → disable-run-button → spawn-daemon-thread →
progress_callback-driven logging → record-history-on-success →
auto-open-report shape.

### RUN_HISTORY_PATTERN
```python
// SOURCE: tabs/id_pattern_extractor_tab.py:38-58, 561-603
history_tool_id = "id_pattern_extractor"
history_tool_label = "ID Pattern Extractor"

@classmethod
def _load_history_entries(cls) -> list[dict]:
    valid_entries = []
    for item in RunHistoryStore.recent_for_tool(cls.history_tool_id):
        if str(item.get("source_path", "")).strip():
            valid_entries.append(item)
    return valid_entries[:cls.HISTORY_LIMIT]
```
`DOIExtractorTab` sets `history_tool_id = "doi_extractor"`,
`history_tool_label = "DOI Extractor"`, otherwise identical.

### TAB_REGISTRATION
```python
// SOURCE: tools_app.py:20-21, 43-44
from tabs.id_pattern_extractor_tab import IDPatternExtractorTab
from tabs.citation_pattern_extractor_tab import CitationPatternExtractorTab
...
"id_pattern_extractor": IDPatternExtractorTab,
"citation_pattern_extractor": CitationPatternExtractorTab,
```
Add `from tabs.doi_extractor_tab import DOIExtractorTab` and
`"doi_extractor": DOIExtractorTab,` alongside these two -- note neither of
these two existing extractors appears in `DEFAULT_NAVIGATION` either (only
in `tools_navigation.json`), so `doi_extractor` doesn't need a
`DEFAULT_NAVIGATION` entry to follow this codebase's established
convention.

### NAV_CONFIG_ENTRY
```json
// SOURCE: config/tools_navigation.json:41-49
{
  "name": "Extractor Tools",
  "tools": [
    { "id": "element_extractor", "label": "Element Extractor" },
    { "id": "word_extractor", "label": "Word Extractor" },
    { "id": "id_pattern_extractor", "label": "ID Pattern Extractor" },
    { "id": "citation_pattern_extractor", "label": "Citation Pattern Extractor" }
  ]
}
```
Add `{ "id": "doi_extractor", "label": "DOI Extractor" }` as a 5th entry in
this existing `tools` array -- no new category.

### TEST_STRUCTURE
```python
// SOURCE: tests/test_citation_pattern_matrix.py:1-14
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.citation_pattern_extractor import CitationPatternExtractor
```

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `core/doi_extractor.py` | CREATE | `DOIExtractor` class: wraps `ElementExtractor.scan_directory`, normalizes/validates DOI values, builds HTML+CSV reports |
| `tabs/doi_extractor_tab.py` | CREATE | `DOIExtractorTab`, mirrors `IDPatternExtractorTab` |
| `tests/test_doi_extractor.py` | CREATE | Unit tests for normalization/validation/dedup + an end-to-end `run_extraction` test against temp files built from the 4 example snippets |
| `tools_app.py` | UPDATE | Import + register `doi_extractor` in `TOOL_CLASS_BY_ID` |
| `config/tools_navigation.json` | UPDATE | Add `doi_extractor` to the existing `"Extractor Tools"` category |

## NOT Building
- No live DOI resolution/validation against `https://doi.org` or the
  Crossref API -- purely offline syntax validation via regex. (If live
  resolution is wanted later, that's a separate feature -- this suite
  already has a `metadata_harvester` FastAPI tab that talks to Crossref,
  which would be the natural place to add it.)
- No new query-type UI (Tag Name / CSS Selector toggle) -- the XPath is
  fixed and hardcoded to the four known DOI-bearing tag shapes; if a fifth
  shape is discovered later, extend `DOIExtractor.DOI_XPATH`, don't expose
  a raw XPath box to the user (that already exists in Element Extractor).
- No IMPACT `impact_config.xml`-based Document Type / Client filtering
  (unlike `IDPatternExtractor`) -- DOI extraction is file-content-driven,
  not IMPACT-metadata-driven, so it scans any XML/HTML file by extension,
  same as the plain `ElementExtractor` tab does.
- No modification to `ElementExtractor.parse_and_extract`/`scan_directory`
  themselves -- this is a pure consumer of the existing method, per the
  explicit instruction to reuse it rather than build a parallel extractor.

---

## Step-by-Step Tasks

### Task 1: `core/doi_extractor.py` -- normalization + validation helpers
- **ACTION**: Create the file with `DOIExtractor.__init__`, `DOI_XPATH`, `DOI_VALIDATION_PATTERN`, `_extract_href`, `normalize_doi`, `is_valid_doi`.
- **IMPLEMENT**:
  ```python
  DOI_XPATH = "//*[@pub-id-type='doi'] | //ext-link[@ext-link-type='doi']"
  DOI_VALIDATION_PATTERN = re.compile(r'^10\.\d{4,9}/\S+$')
  DOI_PREFIX_STRIP = (
      "https://doi.org/", "http://doi.org/",
      "https://dx.doi.org/", "http://dx.doi.org/", "doi:",
  )

  def __init__(self):
      self.element_extractor = ElementExtractor()

  @staticmethod
  def _extract_href(attributes: dict) -> Optional[str]:
      for key, value in attributes.items():
          if key == "href" or key.endswith("}href"):
              return value
      return None

  def normalize_doi(self, raw_text: str, attributes: dict) -> Optional[str]:
      candidate = (raw_text or "").strip()
      if not candidate.lower().startswith("10."):
          href = self._extract_href(attributes)
          if href:
              candidate = href.strip()
      for prefix in self.DOI_PREFIX_STRIP:
          if candidate.lower().startswith(prefix):
              candidate = candidate[len(prefix):]
              break
      return candidate.strip() or None

  def is_valid_doi(self, doi: str) -> bool:
      return bool(doi) and bool(self.DOI_VALIDATION_PATTERN.match(doi))
  ```
- **MIRROR**: `core/element_extractor.py`'s general style (plain functions/regex, no external deps beyond what's already imported)
- **IMPORTS**: `re`, `typing.Optional`, `core.element_extractor.ElementExtractor`
- **GOTCHA**: `attributes` comes from `dict(elem.attrib)` in `parse_and_extract`'s XPath branch (`element_extractor.py:432`) -- for the `ext-link` case, lxml exposes the namespaced `xlink:href` attribute as the Clark-notation key `{http://www.w3.org/1999/xlink}href`, NOT `href`. `_extract_href` must check `key.endswith("}href")`, not just `key == "href"`, or every `ext-link` DOI will silently fall through to using its (already-fine, in these examples) text content -- but would break on a hypothetical `ext-link` where the href and text differ.
- **GOTCHA**: `object-id` DOIs are legitimately sub-article (figure/table) DOIs like `10.1371/journal.pone.0341961.g010` -- the trailing `.g010` is normal and must NOT be treated as an invalid-DOI signal; the validation regex (`^10\.\d{4,9}/\S+$`) already accommodates this since `\S+` matches anything non-whitespace after the slash.
- **VALIDATE**: `python -c "from core.doi_extractor import DOIExtractor; d = DOIExtractor(); print(d.normalize_doi('https://doi.org/10.1016/j.sleep.2020.08.034', {})); print(d.is_valid_doi('10.1097/MD.0000000000047654'))"`

### Task 2: `core/doi_extractor.py` -- match extraction + directory scan
- **ACTION**: Add `extract_dois_from_matches` and `scan_directory`.
- **IMPLEMENT**:
  ```python
  def extract_dois_from_matches(self, matches: List[Dict]) -> List[Dict]:
      results = []
      seen = set()
      for match in matches:
          doi = self.normalize_doi(match.get("text", ""), match.get("attributes", {}))
          if not doi:
              continue
          key = (match.get("tag", ""), doi)
          if key in seen:
              continue
          seen.add(key)
          results.append({
              "tag": match.get("tag", ""),
              "doi": doi,
              "valid": self.is_valid_doi(doi),
              "line": match.get("line", 0),
          })
      return results

  def scan_directory(self, dir_path, recursive=True, filename_filter=None, progress_callback=None):
      scan_results, _total_matches, total_files = self.element_extractor.scan_directory(
          dir_path=dir_path,
          query_type="XPath",
          query_val=self.DOI_XPATH,
          recursive=recursive,
          filename_filter=filename_filter,
          progress_callback=progress_callback,
      )
      doi_results = {}
      total_dois = 0
      for file_path, data in scan_results.items():
          if not data.get("ok", True):
              doi_results[file_path] = {"ok": False, "error": data.get("error", ""), "dois": []}
              continue
          dois = self.extract_dois_from_matches(data.get("matches", []))
          doi_results[file_path] = {"ok": True, "dois": dois}
          total_dois += len(dois)
      return doi_results, total_dois, total_files
  ```
- **MIRROR**: `core/element_extractor.py:525-597` (`scan_directory`'s parameter names/defaults, so the pass-through call reads naturally)
- **IMPORTS**: `typing.Dict, List`
- **GOTCHA**: `ElementExtractor.scan_directory`'s in-memory `_cache` is keyed by `(file_path, query_type, query_val, attr_name, attr_val)` (element_extractor.py:35-39) -- since `DOI_XPATH` is a constant, repeated scans of the same folder without file changes will hit cache and skip re-parsing, which is desired behavior inherited for free, not something to defeat.
- **VALIDATE**: covered by Task 4's tests

### Task 3: `core/doi_extractor.py` -- HTML/CSV report generation + `run_extraction`
- **ACTION**: Add `generate_html_report`, `export_csv`, `run_extraction`.
- **IMPLEMENT**: HTML report with: header (scan root, timestamp), 6 stat cards (Files Scanned, Files With DOI, Files Without DOI, Total DOI Matches, Unique DOIs, Invalid DOIs), a main table (File | Tag | DOI | Valid | Line, one row per match, `Valid=No` rows visually flagged e.g. red text), and a "Files without a DOI" list section. `export_csv` writes header `["File", "Tag", "DOI", "Valid", "Line"]` then one row per match across all files. `run_extraction(root_path, output_dir, recursive=True, filename_filter=None, progress_callback=None)` creates `output_dir/doi_extractor_{ts}/`, calls `scan_directory`, writes `doi_report_{ts}.html` and `doi_matches_{ts}.csv`, returns `{"html_path", "csv_path", "run_folder", "total_files", "total_dois", "files_with_doi", "files_without_doi", "unique_doi_count", "invalid_doi_count"}`.
- **MIRROR**: `core/id_pattern_extractor.py:455-1270` (HTML template CSS/structure, `export_csv`, `run_extraction`'s timestamped-folder + progress_callback staging: `"scan"` → `"report"` → `"complete"`)
- **IMPORTS**: `os`, `html`, `csv`, `datetime.datetime`, `pathlib.Path`
- **GOTCHA**: Compute `unique_doi_count` as `len({doi for data in doi_results.values() if data.get("ok") for m in data["dois"] for doi in [m["doi"]]})` (i.e. unique across the WHOLE scan, not per-file) -- a DOI appearing in two different files (e.g. a shared reference list) should count once in this stat, distinct from `total_dois` which counts every match.
- **VALIDATE**: `python -c "from core.doi_extractor import DOIExtractor; import inspect; print(inspect.signature(DOIExtractor.run_extraction))"`

### Task 4: `tests/test_doi_extractor.py`
- **ACTION**: Create unit + integration tests.
- **IMPLEMENT**: Unit tests for `normalize_doi` covering all 4 example snippet shapes (`article-id`, `pub-id`, `object-id`, `ext-link` with href) plus prefix-stripping variants (`doi:10.xxx`, bare `10.xxx`) and empty/whitespace input. Unit tests for `is_valid_doi` (valid `10.1097/MD...`, invalid `not-a-doi`, invalid empty string). Unit test for `extract_dois_from_matches` dedup (same `(tag, doi)` twice → one result). Integration test: write a temp `.xml` file containing all 4 example snippets embedded in a minimal root element, call `DOIExtractor().scan_directory(tmp_dir)`, assert exactly 4 DOIs found with correct tags and values, then call `run_extraction` and assert the HTML and CSV files exist and the CSV has 4 data rows (+1 header).
- **MIRROR**: `tests/test_citation_pattern_matrix.py:1-14` (`sys.path` boilerplate, `unittest`, `tempfile` fixture files)
- **IMPORTS**: `sys`, `tempfile`, `unittest`, `pathlib.Path`, `core.doi_extractor.DOIExtractor`
- **GOTCHA**: The 4 example snippets must be wrapped in a well-formed XML root (e.g. `<article>...</article>`) with the `ext-link`'s `xmlns:xlink` declaration kept intact on that element (as given), otherwise `lxml.etree.fromstring` may fail depending on parser recovery settings -- use `recover=True` behavior already built into `parse_and_extract`, but keep the test fixture well-formed regardless for a clean assertion baseline.
- **VALIDATE**: `python -m unittest tests.test_doi_extractor -v`

### Task 5: `tabs/doi_extractor_tab.py`
- **ACTION**: Create `DOIExtractorTab(ttk.Frame)`.
- **IMPLEMENT**: Copy `IDPatternExtractorTab` (`tabs/id_pattern_extractor_tab.py`) structure: `history_tool_id = "doi_extractor"`, `history_tool_label = "DOI Extractor"`; settings frame with Scan Root Path (+Browse), Filename Filter entry (optional, default empty = no filter, placeholder text `*_original.xml`), Recursive checkbox, Report Output Folder (+Browse), Open-report checkbox; Run History frame (search/saved-runs/apply/rerun/open) unchanged; progress bar + status; run/cancel/open-last buttons; console log with context menu. `_run_extraction_thread` calls `self.extractor.run_extraction(root_path=..., output_dir=..., recursive=..., filename_filter=..., progress_callback=...)` and logs the returned summary counts (files scanned, DOIs found, unique DOIs, invalid DOIs, files without a DOI).
- **MIRROR**: `tabs/id_pattern_extractor_tab.py` (whole file) -- drop the Document Type / Client Filter comboboxes (lines 137-171) and their references in `_apply_history_entry`/`_current_run_settings`, replace with the single Filename Filter entry.
- **IMPORTS**: `tkinter as tk`, `tkinter.ttk, filedialog, messagebox`, `os`, `threading`, `webbrowser`, `datetime.datetime`, `pathlib.Path`, `core.doi_extractor.DOIExtractor`, `core.run_history.RunHistoryStore`
- **GOTCHA**: `IDPatternExtractorTab._history_summary` (line 470-476) references `doc_type`/`client_filter` fields that won't exist for this tab -- the mirrored `_history_summary` must reference `filename_filter`/`recursive` instead, or `KeyError`/blank display results when the history dropdown renders old entries.
- **VALIDATE**: `python -c "from tabs.doi_extractor_tab import DOIExtractorTab; print(DOIExtractorTab)"`

### Task 6: Register the tab
- **ACTION**: Update `tools_app.py` and `config/tools_navigation.json`.
- **IMPLEMENT**: In `tools_app.py`: add `from tabs.doi_extractor_tab import DOIExtractorTab` near the other extractor imports (after line 21); add `"doi_extractor": DOIExtractorTab,` to `TOOL_CLASS_BY_ID` (after line 44). In `config/tools_navigation.json`: add `{ "id": "doi_extractor", "label": "DOI Extractor" }` to the `"Extractor Tools"` category's `tools` array (after the `citation_pattern_extractor` entry).
- **MIRROR**: TAB_REGISTRATION, NAV_CONFIG_ENTRY patterns above
- **IMPORTS**: n/a
- **GOTCHA**: Same as every prior tab addition in this suite -- both files must be updated together, or the tool is silently invisible (`tools_app.py:176`'s `_normalize_navigation_config` drops unregistered ids with no error).
- **VALIDATE**: `python -c "import tools_app; print(tools_app.CommonToolsApp.TOOL_CLASS_BY_ID['doi_extractor'])"`

---

## Testing Strategy

### Unit Tests

| Test | Input | Expected Output | Edge Case? |
|---|---|---|---|
| `normalize_doi` on article-id text | `"10.1097/MD.0000000000047654"`, `{}` | `"10.1097/MD.0000000000047654"` | No |
| `normalize_doi` on ext-link with matching href | text=`"10.1016/j.sleep.2020.08.034"`, attrs with `{http://www.w3.org/1999/xlink}href`=`"https://doi.org/10.1016/j.sleep.2020.08.034"` | `"10.1016/j.sleep.2020.08.034"` | No |
| `normalize_doi` on `doi:`-prefixed text | `"doi:10.1234/x"` | `"10.1234/x"` | Yes -- prefix variant |
| `normalize_doi` on empty text, no href | `""`, `{}` | `None` | Yes -- empty input |
| `normalize_doi` on text that isn't a DOI, with href fallback | text=`""`, href=`"https://doi.org/10.5/x"` | `"10.5/x"` | Yes -- href fallback path |
| `is_valid_doi` on object-id sub-DOI | `"10.1371/journal.pone.0341961.g010"` | `True` | Yes -- trailing suffix must not fail validation |
| `is_valid_doi` on garbage | `"not-a-doi"` | `False` | Yes -- invalid type |
| `extract_dois_from_matches` dedup | two matches with same `(tag, doi)` | 1 result | Yes -- duplicate |
| `scan_directory` end-to-end | temp XML with all 4 example snippets | 4 DOIs, correct tags | No |
| `run_extraction` end-to-end | same temp dir | HTML + CSV files exist, CSV has 4 data rows | No |

### Edge Cases Checklist
- [x] Empty input (`normalize_doi("", {})`, a file with zero DOI matches)
- [ ] Maximum size input -- not applicable (no fixed buffers; relies on `ElementExtractor`'s existing streaming-per-file approach)
- [x] Invalid types (malformed DOI text, garbage `href`)
- [ ] Concurrent access -- not applicable (single-threaded scan per run, same as `IDPatternExtractor`)
- [ ] Network failure -- not applicable (no network calls, offline-only by design)
- [ ] Permission denied -- not applicable (inherits `ElementExtractor.scan_directory`'s existing per-file try/except → `{"ok": False, "error": ...}` handling)

---

## Validation Commands

### Static Analysis
```bash
python -c "import core.doi_extractor; import tabs.doi_extractor_tab; import tools_app"
```
EXPECT: No import errors

### Unit Tests
```bash
python -m unittest tests.test_doi_extractor -v
```
EXPECT: All tests pass

### Full Test Suite
```bash
python -m pytest tests/ -q
```
EXPECT: No regressions (note: this suite's full `tests/` run is slow --
see prior session's metadata-harvester report -- budget accordingly; a
targeted `python -m unittest tests.test_doi_extractor` is sufficient for
fast iteration)

### Manual Validation
- [ ] `python main.py` launches without error
- [ ] "Extractor Tools" category shows a 5th "DOI Extractor" tab
- [ ] Point it at a folder containing the 4 example XML snippets (in real IMPACT document files) → HTML report opens automatically showing 4 rows with correct DOI values and tags
- [ ] A file with no DOI-bearing tags appears in the "Files without a DOI" section
- [ ] A deliberately malformed DOI (e.g. edit one example to `"not-a-doi"`) shows `Valid=No` in the report
- [ ] Run History records the run and "Rerun Last" works

---

## Acceptance Criteria
- [ ] All 6 tasks completed
- [ ] All validation commands pass
- [ ] Tests written and passing (unit + integration)
- [ ] No import errors
- [ ] Matches UX design (settings form, history, progress, report with Valid column and "no DOI" section)

## Completion Checklist
- [ ] Code follows discovered patterns (`ElementExtractor.scan_directory` reused, not reimplemented; `IDPatternExtractor.run_extraction` pipeline shape; `IDPatternExtractorTab` UI shape)
- [ ] Error handling matches codebase style (per-file `{"ok": False, "error": ...}`, `messagebox.showerror` for input validation)
- [ ] Tests follow test patterns (`unittest` + `sys.path` boilerplate)
- [ ] No hardcoded values beyond the deliberate DOI XPath/regex constants
- [ ] No unnecessary scope additions (no live DOI resolution, no new query-type UI)
- [ ] Self-contained -- no questions needed during implementation

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A real-world DOI-bearing tag shape not covered by the 4 known examples exists in some client's documents | Low | Medium | `DOI_XPATH` is a single named constant in one place -- extending it later is a one-line change, not a redesign |
| `ElementExtractor`'s in-memory cache (keyed by file+query) could serve stale matches if a file changes between two scans within the same app session without a mtime bump on some filesystems | Low | Low | Pre-existing behavior of the reused method, not new risk introduced by this feature |
| Suite's full `tests/` run is slow (observed in the prior metadata-harvester session) | Medium | Low | Task 4's validation targets the new test file directly; full-suite run is a nice-to-have, not a blocker |

## Notes
This plan deliberately does the smallest thing that satisfies the request:
reuse the existing, working `ElementExtractor.scan_directory` engine
end-to-end rather than writing a second XML-walking implementation. The
only genuinely new logic is DOI value normalization (stripping URL
prefixes, falling back to `xlink:href`) and validation (regex), plus a
DOI-shaped report -- everything else is direct reuse or a close mirror of
`IDPatternExtractor`/`IDPatternExtractorTab`.

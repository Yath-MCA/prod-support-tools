# Element Extractor Documentation

**Version:** 2.9  
**Module:** `element_extractor_tab.py` + `core/element_extractor.py` + `search_service/app/routes/extractor_routes.py`

---

## Overview

The Element Extractor is a comprehensive tool for analyzing HTML/XML files, extracting specific elements based on tags, CSS selectors, or XPath queries, and generating interactive HTML reports with CSV export capabilities.

---

## Features

### 1. Scan Modes

- **Single File Mode**: Analyze a single HTML or XML file
- **Folder Scan Mode**: Recursively scan directories for matching files

### 2. Parallel Processing (New in v2.7)

Significantly speed up folder scanning with parallel processing using multiple CPU cores:

| Feature | Description |
|---------|-------------|
| **Use Parallel Processing** | Enable/disable parallel file processing |
| **Workers** | Number of parallel processes (Auto, 2, 4, 6, 8, 12) |

**Performance Expectations:**

| Scenario | Sequential | Parallel (4 workers) | Speedup |
|----------|------------|----------------------|---------|
| 1000 files, simple tag search | 5 min | 1.5 min | 3.3x |
| 1000 files, complex XPath | 15 min | 4 min | 3.75x |
| 100 files (I/O bound) | 30 sec | 12 sec | 2.5x |

**Technical Details:**
- Uses `ProcessPoolExecutor` for true parallel processing across CPU cores
- Automatically caps workers at 8 to avoid overwhelming I/O
- "Auto" setting uses `min(CPU count, 8)` workers
- Progress updates every 5 files
- 30-second timeout per file to handle hung processes
- Individual file failures don't stop the entire scan

**When to Use:**
- Large directories with many files
- Complex XPath or CSS selector queries (CPU-intensive)
- Multi-core machines with available CPU capacity

**Notes:**
- Only available in Folder Scan mode (disabled in Single File mode)
- Cache is disabled in parallel mode (not shared across processes)
- Memory usage increases with more workers

### 3. Query Methods

- **Tag Name**: Extract elements by HTML/XML tag name (e.g., `span`, `div`, `p`)
- **CSS Selector**: Use CSS selectors for precise targeting (e.g., `.ref .mixed-citation`)
- **XPath Query**: Use XPath expressions for complex queries (e.g., `//div[@class='content']`)

### 4. Attribute Filtering

When using Tag Name mode, you can filter by attribute:
- **Name**: Attribute name to check (e.g., `class`, `id`)
- **Value**: Optional attribute value to match

### 5. Folder Scan Options

#### File Extensions
Specify which file types to scan (default: `.xml, .html, .htm, .xhtml`)

#### Filename Filter
Filter files by name pattern:
- `*_original.html` - Files ending with "_original.html"
- `*_updated.html` - Files ending with "_updated.html"
- `*_original.xml` - XML originals ending with "_original.xml" (also accepts legacy "._original.xml")
- `None` - No filename filter

#### DTD Filter
Filter by document type declaration:
- `JATS` - Journal Article Tag Suite
- `BITS` - Book Interchange Tag Suite
- `None` - No DTD filter

#### Client Filter
Filter by client name from impact_config.xml:
- `OUP`, `TNF`, `PLOS`, `BRILL`, `ACS`, `LWW`, `MEDKNOW`
- `None` - No client filter

---

## Filter Options

### Month Filter (New in v2.5)

Filter HTML/XML files by their last modified date when scanning:

| Option | Description |
|--------|-------------|
| **All Time** | No date filtering (default) |
| **This Month** | Files modified in the current calendar month |
| **Last Month** | Files modified in the previous calendar month |
| **Custom** | Specify a custom month using MM-YYYY or YYYY-MM format |

#### Custom Month Formats
- `MM-YYYY`: `06-2026` (June 2026)
- `YYYY-MM`: `2026-06` (June 2026)

The month filter examines the file's modification timestamp (`st_mtime`) and only includes files modified within the specified month and year.

**Note:** Month filter is only available in Folder Scan mode. It is automatically disabled in Single File mode.

---

## Report Organization

### Month-Based Subfolders (New in v2.5)

When enabled, reports are organized into month-based subfolders using the format `YYYY-MM`:

```
~/Documents/impact-support-log/
└── 2026-06/
    └── extraction_target_selector_20260622_143052/
        ├── Element_Extraction_Report_*.html
        ├── Element_Extraction_Summary_*.html
        ├── Element_Extraction_Report_*.csv
        └── matched_files/
```

**Benefits:**
- Easy chronological organization of reports
- Simplified archiving and cleanup
- Better navigation for frequently generated reports

---

## Report Content Options

### Include Outer XML/HTML
Toggle the display of full element markup in the detailed report.

### Include Inner Text Content
Toggle the display of text content within matched elements.

### Export CSV Summary
Generate a CSV file with all match instances for spreadsheet analysis.

### Copy Matched Source Files
Create a copy of all source files that contain matches in the report folder.

---

## History and Persistence

### Run History
- Recent runs are automatically saved to history
- History entries include all filter settings and options
- Search history entries using the search box
- Re-run previous configurations with one click

### History Persistence
The following settings are preserved in history:
- Mode (Single File / Folder Scan)
- Source path
- Query type and value
- Attribute filters
- Recursive option
- Extensions list
- Filename filter
- DTD filter
- Client filter
- **Month filter (v2.5)**
- **Custom month value (v2.5)**
- **Organization by month setting (v2.5)**
- **Parallel mode (v2.7)**
- **Worker count (v2.7)**
- Output directory
- Report content options

---

## Generated Reports

### 1. Detailed Report (`Element_Extraction_Report_*.html`)
- Interactive collapsible file cards
- Per-element details with attributes
- Highlighted year patterns in text
- Copy-to-clipboard functionality
- Search within results

### 2. Summary Report (`Element_Extraction_Summary_*.html`)
- Per-selector statistics cards
- File overview tables
- Overall scan metrics
- Selector comparison

### 3. CSV Export (`Element_Extraction_Report_*.csv`)
- Spreadsheet-compatible format
- Columns: selector, query_type, file_path, file_name, instance_no, line, tag, inner_text, outer_xml
- One row per match instance

---

## API / Core Methods

### `ElementExtractor.scan_directory()`

```python
scan_results, total_matches, total_files = extractor.scan_directory(
    dir_path: Path,
    query_type: str,
    query_val: str,
    attr_name: str = "",
    attr_val: str = "",
    recursive: bool = False,
    extensions: list = None,
    filename_filter: str = None,
    dtd_filter: str = None,
    client_filter: str = None,
    month_filter: str = "All Time",  # New in v2.5
    custom_month: str = "",           # New in v2.5
    progress_callback=None
)
```

### `ElementExtractor._matches_month_filter()`

```python
matches = ElementExtractor._matches_month_filter(
    file_path: Path,
    month_filter: str,  # "All Time", "This Month", "Last Month", "Custom"
    custom_month: str = ""  # "MM-YYYY" or "YYYY-MM" for Custom filter
)
```

---

## REST API (New in v2.8)

The Element Extractor is now available via REST API for integration with external systems.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/extract/folder` | POST | Synchronous folder extraction |
| `/extract/folder/async` | POST | Async folder extraction (for large folders) |
| `/extract/job/{job_id}/status` | GET | Check async job status |
| `/extract/file` | POST | Single file extraction |

### Request/Response Models

#### ExtractFolderRequest
```json
{
  "source_path": "string",           // Required: Path to folder
  "query_type": "string",            // Required: "Tag Name", "CSS Selector", or "XPath"
  "queries": ["string"],             // Required: List of queries to execute
  "recursive": true,                 // Optional: Scan subdirectories (default: true)
  "extensions": [".html", ".xml"],   // Optional: File extensions (default: [".xml", ".html", ".htm", ".xhtml"])
  "filename_filter": "string",       // Optional: Filename pattern filter
  "dtd_filter": "string",          // Optional: DTD type filter (e.g., "JATS", "BITS")
  "client_filter": "string",       // Optional: Client filter
  "month_filter": "All Time",      // Optional: "All Time", "This Month", "Last Month", "Custom"
  "custom_month": "string",        // Optional: "MM-YYYY" or "YYYY-MM" for Custom filter
  "batch_size": 0,                 // Optional: Batch size (0 = no limit)
  "batch_offset": 0,               // Optional: Batch offset for resuming
  "use_parallel": true,              // Optional: Use parallel processing (default: true)
  "max_workers": 4,                // Optional: Number of workers (1-16, default: auto)
  "generate_reports": false,       // Optional: Generate HTML/CSV reports
  "output_dir": "string",          // Optional: Directory for report output
  "attr_name": "string",           // Optional: Attribute name filter
  "attr_val": "string"             // Optional: Attribute value filter
}
```

#### ExtractFileRequest
```json
{
  "file_path": "string",             // Required: Path to file
  "query_type": "string",            // Required: Query type
  "queries": ["string"],             // Required: List of queries
  "attr_name": "string",             // Optional: Attribute name filter
  "attr_val": "string"               // Optional: Attribute value filter
}
```

#### ExtractionResponse (for /extract/folder)
```json
{
  "status": "success",
  "source_path": "string",
  "query_type": "string",
  "queries": ["string"],
  "total_files": 10,
  "total_matches": 25,
  "has_more": false,
  "next_offset": 0,
  "results": [...],
  "report_paths": ["path/to/report.html"],
  "processing_time_ms": 1234
}
```

#### ExtractionJobResponse (for /extract/folder/async)
```json
{
  "job_id": "uuid-string",
  "status": "pending",
  "message": "Extraction job started. Poll /job/{job_id}/status for progress."
}
```

#### JobStatusResponse (for /extract/job/{job_id}/status)
```json
{
  "job_id": "uuid-string",
  "status": "completed",  // "pending", "running", "completed", "failed"
  "progress": 100,
  "result": {...},        // Full extraction result when completed
  "error": null           // Error message if failed
}
```

### Example Usage

#### Single File Extraction
```bash
curl -X POST http://localhost:7000/extract/file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/file.html",
    "query_type": "Tag Name",
    "queries": ["span"]
  }'
```

#### Folder Extraction
```bash
curl -X POST http://localhost:7000/extract/folder \
  -H "Content-Type: application/json" \
  -d '{
    "source_path": "/path/to/folder",
    "query_type": "CSS Selector",
    "queries": [".ref .mixed-citation"],
    "recursive": true,
    "extensions": [".html"]
  }'
```

#### Async Folder Extraction (for large folders)
```bash
# Start async job
curl -X POST http://localhost:7000/extract/folder/async \
  -H "Content-Type: application/json" \
  -d '{
    "source_path": "/path/to/large/folder",
    "query_type": "XPath",
    "queries": ["//div[@class=\"content\"]"],
    "use_parallel": true,
    "max_workers": 8
  }'

# Check job status (poll until completed)
curl http://localhost:7000/extract/job/{job_id}/status
```

### JSP/Java Frontend Integration

The API can be called from a JSP page via AJAX:

```jsp
<script>
async function startExtraction() {
    const response = await fetch('http://localhost:7000/extract/folder', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            source_path: document.getElementById('sourcePath').value,
            query_type: document.getElementById('queryType').value,
            queries: document.getElementById('queries').value.split(',')
        })
    });
    const result = await response.json();
    // Display results
    console.log(`Found ${result.total_matches} matches in ${result.total_files} files`);
}
</script>
```

### Error Handling

The API returns standard HTTP status codes:

| Status Code | Meaning |
|-------------|---------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 404 | Not Found (file/folder doesn't exist) |
| 500 | Internal Server Error |

Error response format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

---

## Mixed-citation Comment + Alpha Text Report

Specialized Element Extractor mode that walks each `mixed-citation` and reports **direct-child** hits only (nested content under `string-name` etc. is ignored).

### GUI

Enable the checkbox **Mixed-citation comment + alpha text** on the Element Extractor tab (alongside other report options). Run a single-file or folder scan as usual; when the checkbox is checked, the suite scans for these hits and writes HTML + CSV reports (opening them if **Open report** is enabled).

### Match rules

| Hit kind | Rule |
|----------|------|
| **comment** | Direct child of `mixed-citation` (`class` or `data-name="mixed-citation"`) that is a comment element: tag `comment`, class `comment`, or `data-name="comment"` (same recognition style as `patterns/refs.py`). |
| **alpha_text** | Direct-child text node whose stripped value matches `^[A-Za-z]+$` only (letters only — no digits, punctuation, or spaces). |

Ignorable ref nodes are skipped via `patterns.refs.is_ignorable_ref_node`. Client is resolved from nearby `impact_config.xml` using the existing Element Extractor client filters.

### Client rollup columns

HTML client rollup table and CSV share these columns:

- `client`
- `files_searched`
- `files_with_hits`
- `comment_hits`
- `alpha_text_hits`
- `total_hits`

The HTML report also includes a hit-details table (`#`, Client, File, Line, Kind, Value).

### Report output

Reports are written under the run folder in `~/Documents/impact-support-log/` (optionally month-organized), named:

- `Mixed_Citation_Direct_Hits_<target>_<timestamp>.html`
- `Mixed_Citation_Direct_Hits_<target>_<timestamp>.csv`

### Core helpers

- Module: `core/mixed_citation_direct_hits.py`
- Thin wrappers: `ElementExtractor.extract_mixed_citation_direct_hits` / `scan_mixed_citation_direct_hits` in `core/element_extractor.py`
- Tests: `tests/test_mixed_citation_direct_hits.py`


## Version History

### v2.9 - Mixed-citation Comment + Alpha Text
- Added specialized report for direct-child `comment` elements and alphabetic-only text under `mixed-citation`
- Client-wise HTML + CSV rollup (files searched vs files with hits)
- GUI checkbox: Mixed-citation comment + alpha text
### v2.8 - REST API
- Added REST API endpoints for element extraction
- Supports synchronous and asynchronous extraction
- Compatible with JSP/Java frontend integration
- In-memory job tracking for async operations

### v2.7 - Parallel Processing
- Added parallel directory scanning using ProcessPoolExecutor
- Added parallel processing toggle and worker count dropdown
- Expect 3-4x speedup on multi-core machines for large directories
- Disabled caching in parallel mode (not shared across processes)
- Added 30-second timeout per file in parallel mode
- Updated history persistence to include parallel mode settings

### v2.5 - Month-Wise Filter Provisions
- Added Month Filter for filtering files by modification date
- Added Report Organization option for month-based subfolders
- Added custom month input with MM-YYYY and YYYY-MM format support
- Updated history persistence to include month filter settings

### v2.4 - ID Pattern Extractor
- Added ID Pattern Extractor tool for analyzing ID patterns across documents

### v2.3 - Copy Matched Files
- Added option to copy matched source files to report folder

### v2.2 - Report Content Options
- Added toggles for Outer XML and Inner Text display
- Added CSV export option

### v2.1 - Multi-Selector Support
- Added support for multiple comma-separated queries
- Added consolidated summary report

### v2.0 - Initial Release
- Core element extraction functionality
- HTML report generation
- Run history persistence

---

## Troubleshooting

### Month Filter Not Working
- Ensure the file system reports accurate modification times
- Verify the file has been modified in the expected month
- Check that the custom month format is correct (MM-YYYY or YYYY-MM)

### Reports Not Organized by Month
- Verify the "Organize reports by month subfolders" checkbox is enabled
- Ensure the output directory has write permissions
- The month folder is created based on the current system date

### History Not Saving Month Settings
- History entries created before v2.5 will use defaults for new settings
- Re-run and save a new history entry to include month filter settings

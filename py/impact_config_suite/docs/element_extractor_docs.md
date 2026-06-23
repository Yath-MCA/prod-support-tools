# IMPACT Config Suite: XML/HTML Element Extractor

**Document Version:** 2.0  
**Last Updated:** June 2026  
**Tool Status:** Production Ready

---

## Executive Summary for Management

### Safety Guarantee: READ-ONLY Operation

**The Element Extractor is completely READ-ONLY.**

- It **only reads** source HTML/XML files to extract information
- It **never modifies, overwrites, or corrupts** the original files in any way
- All output (reports, CSV files) is written **only** to the user-specified output folder
- Original file timestamps, content, and permissions remain **completely unchanged**
- The tool operates safely on production files without risk of data loss

---

## 1. Tool Overview

The Element Extractor is a production-grade tool for analyzing HTML/XML files and extracting specific elements using:
- **Tag Names** (e.g., `span`, `p`, `fig`)
- **CSS Selectors** (e.g., `div.content span`, `a[href]`)
- **XPath Queries** (e.g., `//xref[@rid]`, `//a[@href]`)

### Key Capabilities

| Feature | Description |
|---------|-------------|
| Single File Mode | Analyze one HTML/XML file at a time |
| Folder Scan Mode | Recursively scan entire directories with filters |
| Multi-Selector Support | Run multiple queries in a single operation (comma-separated) |
| Filter Options | Filename filters, DTD filters, Client filters |
| Report Generation | Three report types: Detailed HTML, Summary Dashboard, CSV Export |
| Copy Matched Files | Optional: Copy source files with matches to timestamped folder |

---

## 2. New Features (June 2026 Release)

### 2.1 Multi-Selector Support

Users can now enter **comma-separated selectors** to run multiple extractions in a single operation.

**Example:**
```
span, a[href], //xref[@rid], div.content
```

This runs four separate extractions and generates consolidated reports showing results for all selectors.

**Benefits:**
- Analyze multiple element types in one scan
- Save time on large folder scans
- Compare results across different selectors in a single report

### 2.2 Report Content Toggles

Two new checkboxes control report content (both default to **ON**):

| Toggle | When ON | When OFF |
|--------|---------|----------|
| **Include Outer XML/HTML** | Shows the complete element markup in reports | Hides markup, shows only metadata |
| **Include Inner Text Content** | Shows the text content inside elements | Hides inner text |

**Use Cases:**
- **Keep both ON** for complete analysis and debugging
- **Turn OFF Outer XML** when you only need text content and line numbers
- **Turn OFF Inner Text** when you only need structural analysis
- **Turn both OFF** for minimal reports with just line numbers and attributes

### 2.3 Consolidated Summary Report (NEW)

A new **Summary Dashboard** is always generated alongside the detailed report.

**Features:**
- Patterns-style consolidated statistics cards
- Per-selector metrics: Files with matches / Total files scanned
- Instance counts per selector
- Quick visual overview for management review
- No need to open large detailed reports for quick status checks

### 2.4 CSV Export (NEW)

Optional CSV export provides machine-readable data for further analysis.

**CSV Columns:**
- `selector` - The query that found this match
- `query_type` - Tag Name, CSS Selector, or XPath
- `file_path` - Full path to the source file
- `file_name` - Filename only
- `instance_no` - Match number within that file
- `line` - Line number in source file
- `tag` - HTML/XML tag name
- `inner_text` - Text content inside the element
- `outer_xml` - Complete element markup

**Benefits:**
- Import into Excel for pivot tables and charts
- Feed into other tools for automated processing
- Easy filtering and sorting in spreadsheet applications

### 2.5 Copy Matched Source Files (NEW)

Optional feature to copy all source files that had matches to a separate folder for easy collection and sharing.

**How it Works:**
- When enabled, creates a timestamped subfolder (`matched_files_YYYYMMDD_HHMMSS`) inside the output directory
- Copies only files that had at least one match (not all scanned files)
- Preserves original file timestamps using `shutil.copy2()`
- Handles filename collisions automatically (appends `_1`, `_2`, etc.)

**Use Cases:**
- Collect all files containing specific elements for further analysis
- Package matched files for sharing with team members
- Create subsets of data for downstream processing
- Archive files that meet specific criteria

**Safety:**
- **Default is OFF** (checkbox must be explicitly enabled)
- Original files are **never modified**
- Only **copies** are created in the output folder
- Original file timestamps remain unchanged

---

## 3. Output Structure

All extraction outputs are organized into a single **timestamped run folder**:

```
~/Documents/impact-support-log/
└── extraction_{target}_{selector}_{timestamp}/
    ├── Element_Extraction_Report_{target}_{selector}.html
    ├── Element_Extraction_Summary_{target}_{selector}.html
    ├── Element_Extraction_Report_{target}_{selector}.csv (optional)
    └── matched_files/ (optional)
```

### 3.1 Detailed HTML Report

**Filename:** `Element_Extraction_Report_{target}_{selector}.html`

**Location:** Inside the run folder

**Always Generated:** Yes

**Features:**
- Interactive dark-themed interface
- Collapsible sections per file and per selector
- Real-time search/filter within the report
- One-click copy for element markup
- Line numbers for every match
- Attribute tables for each element

### 3.2 Summary Report

**Filename:** `Element_Extraction_Summary_{target}_{selector}.html`

**Location:** Inside the run folder

**Always Generated:** Yes

**Features:**
- Dashboard-style statistics cards
- Per-selector file match ratios
- Total instance counts
- Quick visual overview

### 3.3 CSV Export

**Filename:** `Element_Extraction_Report_{target}_{selector}.csv`

**Location:** Inside the run folder

**Generated:** Only if "Export CSV" checkbox is enabled (default: ON)

**Features:**
- One row per match instance
- UTF-8 encoding for international characters
- Compatible with Excel, Google Sheets, and data analysis tools

### 3.4 Copied Source Files (Optional)

**Folder:** `matched_files/`

**Generated:** Only if "Copy matched source files" checkbox is enabled (default: OFF)

**Features:**
- Copies only files that had at least one match
- Preserves original file timestamps
- Handles name collisions (appends `_1`, `_2`, etc.)
- Creates subfolder inside the run folder

**Example Output Structure:**
```
~/Documents/impact-support-log/
└── extraction_target_selector_20260622_143052/    # Run folder (timestamped)
    ├── Element_Extraction_Report_target_selector.html
    ├── Element_Extraction_Summary_target_selector.html
    ├── Element_Extraction_Report_target_selector.csv
    └── matched_files/                              # Copied source files
        ├── chapter1.html
        ├── chapter3.html
        └── article_2.html
```

---

## 4. How to Use

### 4.1 Launching the Tool

1. Launch the Framework GUI (run `tools_app.py` or start the application)
2. Navigate to the **Element Extractor** tab (under Extractor Tools)

### 4.2 Configuration Steps

**Step 1: Select Scan Mode**
- **Single File:** Choose one HTML/XML file to analyze
- **Folder Scan:** Scan an entire directory (optionally recursive)

**Step 2: Select Source**
- Click "Browse" to select the file or folder

**Step 3: Configure Extraction Method**

| Method | Example Query | Use Case |
|--------|--------------|----------|
| Tag Name | `span` | Find all span elements |
| Tag Name + Attribute | `span` with attr `class` = `citation` | Find citation spans |
| CSS Selector | `div.content a[href]` | Find links in content divs |
| XPath | `//xref[@rid]` | Find cross-references by ID |

**Step 4: Enable Multi-Selector (Optional)**
- Enter comma-separated queries: `span, p, //xref[@rid]`
- Each query runs as a separate extraction

**Step 5: Configure Report Content**
- Check/uncheck "Include Outer XML/HTML" as needed (default: ON)
- Check/uncheck "Include Inner Text Content" as needed (default: ON)
- Check/uncheck "Export CSV Summary" as needed (default: ON)
- Check/uncheck "Copy matched source files" as needed (default: OFF)

**Step 6: Set Output Folder**
- Default: `~/Documents/impact-support-log`
- All reports save to this location

**Step 7: Run Extraction**
- Click "RUN ELEMENT EXTRACTION"
- Progress appears in the activity log
- Reports open automatically when complete

### 4.3 Folder Scan Options

When using Folder Scan mode, additional filters are available:

| Filter | Description |
|--------|-------------|
| **Recursive Search** | Include subdirectories |
| **Extensions** | File types to scan (default: .xml, .html, .htm, .xhtml) |
| **Filename Filter** | Match specific filename patterns |
| **DTD Filter** | Filter by DTD type (requires impact_config.xml) |
| **Client Filter** | Filter by client (requires impact_config.xml) |

---

## 5. Report Examples

### Example 1: Single File, Single Selector

**Input:**
- Mode: Single File
- File: `chapter1.html`
- Query: `span` (Tag Name)

**Output Folder:** `extraction_chapter1_span_20260622_143052/`

**Contents:**
- `Element_Extraction_Report_chapter1_span.html` (Detailed)
- `Element_Extraction_Summary_chapter1_span.html` (Summary)
- `Element_Extraction_Report_chapter1_span.csv` (CSV, if enabled)

### Example 2: Folder Scan, Multi-Selector

**Input:**
- Mode: Folder Scan
- Folder: `/data/xml_files`
- Recursive: Yes
- Query: `xref, a[href], //fig` (3 selectors)
- Copy matched files: Enabled

**Output Folder:** `extraction_xml_files_xref_and_2_more_20260622_143052/`

**Contents:**
- `Element_Extraction_Report_xml_files_xref_and_2_more.html` (Detailed, 3 selector sections)
- `Element_Extraction_Summary_xml_files_xref_and_2_more.html` (Summary, 3 stat cards)
- `Element_Extraction_Report_xml_files_xref_and_2_more.csv` (CSV with selector column)
- `matched_files/` (Folder with copied source files that had matches)

---

## 6. Technical Architecture

### Core Engine: `core/element_extractor.py`

- **Dual Parsing Engine:** BeautifulSoup (CSS/Tag) + lxml.etree (XPath)
- **Line Number Detection:** Accurate source line tracking via lxml
- **Caching:** In-memory cache prevents re-parsing unchanged files
- **Namespace Handling:** Graceful XML namespace support
- **Config Caching:** `impact_config.xml` values (DTD, Client, Doc-Title, Project-Title, Identifier, Link-Info, Type) cached with mtime invalidation
- **Doc-Title API:** `get_doc_title(file_path)` method retrieves document title from sibling `impact_config.xml`
- **Full Metadata Support:** Reads and displays `<identifier>`, `<link-info>`, `<type>`, `<client>` from `impact_config.xml`
- **Metadata Display:** Shows TYPE|CLIENT|LINK-INFO|IDENTIFIER line in report file headers (light blue monospace)
- **DTD-Based Title Display:** Report file headers show appropriate title based on DTD:
  - **BITS DTD:** Shows `project-title` from `impact_config.xml`
  - **JATS DTD:** Shows `doc-title` from `impact_config.xml`
  - Displays title type badge (e.g., "PROJECT-TITLE" or "DOC-TITLE") and filename as subtitle

### GUI Layer: `element_extractor_tab.py`

- **Multi-threaded Execution:** Background processing prevents UI lockups
- **Cancellation Support:** Stop long-running scans mid-operation
- **Live Console:** Real-time progress and match logging
- **Run History:** Save and re-run previous configurations

---

## 7. Safety and Security

### Data Integrity

| Aspect | Guarantee |
|--------|-----------|
| Source Files | Never modified, opened read-only |
| File Timestamps | Never changed |
| File Permissions | Never altered |
| Output Location | Only user-specified output folder |
| Temporary Files | Cleaned up automatically |

### Error Handling

- Parse errors are logged but don't stop the scan
- Invalid files are skipped and reported
- Malformed XML is handled gracefully via recovery parsers
- All errors appear in the console log and detailed report

---

## 8. Performance Notes

### Large Folder Scans

- Progress bar shows current file and percentage
- Cancel button available at any time
- Cache prevents re-parsing files that haven't changed
- Memory-efficient streaming for large files

### Recommended Practices

1. **Use filters** to reduce scan scope (filename, DTD, client)
2. **Start non-recursive** to test, then enable recursive if needed
3. **Use specific selectors** to reduce match volume
4. **Disable unneeded report content** (Outer XML/Inner Text) for faster generation

---

## 9. Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| No matches found | Check query syntax; verify file contains the elements |
| XPath not working | Ensure query starts with `//` or `/`; check namespace prefixes |
| CSS selector fails | Verify selector syntax; some complex selectors may not be supported |
| Reports not opening | Check output folder path exists and is writable |
| Slow performance | Enable filters; reduce file scope; use non-recursive mode |

### Support

For technical issues or feature requests, contact the development team.

---

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Initial | Basic single-selector extraction with HTML report |
| 2.0 | June 2026 | Multi-selector support, content toggles, summary report, CSV export |
| 2.1 | June 2026 | Copy matched files option added to output folder |
| 2.2 | June 2026 | Doc-title reading from impact_config.xml with caching |
| 2.3 | June 2026 | DTD-based title display (BITS=project-title, JATS=doc-title) in report headers |
| 2.4 | June 2026 | Full metadata display (type, client, link-info, ISBN) in report headers |

---

**End of Document**

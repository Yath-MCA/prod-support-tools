# IMPACT Config Suite GUI

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the GUI
python main.py
```

---

## Tab Tools Overview

### 1. Analyses Tab (Content Analysis Engine)

**Purpose**: Analyzes document content and generates comprehensive analysis reports.

**Features**:
- Root path selection with browse functionality
- Filter by Document ID or Client name
- Recursive sub-directory scanning
- Cache management for performance optimization
- Comprehensive statistics: chapters, figures, tables, footnotes, labels

**How to Use**:
1. Set root path for analysis (e.g., `D:\IMPACT`)
2. Enter Document ID or Client name (optional filter)
3. Enable "Recursive Sub-directory Scan" for deep scanning
4. Click "GENERATE ANALYSIS REPORT"
5. View results in browser
6. Use "Clear Cache" to reset stored results

**Output**:
- Main report: `Documents/IMPACT_ConfigSuite/analyses/Unified_Analysis_<client>.html`
- JSON data: `Documents/IMPACT_ConfigSuite/analyses/Unified_Analysis_<client>.json`
- Per-document copies saved inside each document folder

**Cancel**: Click "Cancel" to abort long-running analysis

---

### 2. Patterns Tab (Journal Patterns Reporter)

**Purpose**: Generates global patterns reports from journal configuration XML files.

**Features**:
- Configurable source directory (default: `src/clientconfig`)
- Custom glob pattern support (default: `**/config.xml`)
- Multi-format output: HTML, JSON, Excel
- Progress logging with timestamps
- Pattern signature analysis

**How to Use**:
1. Set source directory path or use Browse button
2. Adjust search pattern if needed (e.g., `**/*.xml`)
3. Click "GENERATE GLOBAL PATTERNS REPORT"
4. View results in generated HTML report
5. Optionally open Excel audit file

**Output** (saved to `patterns/logs/`):
- `impact_report_<timestamp>.html` - Main report
- `impact_report_<timestamp>.json` - Raw data
- `impact_report_<timestamp>.xlsx` - Excel audit
- `patterns_<timestamp>.json` - Pattern index

**Cancel**: Click "Cancel" to stop processing

---

### 3. Search Tab (Distributed Search Service)

**Purpose**: Provides a web interface for searching through XML and HTML configuration files across the project.

**Features**:
- FastAPI-based search service
- Configurable service port (default: 7000)
- Real-time service output logging
- Health check with status indicator
- Web UI for distributed search

**How to Use**:
1. Set desired port number
2. Click "START SEARCH SERVICE" to launch
3. Wait for service to start (green indicator)
4. Click "OPEN UI IN BROWSER" to access search interface
5. Use the web UI to search configuration files
6. Click "STOP SERVICE" to shut down

**API Endpoints**:
- `POST /fetch` - Fetch document IDs by date range
- `POST /copy` - Copy files for a batch
- `POST /search` - Search terms in batch files

**Cancel**: Click "STOP SERVICE" to terminate the service

---

### 4. CJK Integrity Tab (CJK Integrity Checker)

**Purpose**: Compares original and revised documents to detect character integrity issues.

**Features**:
- Unique ID-based document resolution
- Multiple domain support (PROD, UAT, LOCAL, DEV)
- Default and Custom compare modes
- HTML, JSON, and CSV report generation

**Compare Modes**:

#### Default Mode
Uses `unique_id + domain` to resolve original/revised URLs from `cjk_checker/config.json`.

#### Custom Mode
Manually select local HTML files for original and revised content. No network fetch required.

**How to Use**:
1. Enter Unique ID (required)
2. Select Domain (PROD, UAT, LOCAL, DEV)
3. Choose compare mode:
   - **Default**: Uses configured URLs
   - **Custom**: Select local files
4. Click Compare
5. View generated reports

**Output** (saved to `cjk_checker/reports/`):
- `report_<doc_id>.html`
- `report_<doc_id>.json`
- `report_<doc_id>.csv`

**Configuration**: Edit `cjk_checker/config.json` to configure API endpoints.

---

### 5. Data Transfer Tab (OCI File Download & Mongo Insert)

**Purpose**: Downloads files from OCI bucket and manages MongoDB records.

**Features**:
- Download files from OCI bucket (`bucket-impact`)
- Auto-move folder after download
- MongoDB record insertion
- JSON validation
- Signoff detection with auto status

**How to Use**:

#### Download Files
1. Enter UniqueId
2. Click "Download from OCI"
3. Monitor progress in console output
4. Files auto-move to final location after download

#### Insert MongoDB Record
1. Enter JSON record in text area
2. Click "Validate JSON" to check syntax and signoff
3. Click "Insert Record" to save to MongoDB

**File Paths**:
- Download destination: `C:\_IMPACT\_LOCAL_FILES\IMPACT\{UniqueId}`
- Final location: `C:\_IMPACT\_LOCAL_FILES\{UniqueId}`

**MongoDB**:
- Database: `impact_db`
- Collection: `rfilelist`
- Status auto-set to `active` if signoff detected

**Cancel**: Click "Cancel" to abort active download

---

## Configuration

### CJK Checker Config

Edit `cjk_checker/config.json`:

```json
{
  "timeout": 30,
  "domains": {
    "PROD": {
      "original_url": "https://server-prod/api/original/{doc_id}",
      "revised_url": "https://server-prod/api/revised/{doc_id}"
    },
    "UAT": {
      "original_url": "https://server-uat/api/original/{doc_id}",
      "revised_url": "https://server-uat/api/revised/{doc_id}"
    },
    "LOCAL": {
      "original_url": "http://localhost/api/original/{doc_id}",
      "revised_url": "http://localhost/api/revised/{doc_id}"
    },
    "DEV": {
      "original_url": "https://server-dev/api/original/{doc_id}",
      "revised_url": "https://server-dev/api/revised/{doc_id}"
    }
  },
  "default_domain": "UAT"
}
```

---

## Build EXE (Windows)

Build script files:
- `build_exe.ps1`
- `build_exe.bat`

### Build merged common GUI EXE

```bat
build_exe.bat common
```

or

```powershell
.\build_exe.ps1 -Target common -Clean
```

**Output**: `dist/IMPACT_ConfigSuite_v5.0.exe`

### Build with legacy references

```bat
build_exe.bat common legacy
```

**Additional outputs**:
- `build/impact_suite/` (legacy build-work reference)
- `dist/IMPACT_ConfigSuite_v3.0.exe` (legacy EXE alias)

### Build CJK-only EXE

```bat
build_exe.bat cjk
```

**Output**: `dist/IMPACT_CJK_Integrity_Checker.exe`

### Build CJK with legacy references

```bat
build_exe.bat cjk legacy
```

**Additional outputs**:
- `build/impact_cjk_suite/`
- `dist/IMPACT_CJK_Integrity_Checker_v1.0.exe`

---

## Notes

- Script auto-detects workspace virtual environment Python when available.
- `cjk_checker/config.json` and `cjk_checker/templates/report_template.html` are bundled into the EXE.
- First build can take several minutes.
- Analysis reports are saved to `Documents/IMPACT_ConfigSuite/` when running as EXE.

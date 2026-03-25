# Pattern Report Tool

A Python tool for analyzing and generating reports from XML client configuration files. It extracts pattern information from Figure, Table, and Reference configurations and groups journals by similar patterns.

## Features

- **Pattern Detection**: Automatically groups journals with identical attribute configurations
- **Reference Categorization**: Separates patterns by citation style:
  - 🔢 **Numbered** (`data-label-format: numbered*`)
  - 📖 **Unnumbered** (`data-label-format: unnumbered`) - Author-Year style
  - 📝 **Footnote** (`citation.type: FOOTNOTE`)
- **Figure/Table Pattern Analysis**: Groups by dircite/indircite attributes
- **Part Label Pattern Analysis**: Groups by part_lab_* attributes
- **Percentage Match Statistics**: 
  - Per-pattern percentage of total journals
  - Consolidated percentage summary across all categories
  - Visual percentage badges (high/medium/low)
- **Unit Test Suggestions**: 
  - Minimum journal set for 100% pattern coverage
  - Per-category and client-level recommendations
  - Coverage efficiency metrics
- **Interactive HTML Report**: 
  - Vertical accordion navigation
  - Comparison grid view
  - Pattern anomaly detection (<3 journals)
- **Multiple Output Formats**: HTML, JSON, Excel

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Run from command line:
```bash
cd c:\_IMPACT\tomcat\webapps\impactweb_live\untils_automation\py
python -m pattern_report.report_main
```

### Or import as module:
```python
from pattern_report.report_main import main
main()
```

## Output Files

Reports are saved to `pattern_report/logs/` with timestamp:

| File | Description |
|------|-------------|
| `impact_report_YYYY-MM-DD_HH-MM-SS.html` | Interactive HTML report |
| `impact_report_YYYY-MM-DD_HH-MM-SS.json` | Raw data in JSON format |
| `impact_report_YYYY-MM-DD_HH-MM-SS.xlsx` | Excel spreadsheet |
| `patterns_YYYY-MM-DD_HH-MM-SS.json` | Pattern groupings |
| `impact_report_YYYY-MM-DD_HH-MM-SS.log` | Execution log |

## Charts / Stakeholder Images

- The reporting pipeline now emits percentage statistics in the JSON (`percentage_stats`) alongside `data` and `patterns`.
- To generate shareable PNG charts (bar charts for top patterns and a summary pie chart), use the bundled script `json_to_charts.py`.

Install the chart dependency and run the script (from repository root):

```powershell
pip install -r untils_automation/py/pattern_report/requirements.txt
python untils_automation/py/pattern_report/json_to_charts.py untils_automation/py/pattern_report/out.json
```

- Replace `out.json` with the actual `impact_report_*.json` produced by the tool (see `logs/`).
- By default charts are written to a `charts/` folder next to the JSON; use `--outdir` to override and `--top N` to change the number of top patterns displayed.

Example output files created by the script:

- `charts/ref_numbered_top10.png` — Top 10 numbered-reference patterns by percentage
- `charts/figtab_top10.png` — Top 10 figure/table patterns
- `charts/summary_distribution.png` — Pie chart of pattern distribution across categories

## Report Structure

### 1. 📊 Overall Report
- **Consolidated Pattern Match Summary** - Visual box showing best match % for each category
- **Stats Cards** - Per-category cards showing:
  - Best Pattern Match percentage
  - Total Journals count
  - Total Patterns count
  - Top Pattern name
- Summary of all configurations grouped by Books/Journals
- Filter by type (All / Journals / Books)
- Reference summary by category (Numbered/Unnumbered/Footnote)

### 2. 📚 Reference Pattern Tab
Comparison grid showing patterns side-by-side with percentage badges:
```
┌──────────────────────┬──────────────────────────────────┬──────────────────────────────────┐
│ Attribute            │ ref_numbered_pattern_1           │ ref_numbered_pattern_2           │
│                      │ (7 journals) [45.5%] ★ MAX       │ (3 journals) [19.5%]             │
├──────────────────────┼───────────────┬──────────────────┼───────────────┬──────────────────┤
│                      │ Value         │ Journals         │ Value         │ Journals         │
├──────────────────────┼───────────────┼──────────────────┼───────────────┼──────────────────┤
│ dircite.double_sep   │ ,             │ J1_LWW...        │ ;             │ J2_LWW...        │
│ dircite.openwrap     │ [             │ J1_LWW...        │ ⊘ empty       │ J2_LWW...        │
└──────────────────────┴───────────────┴──────────────────┴───────────────┴──────────────────┘
```

### 3. 📈 Figure/Table Pattern Tab
Same comparison grid for Figure and Table patterns with percentage statistics.

### 4. 🏷️ Part Label Pattern Tab
Patterns for part label attributes (prefix_num, case, format, double_sep).

### 5. 🎯 Unique Pattern Tab
List of all unique patterns found for each attribute across all journals.

### 6. 🔍 Pattern Compare Tab
Highlights anomalies (patterns with <3 journals) and compares against common patterns.

### 7. 🧪 Unit Test Suggestion Tab (NEW)
Intelligent test coverage analysis:

#### Overall Minimum Test Set
- Uses **greedy set cover algorithm** to find optimal journal selection
- Shows minimum journals needed for 100% pattern coverage
- Visual coverage meter

#### Per-Category Suggestions
For each category (Numbered Ref, Unnumbered Ref, Footnote, Figure/Table, Part Labels):
- Total patterns count
- Minimum journals needed
- Recommended journals with coverage percentage
- Expandable pattern coverage details

#### Client-Level Recommendations
- Journals grouped by client
- Highlighted recommended journals from minimum test set
- Pattern coverage count per journal

#### Coverage Summary Table
| Category | Total Patterns | Min Journals | Efficiency |
|----------|----------------|--------------|------------|
| Numbered Ref | 5 | 3 | 1.7x |
| Figure/Table | 8 | 4 | 2.0x |
| **TOTAL** | **25** | **8** | **3.1x** |

## Percentage Match System

Each pattern displays a percentage badge indicating its match ratio:

| Badge | Color | Meaning |
|-------|-------|---------|
| **High** (≥50%) | 🟢 Green | Pattern covers majority of journals |
| **Medium** (25-50%) | 🟡 Yellow | Moderate coverage |
| **Low** (<25%) | 🔴 Red | Limited coverage, may be unique case |

## Configuration

Edit `report_config.py` to customize:

```python
# Attributes to extract from Figure/Table
LABEL_ATTRS = ["part_lab_prefix_num", "part_lab_case", "part_lab_double_sep", "text-format"]
CITE_ATTRS = ["double_sep", "range_sep", "openwrap", "closewrap"]

# Reference-specific attributes
REF_ATTRS = ["data-label-format", "text-format"]
REF_CITATION_ATTRS = ["type"]

# Sections to analyze
SECTION_TAGS = ["Figure", "Table", "Reference"]
```

## Pattern Naming Convention

| Pattern Type | Naming Format |
|-------------|---------------|
| Numbered References | `ref_numbered_pattern_1`, `ref_numbered_pattern_2`, ... |
| Unnumbered References | `ref_unnumbered_pattern_1`, `ref_unnumbered_pattern_2`, ... |
| Footnote References | `ref_footnote_pattern_1`, `ref_footnote_pattern_2`, ... |
| Figure/Table | `figtab_pattern_1`, `figtab_pattern_2`, ... |
| Part Label (Figure) | `partlab_figure_pattern_1`, `partlab_figure_pattern_2`, ... |
| Part Label (Table) | `partlab_table_pattern_1`, `partlab_table_pattern_2`, ... |

## Journal Naming Format

Journals are displayed as: `JOURNAL_CLIENT`
- Example: `EJGH_LWW`, `MD_LWW`, `EDE_TNF`

## Special Value Indicators

| Value | Display |
|-------|---------|
| Empty string `""` | `⊘ empty` |

## File Structure

```
pattern_report/
├── __init__.py
├── report_main.py       # Entry point
├── report_config.py     # Configuration settings
├── report_extract.py    # XML parsing and data extraction
├── report_patterns.py   # Pattern building logic
├── report_template.py   # HTML report generation
├── report_writer.py     # Output file writers (JSON, HTML, Excel)
├── report_log.py        # Logging utility
├── README.md            # This file
├── requirements.txt     # Python dependencies
└── logs/                # Generated reports (auto-created)
```

## Requirements

- Python 3.7+
- lxml
- openpyxl
 - matplotlib (for `json_to_charts.py`)

## Changelog

### v1.2.0 (2025-12-05)
- ✨ Added **Unit Test Suggestion** tab with minimum coverage analysis
- ✨ Added greedy set cover algorithm for optimal journal selection
- ✨ Added client-level test recommendations
- ✨ Added coverage efficiency metrics

### v1.1.0 (2025-12-05)
- ✨ Added **Percentage Match** statistics for each pattern
- ✨ Added **Consolidated Summary Box** in Overall Report
- ✨ Added **Stats Cards** grid with per-category metrics
- ✨ Added visual percentage badges (high/medium/low)

### v1.0.0
- Initial release with pattern detection and HTML report

## License

Internal tool for IMPACT project.

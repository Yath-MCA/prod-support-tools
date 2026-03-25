# Patterns Module

Journal Patterns Reporter - Analyzes XML configuration files for common patterns.

## Features

- Glob-based file discovery
- XML element and attribute extraction
- Pattern signature analysis
- Multi-format output (HTML, JSON, Excel)
- Configurable client filtering

## Dependencies

```
lxml>=4.9.0
openpyxl>=3.1.0
matplotlib>=3.6.0
```

## Usage

```bash
# Via GUI (patterns_tab.py)
python main.py
# Select "Patterns" tab

# Via command line
python -m patterns.report_main
```

## Configuration

Edit `patterns/report_config.py`:
```python
CLIENTCONFIG_DIR = "path/to/clientconfig"
SEARCH_PATTERN = "**/config.xml"
IGNORE_CLIENTS = ["OUP"]  # Clients to skip
```

## Output Files

| File | Description |
|------|-------------|
| `impact_report_<ts>.html` | Main HTML report |
| `impact_report_<ts>.json` | Raw data export |
| `impact_report_<ts>.xlsx` | Excel audit file |
| `patterns_<ts>.json` | Pattern index |

## Patterns Analyzed

- Figure labels and formatting
- Table labels and formatting
- Reference labels and citations
- Part labels and section markers
- Cite attributes (separators, ranges)

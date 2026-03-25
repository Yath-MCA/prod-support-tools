# CJK Integrity Checker

Character Integrity Verification Tool for CJK (Chinese/Japanese/Korean) documents.

## Features

- Original vs Revised document comparison
- Multi-domain support (PROD, UAT, LOCAL, DEV)
- HTML report generation
- JSON and CSV export
- Custom file comparison mode

## Dependencies

```
requests>=2.28.0
beautifulsoup4>=4.11.0
lxml>=4.9.0
```

## Usage

```bash
python main.py
# Select "CJK Integrity" tab

# Or standalone
python -m cjk_checker.main
```

## Configuration

Edit `cjk_checker/config.json`:

```json
{
  "timeout": 30,
  "domains": {
    "PROD": {
      "original_url": "https://server/api/original/{doc_id}",
      "revised_url": "https://server/api/revised/{doc_id}"
    }
  },
  "default_domain": "UAT"
}
```

## Compare Modes

### Default Mode

Uses configured URLs with `unique_id + domain` resolution.

### Custom Mode

Manually select local HTML files:
- Original file picker
- Revised file picker
- No network required

## Output Reports

Saved to `cjk_checker/reports/`:

| File | Description |
|------|-------------|
| `report_<doc_id>.html` | Visual comparison report |
| `report_<doc_id>.json` | Structured data |
| `report_<doc_id>.csv` | Spreadsheet-compatible |

## Report Contents

- Side-by-side text comparison
- Character-level diff highlighting
- Summary statistics
- Integrity status indicators

# IMPACT Config Suite GUI

## Run Common GUI

```bash
python main.py
```

This opens the merged common GUI with tabs, including `CJK Integrity`.

### Compare Tab Inputs

- `Unique ID` (required)
- `Domain` selector: `PROD`, `UAT`, `LOCAL`, `DEV`
- Compare mode:
  - `Default (Original vs Revised by Unique ID)`
  - `Custom HTML Files` (manual file pick for original/revised)

### Compare Modes

1. Default mode
 - Uses `unique_id + domain` to resolve original/revised URLs from `cjk_checker/config.json`.

2. Custom mode
 - Uses selected local HTML files for Original and Revised content.
 - No network fetch required.

## Run CJK Checker Only

```bash
python -m cjk_checker.main
```

## CJK Checker Outputs

Reports are generated under:

`untils_automation/py/impact_config_suite/cjk_checker/reports/`

For each doc ID, these files are created:

- `report_<doc_id>.html`
- `report_<doc_id>.json`
- `report_<doc_id>.csv`

## Configuration

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

Install required packages if needed:

```bash
pip install requests beautifulsoup4 lxml
```

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

Output:

- `dist/IMPACT_ConfigSuite_v5.0.exe`

### Build with legacy references

If existing tooling refers to the old path `build/impact_suite`, build with legacy mode:

```bat
build_exe.bat common legacy
```

or

```powershell
.\build_exe.ps1 -Target common -Clean -LegacyRefs
```

This additionally updates:

- `build/impact_suite/` (legacy build-work reference)
- `dist/IMPACT_ConfigSuite_v3.0.exe` (legacy EXE alias)

### Build CJK-only EXE

```bat
build_exe.bat cjk
```

or

```powershell
.\build_exe.ps1 -Target cjk -Clean
```

Output:

- `dist/IMPACT_CJK_Integrity_Checker.exe`

### Build CJK with legacy references

If old tooling expects a stable CJK alias/build path:

```bat
build_exe.bat cjk legacy
```

or

```powershell
.\build_exe.ps1 -Target cjk -Clean -LegacyRefs
```

This additionally updates:

- `build/impact_cjk_suite/` (legacy CJK build-work reference)
- `dist/IMPACT_CJK_Integrity_Checker_v1.0.exe` (legacy CJK EXE alias)

### Notes

- Script auto-detects workspace virtual environment Python when available.
- `cjk_checker/config.json` and `cjk_checker/templates/report_template.html` are bundled into the EXE.
- First build can take several minutes.


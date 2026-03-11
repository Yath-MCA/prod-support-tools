# Recovered Python Project (from IMPACT_ConfigSuite_v4.0.exe)

This folder contains Python code and assets extracted from:
- `dist/IMPACT_ConfigSuite_v4.0.exe`

## What is recovered
- Plain `.py` source files: 30
- Search service static/template assets recovered:
  - `search_service/app/static/css/style.css`
  - `search_service/app/static/js/app.js`
  - `search_service/app/templates/index.html`
- Requirements files recovered:
  - `search_service/requirements.txt`
  - `patterns/requirements.txt`
- Bytecode-only main entry disassembly:
  - `main_disassembly.txt`

## Quick Run
1. Create/activate a Python env in this folder.
2. Install dependencies for search service:
   - `pip install -r search_service/requirements.txt`
3. Start FastAPI service:
  - `python -m search_service.run`
  - or `start_search_service.bat`
4. Open browser:
   - `http://127.0.0.1:7000/ui`

## Patterns module run
- `start_patterns_report.bat`

## Notes
- EXE `main` entry was packaged as bytecode and could not be directly decompiled to exact original `.py` here.
- See `main_disassembly.txt` for opcode-level reconstruction aid.

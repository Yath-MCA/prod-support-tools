# Prompt: Build a Python GUI Tool for CJK Character Integrity Comparison

## Objective

Create a professional Python desktop application that compares **Original vs Revised HTML documents** for **CJK character integrity**.
The goal is to ensure **no CJK characters are lost or introduced without proper tracking** (`<ins>` / `<del>`).

The tool must generate a **clear HTML QA report** showing differences.

---

# Input Workflow

User provides:

* `unique_doc_id`

The application should:

1. Read configuration from `config.json`
2. Construct URLs using the `unique_doc_id`
3. Fetch **Original HTML** and **Revised HTML** from the configured endpoints.

Example config:

```json
{
  "original_url": "https://server/api/original/{doc_id}",
  "revised_url": "https://server/api/revised/{doc_id}",
  "timeout": 30
}
```

Example final URLs:

```
https://server/api/original/ABC123
https://server/api/revised/ABC123
```

---

# Required Python Libraries

Use the following stack:

* requests
* beautifulsoup4
* lxml
* difflib
* tkinter (GUI)
* re
* pathlib
* webbrowser

Optional enhancements:

* pandas
* jinja2 (HTML template rendering)

---

# CJK Detection Rules

Detect CJK characters using Unicode ranges:

* CJK Unified Ideographs
* CJK Extensions
* Compatibility Ideographs

Regex:

```
[\u4E00-\u9FFF\u3400-\u4DBF]
```

OR preferred modern approach:

```
\p{Script=Han}
```

Count only **actual characters**, not punctuation.

Exclude:

```
\u3000-\u303F
```

---

# Comparison Rules

Compare Original vs Revised HTML and detect:

| Case             | Meaning                            |
| ---------------- | ---------------------------------- |
| OK               | Character unchanged                |
| Inserted         | New character introduced           |
| Deleted          | Character removed                  |
| Tracked Insert   | Character inside `<ins>`           |
| Tracked Delete   | Character inside `<del>`           |
| Untracked Change | Character changed without tracking |

Important rule:

> No CJK character should be lost or introduced without `<ins>` or `<del>` tracking.

---

# HTML Parsing

Steps:

1. Parse HTML using **BeautifulSoup + lxml**
2. Traverse DOM elements
3. Extract text nodes
4. Identify nodes containing CJK characters
5. Map element path

Example path:

```
body > div[2] > p[3] > span[1]
```

---

# Diff Engine

Use:

```
difflib.SequenceMatcher
```

Perform **character-level comparison**.

Highlight:

* Insertions
* Deletions
* Replacements

But only report **CJK characters**.

---

# Report Requirements

Generate a **professional HTML report**.

Output file:

```
report_<doc_id>.html
```

Layout:

### Header

* Document ID
* Original URL
* Revised URL
* Timestamp
* Summary counts

Example summary:

```
Total CJK characters (Original): 421
Total CJK characters (Revised): 422

Inserted: 2
Deleted: 1
Tracked Insert: 1
Tracked Delete: 0
Untracked Changes: 2
```

---

# Report Table Layout

Side-by-side comparison:

| Element Path | Original | Revised | Status |
| ------------ | -------- | ------- | ------ |

Example:

| body > p[3] | 中 | 中 | OK |
| body > p[4] | 文 | — | Deleted |
| body > p[6] | — | 字 | Inserted |
| body > p[8] | 学 | `<ins>学</ins>` | Tracked Insert |

---

# Highlight Colors

Use CSS:

```
Inserted → green
Deleted → red
Tracked Insert → blue
Tracked Delete → orange
Untracked Change → purple
```

Example:

```
<span class="inserted">字</span>
```

---

# Navigation Features

Add report navigation:

### Sidebar

Links to:

```
All
Inserted
Deleted
Tracked
Untracked
```

Clicking filters table rows.

---

# GUI Application

Build a **simple desktop GUI** using `tkinter`.

Window layout:

```
--------------------------------
CJK Integrity Checker
--------------------------------

Document ID: [____________]

[ Fetch & Compare ]

--------------------------------
Status Log
--------------------------------
Fetching original HTML...
Fetching revised HTML...
Comparing characters...
Report generated.

[ Open Report ]
--------------------------------
```

Features:

* Input field for doc_id
* Button to start comparison
* Progress messages
* Button to open generated report
* Error display

---

# Extra Features (Nice to Have)

Add these enhancements if possible:

### 1. DOM Navigation

Allow clicking a row to show:

```
Full Original HTML snippet
Full Revised HTML snippet
```

### 2. Character Index

Show index of the character in the node.

### 3. Download Raw Data

Export CSV or JSON report.

### 4. Statistics Dashboard

Charts showing:

* Inserted count
* Deleted count
* Tracked changes

### 5. Performance Optimization

Support documents up to **10MB HTML**.

---

# Folder Structure

```
cjk_checker/
│
├ config.json
├ main.py
├ fetcher.py
├ parser.py
├ diff_engine.py
├ report_generator.py
├ gui.py
│
├ templates/
│   report_template.html
│
└ reports/
```

---

# Expected Output

A working Python application where:

1. User enters `doc_id`
2. HTML content is fetched automatically
3. CJK comparison runs
4. A professional HTML report is generated
5. GUI allows easy navigation and report viewing

---

# Deliverables

The final code should include:

* Fully working Python scripts
* Config file
* HTML template
* Instructions to run

Example command:

```
python main.py
```

The GUI window should open.

---

# Implementation Status (Completed)

Implemented under:

`untils_automation/py/impact_config_suite/`

Key files delivered:

- `tools_app.py` (common GUI merger)
- `main.py` (common GUI launcher)
- `cjk_checker/fetcher.py`
- `cjk_checker/parser.py`
- `cjk_checker/diff_engine.py`
- `cjk_checker/report_generator.py`
- `cjk_checker/exporter.py`
- `cjk_checker/pipeline.py`
- `cjk_checker/gui.py`
- `cjk_checker/main.py`
- `cjk_checker/config.json`
- `cjk_checker/templates/report_template.html`

Generated outputs per document ID:

- `report_<doc_id>.html`
- `report_<doc_id>.json`
- `report_<doc_id>.csv`

---

# EXE Build Scripts Added

Windows build scripts:

- `build_exe.ps1`
- `build_exe.bat`

Build common GUI EXE:

```bat
build_exe.bat common
```

Build CJK-only EXE:

```bat
build_exe.bat cjk
```

Output EXEs:

- `dist/IMPACT_ConfigSuite_v5.0.exe`
- `dist/IMPACT_CJK_Integrity_Checker.exe`

Legacy compatibility option:

- `build_exe.bat common legacy`

This keeps old references valid by updating:

- `build/impact_suite/`
- `dist/IMPACT_ConfigSuite_v3.0.exe`


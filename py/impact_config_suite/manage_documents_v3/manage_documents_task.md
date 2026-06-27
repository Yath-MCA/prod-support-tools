# AI Development Guide - Document Manager Integration

## Project Overview

This is an enhancement to an **existing Python GUI application**. The goal is **not** to create a new project, but to integrate a reusable **Document Manager** module into the current codebase.

The existing application already performs XML comparison and HTML report generation. The Document Manager will become the foundation for all file management and workflow execution.

---

# Primary Objectives

Implement a document management layer that:

* Scans project folders.
* Organizes document files.
* Downloads missing configuration XML files.
* Maintains a single JSON database.
* Provides common APIs for all future modules.
* Allows interrupted processing to resume.
* Integrates seamlessly with the existing GUI.

---

# Important

Do **NOT** rewrite or redesign the existing GUI.

Do **NOT** change the current XML comparison logic unless required.

Instead:

* reuse existing dialogs
* reuse logging
* reuse progress bar
* reuse threading
* reuse configuration handling
* reuse settings
* reuse report generation

The Document Manager should be an independent module that plugs into the current application.

---

# Single Source of Truth

Every document must exist inside one JSON file.

Example:

```json
{
  "N12345": {
    "docid": "N12345",
    "folder": "N12345",

    "files": {
      "original_html": "N12345/N12345.html",
      "original_xml": "N12345/N12345_original.xml",
      "updated_html": "N12345/N12345_updated.html",
      "config_xml": "N12345/impact_config.xml",
      "compare_report": null
    },

    "process": {
      "organized": true,
      "config_downloaded": true,
      "compared": false,
      "report_generated": false
    },

    "error": null
  }
}
```

No module should scan folders again.

Every module must read from this JSON.

---

# Processing Modes

Implement these modes.

## Scan

Read

```
originalhtml/
originalxml/
updatedhtmlfiles/
```

Build documents.json.

No files are moved.

---

## Folder

Read documents.json.

Move files into

```
Project/

    Nxxxxx/

        Nxxxxx.html

        Nxxxxx_original.xml

        Nxxxxx_updated.html
```

Update JSON paths.

---

## Download XML

Read documents.json.

Download

```
https://backend.company.co/IMPACT/<docid>/impact_config.xml
```

Save as

```
Nxxxxx/

    impact_config.xml
```

Update JSON.

Support:

* configurable delay
* retry
* timeout

Do not download if already exists unless user forces overwrite.

---

## Compare

Read JSON.

For every document

```
original XML

updated HTML

impact_config.xml
```

Run existing comparison engine.

Generate report.

Update JSON.

---

## Report

Generate

* HTML summary
* CSV
* Excel

using existing reporting code.

---

# Required Folder Structure

```
Project

    documents.json

    process.log

    N0001

    N0002

    N0003
```

Each document folder contains

```
html

original xml

updated html

impact_config.xml

report.html
```

---

# GUI Requirements

Reuse existing GUI.

Add one new tab

```
Document Manager
```

Buttons

```
Scan

Organize

Download Config

Compare

Generate Report

Complete Workflow
```

Progress bar should update after each document.

Current log window should display progress.

---

# Configuration

Move all configurable values into one location.

Examples

```
BASE_URL

DOWNLOAD_DELAY

HTTP_TIMEOUT

MAX_RETRIES

THREAD_COUNT

OUTPUT_FOLDER
```

No hardcoded paths.

---

# Logging

Use existing logging system.

Every action should be logged.

Examples

```
Scanning

Moving

Downloading

Comparing

Generating Report

Completed

Failed
```

---

# Resume Support

If processing stops

Restart

Continue from

documents.json

Skip completed items.

---

# Error Handling

Each document stores

```
error

last_step

retry_count
```

Processing continues even if one document fails.

---

# Code Organization

Create reusable classes instead of long scripts.

Example

```
DocumentDatabase

FolderOrganizer

ConfigDownloader

DocumentScanner

CompareManager

ReportManager
```

GUI only calls these classes.

Business logic should never be inside GUI code.

---

# Future Extensions

Design so additional modules can be added easily.

Examples

```
Validation

Cleanup

Statistics

Export

Packaging

Cloud Upload

Diff Viewer

AI Summary
```

without changing the existing architecture.

---

# Coding Standards

* Python 3.11+
* Type hints where practical
* Small reusable methods
* Avoid duplicated code
* Centralize file operations
* Centralize JSON operations
* Centralize logging
* Use pathlib instead of os.path
* Keep GUI responsive using existing threading implementation

---

# Expected Result

The existing GUI becomes the central application.

The new Document Manager module provides:

* reliable document database
* resumable workflow
* reusable APIs
* scalable architecture
* maintainable codebase

All future processing modules should depend on `documents.json` instead of repeatedly scanning the filesystem.

# IMPACT XML Config Editor

A comprehensive GUI tool for editing IMPACT input package XML configurations.

## Features

### Core Functionality
- **Package Browser**: Select and browse input package folders
- **XML Configuration Editor**: Edit journal configuration XML files
- **Contributor Management**: Manage author and contributor information
- **Preview System**: Real-time preview of changes

### Workflow System
- 4-stage workflow tracking:
  1. Select Package
  2. Configure Settings
  3. Create Archive
  4. SFTP Upload

### Operations
- **Archive Creation**: Package configuration into ZIP archives
- **SFTP Upload**: Upload packages to remote servers
- **Auto Upload**: Optional automatic upload after archive creation

### UI Features
- Themed interface using ttkthemes (with fallback to standard tkinter)
- Progress indicators for workflow stages
- Loading animations
- Branding images support

## Dependencies

```
tkinter
Pillow>=9.0.0
ttkthemes>=0.3.0  # Optional, falls back to standard theme
```

Core modules required:
- `core.config_loader`
- `core.xml_processor`
- `core.file_manager`

## Usage

### As Standalone Application
```bash
python editor_app.py
```

### As Tab in Common Tools
The `XMLConfigEditor` class can be instantiated with `is_tab=True` for embedding in notebook tabs.

```python
from editor_app import XMLConfigEditor

# As a tab
editor = XMLConfigEditor(parent=notebook, is_tab=True)
notebook.add(editor, text="XML Editor")
```

## Configuration

The editor uses the core module configuration system. Settings are stored in:
- `Documents/IMPACT_ConfigSuite/config/`

## Workflow Stages

| Stage | Description |
|-------|-------------|
| stage1 | Package Selection |
| stage2 | Configuration Settings |
| stage3 | Archive Creation |
| stage4 | SFTP Upload |

## Notes

This module was reconstructed from bytecode analysis of IMPACT_ConfigSuite_v4.0.exe.
Some implementation details may differ from the original compiled version.

"""
Deep search for editor_app.py in EXE strings
"""

import re
import os


def extract_all_strings(filepath, min_len=6):
    """Extract all printable strings from binary file."""
    strings = []
    current = bytearray()

    with open(filepath, "rb") as f:
        data = f.read()

    for byte in data:
        if 32 <= byte <= 126:  # Printable ASCII
            current.append(byte)
        else:
            if len(current) >= min_len:
                try:
                    s = current.decode("ascii")
                    strings.append(s)
                except:
                    pass
            current = bytearray()

    return strings


def main():
    exe_path = "D:/PERSONAL/LIVE_PROJECTS/prod-support-tools/py/archive/impact_config_editor/dist/IMPACT_INPUT_PACKAGE_XML_EDITOR_V1.2.exe"

    print(f"Extracting strings...")
    strings = extract_all_strings(exe_path, min_len=6)
    print(f"Found {len(strings)} strings\n")

    # Search for editor patterns
    print("=" * 60)
    print("SEARCHING FOR EDITOR_APP RELATED CONTENT")
    print("=" * 60)

    editor_terms = [
        "editor",
        "Editor",
        "EDITOR",
        "XMLConfig",
        "ConfigEditor",
        "validate",
        "Validate",
        "validation",
        "workflow",
        "Workflow",
        "WF",
        "import",
        "export",
        "Export",
        "Import",
        "tree",
        "Tree",
        "Node",
        "node",
        "canvas",
        "Canvas",
        "scroll",
        "Scroll",
        "text",
        "Text",
        "entry",
        "Entry",
        "button",
        "Button",
        "widget",
        "Widget",
        "frame",
        "Frame",
        "window",
        "Window",
        "menu",
        "Menu",
        "context",
        "Context",
    ]

    for term in editor_terms:
        matches = [s for s in strings if term in s]
        if matches:
            print(f"\n'{term}': {len(matches)} matches")
            for m in matches[:3]:
                if len(m) > 80:
                    m = m[:80] + "..."
                print(f"  {m}")

    # Look for file paths that might indicate source structure
    print("\n" + "=" * 60)
    print("SOURCE FILE PATHS")
    print("=" * 60)

    for s in strings:
        if ".py" in s or ".pyc" in s:
            print(s[:100])

    # Look for specific editor_app references
    print("\n" + "=" * 60)
    print("LOOKING FOR editor_app.py")
    print("=" * 60)

    for s in strings:
        if "editor_app" in s.lower() or "xml_config_editor" in s.lower():
            print(s)


if __name__ == "__main__":
    main()

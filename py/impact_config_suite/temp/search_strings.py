"""
Search for strings in EXE that might reveal editor_app.py content
"""

import re
import os


def extract_strings(filepath, min_len=8):
    """Extract printable strings from binary file."""
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


def search_for_editor_content(strings):
    """Search for editor-related content."""

    # Keywords to search
    keywords = [
        "XMLConfigEditor",
        "editor_app",
        "editor",
        "validate",
        "validation",
        "workflow",
        "import",
        "def ",
        "class ",
        "tkinter",
        "ttk",
        "tk",
        "XML",
        "xml",
        "element",
        "Element",
    ]

    results = {}
    for keyword in keywords:
        matches = [s for s in strings if keyword.lower() in s.lower()]
        if matches:
            results[keyword] = matches[:20]  # Limit to 20 matches

    return results


def find_source_code_snippets(strings):
    """Look for Python source code patterns."""

    python_patterns = []

    for s in strings:
        # Look for Python-like patterns
        if any(
            pattern in s
            for pattern in [
                "def ",
                "class ",
                "import ",
                "from ",
                "self.",
                "__init__",
                "__main__",
                ".py",
                "import tkinter",
                "import ttk",
            ]
        ):
            python_patterns.append(s)

    return python_patterns


def main():
    exe_path = "D:/PERSONAL/LIVE_PROJECTS/prod-support-tools/py/archive/impact_config_editor/dist/IMPACT_INPUT_PACKAGE_XML_EDITOR_V1.2.exe"

    print(f"Extracting strings from {exe_path}...")
    strings = extract_strings(exe_path, min_len=10)
    print(f"Found {len(strings)} strings\n")

    # Search for editor content
    print("=" * 60)
    print("EDITOR-RELATED CONTENT")
    print("=" * 60)

    results = search_for_editor_content(strings)

    for keyword, matches in results.items():
        print(f"\n--- '{keyword}' ({len(matches)} matches) ---")
        for m in matches[:5]:
            if len(m) > 100:
                m = m[:100] + "..."
            print(f"  {m}")

    # Look for Python source patterns
    print("\n" + "=" * 60)
    print("PYTHON SOURCE PATTERNS")
    print("=" * 60)

    patterns = find_source_code_snippets(strings)
    for p in patterns[:30]:
        if len(p) > 80:
            p = p[:80] + "..."
        print(f"  {p}")


if __name__ == "__main__":
    main()

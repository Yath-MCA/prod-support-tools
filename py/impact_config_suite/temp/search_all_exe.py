"""
Search for editor_app in all EXE files
"""

import os


def search_in_file(filepath):
    """Search for editor_app references in binary file."""
    with open(filepath, "rb") as f:
        data = f.read()

    patterns = [
        b"editor_app",
        b"XMLConfigEditor",
        b"xml_config_editor",
        b"ConfigEditor",
    ]

    results = []
    for pattern in patterns:
        if pattern in data:
            # Find position and context
            pos = data.find(pattern)
            context_start = max(0, pos - 20)
            context_end = min(len(data), pos + len(pattern) + 20)
            context = data[context_start:context_end]

            # Try to decode as ASCII
            try:
                context_str = context.decode("ascii")
                context_str = context_str.replace("\x00", " ")
            except:
                context_str = repr(context)

            results.append(
                {"pattern": pattern.decode(), "position": pos, "context": context_str}
            )

    return results


def main():
    exe_dir = "D:/PERSONAL/LIVE_PROJECTS/prod-support-tools/py/archive/impact_config_editor/dist"

    print("Searching for editor_app in all EXE files...\n")

    for filename in os.listdir(exe_dir):
        if filename.endswith(".exe"):
            filepath = os.path.join(exe_dir, filename)
            size = os.path.getsize(filepath) / (1024 * 1024)
            print(f"Checking: {filename} ({size:.1f} MB)")

            results = search_in_file(filepath)

            if results:
                print(f"  FOUND editor_app references!")
                for r in results:
                    print(f"    - {r['pattern']} at position {r['position']}")
                    print(f"      Context: {r['context'][:80]}")
            else:
                print(f"  No editor_app references found")


if __name__ == "__main__":
    main()

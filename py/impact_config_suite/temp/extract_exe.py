import struct
import os
import sys
import zlib
import marshal
import types


def extract_pyinstaller_exe(exe_path, output_dir):
    """Extract Python bytecode from PyInstaller EXE."""

    with open(exe_path, "rb") as f:
        data = f.read()

    # Find the PyInstaller magic bytes
    MAGIC = b"PYZ\x00"

    # Find all PYZ sections
    pyz_sections = []
    pos = 0
    while True:
        idx = data.find(MAGIC, pos)
        if idx == -1:
            break
        pyz_sections.append(idx)
        pos = idx + 1

    print(f"Found {len(pyz_sections)} PYZ sections at positions: {pyz_sections[:5]}...")

    # Try to find Python structures
    # Look for marshal.loads patterns

    # Check for embedded .pyz or bytecode
    if len(data) > 50000000:  # EXE is likely PyInstaller
        print("Large EXE file - attempting extraction...")

        # Try to find and extract CArchive
        # PyInstaller stores data in a CArchive format

        # Find signature
        SIG = b"MEI\x00\x00\x00"  # MEI signature for PyInstaller

        archives = []
        pos = 0
        while True:
            idx = data.find(SIG, pos)
            if idx == -1:
                break
            archives.append(idx)
            pos = idx + 1

        print(f"Found {len(archives)} potential archive markers")

    # Alternative: Look for pyc files embedded
    # Pyc header is 16 bytes: magic (4), flags (4), timestamp (4), size (4)
    PYC_MAGIC = b"\x61\x0d\x0d\x0d"  # Python 3.13 magic (varies)

    print("\nSearching for embedded Python bytecode...")

    # Try to find and decode marshal data
    # Python 3.11+ uses marshal for frozen imports

    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_exe.py <path_to_exe>")
        sys.exit(1)

    exe_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "extracted"

    os.makedirs(output_dir, exist_ok=True)

    result = extract_pyinstaller_exe(exe_path, output_dir)

    if result:
        print(f"Extracted {len(result)} files to {output_dir}")
    else:
        print("Could not extract - file may be packed differently")

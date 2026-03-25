import struct
import os
import sys
import zlib
import marshal
from pathlib import Path


def extract_from_pyinstaller(data):
    """Manually extract from PyInstaller archive."""

    # PyInstaller header constants
    MAGIC = b"MEI\x00\x00\x00\x01\x00\x00\x00"

    # Find all occurrences of the magic
    positions = []
    pos = 0
    while True:
        idx = data.find(MAGIC, pos)
        if idx == -1:
            break
        positions.append(idx)
        pos = idx + 1

    print(f"Found {len(positions)} MEI markers")

    # Python 3.13 PyInstaller - try to find marshalled data
    # Look for the PKG marker (second-stage bootloader)

    PKG_MARKER = b"PKG\x00"
    pkg_pos = data.find(PKG_MARKER)
    print(f"PKG marker at: {pkg_pos}")

    # Try to find and extract pyz data
    PYZ_MARKER = b"PYZ\x00"
    pyz_positions = []
    pos = 0
    while True:
        idx = data.find(PYZ_MARKER, pos)
        if idx == -1:
            break
        pyz_positions.append(idx)
        pos = idx + 1

    print(f"PYZ markers at: {pyz_positions[:5]}...")

    # Try to extract using zlib
    for i, pyz_pos in enumerate(pyz_positions[:3]):
        print(f"\nAttempting PYZ extraction at position {pyz_pos}...")

        # Try different starting points around the marker
        for offset in range(-1000, 1000, 100):
            start = pyz_pos + offset
            if start < 0:
                continue
            try:
                # Try decompressing
                test_data = data[start : start + 500000]
                try:
                    decompressed = zlib.decompress(test_data)
                    print(
                        f"  Offset {offset}: Successfully decompressed {len(decompressed)} bytes"
                    )

                    # Look for marshal data in decompressed
                    # Marshal data starts with certain patterns
                    for mpos in range(0, len(decompressed), 1000):
                        chunk = decompressed[mpos : mpos + 100]
                        if len(chunk) > 16:
                            # Check for pyc magic in various versions
                            magics = [
                                b"\x61\x0d\x0d\x0d",  # 3.13
                                b"\xa7\x0d\x0d\x0d",  # 3.12
                                b"\x55\x0d\x0d\x0d",  # 3.11
                                b"\x0f\x0d\x0d\x0d",  # 3.10
                            ]
                            for magic in magics:
                                if chunk.startswith(magic):
                                    print(
                                        f"    Found pyc magic at relative offset {mpos}"
                                    )
                except:
                    pass
            except:
                pass

    return None


if __name__ == "__main__":
    exe_path = "D:/PERSONAL/LIVE_PROJECTS/prod-support-tools/py/archive/impact_config_editor/dist/IMPACT_INPUT_PACKAGE_XML_EDITOR_V1.2.exe"

    print(f"Reading {exe_path}...")
    with open(exe_path, "rb") as f:
        data = f.read()

    print(f"File size: {len(data):,} bytes")

    result = extract_from_pyinstaller(data)

    if result:
        print(f"\nExtracted files: {len(result)}")
    else:
        print("\nManual extraction not successful")

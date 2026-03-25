"""
PyInstaller Archive Parser
Extracts Python modules from PyInstaller onefile/bundle archives
"""

import struct
import os
import sys
import zlib
import marshal
from pathlib import Path


def find_sections(data):
    """Find various PyInstaller markers."""

    markers = {
        "MEI": b"MEI\x00\x00\x00\x01",
        "PKG": b"PKG\x00",
        "PYZ": b"PYZ\x00",
        "PYZ2": b"PYZ\x01",
        "PYZ_MAGIC": b"\x00\x00\x00\x00",
        "STRUCT": b"\x00\x00\x00\x00\x00\x00\x00\x00",
    }

    results = {}
    for name, marker in markers.items():
        positions = []
        pos = 0
        while True:
            idx = data.find(marker, pos)
            if idx == -1:
                break
            positions.append(idx)
            pos = idx + 1
        if positions:
            results[name] = positions[:5]  # First 5 only
            print(f"{name}: {len(positions)} occurrences at {positions[:3]}...")

    return results


def extract_pyz(data, position):
    """Try to extract PYZ (zlib compressed) section."""
    print(f"\nAttempting PYZ extraction at position {position}")

    # PYZ section typically starts with the marker followed by metadata
    # Then comes zlib compressed Python code objects

    # Try to find the start of zlib data
    for start_offset in range(0, 200, 10):
        test_start = position + start_offset
        if test_start + 100 > len(data):
            break

        # Try decompressing from various offsets
        for size in [100000, 500000, 1000000]:
            if test_start + size > len(data):
                continue
            try:
                test_data = data[test_start : test_start + size]
                dc = zlib.decompress(test_data)
                print(
                    f"  Offset {start_offset}, size {size}: SUCCESS - {len(dc)} bytes"
                )

                # Now parse the marshalled data
                parse_marshalled(dc, f"pyz_offset_{start_offset}")

                return dc
            except Exception as e:
                pass

    return None


def parse_marshalled(data, prefix):
    """Parse marshalled Python code objects."""
    print(f"  Parsing {len(data)} bytes of marshalled data...")

    pos = 0
    count = 0

    while pos < len(data) - 20 and count < 10:
        # Look for pyc headers
        # Python 3.13 pyc header: magic (4) + flags (4) + timestamp (4) + size (4) = 16 bytes
        if pos + 16 > len(data):
            break

        magic = data[pos : pos + 4]
        flags = struct.unpack("<I", data[pos + 4 : pos + 8])[0]

        # Check for valid magic numbers
        valid_magics = [
            b"\x61\x0d\x0d\x0d",  # 3.13
            b"\xa7\x0d\x0d\x0d",  # 3.12
            b"\x55\x0d\x0d\x0d",  # 3.11
            b"\x0f\x0d\x0d\x0d",  # 3.10
            b"\x33\x0d\x0d\x0d",  # 3.9
            b"\x42\x0d\x0d\x0d",  # 3.8
        ]

        if magic in valid_magics:
            size = struct.unpack("<I", data[pos + 12 : pos + 16])[0]
            print(f"  Found pyc at offset {pos}: magic={magic.hex()}, size={size}")

            # Try to unmarshal
            try:
                code = marshal.loads(data[pos + 16 :])
                print(f"    Code object: {type(code).__name__}")
                if hasattr(code, "co_name"):
                    print(f"    Name: {code.co_name}")
                count += 1
            except:
                pass

        pos += 1


def main():
    exe_path = "D:/PERSONAL/LIVE_PROJECTS/prod-support-tools/py/archive/impact_config_editor/dist/IMPACT_INPUT_PACKAGE_XML_EDITOR_V1.2.exe"

    print(f"Reading {exe_path}...")
    with open(exe_path, "rb") as f:
        data = f.read()

    print(f"File size: {len(data):,} bytes ({len(data) / 1024 / 1024:.1f} MB)\n")

    sections = find_sections(data)

    if "PYZ" in sections:
        for pos in sections["PYZ"][:2]:
            extract_pyz(data, pos)


if __name__ == "__main__":
    main()

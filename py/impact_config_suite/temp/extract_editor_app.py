"""
Extract editor_app.pyc from IMPACT_ConfigSuite_v4.0.exe
"""

import struct
import zlib
import marshal
import os


def find_pyz_section(data):
    """Find the PYZ (zlib compressed) section."""
    PYZ_MAGIC = b"PYZ\x00"

    positions = []
    pos = 0
    while True:
        idx = data.find(PYZ_MAGIC, pos)
        if idx == -1:
            break
        positions.append(idx)
        pos = idx + 1

    print(f"Found {len(positions)} PYZ markers")
    return positions


def extract_pyz_content(data, pyz_pos):
    """Extract and decompress PYZ section."""
    print(f"\nPYZ section at position: {pyz_pos}")

    # Try to find the start of compressed data
    # PYZ typically starts with metadata, then zlib compressed marshal data

    # Look for zlib magic bytes (78 9C or 78 DA)
    ZLIB_MAGIC = b"\x78\x9c"

    for offset in range(0, 5000, 100):
        test_start = pyz_pos + offset
        if test_start + 4 > len(data):
            break

        # Check if this looks like zlib data
        if data[test_start : test_start + 2] in [b"\x78\x9c", b"\x78\xda", b"\x78\x01"]:
            print(f"Found zlib header at offset {offset} from PYZ marker")

            # Try to decompress
            try:
                test_data = data[test_start : test_start + 5000000]  # Up to 5MB
                decompressed = zlib.decompress(test_data)
                print(f"Successfully decompressed {len(decompressed):,} bytes")

                # Look for marshal data
                return decompressed, test_start
            except Exception as e:
                pass

    return None, None


def find_marshal_data(data):
    """Find marshal-formatted Python code objects."""
    print("\nSearching for marshal data...")

    # Try to unmarshal various positions
    for pos in range(0, len(data) - 100, 1000):
        try:
            # Check if this position has marshal data
            # Marshal format starts with type codes
            type_code = data[pos]

            # Valid marshal type codes start with specific values
            valid_starts = [
                0x63,
                0x65,
                0x66,
                0x69,
                0x6E,
                0x73,
                0x74,
                0x7D,
                0xC0,
                0xE0,
                0xF0,
            ]
            # 'c'=99 object, 'e'=101 code, 'f'=102 frozenset, 'i'=105 int
            # 'n'=110 set, 's'=115 str, 't'=116 tuple, '}'=125 dict
            # 0xc0+ extended

            if type_code in valid_starts or (type_code >= 0xC0 and type_code < 0xF0):
                try:
                    obj = marshal.loads(data[pos:])
                    obj_type = type(obj).__name__
                    print(f"Found marshal at position {pos}: {obj_type}")

                    if hasattr(obj, "co_name"):
                        print(f"  Code object name: {obj.co_name}")
                    if hasattr(obj, "__name__"):
                        print(f"  Module name: {obj.__name__}")

                except:
                    pass
        except:
            pass

    return None


def main():
    exe_path = "D:/PERSONAL/LIVE_PROJECTS/prod-support-tools/py/impact_config_suite/dist/IMPACT_ConfigSuite_v4.0.exe"

    print(f"Reading {exe_path}...")
    with open(exe_path, "rb") as f:
        data = f.read()

    print(f"File size: {len(data):,} bytes\n")

    # Find PYZ sections
    pyz_positions = find_pyz_section(data)

    if pyz_positions:
        for pyz_pos in pyz_positions[:2]:
            decompressed, start_pos = extract_pyz_content(data, pyz_pos)

            if decompressed:
                find_marshal_data(decompressed)

                # Try to find editor_app specifically
                if b"editor_app" in decompressed:
                    print("\nFOUND editor_app in decompressed data!")
                    pos = decompressed.find(b"editor_app")
                    print(f"Position: {pos}")
                else:
                    print("\neditor_app NOT found in this section")
                    # Try with partial match
                    if b"editor" in decompressed:
                        count = decompressed.count(b"editor")
                        print(f"Found 'editor' {count} times")
                        pos = decompressed.find(b"editor")
                        print(f"First occurrence at: {pos}")


if __name__ == "__main__":
    main()

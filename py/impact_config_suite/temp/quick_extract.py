"""
Quick extraction of editor_app from ConfigSuite v4.0
"""

import struct
import os


def extract_pyz_toc(data, pyz_pos):
    """Extract PYZ table of contents."""
    print(f"PYZ at: {pyz_pos}")

    # The PYZ section contains:
    # - Magic bytes (4)
    # - Python modules (marshalled tuples of (name, data))
    # Each module is: (name_str, marshalled_code_object)

    # Try different offsets from the PYZ marker
    for offset in [0, 4, 8, 12, 16, 20]:
        start = pyz_pos + offset
        print(f"\nTrying offset {offset}...")

        # Try to find marshalled data
        # Python marshal type codes
        try:
            import marshal

            # Try to unmarshal starting from various points
            for sub_offset in range(0, 500, 50):
                test_start = start + sub_offset
                if test_start + 100 > len(data):
                    break

                try:
                    obj = marshal.loads(data[test_start:])
                    obj_type = type(obj).__name__

                    if hasattr(obj, "__name__"):
                        name = obj.__name__
                    elif hasattr(obj, "co_name"):
                        name = obj.co_name
                    else:
                        name = str(obj)[:50]

                    print(f"  Offset {sub_offset}: {obj_type} - {name}")

                    # Check if it's editor_app
                    if "editor" in name.lower():
                        print(f"\n*** FOUND: {name} ***")

                except:
                    pass

        except Exception as e:
            pass


def main():
    exe_path = "D:/PERSONAL/LIVE_PROJECTS/prod-support-tools/py/impact_config_suite/dist/IMPACT_ConfigSuite_v4.0.exe"

    print("Reading EXE...")
    with open(exe_path, "rb") as f:
        data = f.read()

    print(f"Size: {len(data):,} bytes\n")

    # Find PYZ
    pyz_pos = data.find(b"PYZ\x00")
    print(f"PYZ marker at: {pyz_pos}")

    if pyz_pos > 0:
        extract_pyz_toc(data, pyz_pos)


if __name__ == "__main__":
    main()

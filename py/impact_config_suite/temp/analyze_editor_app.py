"""
Analyze editor_app.pyc using disassembly
"""

import marshal
import dis
import inspect


def analyze_pyc(pyc_path):
    """Analyze and disassemble a .pyc file."""

    with open(pyc_path, "rb") as f:
        data = f.read()

    # Skip the 16-byte header
    code = marshal.loads(data[16:])

    print("=" * 60)
    print("EDITOR_APP.PYC ANALYSIS")
    print("=" * 60)

    print(f"\nTop-level code object: {code.co_name}")
    print(f"Filename: {code.co_filename}")
    print(f"Arguments: {code.co_varnames[: code.co_argcount]}")
    print(f"Local variables: {code.co_varnames}")
    print(f"Constants: {len(code.co_consts)} items")
    print(f"Names used: {code.co_names}")

    print("\n" + "-" * 60)
    print("CODE OBJECTS (Classes and Functions)")
    print("-" * 60)

    for const in code.co_consts:
        if isinstance(const, type(code)):
            print(f"\nClass/Function: {const.co_name}")
            print(f"  Arguments: {const.co_varnames[: const.co_argcount]}")
            print(f"  Variables: {const.co_varnames}")
            print(f"  Constants: {len(const.co_consts)}")
            print(f"  Names: {const.co_names}")

            # Look for string constants that might be docstrings or messages
            for c in const.co_consts:
                if isinstance(c, str) and len(c) > 10:
                    if any(
                        word in c.lower()
                        for word in [
                            "xml",
                            "editor",
                            "validate",
                            "save",
                            "load",
                            "open",
                            "file",
                            "config",
                        ]
                    ):
                        print(f"    String: {c[:100]}...")

    print("\n" + "-" * 60)
    print("DISASSEMBLY (Top Level)")
    print("-" * 60)

    dis.dis(code)


if __name__ == "__main__":
    pyc_path = "D:/PERSONAL/LIVE_PROJECTS/prod-support-tools/pyinstxtractor-master/IMPACT_ConfigSuite_v4.0.exe_extracted/PYZ.pyz_extracted/editor_app.pyc"
    analyze_pyc(pyc_path)

from __future__ import annotations

import argparse
import json
import marshal
import os
import subprocess
import sys
import types
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader


def sanitize_name(name: str) -> str:
    # Keep package-like structure while preventing invalid path segments.
    return name.replace("..", "__").replace("\\", "/").strip("/")


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def as_bytes(blob: object) -> bytes:
    if isinstance(blob, bytes):
        return blob
    if isinstance(blob, bytearray):
        return bytes(blob)
    if isinstance(blob, types.CodeType):
        return marshal.dumps(blob)
    return bytes(blob)


def extract_archive(exe_path: Path, output_dir: Path) -> tuple[Path, Path, Path, list[dict[str, str]]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    pyc_dir = output_dir / "pyc"
    pyz_dir = output_dir / "pyz"
    raw_dir.mkdir(parents=True, exist_ok=True)
    pyc_dir.mkdir(parents=True, exist_ok=True)
    pyz_dir.mkdir(parents=True, exist_ok=True)

    arch = CArchiveReader(str(exe_path))
    manifest: list[dict[str, str]] = []

    for name, toc in arch.toc.items():
        pos, dlen, ulen, compressed, typecode = toc
        out_name = sanitize_name(name)
        ext = ".pyc" if typecode in ("m", "M", "s") else ".bin"
        dest = (pyc_dir if ext == ".pyc" else raw_dir) / f"{out_name}{ext}"

        try:
            blob = arch.extract(name)
            write_bytes(dest, as_bytes(blob))
            status = "ok"
            err = ""
        except Exception as exc:  # pragma: no cover - best effort extraction
            status = "error"
            err = str(exc)

        manifest.append(
            {
                "name": name,
                "typecode": str(typecode),
                "compressed": str(compressed),
                "stored_len": str(dlen),
                "uncompressed_len": str(ulen),
                "status": status,
                "error": err,
                "output": str(dest.relative_to(output_dir)) if status == "ok" else "",
            }
        )

    # Extract modules packed in embedded PYZ archives where most .py modules live.
    for name, toc in arch.toc.items():
        _pos, _dlen, _ulen, _compressed, typecode = toc
        if typecode != "z":
            continue
        try:
            embedded = arch.open_embedded_archive(name)
        except Exception as exc:
            manifest.append(
                {
                    "name": name,
                    "typecode": "z",
                    "compressed": "",
                    "stored_len": "",
                    "uncompressed_len": "",
                    "status": "error",
                    "error": f"open_embedded_archive failed: {exc}",
                    "output": "",
                }
            )
            continue

        for mod_name in embedded.toc.keys():
            safe_mod = sanitize_name(mod_name).replace(".", "/")
            dest = pyz_dir / f"{safe_mod}.pyc"
            try:
                blob = embedded.extract(mod_name)
                write_bytes(dest, as_bytes(blob))
                status = "ok"
                err = ""
            except Exception as exc:
                status = "error"
                err = str(exc)

            manifest.append(
                {
                    "name": f"{name}:{mod_name}",
                    "typecode": "zmod",
                    "compressed": "",
                    "stored_len": "",
                    "uncompressed_len": "",
                    "status": status,
                    "error": err,
                    "output": str(dest.relative_to(output_dir)) if status == "ok" else "",
                }
            )

    return raw_dir, pyc_dir, pyz_dir, manifest


def decompile_pyc(pyc_dirs: list[Path], decompiled_dir: Path) -> tuple[int, int, str]:
    decompiled_dir.mkdir(parents=True, exist_ok=True)
    pyc_files: list[Path] = []
    for folder in pyc_dirs:
        if folder.exists():
            pyc_files.extend(sorted(folder.rglob("*.pyc")))
    if not pyc_files:
        return 0, 0, "No .pyc files found"

    try:
        import decompyle3  # noqa: F401
    except Exception:
        return 0, len(pyc_files), "decompyle3 not installed"

    success = 0
    for pyc in pyc_files:
        rel = None
        for root in pyc_dirs:
            try:
                rel = pyc.relative_to(root)
                break
            except ValueError:
                continue
        if rel is None:
            rel = Path(pyc.name)

        target = decompiled_dir / rel.with_suffix(".py")
        target.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable,
            "-m",
            "decompyle3.main",
            "-o",
            str(target.parent),
            str(pyc),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0 and target.exists():
            success += 1
        elif proc.returncode == 0:
            # Some versions place output with default naming inside dir.
            generated = list(target.parent.glob("*.py"))
            if generated:
                success += 1

    return success, len(pyc_files), "decompile attempted"


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover contents from a PyInstaller EXE")
    parser.add_argument("exe", help="Path to EXE")
    parser.add_argument("--out", default="recovered", help="Output directory")
    parser.add_argument("--decompile", action="store_true", help="Try decompiling .pyc with decompyle3")
    args = parser.parse_args()

    exe = Path(args.exe).resolve()
    out = Path(args.out).resolve()
    if not exe.exists():
        print(f"EXE not found: {exe}")
        return 1

    raw_dir, pyc_dir, pyz_dir, manifest = extract_archive(exe, out)
    summary = {
        "exe": str(exe),
        "output": str(out),
        "total_entries": len(manifest),
        "ok_entries": sum(1 for m in manifest if m["status"] == "ok"),
        "error_entries": sum(1 for m in manifest if m["status"] != "ok"),
        "pyc_files": len(list(pyc_dir.rglob("*.pyc"))),
        "pyz_module_files": len(list(pyz_dir.rglob("*.pyc"))),
        "raw_files": len(list(raw_dir.rglob("*"))),
    }

    if args.decompile:
        dec_dir = out / "decompiled"
        dec_ok, dec_total, dec_msg = decompile_pyc([pyc_dir, pyz_dir], dec_dir)
        summary["decompile"] = {
            "status": dec_msg,
            "success": dec_ok,
            "total": dec_total,
            "dir": str(dec_dir),
        }

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import os
import subprocess
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DEFAULT_DECOMPILER = "pycdc.exe"
DEFAULT_OUTPUT_FOLDER = "recovered_code"
DEFAULT_WORKERS = 4


def find_pyc_files(root_dir):
    pyc_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if f.endswith(".pyc"):
                pyc_files.append(os.path.join(dirpath, f))
    return pyc_files


def get_relative_path(pyc_path, base_dir):
    rel = os.path.relpath(pyc_path, base_dir)
    return rel.replace(".pyc", ".py").replace(os.sep, "_")


def decompile_file(pyc_path, output_folder, decompiler, base_dir):
    output_name = get_relative_path(pyc_path, base_dir)
    output_path = os.path.join(output_folder, output_name)

    if os.path.exists(output_path):
        return f"SKIP (exists): {pyc_path}"

    print(f"Decompiling {pyc_path}...")
    try:
        with open(output_path, "w", encoding="utf-8", errors="replace") as f:
            subprocess.run([decompiler, pyc_path], stdout=f, check=True, timeout=300)
        return f"OK: {pyc_path}"
    except subprocess.TimeoutExpired:
        return f"TIMEOUT: {pyc_path}"
    except Exception as e:
        return f"ERROR ({type(e).__name__}): {pyc_path}"


def main():
    parser = argparse.ArgumentParser(description="Batch decompile .pyc files")
    parser.add_argument(
        "path", nargs="?", default=".", help="Directory to search for .pyc files"
    )
    parser.add_argument(
        "-o", "--output", default=DEFAULT_OUTPUT_FOLDER, help="Output folder"
    )
    parser.add_argument(
        "-d", "--decompiler", default=DEFAULT_DECOMPILER, help="Decompiler executable"
    )
    parser.add_argument(
        "-w", "--workers", type=int, default=DEFAULT_WORKERS, help="Parallel workers"
    )
    parser.add_argument(
        "-r", "--recursive", action="store_true", default=True, help="Recursive search"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show files without decompiling"
    )

    args = parser.parse_args()

    if not os.path.exists(args.output):
        os.makedirs(args.output)

    pyc_files = find_pyc_files(args.path)

    if not pyc_files:
        print("No .pyc files found!")
        return

    print(f"Found {len(pyc_files)} .pyc file(s)")

    if args.dry_run:
        for f in pyc_files:
            print(f)
        return

    results = {"ok": 0, "skip": 0, "error": 0, "timeout": 0}

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                decompile_file, f, args.output, args.decompiler, args.path
            ): f
            for f in pyc_files
        }

        for future in as_completed(futures):
            result = future.result()
            print(result)
            if result.startswith("OK"):
                results["ok"] += 1
            elif result.startswith("SKIP"):
                results["skip"] += 1
            elif result.startswith("TIMEOUT"):
                results["timeout"] += 1
            else:
                results["error"] += 1

    print(
        f"\nDone! Results: {results['ok']} OK, {results['skip']} skipped, "
        f"{results['timeout']} timeout, {results['error']} errors"
    )
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()

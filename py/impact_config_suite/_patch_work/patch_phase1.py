# -*- coding: utf-8 -*-
"""Apply EE batch-wise progressive JSON patches."""
from pathlib import Path
import re

ROOT = Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"FAIL: marker not found for {label}")
    return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# 1) core/element_extractor.py — constant + scan_directory_parallel batching
# ---------------------------------------------------------------------------
ee_path = ROOT / "core" / "element_extractor.py"
ee = ee_path.read_text(encoding="utf-8")

if "EE_SCAN_BATCH_SIZE" not in ee:
    ee = replace_once(
        ee,
        "except ImportError:\n    pass\n\nclass ElementExtractor:",
        "except ImportError:\n    pass\n\n"
        "# File-chunk size for progressive parallel scans (by_docid / partials cadence).\n"
        "EE_SCAN_BATCH_SIZE = 250\n\n"
        "class ElementExtractor:",
        "add EE_SCAN_BATCH_SIZE",
    )

old_sig = '''    def scan_directory_parallel(self, dir_path: Path, query_type: str, query_val: str,
                               attr_name: str = "", attr_val: str = "",
                               extensions: list = None, filename_filter: str = None,
                               dtd_filter: str = None, client_filter: str = None,
                               month_filter: str = "All Time", custom_month: str = "",
                               batch_size: int = 0, batch_offset: int = 0,
                               max_workers: int = None, progress_callback=None,
                               recursive: bool = True, use_index: bool = True, log_callback=None,
                               file_result_callback=None):
        """
        Parallel directory scanning using ProcessPoolExecutor for 3-4x speedup on multi-core machines.

        Args:
            dir_path: Root directory path to scan
            query_type: Type of query ("Tag Name", "CSS Selector", "XPath")
            query_val: Query value to search for
            attr_name: Attribute name filter (for Tag Name queries)
            attr_val: Attribute value filter (for Tag Name queries)
            extensions: List of file extensions to scan (default: ['.xml', '.html', '.htm', '.xhtml'])
            filename_filter: Filename pattern filter
            dtd_filter: DTD type filter (requires impact_config.xml)
            client_filter: Client name filter (requires impact_config.xml)
            month_filter: Month filter ("All Time", "This Month", "Last Month", "Custom")
            custom_month: Custom month string when month_filter is "Custom"
            batch_size: Number of folders to process (0 means no batch limit)
            batch_offset: Number of folders to skip (for resuming)
            max_workers: Number of parallel processes (default: min(CPU count, 8))
            progress_callback: Optional callback(current, total, filename) for progress updates
            recursive: Whether to scan subdirectories recursively (default: True)
            file_result_callback: Optional callback(file_path_str, result_dict) on main thread
                as each worker result arrives (for progressive by_docid writes).

        Returns:
            Tuple of (scan_results, total_matches, total_files, has_more, next_offset)
            - scan_results: Dict of file_path -> {"ok": bool, "matches": list, "error": str}
            - total_matches: Total number of matching elements found
            - total_files: Number of files processed
            - has_more: True if there are more folders to process after this batch
            - next_offset: Offset to use for the next batch (if has_more is True)
        """'''

new_sig = '''    def scan_directory_parallel(self, dir_path: Path, query_type: str, query_val: str,
                               attr_name: str = "", attr_val: str = "",
                               extensions: list = None, filename_filter: str = None,
                               dtd_filter: str = None, client_filter: str = None,
                               month_filter: str = "All Time", custom_month: str = "",
                               batch_size: int = 0, batch_offset: int = 0,
                               max_workers: int = None, progress_callback=None,
                               recursive: bool = True, use_index: bool = True, log_callback=None,
                               file_result_callback=None,
                               file_batch_size: int = None,
                               batch_done_callback=None):
        """
        Parallel directory scanning using ProcessPoolExecutor for 3-4x speedup on multi-core machines.

        When more than ``file_batch_size`` files are collected (default
        ``EE_SCAN_BATCH_SIZE`` = 250), work is submitted and completed in
        file-chunks so callers can flush progressive artifacts after each chunk.

        Args:
            dir_path: Root directory path to scan
            query_type: Type of query ("Tag Name", "CSS Selector", "XPath")
            query_val: Query value to search for
            attr_name: Attribute name filter (for Tag Name queries)
            attr_val: Attribute value filter (for Tag Name queries)
            extensions: List of file extensions to scan (default: ['.xml', '.html', '.htm', '.xhtml'])
            filename_filter: Filename pattern filter
            dtd_filter: DTD type filter (requires impact_config.xml)
            client_filter: Client name filter (requires impact_config.xml)
            month_filter: Month filter ("All Time", "This Month", "Last Month", "Custom")
            custom_month: Custom month string when month_filter is "Custom"
            batch_size: Number of folders to process (0 means no batch limit)
            batch_offset: Number of folders to skip (for resuming)
            max_workers: Number of parallel processes (default: min(CPU count, 8))
            progress_callback: Optional callback(current, total, filename) for progress updates
            recursive: Whether to scan subdirectories recursively (default: True)
            file_result_callback: Optional callback(file_path_str, result_dict) on main thread
                as each worker result arrives (for progressive by_docid writes).
            file_batch_size: Max files per parallel chunk (default EE_SCAN_BATCH_SIZE).
                Use 0 to submit all files in one shot (legacy behaviour).
            batch_done_callback: Optional callback(batch_index, batch_files, batch_results_summary)
                invoked on the main thread after each file chunk completes.

        Returns:
            Tuple of (scan_results, total_matches, total_files, has_more, next_offset)
            - scan_results: Dict of file_path -> {"ok": bool, "matches": list, "error": str}
            - total_matches: Total number of matching elements found
            - total_files: Number of files processed
            - has_more: True if there are more folders to process after this batch
            - next_offset: Offset to use for the next batch (if has_more is True)
        """'''

ee = replace_once(ee, old_sig, new_sig, "scan_directory_parallel signature")

old_loop = '''        total_files = len(all_files)

        # Process files in parallel
        scan_results = {}
        total_matches = 0
        processed_count = 0

        # Use ProcessPoolExecutor for parallel processing
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self._process_single_file,
                              file_path, query_type, query_val,
                              attr_name, attr_val): file_path
                for file_path in all_files
            }

            # Collect results as they complete (main thread: safe for progressive store writes)
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                processed_count += 1
                abs_key = str(file_path.absolute())

                try:
                    result = future.result()  # No timeout - allow slow files to complete
                    if result:
                        scan_results[abs_key] = result
                        if result.get("ok") and result.get("matches"):
                            total_matches += len(result["matches"])
                    else:
                        result = {"ok": False, "error": "empty worker result", "matches": []}
                        scan_results[abs_key] = result
                except Exception as e:
                    result = {
                        "ok": False,
                        "error": str(e),
                        "matches": []
                    }
                    scan_results[abs_key] = result

                if file_result_callback is not None:
                    try:
                        file_result_callback(abs_key, scan_results[abs_key])
                    except Exception:
                        pass

                # Report progress every 5 files
                if progress_callback and processed_count % 5 == 0:
                    progress_callback(processed_count, total_files, file_path.name)

        # Final progress callback if not already reported
        if progress_callback and total_files > 0 and processed_count % 5 != 0:
            progress_callback(processed_count, total_files, all_files[-1].name if all_files else "")

        return scan_results, total_matches, total_files, has_more, next_offset'''

new_loop = '''        total_files = len(all_files)

        # Process files in parallel (chunked when file count exceeds file_batch_size)
        scan_results = {}
        total_matches = 0
        processed_count = 0
        callback_error_logged = False
        batch_callback_error_logged = False

        if file_batch_size is None:
            file_batch_size = EE_SCAN_BATCH_SIZE
        try:
            file_batch_size = int(file_batch_size)
        except (TypeError, ValueError):
            file_batch_size = EE_SCAN_BATCH_SIZE
        # 0 => legacy single-submit of the entire file list
        if file_batch_size <= 0:
            chunk_size = total_files or 1
        else:
            chunk_size = file_batch_size

        if log_callback and total_files > chunk_size:
            try:
                log_callback(
                    f"  Parallel file batching: {total_files} file(s) in chunks of {chunk_size}"
                )
            except Exception:
                pass

        def _invoke_file_callback(abs_key, result_dict):
            nonlocal callback_error_logged
            if file_result_callback is None:
                return
            try:
                file_result_callback(abs_key, result_dict)
            except Exception as exc:
                if not callback_error_logged:
                    callback_error_logged = True
                    msg = f"file_result_callback error (further errors suppressed): {exc}"
                    if log_callback:
                        try:
                            log_callback(msg)
                        except Exception:
                            pass
                    else:
                        print(msg)

        def _invoke_batch_done(batch_index, batch_files, summary):
            nonlocal batch_callback_error_logged
            if batch_done_callback is None:
                return
            try:
                batch_done_callback(batch_index, batch_files, summary)
            except Exception as exc:
                if not batch_callback_error_logged:
                    batch_callback_error_logged = True
                    msg = f"batch_done_callback error (further errors suppressed): {exc}"
                    if log_callback:
                        try:
                            log_callback(msg)
                        except Exception:
                            pass
                    else:
                        print(msg)

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            batch_index = 0
            for chunk_start in range(0, total_files or 1 if all_files else 0, chunk_size):
                batch_files = all_files[chunk_start:chunk_start + chunk_size]
                if not batch_files:
                    break
                batch_index += 1
                batch_hit_files = 0
                batch_matches = 0
                batch_file_summaries = []

                future_to_file = {
                    executor.submit(
                        self._process_single_file,
                        file_path, query_type, query_val,
                        attr_name, attr_val,
                    ): file_path
                    for file_path in batch_files
                }

                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    processed_count += 1
                    abs_key = str(file_path.absolute())

                    try:
                        result = future.result()  # No timeout - allow slow files to complete
                        if result:
                            scan_results[abs_key] = result
                            if result.get("ok") and result.get("matches"):
                                total_matches += len(result["matches"])
                        else:
                            result = {"ok": False, "error": "empty worker result", "matches": []}
                            scan_results[abs_key] = result
                    except Exception as e:
                        result = {
                            "ok": False,
                            "error": str(e),
                            "matches": []
                        }
                        scan_results[abs_key] = result

                    hit_count = 0
                    if result.get("ok") and result.get("matches"):
                        hit_count = len(result["matches"])
                        batch_matches += hit_count
                        batch_hit_files += 1

                    batch_file_summaries.append({
                        "path": abs_key,
                        "docid": file_path.parent.name,
                        "name": file_path.name,
                        "ok": bool(result.get("ok", True)),
                        "hit_count": hit_count,
                        "error": str(result.get("error", "") or ""),
                    })

                    _invoke_file_callback(abs_key, scan_results[abs_key])

                    if progress_callback and processed_count % 5 == 0:
                        progress_callback(processed_count, total_files, file_path.name)

                summary = {
                    "batch_index": batch_index,
                    "chunk_size": chunk_size,
                    "files_in_batch": len(batch_files),
                    "files_completed_total": processed_count,
                    "files_total": total_files,
                    "matches_in_batch": batch_matches,
                    "files_with_hits": batch_hit_files,
                    "files": batch_file_summaries,
                }
                _invoke_batch_done(
                    batch_index,
                    [str(p) for p in batch_files],
                    summary,
                )

        # Final progress callback if not already reported
        if progress_callback and total_files > 0 and processed_count % 5 != 0:
            progress_callback(processed_count, total_files, all_files[-1].name if all_files else "")

        return scan_results, total_matches, total_files, has_more, next_offset'''

ee = replace_once(ee, old_loop, new_loop, "scan_directory_parallel loop")

# Also log once in scan_bibr_citations callback swallow
old_bibr_cb = '''                if file_result_callback is not None and abs_key in scan_results:
                    try:
                        file_result_callback(abs_key, scan_results[abs_key])
                    except Exception:
                        pass
            return scan_results, total_matches, total_files'''

# Only replace if unique - check count
if ee.count(old_bibr_cb) == 1:
    ee = replace_once(
        ee,
        old_bibr_cb,
        '''                if file_result_callback is not None and abs_key in scan_results:
                    try:
                        file_result_callback(abs_key, scan_results[abs_key])
                    except Exception as exc:
                        # Log once so progressive writers are not silently broken
                        if not getattr(_scan_list, "_cb_err_logged", False):
                            _scan_list._cb_err_logged = True
                            if log_callback:
                                try:
                                    log_callback(
                                        f"file_result_callback error (further errors suppressed): {exc}"
                                    )
                                except Exception:
                                    pass
            return scan_results, total_matches, total_files''',
        "bibr callback log",
    )

ee_path.write_text(ee, encoding="utf-8")
print("Patched element_extractor.py")


# ---------------------------------------------------------------------------
# 2) core/ee_report_store.py — progress + batch partial helpers
# ---------------------------------------------------------------------------
store_path = ROOT / "core" / "ee_report_store.py"
store = store_path.read_text(encoding="utf-8")

store = replace_once(
    store,
    '''        self.by_docid_dir = self.run_folder / "by_docid"
        # Legacy alias — P0 no longer uses partials/
        self.partials_dir = self.run_folder / "partials"
        self._files: list[dict] = []
        self._writes_since_flush = 0
        self._last_flush_monotonic = time.monotonic()
        self._dirty = False
        self._last_status = "running"
        self._last_stats: dict = {}
''',
    '''        self.by_docid_dir = self.run_folder / "by_docid"
        # Used again for progressive scan batch JSON (partials/batch_NNNN.json)
        self.partials_dir = self.run_folder / "partials"
        self._files: list[dict] = []
        self._writes_since_flush = 0
        self._last_flush_monotonic = time.monotonic()
        self._dirty = False
        self._last_status = "running"
        self._last_stats: dict = {}
        # Files observed by progressive upsert (includes zero-hit skips)
        self._files_scanned = 0
        self._batch_manifest: dict = {
            "batches_completed": 0,
            "files_completed": 0,
            "batches": [],
        }
''',
    "store init scanned/manifest",
)

# Insert helpers after match_stats
store = replace_once(
    store,
    '''    def match_stats(self) -> tuple[int, int]:
        """Return (files_with_hits, bucket_rows) from in-memory records."""
        files_with = sum(1 for r in self._files if r.get("ok") and r.get("matches"))
        bucket_rows = sum(len(r.get("matches") or []) for r in self._files if r.get("ok"))
        return files_with, bucket_rows
''',
    '''    def match_stats(self) -> tuple[int, int]:
        """Return (files_with_hits, bucket_rows) from in-memory records."""
        files_with = sum(1 for r in self._files if r.get("ok") and r.get("matches"))
        bucket_rows = sum(len(r.get("matches") or []) for r in self._files if r.get("ok"))
        return files_with, bucket_rows

    def note_file_scanned(self) -> int:
        """Increment processed-file counter (including zero-hit files). Return new count."""
        self._files_scanned = int(getattr(self, "_files_scanned", 0) or 0) + 1
        return self._files_scanned

    def maybe_flush_progress(self, *, status: str, stats: dict | None = None) -> Path | None:
        """Flush index for progress visibility even when no new by_docid writes occurred.

        Flushes when dirty and (N writes or interval), OR when ``files_done`` is a
        multiple of ``flush_every``, OR when the flush interval elapsed since last flush.
        """
        if stats is not None:
            self._last_stats = dict(stats)
        due_writes = self._dirty and self._writes_since_flush >= self.flush_every
        due_t = (time.monotonic() - self._last_flush_monotonic) >= self.flush_interval_s
        done = int((stats or self._last_stats or {}).get("files_done") or 0)
        due_scanned = done > 0 and (done % self.flush_every == 0)
        if due_writes or (self._dirty and due_t) or due_scanned or (due_t and stats is not None):
            return self.flush_index(status=status, stats=stats if stats is not None else self._last_stats)
        return None

    def write_batch_partial(self, batch_index: int, summary: dict) -> Path:
        """Write ``partials/batch_NNNN.json`` for one completed file chunk."""
        self.partials_dir.mkdir(parents=True, exist_ok=True)
        idx = int(batch_index)
        path = self.partials_dir / f"batch_{idx:04d}.json"
        payload = dict(summary or {})
        payload.setdefault("batch_index", idx)
        # Enrich hit rows with result_ref when the by_docid record already exists
        path_to_ref = {
            str(r.get("path") or ""): r.get("result_ref")
            for r in self._files
            if r.get("result_ref")
        }
        files_out = []
        for entry in list(payload.get("files") or []):
            row = dict(entry)
            ref = path_to_ref.get(str(row.get("path") or ""))
            if ref and int(row.get("hit_count") or 0) > 0:
                row["result_ref"] = ref
            files_out.append(row)
        payload["files"] = files_out
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        # Keep a slim running manifest of completed batches (no mega merged matches)
        batches = list(self._batch_manifest.get("batches") or [])
        batches = [b for b in batches if int(b.get("index") or 0) != idx]
        batches.append({
            "index": idx,
            "path": f"partials/batch_{idx:04d}.json",
            "files": int(payload.get("files_in_batch") or len(files_out)),
            "hits": int(payload.get("matches_in_batch") or 0),
            "files_with_hits": int(payload.get("files_with_hits") or 0),
        })
        batches.sort(key=lambda b: int(b.get("index") or 0))
        self._batch_manifest = {
            "source_path": self.source_path,
            "kind": self.kind,
            "scan_batch_size": int(payload.get("chunk_size") or 0) or None,
            "batches_completed": len(batches),
            "files_completed": int(payload.get("files_completed_total") or 0),
            "files_total": int(payload.get("files_total") or 0),
            "batches": batches,
        }
        manifest_path = self.run_folder / "manifest.json"
        # Preserve any pre-existing keys (e.g. dtd_filter) when present
        existing: dict = {}
        if manifest_path.is_file():
            try:
                existing = json.loads(manifest_path.read_text(encoding="utf-8"))
                if not isinstance(existing, dict):
                    existing = {}
            except Exception:
                existing = {}
        existing.update(self._batch_manifest)
        manifest_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        return path
''',
    "store progress/batch helpers",
)

store_path.write_text(store, encoding="utf-8")
print("Patched ee_report_store.py")

print("OK phase1")

# -*- coding: utf-8 -*-
"""Patch element_extractor_tab for zero-hit progress + batch_done wiring."""
from pathlib import Path

ROOT = Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite")
tab_path = ROOT / "tabs" / "element_extractor_tab.py"
tab = tab_path.read_text(encoding="utf-8")


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"FAIL: marker not found for {label}\n--- snip ---\n{old[:200]}")
    return text.replace(old, new, 1)


# Update import to also pull EE_SCAN_BATCH_SIZE
tab = replace_once(
    tab,
    "from core.element_extractor import ElementExtractor\n",
    "from core.element_extractor import EE_SCAN_BATCH_SIZE, ElementExtractor\n",
    "import EE_SCAN_BATCH_SIZE",
)

old_upsert = '''    def _extract_live_upsert_file(
        self,
        store: EEReportStore,
        file_path_str: str,
        data: dict,
        query_val: str,
        query_type: str,
        *,
        open_report: bool = False,
        report_path: str | Path | None = None,
        files_total: int = 0,
    ) -> None:
        """Merge one extract file result into the live store and write by_docid (main thread)."""
        if store is None:
            return
        fp = Path(file_path_str)
        abs_path = str(fp.absolute())
        docid = fp.parent.name
        fid = f"{docid}_{fp.name}"
        matches_out = [
            self._extract_match_payload(m, query_val, query_type)
            for m in (data.get("matches") or [])
        ]
        ok = bool(data.get("ok", True))
        err = str(data.get("error", "") or "")
        # Skip empty successful files (matches detailed-report focus)
        if ok and not matches_out:
            return

        existing = None
        for rec in store._files:
            if _safe_id_local(str(rec.get("id") or "")) == _safe_id_local(fid) or rec.get("id") == fid:
                existing = rec
                break
        if existing is None:
            # also match by path
            for rec in store._files:
                if str(rec.get("path") or "") == abs_path:
                    existing = rec
                    break

        if existing is not None:
            if not ok:
                existing["ok"] = False
                existing["error"] = err or existing.get("error", "")
            existing.setdefault("matches", []).extend(matches_out)
            # rebuild query_breakdown
            breakdown = {}
            for m in existing["matches"]:
                qv = str(m.get("query_val") or "")
                breakdown[qv] = breakdown.get(qv, 0) + 1
            existing["query_breakdown"] = breakdown
            lines = [m.get("line") for m in existing["matches"] if m.get("line") not in (None, "")]
            existing["lines_preview"] = lines[:10]
            store.write_result(existing)
        else:
            try:
                meta = self.extractor.get_file_metadata(fp)
            except Exception:
                meta = {}
            breakdown = {}
            for m in matches_out:
                qv = str(m.get("query_val") or "")
                breakdown[qv] = breakdown.get(qv, 0) + 1
            record = {
                "id": fid,
                "path": abs_path,
                "name": fp.name,
                "doc_type": meta.get("doc_type", ""),
                "client": meta.get("client", ""),
                "link_info": meta.get("link_info", ""),
                "identifier": meta.get("identifier", ""),
                "project_shortcode": "",
                "ok": ok,
                "error": err,
                "matches": matches_out,
                "query_breakdown": breakdown,
                "lines_preview": [m.get("line") for m in matches_out if m.get("line") not in (None, "")][:10],
            }
            store.write_result(record)

        files_with, bucket_rows = store.match_stats()
        done = len(store._files)
        running_stats = {
            "files_done": done,
            "files_total": files_total or done,
            "files_with_hits": files_with,
            "bucket_rows": bucket_rows,
        }
        if open_report and report_path and not getattr(self, "_extract_report_opened_early", False):
            store.flush_index(status="running", stats=running_stats)
            webbrowser.open(f"file:///{report_path}")
            self._extract_report_opened_early = True
        else:
            store.maybe_flush_index(status="running", stats=running_stats)
'''

new_upsert = '''    def _extract_live_upsert_file(
        self,
        store: EEReportStore,
        file_path_str: str,
        data: dict,
        query_val: str,
        query_type: str,
        *,
        open_report: bool = False,
        report_path: str | Path | None = None,
        files_total: int = 0,
    ) -> None:
        """Merge one extract file result into the live store and write by_docid (main thread).

        Zero-hit successful files skip by_docid bodies but still advance ``files_done``
        and periodically flush slim ``index.js`` so the run folder shows progress during
        sparse XPath / selector scans.
        """
        if store is None:
            return
        fp = Path(file_path_str)
        abs_path = str(fp.absolute())
        docid = fp.parent.name
        fid = f"{docid}_{fp.name}"
        matches_out = [
            self._extract_match_payload(m, query_val, query_type)
            for m in (data.get("matches") or [])
        ]
        ok = bool(data.get("ok", True))
        err = str(data.get("error", "") or "")

        # Always advance scanned count (including zero-hit successes)
        done = store.note_file_scanned()
        ft = int(files_total or 0) or int(getattr(self, "_extract_live_files_total", 0) or 0)

        # Skip empty successful files for by_docid bodies (detailed-report focus),
        # but keep progress visible via stats + periodic index flush.
        if ok and not matches_out:
            files_with, bucket_rows = store.match_stats()
            running_stats = {
                "files_done": done,
                "files_total": max(ft, done),
                "files_with_hits": files_with,
                "bucket_rows": bucket_rows,
            }
            if open_report and report_path and not getattr(self, "_extract_report_opened_early", False):
                # Open shell early even before first hit so user sees the run folder live
                store.flush_index(status="running", stats=running_stats)
                webbrowser.open(f"file:///{report_path}")
                self._extract_report_opened_early = True
            else:
                store.maybe_flush_progress(status="running", stats=running_stats)
            return

        existing = None
        for rec in store._files:
            if _safe_id_local(str(rec.get("id") or "")) == _safe_id_local(fid) or rec.get("id") == fid:
                existing = rec
                break
        if existing is None:
            # also match by path
            for rec in store._files:
                if str(rec.get("path") or "") == abs_path:
                    existing = rec
                    break

        if existing is not None:
            if not ok:
                existing["ok"] = False
                existing["error"] = err or existing.get("error", "")
            existing.setdefault("matches", []).extend(matches_out)
            # rebuild query_breakdown
            breakdown = {}
            for m in existing["matches"]:
                qv = str(m.get("query_val") or "")
                breakdown[qv] = breakdown.get(qv, 0) + 1
            existing["query_breakdown"] = breakdown
            lines = [m.get("line") for m in existing["matches"] if m.get("line") not in (None, "")]
            existing["lines_preview"] = lines[:10]
            store.write_result(existing)
        else:
            try:
                meta = self.extractor.get_file_metadata(fp)
            except Exception:
                meta = {}
            breakdown = {}
            for m in matches_out:
                qv = str(m.get("query_val") or "")
                breakdown[qv] = breakdown.get(qv, 0) + 1
            record = {
                "id": fid,
                "path": abs_path,
                "name": fp.name,
                "doc_type": meta.get("doc_type", ""),
                "client": meta.get("client", ""),
                "link_info": meta.get("link_info", ""),
                "identifier": meta.get("identifier", ""),
                "project_shortcode": "",
                "ok": ok,
                "error": err,
                "matches": matches_out,
                "query_breakdown": breakdown,
                "lines_preview": [m.get("line") for m in matches_out if m.get("line") not in (None, "")][:10],
            }
            store.write_result(record)

        files_with, bucket_rows = store.match_stats()
        running_stats = {
            "files_done": done,
            "files_total": max(ft, done),
            "files_with_hits": files_with,
            "bucket_rows": bucket_rows,
        }
        if open_report and report_path and not getattr(self, "_extract_report_opened_early", False):
            store.flush_index(status="running", stats=running_stats)
            webbrowser.open(f"file:///{report_path}")
            self._extract_report_opened_early = True
        else:
            store.maybe_flush_index(status="running", stats=running_stats)
'''

tab = replace_once(tab, old_upsert, new_upsert, "upsert zero-hit fix")

# Helper method for batch_done — insert before _extract_live_upsert_file
helper = '''    def _extract_live_on_batch_done(self, batch_index, batch_files, batch_summary) -> None:
        """Write partials/batch_NNNN.json + flush index after each parallel file chunk."""
        store = getattr(self, "_extract_live_store", None)
        if store is None:
            return
        summary = dict(batch_summary or {})
        try:
            total = int(summary.get("files_total") or 0)
            if total:
                self._extract_live_files_total = total
        except Exception:
            pass
        # Attach result_ref for hits already written to by_docid
        try:
            path = store.write_batch_partial(int(batch_index), summary)
            self._log(
                f"  Partial batch JSON: {path.name} "
                f"({summary.get('files_in_batch', '?')} files, "
                f"{summary.get('matches_in_batch', 0)} hits)"
            )
        except Exception as exc:
            self._log(f"  Warning: failed to write batch partial: {exc}")
            return
        files_with, bucket_rows = store.match_stats()
        done = int(getattr(store, "_files_scanned", 0) or summary.get("files_completed_total") or 0)
        ft = int(getattr(self, "_extract_live_files_total", 0) or summary.get("files_total") or 0)
        store.flush_index(
            status="running",
            stats={
                "files_done": done,
                "files_total": max(ft, done),
                "files_with_hits": files_with,
                "bucket_rows": bucket_rows,
                "batches_completed": int(summary.get("batch_index") or batch_index or 0),
            },
        )

'''

tab = replace_once(
    tab,
    "    def _extract_live_upsert_file(\n",
    helper + "    def _extract_live_upsert_file(\n",
    "insert batch_done helper",
)

# Wire both parallel call sites: batch mode and full folder scan
# Pattern 1: _on_extract_file_done_batch + scan_directory_parallel with batch_size=batch_size
old_batch_call = '''                        def _on_extract_file_done_batch(file_path_str, result_dict, qv=query_val, qt=query_type):
                            if getattr(self, "_extract_live_store", None) is None:
                                return
                            self._extract_live_upsert_file(
                                self._extract_live_store,
                                file_path_str,
                                result_dict,
                                qv,
                                qt,
                                open_report=open_report,
                                report_path=getattr(self, "_extract_seed_report_path", None),
                                files_total=0,
                            )

                        scan_results, total_matches, total_files, has_more, next_offset = \\
                            self.extractor.scan_directory_parallel(
                                source_path, query_type, query_val,
                                attr_name=attr_name, attr_val=attr_val,
                                extensions=extensions, filename_filter=filename_filter,
                                dtd_filter=dtd_filter, client_filter=client_filter,
                                month_filter=month_filter, custom_month=custom_month,
                                batch_size=batch_size, batch_offset=batch_offset,
                                max_workers=worker_count,
                                progress_callback=progress_update,
                                recursive=recursive,
                                use_index=bool(self.use_folder_index_var.get()) if hasattr(self, 'use_folder_index_var') else True,
                                log_callback=self._log,
                                file_result_callback=_on_extract_file_done_batch,
                            )
'''

new_batch_call = '''                        def _on_extract_file_done_batch(file_path_str, result_dict, qv=query_val, qt=query_type):
                            if getattr(self, "_extract_live_store", None) is None:
                                return
                            self._extract_live_upsert_file(
                                self._extract_live_store,
                                file_path_str,
                                result_dict,
                                qv,
                                qt,
                                open_report=open_report,
                                report_path=getattr(self, "_extract_seed_report_path", None),
                                files_total=int(getattr(self, "_extract_live_files_total", 0) or 0),
                            )

                        scan_results, total_matches, total_files, has_more, next_offset = \\
                            self.extractor.scan_directory_parallel(
                                source_path, query_type, query_val,
                                attr_name=attr_name, attr_val=attr_val,
                                extensions=extensions, filename_filter=filename_filter,
                                dtd_filter=dtd_filter, client_filter=client_filter,
                                month_filter=month_filter, custom_month=custom_month,
                                batch_size=batch_size, batch_offset=batch_offset,
                                max_workers=worker_count,
                                progress_callback=progress_update,
                                recursive=recursive,
                                use_index=bool(self.use_folder_index_var.get()) if hasattr(self, 'use_folder_index_var') else True,
                                log_callback=self._log,
                                file_result_callback=_on_extract_file_done_batch,
                                file_batch_size=EE_SCAN_BATCH_SIZE,
                                batch_done_callback=self._extract_live_on_batch_done,
                            )
'''

tab = replace_once(tab, old_batch_call, new_batch_call, "wire batch-mode parallel")

old_full_call = '''                        def _on_extract_file_done(file_path_str, result_dict, qv=query_val, qt=query_type):
                            if getattr(self, "_extract_live_store", None) is None:
                                return
                            self._extract_live_upsert_file(
                                self._extract_live_store,
                                file_path_str,
                                result_dict,
                                qv,
                                qt,
                                open_report=open_report,
                                report_path=getattr(self, "_extract_seed_report_path", None),
                                files_total=0,
                            )

                        scan_results, total_matches, total_files, _, _ = \\
                            self.extractor.scan_directory_parallel(
                                source_path, query_type, query_val,
                                attr_name=attr_name, attr_val=attr_val,
                                extensions=extensions, filename_filter=filename_filter,
                                dtd_filter=dtd_filter, client_filter=client_filter,
                                month_filter=month_filter, custom_month=custom_month,
                                batch_size=0, batch_offset=0,
                                max_workers=worker_count,
                                progress_callback=progress_update,
                                recursive=recursive,
                                use_index=bool(self.use_folder_index_var.get()) if hasattr(self, 'use_folder_index_var') else True,
                                log_callback=self._log,
                                file_result_callback=_on_extract_file_done,
                            )
'''

new_full_call = '''                        def _on_extract_file_done(file_path_str, result_dict, qv=query_val, qt=query_type):
                            if getattr(self, "_extract_live_store", None) is None:
                                return
                            self._extract_live_upsert_file(
                                self._extract_live_store,
                                file_path_str,
                                result_dict,
                                qv,
                                qt,
                                open_report=open_report,
                                report_path=getattr(self, "_extract_seed_report_path", None),
                                files_total=int(getattr(self, "_extract_live_files_total", 0) or 0),
                            )

                        scan_results, total_matches, total_files, _, _ = \\
                            self.extractor.scan_directory_parallel(
                                source_path, query_type, query_val,
                                attr_name=attr_name, attr_val=attr_val,
                                extensions=extensions, filename_filter=filename_filter,
                                dtd_filter=dtd_filter, client_filter=client_filter,
                                month_filter=month_filter, custom_month=custom_month,
                                batch_size=0, batch_offset=0,
                                max_workers=worker_count,
                                progress_callback=progress_update,
                                recursive=recursive,
                                use_index=bool(self.use_folder_index_var.get()) if hasattr(self, 'use_folder_index_var') else True,
                                log_callback=self._log,
                                file_result_callback=_on_extract_file_done,
                                file_batch_size=EE_SCAN_BATCH_SIZE,
                                batch_done_callback=self._extract_live_on_batch_done,
                            )
'''

tab = replace_once(tab, old_full_call, new_full_call, "wire full-folder parallel")

# Also update progress_update helpers to record files_total — both places set status.
# Patch the folder-scan progress_update (full mode) to stash total.
# There are two similar progress_update defs. Update both by replacing the common body pattern carefully.

# Seed: reset _extract_live_files_total when seeding store
tab = replace_once(
    tab,
    '''            self._extract_report_opened_early = False
            _seed_store = EEReportStore(run_folder, kind="extract", source_path=str(source_path))
            self._extract_live_store = _seed_store
''',
    '''            self._extract_report_opened_early = False
            self._extract_live_files_total = 0
            _seed_store = EEReportStore(run_folder, kind="extract", source_path=str(source_path))
            self._extract_live_store = _seed_store
''',
    "seed files_total reset",
)

# Enhance progress_update in both parallel paths to set _extract_live_files_total
# Replace the two nearly-identical defs' first lines after percent calc.

# Use a more surgical approach: wrap status set to also stash total
old_prog_a = '''                    def progress_update(current, total, file_name):
                        percent = int((current / total) * 100) if total > 0 else 0
                        mode_str = "Parallel" if use_parallel else "Batch"
                        def _update(p=percent, ms=mode_str, c=current, t=total, n=file_name, qi=query_idx, ql=len(queries)):
                            self.progress_bar.config(value=p)
                            self.status_var.set(f"{ms} Query {qi + 1}/{ql} - Scanning ({c}/{t}): {n}")
                        self._ui(_update)
'''

new_prog_a = '''                    def progress_update(current, total, file_name):
                        if total:
                            self._extract_live_files_total = int(total)
                        percent = int((current / total) * 100) if total > 0 else 0
                        mode_str = "Parallel" if use_parallel else "Batch"
                        def _update(p=percent, ms=mode_str, c=current, t=total, n=file_name, qi=query_idx, ql=len(queries)):
                            self.progress_bar.config(value=p)
                            self.status_var.set(f"{ms} Query {qi + 1}/{ql} - Scanning ({c}/{t}): {n}")
                        self._ui(_update)
'''

tab = replace_once(tab, old_prog_a, new_prog_a, "progress_update batch path")

old_prog_b = '''                    def progress_update(current, total, file_name):
                        percent = int((current / total) * 100) if total > 0 else 0
                        mode_str = "Parallel" if use_parallel else "Query"
                        def _update(p=percent, ms=mode_str, c=current, t=total, n=file_name, qi=query_idx, ql=len(queries)):
                            self.progress_bar.config(value=p)
                            self.status_var.set(f"{ms} {qi + 1}/{ql} - Scanning ({c}/{t}): {n}")
                        self._ui(_update)
'''

new_prog_b = '''                    def progress_update(current, total, file_name):
                        if total:
                            self._extract_live_files_total = int(total)
                        percent = int((current / total) * 100) if total > 0 else 0
                        mode_str = "Parallel" if use_parallel else "Query"
                        def _update(p=percent, ms=mode_str, c=current, t=total, n=file_name, qi=query_idx, ql=len(queries)):
                            self.progress_bar.config(value=p)
                            self.status_var.set(f"{ms} {qi + 1}/{ql} - Scanning ({c}/{t}): {n}")
                        self._ui(_update)
'''

tab = replace_once(tab, old_prog_b, new_prog_b, "progress_update full path")

tab_path.write_text(tab, encoding="utf-8")
print("Patched element_extractor_tab.py")

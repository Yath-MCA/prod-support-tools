# -*- coding: utf-8 -*-
"""Patch EE always-write by_docid/<docid>.json + resume skip."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite")
STORE = ROOT / "core" / "ee_report_store.py"
EXTRACTOR = ROOT / "core" / "element_extractor.py"
TAB = ROOT / "tabs" / "element_extractor_tab.py"
TEST_STORE = ROOT / "tests" / "test_ee_report_store.py"
TEST_BATCH = ROOT / "tests" / "test_ee_scan_batching.py"
NEW_TEST = ROOT / "tests" / "test_ee_docid_json_resume.py"

HELPERS_AFTER_SAFE_ID = r'''

def normalize_source_key(path_or_name: str | Path) -> str:
    """Basename used as the sources{} key (e.g. N1_original.xml, updated.html)."""
    return Path(path_or_name).name


def docid_from_file_path(file_path: str | Path) -> str:
    """Doc folder name: parent of the scanned file (IMPACT layout)."""
    return Path(file_path).parent.name

'''

DOCID_METHODS = r'''
    # --- Always-write per-docid JSON (sources -> query -> matches) ---

    def docid_json_path(self, docid: str) -> Path:
        return self.by_docid_dir / f"{_safe_id(str(docid or 'item'))}.json"

    def load_docid_json(self, docid: str) -> dict:
        """Load by_docid/<docid>.json; migrate legacy hit-only .js when needed."""
        self.by_docid_dir.mkdir(parents=True, exist_ok=True)
        path = self.docid_json_path(docid)
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    data.setdefault("docid", str(docid))
                    data.setdefault("sources", {})
                    if not isinstance(data.get("sources"), dict):
                        data["sources"] = {}
                    return data
            except Exception:
                pass
        migrated = self._migrate_legacy_js_for_docid(docid)
        if migrated is not None:
            return migrated
        return {"docid": str(docid), "sources": {}}

    def _migrate_legacy_js_for_docid(self, docid: str) -> dict | None:
        """Best-effort convert legacy by_docid/<docid>_*.js hit files into nested JSON."""
        safe = _safe_id(str(docid or "item"))
        if not self.by_docid_dir.is_dir():
            return None
        candidates = sorted(
            [
                p
                for p in self.by_docid_dir.glob("*.js")
                if p.stem == safe or p.stem.startswith(safe + "_")
            ]
        )
        if not candidates:
            return None
        sources: dict = {}
        for js_path in candidates:
            try:
                text = js_path.read_text(encoding="utf-8")
            except Exception:
                continue
            marker = "= "
            # Expect: window.__EE_DOC__[<key>] = <json>;
            if "window.__EE_DOC__" not in text or marker not in text:
                continue
            try:
                body = text.split("=", 1)[1]
                # drop trailing assignment noise after first JSON object
                body = body.strip()
                if body.endswith(";"):
                    body = body[:-1].strip()
                # body may be "window.__EE_DOC__[k] = {...}" already split wrong —
                # re-parse from last '=' after __EE_DOC__
                if "window.__EE_DOC__" in text:
                    after = text.split("window.__EE_DOC__", 1)[1]
                    after = after.split("=", 1)[1].strip()
                    if after.endswith(";"):
                        after = after[:-1].strip()
                    record = json.loads(after)
                else:
                    record = json.loads(body)
            except Exception:
                continue
            if not isinstance(record, dict):
                continue
            source_key = normalize_source_key(
                record.get("name") or record.get("path") or js_path.stem
            )
            matches = list(record.get("matches") or [])
            by_query: dict = sources.setdefault(source_key, {})
            if matches:
                for m in matches:
                    q = str(m.get("query_val") or "")
                    by_query.setdefault(q, []).append(m)
            else:
                # legacy empty hit file — mark unknown query only if none yet
                by_query.setdefault("", [])
        if not sources:
            return None
        out = {"docid": str(docid), "sources": sources}
        # Persist migration so resume sees JSON next time
        try:
            self.docid_json_path(docid).write_text(
                json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass
        return out

    def has_source_query(self, docid: str, source_key: str, query: str) -> bool:
        """True when sources[source_key][query] is already present (even if [])."""
        rec = self.load_docid_json(docid)
        src = (rec.get("sources") or {}).get(str(source_key))
        if not isinstance(src, dict):
            return False
        return str(query) in src

    def upsert_docid_source_query(
        self,
        docid: str,
        source_key: str,
        query: str,
        matches: list | None,
        *,
        ok: bool = True,
        error: str = "",
    ) -> Path:
        """Always write/update by_docid/<docid>.json for this source+query (hits or [])."""
        self.by_docid_dir.mkdir(parents=True, exist_ok=True)
        rec = self.load_docid_json(docid)
        rec["docid"] = str(docid)
        sources = rec.setdefault("sources", {})
        if not isinstance(sources, dict):
            sources = {}
            rec["sources"] = sources
        src_map = sources.setdefault(str(source_key), {})
        if not isinstance(src_map, dict):
            src_map = {}
            sources[str(source_key)] = src_map
        # Empty list = scanned, zero hits. Errors still record the list provided.
        src_map[str(query)] = list(matches or [])
        if not ok and error:
            # Keep a light error breadcrumb without breaking the schema
            err_map = rec.setdefault("errors", {})
            if not isinstance(err_map, dict):
                err_map = {}
                rec["errors"] = err_map
            err_map.setdefault(str(source_key), {})[str(query)] = str(error)
        path = self.docid_json_path(docid)
        path.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def filter_paths_needing_scan(
        self,
        file_paths: list,
        query: str,
    ) -> tuple[list, int]:
        """Return (paths_to_scan, skipped_count) based on existing docid JSON."""
        to_scan = []
        skipped = 0
        q = str(query)
        for raw in file_paths or []:
            fp = Path(raw)
            docid = docid_from_file_path(fp)
            source_key = normalize_source_key(fp)
            if self.has_source_query(docid, source_key, q):
                skipped += 1
                continue
            to_scan.append(fp)
        return to_scan, skipped

'''

def patch_store():
    text = STORE.read_text(encoding="utf-8")
    if "def upsert_docid_source_query" in text:
        print("store: helpers already present")
        return
    if "def normalize_source_key" not in text:
        needle = "def _safe_id(raw: str) -> str:\n    s = re.sub(r\"[^A-Za-z0-9._-]+\", \"_\", (raw or \"\").strip())[:120]\n    return s or \"item\"\n"
        if needle not in text:
            raise SystemExit("safe_id block not found")
        text = text.replace(needle, needle + HELPERS_AFTER_SAFE_ID, 1)
    # Insert methods before write_result
    marker = "    def write_result(self, file_record: dict) -> Path:\n"
    if marker not in text:
        raise SystemExit("write_result marker not found")
    text = text.replace(marker, DOCID_METHODS + "\n" + marker, 1)
    # Update docstring at top
    text = text.replace(
        '"""Progressive Element Extractor report artifacts (by_docid + index.js)."""',
        '"""Progressive Element Extractor report artifacts (by_docid JSON + index.js)."""',
        1,
    )
    STORE.write_text(text, encoding="utf-8")
    print("store: patched")


def patch_extractor():
    text = EXTRACTOR.read_text(encoding="utf-8")
    if "skip_file_predicate" in text and "def scan_directory_parallel" in text:
        # check if already in signature
        if "skip_file_predicate=None" in text:
            print("extractor: skip_file_predicate already present")
            return
    old_sig = """    def scan_directory_parallel(self, dir_path: Path, query_type: str, query_val: str,
                               attr_name: str = "", attr_val: str = "",
                               extensions: list = None, filename_filter: str = None,
                               dtd_filter: str = None, client_filter: str = None,
                               month_filter: str = "All Time", custom_month: str = "",
                               batch_size: int = 0, batch_offset: int = 0,
                               max_workers: int = None, progress_callback=None,
                               recursive: bool = True, use_index: bool = True, log_callback=None,
                               file_result_callback=None,
                               file_batch_size: int = None,
                               batch_done_callback=None):"""
    new_sig = """    def scan_directory_parallel(self, dir_path: Path, query_type: str, query_val: str,
                               attr_name: str = "", attr_val: str = "",
                               extensions: list = None, filename_filter: str = None,
                               dtd_filter: str = None, client_filter: str = None,
                               month_filter: str = "All Time", custom_month: str = "",
                               batch_size: int = 0, batch_offset: int = 0,
                               max_workers: int = None, progress_callback=None,
                               recursive: bool = True, use_index: bool = True, log_callback=None,
                               file_result_callback=None,
                               file_batch_size: int = None,
                               batch_done_callback=None,
                               skip_file_predicate=None):"""
    if old_sig not in text:
        raise SystemExit("scan_directory_parallel signature not found")
    text = text.replace(old_sig, new_sig, 1)
    # Docstring addition
    doc_add_old = """            batch_done_callback: Optional callback(batch_index, batch_files, batch_results_summary)
                invoked on the main thread after each file chunk completes.

        Returns:"""
    doc_add_new = """            batch_done_callback: Optional callback(batch_index, batch_files, batch_results_summary)
                invoked on the main thread after each file chunk completes.
            skip_file_predicate: Optional callback(file_path) -> bool; when True, the file is
                omitted from parallel extract (already-processed docid/source/query resume).

        Returns:"""
    if doc_add_old not in text:
        raise SystemExit("docstring block not found")
    text = text.replace(doc_add_old, doc_add_new, 1)
    # After all_files collected (total_files = len(all_files)), filter
    filter_anchor = """        total_files = len(all_files)

        # Process files in parallel (chunked when file count exceeds file_batch_size)
"""
    filter_insert = """        total_files = len(all_files)

        if skip_file_predicate is not None and all_files:
            kept = []
            skipped_n = 0
            for fp in all_files:
                try:
                    if skip_file_predicate(fp):
                        skipped_n += 1
                        continue
                except Exception:
                    kept.append(fp)
                    continue
                kept.append(fp)
            all_files = kept
            total_files = len(all_files)
            if log_callback and skipped_n:
                try:
                    log_callback(
                        f"Skipping {skipped_n} already-processed docid/source/query"
                    )
                except Exception:
                    pass

        # Process files in parallel (chunked when file count exceeds file_batch_size)
"""
    if filter_anchor not in text:
        raise SystemExit("filter anchor not found")
    text = text.replace(filter_anchor, filter_insert, 1)
    EXTRACTOR.write_text(text, encoding="utf-8")
    print("extractor: patched")


def patch_tab():
    text = TAB.read_text(encoding="utf-8")
    # Update import
    old_imp = "from core.ee_report_store import EEReportStore, _safe_id as _safe_id_local"
    new_imp = (
        "from core.ee_report_store import (\n"
        "    EEReportStore,\n"
        "    _safe_id as _safe_id_local,\n"
        "    normalize_source_key,\n"
        "    docid_from_file_path,\n"
        ")"
    )
    if "normalize_source_key" not in text:
        if old_imp not in text:
            raise SystemExit("tab import not found")
        text = text.replace(old_imp, new_imp, 1)

    # Replace _extract_live_upsert_file body with always-write version
    start = text.find("    def _extract_live_upsert_file(")
    if start < 0:
        raise SystemExit("upsert method not found")
    end = text.find("    def _write_extract_progressive_report(", start)
    if end < 0:
        raise SystemExit("next method not found")
    new_method = '''    def _extract_live_upsert_file(
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
        """Merge one extract file result into the live store (main thread).

        Always upserts ``by_docid/<docid>.json`` under sources[source][query]
        (empty list = scanned, zero hits). Hit bodies still write legacy
        ``by_docid/<docid>_<file>.js`` for thin-shell lazy load + index.
        """
        if store is None:
            return
        fp = Path(file_path_str)
        abs_path = str(fp.absolute())
        docid = docid_from_file_path(fp)
        source_key = normalize_source_key(fp)
        fid = f"{docid}_{fp.name}"
        matches_out = [
            self._extract_match_payload(m, query_val, query_type)
            for m in (data.get("matches") or [])
        ]
        ok = bool(data.get("ok", True))
        err = str(data.get("error", "") or "")

        # Source-of-truth JSON: always write for this docid/source/query
        try:
            store.upsert_docid_source_query(
                docid,
                source_key,
                query_val,
                matches_out,
                ok=ok,
                error=err,
            )
        except Exception as exc:
            self._log(f"  Warning: failed to write by_docid JSON for {docid}/{source_key}: {exc}")

        # Always advance scanned count (including zero-hit successes)
        done = store.note_file_scanned()
        ft = int(files_total or 0) or int(getattr(self, "_extract_live_files_total", 0) or 0)

        # Zero-hit / empty: progress only (no lazy-load .js body)
        if ok and not matches_out:
            files_with, bucket_rows = store.match_stats()
            running_stats = {
                "files_done": done,
                "files_total": max(ft, done),
                "files_with_hits": files_with,
                "bucket_rows": bucket_rows,
            }
            store.maybe_flush_progress(status="running", stats=running_stats)
            return

        existing = None
        for rec in store._files:
            if _safe_id_local(str(rec.get("id") or "")) == _safe_id_local(fid) or rec.get("id") == fid:
                existing = rec
                break
        if existing is None:
            for rec in store._files:
                if str(rec.get("path") or "") == abs_path:
                    existing = rec
                    break

        if existing is not None:
            if not ok:
                existing["ok"] = False
                existing["error"] = err or existing.get("error", "")
            existing.setdefault("matches", []).extend(matches_out)
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
    text = text[:start] + new_method + text[end:]

    # Helper method for resume filter (insert before _extract_live_on_batch_done)
    if "_filter_extract_paths_for_resume" not in text:
        helper = '''    def _filter_extract_paths_for_resume(self, file_paths, query_val: str):
        """Drop paths whose by_docid JSON already has this source+query. Log skip count."""
        store = getattr(self, "_extract_live_store", None)
        if store is None or not file_paths:
            return list(file_paths or [])
        to_scan, skipped = store.filter_paths_needing_scan(list(file_paths), query_val)
        if skipped:
            self._log(f"Skipping {skipped} already-processed docid/source/query")
        return to_scan

'''
        anchor = "    def _extract_live_on_batch_done(self, batch_index, batch_files, batch_summary) -> None:"
        if anchor not in text:
            raise SystemExit("batch_done anchor missing for helper insert")
        text = text.replace(anchor, helper + anchor, 1)

    # Sequential: always upsert (including zero-hit success)
    # Replace the sequential loop body that only upserts on matches
    old_seq = '''                            try:
                                cached = self.extractor._get_cached(file_path, query_type, query_val, attr_name, attr_val)
                                if cached is not None:
                                    matches = cached
                                else:
                                    matches = self.extractor.parse_and_extract(file_path, query_type, query_val, attr_name, attr_val)
                                    self.extractor._set_cache(file_path, query_type, query_val, attr_name, attr_val, matches)

                                if matches:
                                    scan_results[str(file_path.absolute())] = {
                                        "ok": True,
                                        "matches": matches
                                    }
                                    total_matches += len(matches)
                                    if getattr(self, "_extract_live_store", None) is not None:
                                        self._extract_live_upsert_file(
                                            self._extract_live_store,
                                            str(file_path.absolute()),
                                            scan_results[str(file_path.absolute())],
                                            query_val,
                                            query_type,
                                            open_report=open_report,
                                            report_path=getattr(self, "_extract_seed_report_path", None),
                                            files_total=total_files_scanned or total_files,
                                        )
                            except Exception as e:
                                scan_results[str(file_path.absolute())] = {
                                    "ok": False,
                                    "error": str(e),
                                    "matches": []
                                }
                                if getattr(self, "_extract_live_store", None) is not None:
                                    self._extract_live_upsert_file(
                                        self._extract_live_store,
                                        str(file_path.absolute()),
                                        scan_results[str(file_path.absolute())],
                                        query_val,
                                        query_type,
                                        open_report=open_report,
                                        report_path=getattr(self, "_extract_seed_report_path", None),
                                        files_total=total_files_scanned or total_files,
                                    )'''
    new_seq = '''                            try:
                                cached = self.extractor._get_cached(file_path, query_type, query_val, attr_name, attr_val)
                                if cached is not None:
                                    matches = cached
                                else:
                                    matches = self.extractor.parse_and_extract(file_path, query_type, query_val, attr_name, attr_val)
                                    self.extractor._set_cache(file_path, query_type, query_val, attr_name, attr_val, matches)

                                scan_results[str(file_path.absolute())] = {
                                    "ok": True,
                                    "matches": matches or [],
                                }
                                if matches:
                                    total_matches += len(matches)
                                if getattr(self, "_extract_live_store", None) is not None:
                                    self._extract_live_upsert_file(
                                        self._extract_live_store,
                                        str(file_path.absolute()),
                                        scan_results[str(file_path.absolute())],
                                        query_val,
                                        query_type,
                                        open_report=open_report,
                                        report_path=getattr(self, "_extract_seed_report_path", None),
                                        files_total=total_files_scanned or total_files,
                                    )
                            except Exception as e:
                                scan_results[str(file_path.absolute())] = {
                                    "ok": False,
                                    "error": str(e),
                                    "matches": []
                                }
                                if getattr(self, "_extract_live_store", None) is not None:
                                    self._extract_live_upsert_file(
                                        self._extract_live_store,
                                        str(file_path.absolute()),
                                        scan_results[str(file_path.absolute())],
                                        query_val,
                                        query_type,
                                        open_report=open_report,
                                        report_path=getattr(self, "_extract_seed_report_path", None),
                                        files_total=total_files_scanned or total_files,
                                    )'''
    if old_seq not in text:
        raise SystemExit("sequential block not found exactly")
    text = text.replace(old_seq, new_seq, 1)

    # Before sequential for-loop over all_files, apply resume filter
    seq_loop = '''                        for i, file_path in enumerate(all_files):
                            if self.cancelled:
                                break
                            progress_update(i + 1, total_files, file_path.name)'''
    seq_loop_new = '''                        # Resume: skip docid/source/query already present in by_docid JSON
                        all_files = self._filter_extract_paths_for_resume(all_files, query_val)
                        total_files = len(all_files)
                        total_files_scanned = max(total_files_scanned, total_files)

                        for i, file_path in enumerate(all_files):
                            if self.cancelled:
                                break
                            progress_update(i + 1, total_files, file_path.name)'''
    if seq_loop not in text:
        raise SystemExit("sequential loop not found")
    text = text.replace(seq_loop, seq_loop_new, 1)

    # Parallel: add skip_file_predicate to both scan_directory_parallel call sites
    # Find the two call patterns with file_result_callback=_on_extract_file_done
    # and file_result_callback=_on_extract_file_done_batch

    def inject_skip(call_snippet_end: str) -> None:
        nonlocal text
        # We inject before the closing of scan_directory_parallel(
        # Look for batch_done_callback=self._extract_live_on_batch_done,
        #                             )
        target = "batch_done_callback=self._extract_live_on_batch_done,\n                            )"
        if "skip_file_predicate=" in text and text.count("skip_file_predicate=") >= 2:
            return
        replacement = (
            "batch_done_callback=self._extract_live_on_batch_done,\n"
            "                                skip_file_predicate=lambda fp, qv=query_val: (\n"
            "                                    getattr(self, '_extract_live_store', None) is not None\n"
            "                                    and self._extract_live_store.has_source_query(\n"
            "                                        docid_from_file_path(fp),\n"
            "                                        normalize_source_key(fp),\n"
            "                                        qv,\n"
            "                                    )\n"
            "                                ),\n"
            "                            )"
        )
        count = text.count(target)
        if count < 1:
            raise SystemExit(f"parallel batch_done closing not found ({call_snippet_end})")
        text = text.replace(target, replacement)

    inject_skip("parallel")

    TAB.write_text(text, encoding="utf-8")
    print("tab: patched")


NEW_TEST_CONTENT = r'''# -*- coding: utf-8 -*-
"""Always-write by_docid/<docid>.json + resume skip for source+query."""
from __future__ import annotations

import json
from pathlib import Path

from core.ee_report_store import (
    EEReportStore,
    normalize_source_key,
    docid_from_file_path,
)


def test_normalize_source_key_is_basename():
    assert normalize_source_key(r"C:\data\N1\N1_original.xml") == "N1_original.xml"
    assert normalize_source_key(Path("/tmp/updated.html")) == "updated.html"


def test_docid_from_file_path_is_parent_name():
    assert docid_from_file_path(Path("/docs/1234567/original.xml")) == "1234567"


def test_upsert_always_writes_empty_array(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="extract", source_path=str(tmp_path))
    path = store.upsert_docid_source_query(
        "1234567", "original.xml", "//author-comment", [], ok=True
    )
    assert path.name == "1234567.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["docid"] == "1234567"
    assert data["sources"]["original.xml"]["//author-comment"] == []


def test_upsert_hits_under_source_and_query(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="extract", source_path=str(tmp_path))
    hits = [{"line": 1, "tag": "author-comment", "query_val": "//author-comment", "html": "<x/>"}]
    store.upsert_docid_source_query("N1", "updated.html", "//author-comment", hits)
    store.upsert_docid_source_query("N1", "updated.html", "//mixed-citation", [])
    store.upsert_docid_source_query("N1", "original.xml", "//author-comment", [])
    data = json.loads((run / "by_docid" / "N1.json").read_text(encoding="utf-8"))
    assert data["sources"]["updated.html"]["//author-comment"][0]["tag"] == "author-comment"
    assert data["sources"]["updated.html"]["//mixed-citation"] == []
    assert data["sources"]["original.xml"]["//author-comment"] == []


def test_has_source_query_and_filter_resume(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="extract", source_path=str(tmp_path))
    store.upsert_docid_source_query("doc_a", "doc.html", "span", [])
    paths = [
        tmp_path / "doc_a" / "doc.html",
        tmp_path / "doc_b" / "doc.html",
        tmp_path / "doc_a" / "other.html",
    ]
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("<html/>", encoding="utf-8")

    assert store.has_source_query("doc_a", "doc.html", "span") is True
    assert store.has_source_query("doc_a", "doc.html", "div") is False
    assert store.has_source_query("doc_a", "other.html", "span") is False

    to_scan, skipped = store.filter_paths_needing_scan(paths, "span")
    assert skipped == 1
    names = {p.name for p in to_scan}
    assert names == {"doc.html", "other.html"} or "other.html" in names
    # doc_a/doc.html skipped; doc_b/doc.html and doc_a/other.html remain
    assert len(to_scan) == 2
    assert all(not (p.parent.name == "doc_a" and p.name == "doc.html") for p in to_scan)

    # Different query does not skip
    to_scan2, skipped2 = store.filter_paths_needing_scan(paths, "div")
    assert skipped2 == 0
    assert len(to_scan2) == 3


def test_legacy_js_migrates_on_load(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="extract", source_path=str(tmp_path))
    store.by_docid_dir.mkdir(parents=True, exist_ok=True)
    fid = "N1_a.xml"
    record = {
        "id": fid,
        "name": "a.xml",
        "path": "N1/a.xml",
        "ok": True,
        "matches": [{"query_val": "//x", "html": "<x/>"}],
    }
    body = json.dumps(record, ensure_ascii=False)
    (store.by_docid_dir / f"{fid}.js").write_text(
        "window.__EE_DOC__ = window.__EE_DOC__ || {};\n"
        f"window.__EE_DOC__[{json.dumps(fid)}] = {body};\n",
        encoding="utf-8",
    )
    loaded = store.load_docid_json("N1")
    assert "a.xml" in loaded["sources"]
    assert loaded["sources"]["a.xml"]["//x"][0]["html"] == "<x/>"
    assert (store.by_docid_dir / "N1.json").is_file()
    assert store.has_source_query("N1", "a.xml", "//x") is True
'''


def patch_tests():
    NEW_TEST.write_text(NEW_TEST_CONTENT, encoding="utf-8")
    print("new test written:", NEW_TEST.name)

    # Soft-update batching test expectation comment remains valid for .js hit-only;
    # always-write JSON is additional — update e2e-ish test to also assert JSON when using upsert.
    text = TEST_BATCH.read_text(encoding="utf-8")
    old_on_file = '''    def on_file(path_str, result):
        # Mimic tab: count every file; write by_docid only on hits
        store.note_file_scanned()
        if result.get("ok") and result.get("matches"):
            fp = Path(path_str)
            store.write_result({
                "id": f"{fp.parent.name}_{fp.name}",
                "path": path_str,
                "name": fp.name,
                "ok": True,
                "error": "",
                "matches": result["matches"],
            })
        store.maybe_flush_progress(
            status="running",
            stats={
                "files_done": store._files_scanned,
                "files_total": 7,
                "files_with_hits": store.match_stats()[0],
                "bucket_rows": store.match_stats()[1],
            },
        )'''
    new_on_file = '''    def on_file(path_str, result):
        # Mimic tab: always-write docid JSON; .js only on hits
        from core.ee_report_store import normalize_source_key, docid_from_file_path
        fp = Path(path_str)
        matches = result.get("matches") or []
        store.upsert_docid_source_query(
            docid_from_file_path(fp),
            normalize_source_key(fp),
            "span",
            matches,
            ok=bool(result.get("ok", True)),
            error=str(result.get("error", "") or ""),
        )
        store.note_file_scanned()
        if result.get("ok") and matches:
            store.write_result({
                "id": f"{fp.parent.name}_{fp.name}",
                "path": path_str,
                "name": fp.name,
                "ok": True,
                "error": "",
                "matches": matches,
            })
        store.maybe_flush_progress(
            status="running",
            stats={
                "files_done": store._files_scanned,
                "files_total": 7,
                "files_with_hits": store.match_stats()[0],
                "bucket_rows": store.match_stats()[1],
            },
        )'''
    if old_on_file in text:
        text = text.replace(old_on_file, new_on_file, 1)
        # Assert JSON always written for all 7 docs
        old_assert = '''    # by_docid only for hits (0,2,4,6) => 4
    assert len(list((run / "by_docid").glob("*.js"))) == 4'''
        new_assert = '''    # legacy .js only for hits (0,2,4,6) => 4; JSON for every docid => 7
    assert len(list((run / "by_docid").glob("*.js"))) == 4
    assert len(list((run / "by_docid").glob("*.json"))) == 7'''
        if old_assert not in text:
            raise SystemExit("batch assert not found")
        text = text.replace(old_assert, new_assert, 1)
        TEST_BATCH.write_text(text, encoding="utf-8")
        print("batching test: updated")
    else:
        print("batching test: on_file block not found (skip)")


def main():
    patch_store()
    patch_extractor()
    patch_tab()
    patch_tests()
    print("DONE")


if __name__ == "__main__":
    main()

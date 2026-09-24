from pathlib import Path
p = Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite\tabs\element_extractor_tab.py")
t = p.read_text(encoding="utf-8")
old = '''        if ok and not matches_out:
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
'''
new = '''        if ok and not matches_out:
            files_with, bucket_rows = store.match_stats()
            running_stats = {
                "files_done": done,
                "files_total": max(ft, done),
                "files_with_hits": files_with,
                "bucket_rows": bucket_rows,
            }
            # Do not open the browser on zero-hit files (still wait for first by_docid write);
            # only advance stats + periodically flush slim index.js for live progress.
            store.maybe_flush_progress(status="running", stats=running_stats)
            return
'''
if old not in t:
    raise SystemExit("zero-hit browser block not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("zero-hit browser behavior restored")

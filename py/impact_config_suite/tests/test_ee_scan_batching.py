# -*- coding: utf-8 -*-
"""Tests for EE scan file-batching + zero-hit progressive progress."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from core.element_extractor import EE_SCAN_BATCH_SIZE, ElementExtractor
from core.ee_report_store import EEReportStore


def test_ee_scan_batch_size_constant():
    assert EE_SCAN_BATCH_SIZE == 250


def test_write_batch_partial_and_manifest(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="extract", source_path=str(tmp_path))
    # Simulate a hit already written so result_ref can be attached
    store.write_result({
        "id": "N1_a.xml",
        "path": str(tmp_path / "N1" / "a.xml"),
        "name": "a.xml",
        "ok": True,
        "error": "",
        "matches": [{"line": 1, "query_val": "//x"}],
    })
    hit_path = str(tmp_path / "N1" / "a.xml")
    miss_path = str(tmp_path / "N2" / "b.xml")
    summary = {
        "batch_index": 1,
        "chunk_size": 250,
        "files_in_batch": 2,
        "files_completed_total": 2,
        "files_total": 2,
        "matches_in_batch": 1,
        "files_with_hits": 1,
        "files": [
            {"path": hit_path, "docid": "N1", "name": "a.xml", "ok": True, "hit_count": 1, "error": ""},
            {"path": miss_path, "docid": "N2", "name": "b.xml", "ok": True, "hit_count": 0, "error": ""},
        ],
    }
    path = store.write_batch_partial(1, summary)
    assert path.name == "batch_0001.json"
    assert path.parent.name == "partials"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["files_in_batch"] == 2
    hit_row = next(r for r in data["files"] if r["hit_count"] == 1)
    assert hit_row.get("result_ref", "").startswith("by_docid/")
    miss_row = next(r for r in data["files"] if r["hit_count"] == 0)
    assert "result_ref" not in miss_row
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["batches_completed"] == 1
    assert manifest["files_completed"] == 2
    assert manifest["batches"][0]["path"] == "partials/batch_0001.json"


def test_note_file_scanned_and_maybe_flush_progress_zero_hit(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(
        run, kind="extract", source_path=str(tmp_path), flush_every=3, flush_interval_s=999
    )
    assert store.note_file_scanned() == 1
    assert store.note_file_scanned() == 2
    # Not due yet (done=2, flush_every=3)
    assert store.maybe_flush_progress(status="running", stats={"files_done": 2, "files_total": 10}) is None
    assert not (run / "index.js").exists()
    # Due on multiple of flush_every even without dirty by_docid writes
    flushed = store.maybe_flush_progress(
        status="running", stats={"files_done": 3, "files_total": 10, "files_with_hits": 0, "bucket_rows": 0}
    )
    assert flushed is not None
    assert flushed.name == "index.js"
    text = flushed.read_text(encoding="utf-8")
    payload = json.loads(text.split("window.__EE_INDEX__ =", 1)[1].split(";", 1)[0].strip())
    assert payload["stats"]["files_done"] == 3
    assert payload["stats"]["files_with_hits"] == 0
    assert payload["files"] == []  # no by_docid bodies for zero-hits


def _make_tree(root: Path, n: int, *, hit_every: int = 0):
    """Create n doc folders each with one html file. hit_every>0 => span every Nth file."""
    root.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        folder = root / f"doc_{i:04d}"
        folder.mkdir()
        if hit_every and (i % hit_every == 0):
            body = f"<html><body><span>hit {i}</span></body></html>"
        else:
            body = f"<html><body><div>miss {i}</div></body></html>"
        (folder / "doc.html").write_text(body, encoding="utf-8")


def test_scan_directory_parallel_batches_when_over_size(tmp_path):
    source = tmp_path / "scan"
    # Use a small file_batch_size to avoid creating 251 real files in CI-ish runs
    n = 12
    _make_tree(source, n, hit_every=3)
    extractor = ElementExtractor()
    batches_seen = []

    def on_batch(batch_index, batch_files, summary):
        batches_seen.append((batch_index, len(batch_files), summary["files_in_batch"], summary["files_total"]))

    results, matches, total, has_more, next_offset = extractor.scan_directory_parallel(
        source,
        "Tag Name",
        "span",
        max_workers=2,
        file_batch_size=5,
        batch_done_callback=on_batch,
    )
    assert total == n
    assert len(results) == n
    assert matches == 4  # indices 0,3,6,9
    assert not has_more
    # 12 files / chunk 5 => batches of 5,5,2
    assert [b[1] for b in batches_seen] == [5, 5, 2]
    assert [b[0] for b in batches_seen] == [1, 2, 3]
    assert all(b[3] == n for b in batches_seen)


def test_scan_directory_parallel_single_batch_when_under_size(tmp_path):
    source = tmp_path / "scan_small"
    _make_tree(source, 3, hit_every=1)
    extractor = ElementExtractor()
    batches_seen = []

    def on_batch(batch_index, batch_files, summary):
        batches_seen.append(batch_index)

    results, matches, total, _, _ = extractor.scan_directory_parallel(
        source,
        "Tag Name",
        "span",
        max_workers=2,
        file_batch_size=250,
        batch_done_callback=on_batch,
    )
    assert total == 3
    assert matches == 3
    assert batches_seen == [1]


def test_scan_directory_parallel_file_callback_error_logged_once(tmp_path, capsys):
    source = tmp_path / "scan_cb"
    _make_tree(source, 4, hit_every=1)
    extractor = ElementExtractor()
    logs = []

    def boom(_path, _result):
        raise RuntimeError("callback exploded")

    def log_cb(msg):
        logs.append(str(msg))

    extractor.scan_directory_parallel(
        source,
        "Tag Name",
        "span",
        max_workers=2,
        file_batch_size=2,
        file_result_callback=boom,
        log_callback=log_cb,
    )
    hits = [m for m in logs if "file_result_callback error" in m]
    assert len(hits) == 1


def test_scan_batches_write_partials_via_store_callback(tmp_path):
    """End-to-end-ish: batch_done writes partials into the run folder."""
    source = tmp_path / "scan_store"
    _make_tree(source, 7, hit_every=2)
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="extract", source_path=str(source), flush_every=2, flush_interval_s=999)
    extractor = ElementExtractor()

    def on_file(path_str, result):
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
        )

    def on_batch(batch_index, batch_files, summary):
        store.write_batch_partial(batch_index, summary)
        store.flush_index(
            status="running",
            stats={
                "files_done": store._files_scanned,
                "files_total": summary["files_total"],
                "files_with_hits": store.match_stats()[0],
                "bucket_rows": store.match_stats()[1],
            },
        )

    extractor.scan_directory_parallel(
        source,
        "Tag Name",
        "span",
        max_workers=2,
        file_batch_size=3,
        file_result_callback=on_file,
        batch_done_callback=on_batch,
    )
    partials = sorted((run / "partials").glob("batch_*.json"))
    assert [p.name for p in partials] == ["batch_0001.json", "batch_0002.json", "batch_0003.json"]
    assert store._files_scanned == 7
    assert (run / "index.js").is_file()
    # legacy .js only for hits (0,2,4,6) => 4; JSON for every docid => 7
    assert len(list((run / "by_docid").glob("*.js"))) == 4
    assert len(list((run / "by_docid").glob("*.json"))) == 7
    payload = json.loads(
        (run / "index.js").read_text(encoding="utf-8").split("window.__EE_INDEX__ =", 1)[1].split(";", 1)[0].strip()
    )
    assert payload["stats"]["files_done"] == 7

# -*- coding: utf-8 -*-
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

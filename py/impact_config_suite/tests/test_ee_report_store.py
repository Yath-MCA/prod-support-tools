import json
from pathlib import Path

from core.ee_report_store import EEReportStore


def test_snapshot_run_meta_copies_nearest_meta(tmp_path):
    scan = tmp_path / "JATS"
    scan.mkdir()
    (scan / "meta.json").write_text(
        json.dumps({"N1": {"client": "TNF", "dtd": "JATS"}}), encoding="utf-8"
    )
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="doi_pubid_by_ref", source_path=str(scan))
    out = store.snapshot_run_meta(scan)
    assert out is not None
    assert out.name == "run_meta.json"
    assert json.loads(out.read_text(encoding="utf-8"))["N1"]["client"] == "TNF"


def test_snapshot_run_meta_none_when_missing(tmp_path):
    scan = tmp_path / "JATS"
    scan.mkdir()
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="doi_pubid_by_ref", source_path=str(scan))
    assert store.snapshot_run_meta(scan) is None
    assert not (run / "run_meta.json").exists()


def _record(fid: str, name: str, matches=None):
    return {
        "id": fid,
        "path": f"{name}",
        "name": name,
        "doc_type": "Journals",
        "client": "TNF",
        "link_info": "",
        "identifier": fid.upper(),
        "ok": True,
        "error": "",
        "matches": matches if matches is not None else [{"bucket": 1, "element_kind": "pub-id"}],
    }


def test_write_result_writes_by_docid_not_partials(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="doi_pubid_by_ref", source_path=str(tmp_path))
    path = store.write_result(_record("n1_a", "a.html"))
    assert path.parent.name == "by_docid"
    assert path.suffix == ".js"
    text = path.read_text(encoding="utf-8")
    assert "window.__EE_DOC__" in text
    assert not (run / "partials").exists()
    assert (run / "index.js").exists() is False  # no auto full flush on every write


def test_flush_index_from_memory_no_disk_reload(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(
        run, kind="doi_pubid_by_ref", source_path=str(tmp_path), flush_every=999, flush_interval_s=999
    )
    store.write_result(_record("f1", "a.html"))
    store.write_result(_record("f2", "b.html", matches=[]))
    # Corrupt by_docid on disk — flush must still use in-memory records
    for p in (run / "by_docid").glob("*.js"):
        p.write_text("BROKEN", encoding="utf-8")
    data_path = store.flush_index(status="running", stats={"files_done": 2})
    assert data_path.name == "index.js"
    text = data_path.read_text(encoding="utf-8")
    assert "window.__EE_INDEX__" in text
    assert "window.__EE_REPORT__" in text
    payload = json.loads(text.split("window.__EE_INDEX__ =", 1)[1].split(";", 1)[0].strip())
    assert len(payload["files"]) == 2
    assert payload["status"] == "running"


def test_finalize_retains_by_docid_and_completes_index(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(
        run, kind="doi_pubid_by_ref", source_path=str(tmp_path), flush_every=999, flush_interval_s=999
    )
    store.write_shell_html("report.html", "DOI test")
    store.write_manifest("", "TNF", [{"docid": "N1", "path": "a.html"}])
    store.write_result(_record("f1", "a.html"))
    store.write_result(_record("f2", "b.html", matches=[]))
    assert (run / "by_docid").is_dir()
    data_path = store.finalize(status="complete", stats={"files_scanned": 2})
    assert data_path.name == "index.js"
    text = data_path.read_text(encoding="utf-8")
    assert '"status": "complete"' in text or '"status":"complete"' in text
    assert (run / "by_docid").is_dir()
    assert list((run / "by_docid").glob("*.js"))
    assert not (run / "partials").exists()
    payload = json.loads(text.split("window.__EE_INDEX__ =", 1)[1].split(";", 1)[0].strip())
    assert len(payload["files"]) == 2


def test_maybe_flush_respects_every_n(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(
        run, kind="doi_pubid_by_ref", source_path=str(tmp_path), flush_every=3, flush_interval_s=999
    )
    store.write_result(_record("f1", "a.html"))
    assert store.maybe_flush_index(status="running") is None
    store.write_result(_record("f2", "b.html"))
    assert store.maybe_flush_index(status="running") is None
    store.write_result(_record("f3", "c.html"))
    flushed = store.maybe_flush_index(status="running", stats={"files_done": 3})
    assert flushed is not None
    assert flushed.name == "index.js"
    assert (run / "index.js").is_file()


def test_write_result_upserts_same_id(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(
        run, kind="doi_pubid_by_ref", source_path=str(tmp_path), flush_every=999, flush_interval_s=999
    )
    store.write_result(_record("f1", "a.html", matches=[{"bucket": 1}]))
    store.write_result(_record("f1", "a.html", matches=[{"bucket": 1}, {"bucket": 2}]))
    assert len(store._files) == 1
    assert len(store._files[0]["matches"]) == 2
    data_path = store.flush_index(status="complete")
    payload = json.loads(
        data_path.read_text(encoding="utf-8").split("window.__EE_INDEX__ =", 1)[1].split(";", 1)[0].strip()
    )
    assert len(payload["files"]) == 1


def test_flush_index_omits_match_bodies(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(
        run, kind="doi_pubid_by_ref", source_path=str(tmp_path),
        flush_every=999, flush_interval_s=999,
    )
    store.write_result({
        "id": "n1_a",
        "path": "a.html",
        "name": "a.html",
        "doc_type": "Journals",
        "client": "TNF",
        "link_info": "",
        "identifier": "DOC1",
        "project_shortcode": "ABC",
        "ok": True,
        "error": "",
        "matches": [
            {
                "bucket": 1,
                "element_kind": "pub-id",
                "under_comment": True,
                "doi_org_in_href": False,
                "doi_org_in_text": True,
                "html": "<pub-id>x</pub-id>",
                "text": "x",
                "href": "",
                "line": 1,
                "in_ref": True,
            }
        ],
    })
    path = store.flush_index(status="complete")
    payload = json.loads(
        path.read_text(encoding="utf-8")
        .split("window.__EE_INDEX__ =", 1)[1]
        .split(";", 1)[0]
        .strip()
    )
    entry = payload["files"][0]
    assert "matches" not in entry
    assert entry["match_count"] == 1
    assert entry["result_ref"] == "by_docid/n1_a.js"
    assert entry["doc_key"] == "n1_a"
    assert entry["filter_hints"]["kinds"] == ["pub-id"]
    assert entry["filter_hints"]["under_comment"] is True
    assert entry["filter_hints"]["doi_org_href"] is False
    assert entry["filter_hints"]["doi_org_text"] is True
    doc_js = (run / "by_docid" / "n1_a.js").read_text(encoding="utf-8")
    assert "<pub-id>x</pub-id>" in doc_js


def test_doi_shell_html_loads_index_js(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="doi_pubid_by_ref", source_path=str(tmp_path))
    html_path = store.write_doi_shell_html("DOI_PubID_By_Ref_x.html", "DOI / pub-id by ref")
    text = html_path.read_text(encoding="utf-8")
    assert 'src="index.js"' in text
    assert "filterUnderComment" in text
    assert 'id="filterProjectShortcode"' in text
    assert 'id="filterElementKind"' in text
    assert 'value="doi"' in text
    assert 'value="uri"' in text
    assert 'value="pub-id"' in text
    assert "Outer HTML/XML Markup" in text
    assert "Copy Markup" in text
    assert "Copy Path" in text
    assert 'class="file-path"' not in text
    assert 'class="file-metadata"' in text
    assert "__EE_INDEX__" in text or "__EE_REPORT__" in text


def test_doi_shell_has_lazy_load_hooks(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="doi_pubid_by_ref", source_path=str(tmp_path))
    text = store.write_doi_shell_html("r.html", "DOI").read_text(encoding="utf-8")
    assert "function loadDoc(" in text
    assert "window.__EE_DOC__" in text
    assert "data-result-ref" in text
    assert "data-doc-key" in text
    assert "data-loaded" in text
    assert "data-kinds" in text

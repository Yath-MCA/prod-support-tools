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


def test_write_partial_and_finalize_merges_and_cleans(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="doi_pubid_by_ref", source_path=str(tmp_path))
    store.write_shell_html("report.html", "DOI test")
    store.write_manifest("", "TNF", [{"docid": "N1", "path": "a.html"}])
    store.write_partial({
        "id": "f1", "path": "a.html", "name": "a.html",
        "doc_type": "Journals", "client": "TNF", "link_info": "", "identifier": "DOC1",
        "ok": True, "error": "", "matches": [{"bucket": 1, "element_kind": "pub-id"}],
    })
    store.write_partial({
        "id": "f2", "path": "b.html", "name": "b.html",
        "doc_type": "Journals", "client": "TNF", "link_info": "", "identifier": "DOC2",
        "ok": True, "error": "", "matches": [],
    })
    assert (run / "partials").is_dir()
    data_path = store.finalize(status="complete", stats={"files_scanned": 2})
    assert data_path.name == "report-data.js"
    text = data_path.read_text(encoding="utf-8")
    assert text.startswith("window.__EE_REPORT__ = ")
    assert "doi_pubid_by_ref" in text
    assert '"status": "complete"' in text or '"status":"complete"' in text
    assert not (run / "partials").exists()
    payload = json.loads(text.split("=", 1)[1].strip().rstrip(";"))
    assert len(payload["files"]) == 2


def test_rebuild_keeps_partials(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="doi_pubid_by_ref", source_path=str(tmp_path))
    store.write_partial({
        "id": "f1", "path": "a.html", "name": "a.html",
        "doc_type": "", "client": "", "link_info": "", "identifier": "",
        "ok": True, "error": "", "matches": [{"bucket": 5}],
    })
    store.rebuild_report_data(status="running")
    assert (run / "partials").is_dir()
    assert (run / "report-data.js").is_file()


def test_doi_shell_html_loads_report_data_js(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="doi_pubid_by_ref", source_path=str(tmp_path))
    html_path = store.write_doi_shell_html("DOI_PubID_By_Ref_x.html", "DOI / pub-id by ref")
    text = html_path.read_text(encoding="utf-8")
    assert 'src="report-data.js"' in text
    assert "filterUnderComment" in text
    assert "Outer HTML/XML Markup" in text
    assert "Copy Markup" in text

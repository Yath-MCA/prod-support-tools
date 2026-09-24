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


def test_extract_shell_html_cfg_and_lazy_load(tmp_path):
    from core.ee_report_store import extract_shell_html

    text = extract_shell_html(
        "Extract demo",
        show_outer_xml=False,
        show_inner_text=True,
        query_label="CSS Selector: div.note",
    )
    assert 'src="index.js"' in text
    assert "window.__EE_CFG__" in text
    assert '"show_outer_xml": false' in text or '"show_outer_xml":false' in text
    assert '"show_inner_text": true' in text or '"show_inner_text":true' in text
    assert "Element Extraction" in text
    assert "filterQuery" in text
    assert "function loadDoc(" in text
    assert "Outer HTML/XML Markup" in text
    assert "Inner Text Content" in text
    assert "Attributes:" in text


def test_extract_kind_progressive_artifacts(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="extract", source_path=str(tmp_path))
    store.write_manifest("", "TNF", [{"docid": "N1", "path": "a.xml"}])
    html_path = store.write_extract_shell_html(
        "Element_Extraction_Report_x.html",
        "Element Extraction - x",
        show_outer_xml=True,
        show_inner_text=False,
        query_label="Tag Name: ext-link",
    )
    store.flush_index(status="running", stats={"files_done": 0, "files_total": 1})
    assert html_path.is_file()
    assert (run / "manifest.json").is_file()
    assert (run / "index.js").is_file()

    store.write_result({
        "id": "N1_a.xml",
        "path": "a.xml",
        "name": "a.xml",
        "doc_type": "Journals",
        "client": "TNF",
        "link_info": "",
        "identifier": "DOC1",
        "project_shortcode": "",
        "ok": True,
        "error": "",
        "matches": [{
            "line": 12,
            "tag": "ext-link",
            "element_kind": "ext-link",
            "attributes": {"ext-link-type": "uri"},
            "text": "https://example.com",
            "html": '<ext-link ext-link-type="uri">https://example.com</ext-link>',
            "query_val": "ext-link",
            "query_type": "Tag Name",
        }],
    })
    store.finalize(status="complete", stats={"files_scanned": 1, "files_with_hits": 1, "bucket_rows": 1})

    assert list((run / "by_docid").glob("*.js"))
    idx = json.loads(
        (run / "index.js").read_text(encoding="utf-8")
        .split("window.__EE_INDEX__ =", 1)[1]
        .split(";", 1)[0]
        .strip()
    )
    assert idx["kind"] == "extract"
    assert idx["status"] == "complete"
    entry = idx["files"][0]
    assert "matches" not in entry
    assert entry["match_count"] == 1
    assert entry["filter_hints"]["kinds"] == ["ext-link"]
    assert entry["filter_hints"]["queries"] == ["ext-link"]
    doc = (run / "by_docid" / "N1_a.xml.js").read_text(encoding="utf-8")
    assert "ext-link-type" in doc
    assert "https://example.com" in doc
    shell = html_path.read_text(encoding="utf-8")
    assert '"show_inner_text": false' in shell or '"show_inner_text":false' in shell


def test_write_shell_html_dispatches_extract(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="extract", source_path=str(tmp_path))
    path = store.write_shell_html("r.html", "Extract", show_outer_xml=True, show_inner_text=True)
    text = path.read_text(encoding="utf-8")
    assert "Element Extraction" in text
    assert "window.__EE_CFG__" in text



def test_summary_shell_html_uses_index(tmp_path):
    from core.ee_report_store import summary_shell_html

    text = summary_shell_html("Summary demo", query_label="CSS: div", index_src="index.js")
    assert 'src="index.js"' in text
    assert "Element Extraction Summary" in text
    assert "function buildSelectorStats" in text or "buildSelectorStats" in text
    assert "loadDoc" in text


def test_extract_summary_shell_via_store(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="extract", source_path=str(tmp_path))
    store.flush_index(status="running", stats={"files_done": 0})
    path = store.write_summary_shell_html(
        "Element_Extraction_Summary_x.html",
        "Summary - x",
        query_label="Tag Name: p",
    )
    assert path.is_file()
    assert "Element Extraction Summary" in path.read_text(encoding="utf-8")


def test_citation_type_kind_progressive(tmp_path):
    run = tmp_path / "citation_type_bibr"
    run.mkdir()
    store = EEReportStore(run, kind="citation_type", source_path=str(tmp_path))
    html_path = store.write_shell_html("Citation_Type_Report_x.html", "Citation Type")
    store.write_result({
        "id": "N1_a.xml",
        "path": "a.xml",
        "name": "a.xml",
        "ok": True,
        "error": "",
        "matches": [{
            "line": 10,
            "element_kind": "Direct",
            "subcategory": "Direct",
            "classification": "Direct",
            "cite_type": "bibr",
            "text": "(Smith, 2020)",
            "html": "<xref>Smith</xref>",
            "snippet": "Smith",
        }],
    })
    store.finalize(status="complete", stats={"files_with_hits": 1, "bucket_rows": 1})
    assert html_path.is_file()
    assert "Citation Type Report" in html_path.read_text(encoding="utf-8")
    assert list((run / "by_docid").glob("*.js"))
    idx = (run / "index.js").read_text(encoding="utf-8")
    assert "window.__EE_INDEX__" in idx
    assert "matches" not in json.loads(idx.split("window.__EE_INDEX__ =", 1)[1].split(";", 1)[0].strip())["files"][0]


def test_entire_citation_kind_progressive(tmp_path):
    run = tmp_path / "entire_citation_bibr"
    run.mkdir()
    store = EEReportStore(run, kind="entire_citation", source_path=str(tmp_path))
    html_path = store.write_shell_html("Entire_Citation_Report_x.html", "Entire Citation")
    store.write_result({
        "id": "single_author_year",
        "name": "Single Author (Year)",
        "pattern_key": "Single Author (Year)",
        "cite_type": "bibr",
        "pattern_count": 3,
        "match_count": 3,
        "ok": True,
        "error": "",
        "matches": [{"entire_citation": "Smith (2020)", "html": "<p>Smith (2020)</p>", "element_kind": "Single Author (Year)"}],
    })
    store.finalize(status="complete", stats={"pattern_count": 1, "bucket_rows": 3})
    assert "Entire Citation Report" in html_path.read_text(encoding="utf-8")
    payload = json.loads(
        (run / "index.js").read_text(encoding="utf-8").split("window.__EE_INDEX__ =", 1)[1].split(";", 1)[0].strip()
    )
    assert payload["files"][0]["pattern_key"] == "Single Author (Year)"
    assert payload["files"][0]["pattern_count"] == 3
    assert "matches" not in payload["files"][0]


def test_mixed_citation_kind_progressive(tmp_path):
    run = tmp_path / "mixed_citation"
    run.mkdir()
    store = EEReportStore(run, kind="mixed_citation", source_path=str(tmp_path))
    html_path = store.write_shell_html("Mixed_Citation_Direct_Hits_x.html", "Mixed")
    store.write_result({
        "id": "N1_a.xml",
        "path": "a.xml",
        "name": "a.xml",
        "client": "TNF",
        "ok": True,
        "error": "",
        "matches": [
            {"kind": "comment", "element_kind": "comment", "value": "see also", "text": "see also", "line": 5},
            {"kind": "alpha_text", "element_kind": "alpha_text", "value": "and", "text": "and", "line": 6},
        ],
    })
    store.finalize(
        status="complete",
        stats={
            "files_total": 1,
            "files_with_hits": 1,
            "bucket_rows": 2,
            "rollup": [{"client": "TNF", "files_searched": 1, "files_with_hits": 1, "comment_hits": 1, "alpha_text_hits": 1, "total_hits": 2}],
        },
    )
    shell = html_path.read_text(encoding="utf-8")
    assert "Mixed-citation Comment + Alpha Text" in shell
    assert "rollup" in shell.lower() or "Client rollup" in shell
    assert list((run / "by_docid").glob("*.js"))

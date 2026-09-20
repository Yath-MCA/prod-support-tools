from bs4 import BeautifulSoup
from core.doi_pubid_by_ref import extract_buckets_from_soup

SAMPLE = """
<html><body>
  <div class="ref" data-name="ref">
    <span class="pub-id" data-name="pub-id">10.1/AAA</span>
    <span class="pub-id" data-name="pub-id">10.1/BBB</span>
    <a class="ext-link" ext-link-type="doi" href="https://doi.org/10.1/CCC">doi</a>
    <span class="comment" data-name="comment">
      <span class="ext-link" data-name="ext-link" ext-link-type="uri"
            xlink:href="https://doi.org/10.1109/TSMCB.2009.2015956">https://example.com/x</span>
    </span>
    <span class="ext-link" ext-link-type="uri" href="https://example.org/page">see doi.org/manual</span>
  </div>
  <span class="pub-id">10.1/OUT</span>
  <ext-link ext-link-type="doi" href="https://doi.org/10.1/OUTDOI">out</ext-link>
  <comment><ext-link ext-link-type="uri" xlink:href="https://example.com/no">plain</ext-link></comment>
</body></html>
"""


def test_six_buckets_first_only_and_flags():
    soup = BeautifulSoup(SAMPLE, "lxml")
    rows = extract_buckets_from_soup(soup)
    by_bucket = {r["bucket"]: r for r in rows}
    assert set(by_bucket) == {1, 2, 3, 4, 5, 6}
    assert by_bucket[1]["text"].strip() == "10.1/AAA"
    assert by_bucket[2]["text"].strip() == "10.1/OUT"
    assert by_bucket[5]["under_comment"] is True
    assert by_bucket[5]["doi_org_in_href"] is True
    assert by_bucket[5]["doi_org_in_text"] is False
    assert by_bucket[6]["under_comment"] is True
    assert by_bucket[6]["doi_org_in_href"] is False


def test_uri_doi_org_in_text_flag():
    html = '''<div class="ref"><span class="ext-link" ext-link-type="uri"
              href="https://example.org/x">https://doi.org/10.1/TXT</span></div>'''
    rows = extract_buckets_from_soup(BeautifulSoup(html, "lxml"))
    uri = [r for r in rows if r["bucket"] == 5][0]
    assert uri["doi_org_in_href"] is False
    assert uri["doi_org_in_text"] is True


def test_xref_class_is_not_ref_ancestor():
    html = '''<div class="xref"><span class="pub-id">10.1/X</span></div>'''
    rows = extract_buckets_from_soup(BeautifulSoup(html, "lxml"))
    assert len(rows) == 1
    assert rows[0]["bucket"] == 2
    assert rows[0]["in_ref"] is False


def test_write_csv(tmp_path):
    import csv
    from pathlib import Path
    from core.doi_pubid_by_ref import write_doi_pubid_by_ref_csv, CSV_HEADER

    results = [{
        "path": str(tmp_path / "a.xml"),
        "doc_type": "Books", "client": "TNF", "link_info": "x", "identifier": "ID1",
        "ok": True,
        "buckets": [{
            "bucket": 5, "element_kind": "uri", "in_ref": True,
            "under_comment": True, "doi_org_in_href": True, "doi_org_in_text": False,
            "line": 10, "text": "t", "href": "https://doi.org/10.1/x", "html": "<a/>",
        }],
    }, {
        "path": str(tmp_path / "empty.xml"),
        "doc_type": "", "client": "", "link_info": "", "identifier": "",
        "ok": True,
        "buckets": [],
    }]
    out = tmp_path / "out.csv"
    write_doi_pubid_by_ref_csv(results, out)
    rows = list(csv.reader(out.open(encoding="utf-8", newline="")))
    assert rows[0] == CSV_HEADER
    assert len(rows) == 2
    assert rows[1][6] == "5"
    assert rows[1][9] == "True"


def test_html_omits_empty_files_and_has_controls(tmp_path):
    import json
    from core.ee_report_store import EEReportStore
    from core.doi_pubid_by_ref import generate_doi_pubid_by_ref_html

    run = tmp_path / "run"
    run.mkdir()
    store = EEReportStore(run, kind="doi_pubid_by_ref", source_path=str(tmp_path))
    shell = store.write_doi_shell_html("DOI_report.html", "DOI / pub-id by ref — test")
    store.write_partial({
        "id": "hit", "path": str(tmp_path / "hit.xml"), "name": "hit.xml",
        "doc_type": "Books", "client": "TNF", "link_info": "pub", "identifier": "DOC1",
        "ok": True, "error": "",
        "matches": [
            {
                "bucket": 1, "element_kind": "pub-id", "in_ref": True,
                "under_comment": False, "doi_org_in_href": False, "doi_org_in_text": False,
                "line": 1, "text": "10.1/A", "href": "", "html": "<pub-id>10.1/A</pub-id>",
            },
            {
                "bucket": 5, "element_kind": "uri", "in_ref": True,
                "under_comment": True, "doi_org_in_href": True, "doi_org_in_text": True,
                "line": 2, "text": "see doi.org", "href": "https://doi.org/10.1/x",
                "html": "<a href='https://doi.org/10.1/x'>see doi.org</a>",
            },
        ],
    })
    store.write_partial({
        "id": "empty", "path": str(tmp_path / "empty.xml"), "name": "empty.xml",
        "doc_type": "Journals", "client": "Other", "link_info": "", "identifier": "DOC2",
        "ok": True, "error": "", "matches": [],
    })
    data_path = store.finalize(status="complete", stats={"files_scanned": 2})
    html_out = shell.read_text(encoding="utf-8")
    # Compat helper still returns shell with controls
    assert "filterUnderComment" in generate_doi_pubid_by_ref_html([], str(tmp_path))
    assert 'class="controls-panel"' in html_out
    assert "Collapse All" in html_out
    assert "Copy Markup" in html_out
    assert "Open HTML" in html_out
    assert "Copy Path" in html_out
    assert "Outer HTML/XML Markup" in html_out
    assert 'id="filterDocType"' in html_out
    assert 'id="filterClient"' in html_out
    assert 'id="filterIdentifier"' in html_out
    assert 'id="filterUnderComment"' in html_out
    assert 'id="filterDoiOrgHref"' in html_out
    assert 'id="filterDoiOrgText"' in html_out
    assert 'src="report-data.js"' in html_out
    payload = json.loads(data_path.read_text(encoding="utf-8").split("=", 1)[1].strip().rstrip(";"))
    names = [f.get("name") for f in payload["files"]]
    assert "hit.xml" in names
    assert "empty.xml" in names  # stored in data; shell UI omits empty matches when rendering
    hit = next(f for f in payload["files"] if f["name"] == "hit.xml")
    assert hit["matches"][1]["under_comment"] is True
    assert "Books" in json.dumps(payload)
    assert "TNF" in json.dumps(payload)
    assert "DOC1" in json.dumps(payload)

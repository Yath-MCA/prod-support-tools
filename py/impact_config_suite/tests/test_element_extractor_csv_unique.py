import csv
from pathlib import Path

from core.element_extractor import ElementExtractor
from core.match_uniqueness import annotate_selector_results

XLINK = "{http://www.w3.org/1999/xlink}href"

EXPECTED_HEADER = [
    "selector", "query_type", "file_path", "file_name",
    "doc_type", "client", "link_info", "identifier",
    "instance_no", "line", "tag", "inner_text", "outer_xml",
    "is_unique", "unique_group_size",
]


def _selector_results(file_path: str, matches: list):
    return [{
        "query_val": "ext-link",
        "query_type": "CSS Selector",
        "scan_results": {
            file_path: {"ok": True, "matches": matches},
        },
    }]


def test_export_csv_header_and_meta_and_unique_flags(tmp_path: Path, monkeypatch):
    extractor = ElementExtractor()
    file_path = str(tmp_path / "doc.xml")

    def fake_meta(path: Path):
        return {
            "doc_type": "Books",
            "client": "TNF",
            "link_info": "pubkittnf",
            "identifier": "D2V085_Melzer190226TNF_FSM",
            "dtd": "BITS",
            "doc_title": "",
            "project_title": "",
        }

    monkeypatch.setattr(extractor, "get_file_metadata", fake_meta)

    matches = [
        {"tag": "ext-link", "attributes": {"class": "x", XLINK: "u1"}, "line": 10, "text": "A", "html": "<a/>"},
        {"tag": "ext-link", "attributes": {"class": "x", XLINK: "u2"}, "line": 11, "text": "B", "html": "<b/>"},
    ]
    results = _selector_results(file_path, matches)
    annotate_selector_results(results)

    full_path = tmp_path / "full.csv"
    unique_path = tmp_path / "unique.csv"
    extractor.export_csv(results, full_path, unique_only=False)
    extractor.export_csv(results, unique_path, unique_only=True)

    with full_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == EXPECTED_HEADER
    assert len(rows) == 3  # header + 2
    assert rows[1][4:8] == ["Books", "TNF", "pubkittnf", "D2V085_Melzer190226TNF_FSM"]
    assert rows[1][-2:] == ["True", "2"]
    assert rows[2][-2:] == ["False", "2"]
    assert rows[1][8] == "1" and rows[2][8] == "2"  # instance_no

    with unique_path.open(encoding="utf-8", newline="") as f:
        urows = list(csv.reader(f))
    assert urows[0] == EXPECTED_HEADER
    assert len(urows) == 2  # header + first only
    assert urows[1][8] == "1"  # original instance_no kept
    assert urows[1][-2] == "True"


def test_html_report_contains_unique_view(tmp_path, monkeypatch):
    extractor = ElementExtractor()
    monkeypatch.setattr(extractor, "get_file_metadata", lambda p: {
        "doc_type": "Books", "client": "TNF", "link_info": "pubkittnf",
        "identifier": "ID1", "dtd": "", "doc_title": "", "project_title": "",
    })
    monkeypatch.setattr(extractor, "get_file_title", lambda p: ("filename", Path(p).name))
    matches = [
        {"tag": "a", "attributes": {"class": "x", XLINK: "1"}, "line": 1, "text": "A", "html": "<a/>"},
        {"tag": "a", "attributes": {"class": "x", XLINK: "2"}, "line": 2, "text": "B", "html": "<b/>"},
    ]
    results = [{
        "query_val": "a", "query_type": "CSS Selector", "total_matches": 2,
        "scan_results": {str(tmp_path / "f.xml"): {"ok": True, "matches": matches}},
    }]
    html_out = extractor.generate_html_report(
        str(tmp_path), "CSS Selector", "a", "", "", results, 2, 1, True
    )
    assert 'id="view-unique"' in html_out
    assert "Unique Matches" in html_out
    assert "showView" in html_out

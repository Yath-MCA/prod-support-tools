from bs4 import BeautifulSoup
from core.mixed_citation_direct_hits import (
    extract_direct_hits_from_soup,
    is_alpha_only_text,
)

SAMPLE = """
<div class="ref" data-name="ref" id="CIT0014">
  <span class="mixed-citation" data-name="mixed-citation" publication-type="webpage">
    <span class="year" data-name="year">2009</span>.
    <span class="comment" data-name="comment">Retrieved from archive</span>
    SomeAlpha
    <span class="string-name"><span class="comment">nested</span></span>
  </span>
</div>
"""

def test_alpha_only_text_rules():
    assert is_alpha_only_text("SomeAlpha")
    assert not is_alpha_only_text("2009")
    assert not is_alpha_only_text(".")
    assert not is_alpha_only_text("A B")
    assert not is_alpha_only_text("  ")

def test_direct_comment_and_alpha_text_match():
    soup = BeautifulSoup(SAMPLE, "lxml")
    hits = extract_direct_hits_from_soup(soup)
    kinds = sorted(h["kind"] for h in hits)
    assert kinds == ["alpha_text", "comment"]
    assert any(h["kind"] == "comment" and "Retrieved" in h["value"] for h in hits)
    assert any(h["kind"] == "alpha_text" and h["value"] == "SomeAlpha" for h in hits)

def test_nested_comment_excluded():
    soup = BeautifulSoup(SAMPLE, "lxml")
    hits = extract_direct_hits_from_soup(soup)
    assert not any(h.get("value") == "nested" for h in hits)


# --- Task 2: client rollup + report generation ---

import csv
from pathlib import Path


def _sample_file_results():
    return [
        {
            "path": r"C:\data\client_a\file1.html",
            "client": "ClientA",
            "ok": True,
            "hits": [
                {"kind": "comment", "value": "Retrieved from archive", "line": 10},
                {"kind": "alpha_text", "value": "SomeAlpha", "line": 11},
                {"kind": "comment", "value": "see note", "line": 20},
            ],
        },
        {
            "path": r"C:\data\client_a\file2.html",
            "client": "ClientA",
            "ok": True,
            "hits": [],
        },
        {
            "path": r"C:\data\client_b\file3.html",
            "client": "ClientB",
            "ok": True,
            "hits": [
                {"kind": "alpha_text", "value": "OnlyAlpha", "line": 5},
            ],
        },
        {
            "path": r"C:\data\client_b\file4.html",
            "client": "ClientB",
            "ok": True,
            "hits": [],
        },
    ]


def test_rollup_by_client_counts_searched_hits_and_kinds():
    from core.mixed_citation_direct_hits import rollup_by_client

    rows = rollup_by_client(_sample_file_results())
    by_client = {r["client"]: r for r in rows}

    assert set(by_client) == {"ClientA", "ClientB"}

    a = by_client["ClientA"]
    assert a["files_searched"] == 2
    assert a["files_with_hits"] == 1
    assert a["comment_hits"] == 2
    assert a["alpha_text_hits"] == 1
    assert a["total_hits"] == 3

    b = by_client["ClientB"]
    assert b["files_searched"] == 2
    assert b["files_with_hits"] == 1
    assert b["comment_hits"] == 0
    assert b["alpha_text_hits"] == 1
    assert b["total_hits"] == 1


def test_generate_html_report_includes_clients_and_rollup_numbers():
    from core.mixed_citation_direct_hits import (
        generate_mixed_citation_direct_hits_report_html,
        rollup_by_client,
    )

    file_results = _sample_file_results()
    # Include a client name that needs HTML escaping
    file_results.append(
        {
            "path": r"C:\data\evil\file5.html",
            "client": "Acme <script>alert(1)</script>",
            "ok": True,
            "hits": [{"kind": "comment", "value": "x & y", "line": 1}],
        }
    )
    rollup_rows = rollup_by_client(file_results)
    html_out = generate_mixed_citation_direct_hits_report_html(
        r"C:\data",
        file_results,
        rollup_rows,
    )
    assert isinstance(html_out, str)
    assert "ClientA" in html_out
    assert "ClientB" in html_out
    # Escape-safe: raw script tag must not appear unescaped
    assert "<script>alert(1)</script>" not in html_out
    assert "Acme" in html_out
    # Rollup numbers present (ClientA total_hits=3, files_searched=2, etc.)
    assert "3" in html_out
    assert "2" in html_out
    assert "1" in html_out
    assert "comment" in html_out.lower() or "Comment" in html_out


def test_write_csv_has_expected_header_columns(tmp_path):
    from core.mixed_citation_direct_hits import (
        rollup_by_client,
        write_mixed_citation_direct_hits_csv,
    )

    file_results = _sample_file_results()
    rollup_rows = rollup_by_client(file_results)
    csv_path = tmp_path / "mixed_citation_direct_hits.csv"
    written = write_mixed_citation_direct_hits_csv(csv_path, file_results, rollup_rows)
    assert Path(written) == csv_path
    assert csv_path.is_file()

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

    header_lower = [h.strip().lower() for h in header]
    for col in (
        "client",
        "files_searched",
        "files_with_hits",
        "comment_hits",
        "alpha_text_hits",
        "total_hits",
    ):
        assert col in header_lower, f"missing column {col!r} in {header}"
# --- Task 3: ElementExtractor scan integration ---

SAMPLE_HIT_HTML = """
<html><body>
<div class="ref" data-name="ref" id="CIT0014">
  <span class="mixed-citation" data-name="mixed-citation" publication-type="webpage">
    <span class="year" data-name="year">2009</span>.
    <span class="comment" data-name="comment">Retrieved from archive</span>
    SomeAlpha
    <span class="string-name"><span class="comment">nested</span></span>
  </span>
</div>
</body></html>
"""

SAMPLE_CLEAN_HTML = """
<html><body>
<div class="ref" data-name="ref" id="CIT0001">
  <span class="mixed-citation" data-name="mixed-citation">
    <span class="year" data-name="year">2020</span>.
  </span>
</div>
</body></html>
"""


def test_extract_mixed_citation_direct_hits_via_element_extractor(tmp_path):
    from core.element_extractor import ElementExtractor

    html_path = tmp_path / "with_hits.html"
    html_path.write_text(SAMPLE_HIT_HTML, encoding="utf-8")

    extractor = ElementExtractor()
    hits = extractor.extract_mixed_citation_direct_hits(html_path)

    assert isinstance(hits, list)
    assert len(hits) >= 2
    kinds = sorted(h["kind"] for h in hits)
    assert "alpha_text" in kinds
    assert "comment" in kinds
    assert any(h["kind"] == "comment" and "Retrieved" in h["value"] for h in hits)
    assert any(h["kind"] == "alpha_text" and h["value"] == "SomeAlpha" for h in hits)


def test_scan_mixed_citation_direct_hits_dir_shape_and_counts(tmp_path):
    from core.element_extractor import ElementExtractor

    hit_file = tmp_path / "with_hits.html"
    clean_file = tmp_path / "clean.html"
    hit_file.write_text(SAMPLE_HIT_HTML, encoding="utf-8")
    clean_file.write_text(SAMPLE_CLEAN_HTML, encoding="utf-8")

    extractor = ElementExtractor()
    results = extractor.scan_mixed_citation_direct_hits(tmp_path, recursive=False)

    assert isinstance(results, dict)
    assert len(results) == 2

    # Keys are absolute path strings; both files present
    abs_hit = str(hit_file.resolve())
    abs_clean = str(clean_file.resolve())
    # Allow either resolve() or absolute() string forms
    by_name = {Path(k).name: (k, v) for k, v in results.items()}
    assert "with_hits.html" in by_name
    assert "clean.html" in by_name

    hit_key, hit_data = by_name["with_hits.html"]
    clean_key, clean_data = by_name["clean.html"]

    for data in (hit_data, clean_data):
        assert "ok" in data
        assert "hits" in data
        assert "client" in data

    assert hit_data["ok"] is True
    assert len(hit_data["hits"]) == 2
    assert clean_data["ok"] is True
    assert len(clean_data["hits"]) == 0


def test_scan_mixed_citation_direct_hits_client_filter(tmp_path):
    """With stub impact_config.xml, client_filter excludes non-matching client dirs."""
    from core.element_extractor import ElementExtractor

    match_dir = tmp_path / "client_a"
    other_dir = tmp_path / "client_b"
    match_dir.mkdir()
    other_dir.mkdir()

    (match_dir / "impact_config.xml").write_text(
        '<?xml version="1.0"?><config><dtd name="JATS"/>'
        '<client name="ClientA"/><doc-title>A</doc-title></config>',
        encoding="utf-8",
    )
    (other_dir / "impact_config.xml").write_text(
        '<?xml version="1.0"?><config><dtd name="JATS"/>'
        '<client name="ClientB"/><doc-title>B</doc-title></config>',
        encoding="utf-8",
    )
    (match_dir / "a.html").write_text(SAMPLE_HIT_HTML, encoding="utf-8")
    (other_dir / "b.html").write_text(SAMPLE_HIT_HTML, encoding="utf-8")

    extractor = ElementExtractor()
    results = extractor.scan_mixed_citation_direct_hits(
        tmp_path,
        recursive=True,
        client_filter="ClientA",
    )

    assert isinstance(results, dict)
    names = {Path(k).name for k in results}
    assert "a.html" in names
    assert "b.html" not in names

    a_data = next(v for k, v in results.items() if Path(k).name == "a.html")
    assert a_data["ok"] is True
    assert a_data["client"] == "ClientA"
    assert len(a_data["hits"]) == 2

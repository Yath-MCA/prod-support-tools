#!/usr/bin/env python3
"""Unit tests for Direct/Indirect bibliographic citation classification."""

import sys
import tempfile
from pathlib import Path

# Allow importing from the package root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.element_extractor import ElementExtractor


SAMPLE_HTML = """<!DOCTYPE html>
<html><body>
<p>
  As shown by
  <a class="xref" data-name="xref" data-role="bibr" ref-type="bibr"
     rid="ref-223" data-cke-saved-href="#ref-223">Anderson (1978)</a>
  and also
  <a class="xref" data-role="bibr" rid="ref-224">Billig (1995)</a>
  the effect is clear.
</p>
<p>
  Later work confirmed this
  (<a class="xref" data-name="xref" data-role="bibr" ref-type="bibr"
      rid="ref-085" data-cke-saved-href="#ref-085">Kramer, 1997</a>, p. 526).
</p>
<p>
  Memory studies
  (<a class="xref" data-role="bibr" rid="ref-069">Halbwachs, 2011</a>, pp. 142–143).
</p>
<p>
  Simple parenthetical
  (<a class="xref" data-role="bibr" rid="ref-153">Borg, 1991</a>).
</p>
<p>
  Multi-cite group
  (Smith, 1990;
  <a class="xref" data-role="bibr" rid="ref-100">Jones, 1991</a>).
</p>
<p>
  Bare cite
  <a class="xref" data-role="bibr" rid="ref-50">Anderson 1978</a>
  without parentheses.
</p>
<p>
  News style
  <a class="xref" data-role="bibr" rid="ref-60">ABS-CBN News, 2017</a>
  also bare.
</p>
<p>
  Two-word single author
  (<a class="xref" data-role="bibr" rid="ref-200">Apinan Poshyananda, 1992</a>).
</p>
<p>
  Dual ampersand
  (<a class="xref" data-role="bibr" rid="ref-201">Baker &amp; Pasuk Phongpaichit, 2014</a>).
</p>
<p>
  Dual and direct
  <a class="xref" data-role="bibr" rid="ref-202">Muzaini and Yeoh (2016)</a>.
</p>
<p>
  Et al.
  (<a class="xref" data-role="bibr" rid="ref-203">Blair et al., 1991</a>).
</p>
<p>
  Possessive
  <a class="xref" data-role="bibr" rid="ref-204">Schumacher’s (2019)</a>.
</p>
<p>
  Unknown year
  (<a class="xref" data-role="bibr" rid="ref-205">Mohamed &amp; Chew, n.d.</a>).
</p>
</body></html>
"""


def _write_sample(tmp_dir: Path) -> Path:
    path = tmp_dir / "sample_bibr.html"
    path.write_text(SAMPLE_HTML, encoding="utf-8")
    return path


def test_classify_direct_indirect_unclassified():
    extractor = ElementExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_sample(Path(tmp))
        matches = extractor.extract_bibr_citations(path)

    by_text = {m["text"]: m for m in matches}

    assert by_text["Anderson (1978)"]["classification"] == "Direct"
    assert by_text["Billig (1995)"]["classification"] == "Direct"
    assert by_text["Kramer, 1997"]["classification"] == "Indirect"
    assert by_text["Halbwachs, 2011"]["classification"] == "Indirect"
    assert by_text["Borg, 1991"]["classification"] == "Indirect"
    assert by_text["Jones, 1991"]["classification"] == "Indirect"
    assert by_text["Anderson 1978"]["classification"] == "Unclassified"
    assert by_text["ABS-CBN News, 2017"]["classification"] == "Unclassified"
    assert by_text["Muzaini and Yeoh (2016)"]["classification"] == "Direct"
    assert by_text["Schumacher’s (2019)"]["classification"] == "Direct"
    assert by_text["Apinan Poshyananda, 1992"]["classification"] == "Indirect"
    assert by_text["Blair et al., 1991"]["classification"] == "Indirect"


def test_indirect_page_subcategories():
    extractor = ElementExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_sample(Path(tmp))
        matches = extractor.extract_bibr_citations(path)

    by_text = {m["text"]: m["subcategory"] for m in matches}

    assert by_text["Kramer, 1997"] == "Indirect + p."
    assert by_text["Halbwachs, 2011"] == "Indirect + pp."
    assert by_text["Borg, 1991"] == "Indirect"
    assert by_text["Jones, 1991"] == "Indirect"
    assert by_text["Anderson (1978)"] == "Direct"


def test_entire_citation_wrap():
    extractor = ElementExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_sample(Path(tmp))
        matches = extractor.extract_bibr_citations(path)

    kramer = next(m for m in matches if m["text"] == "Kramer, 1997")
    assert kramer["entire_citation"].startswith("(")
    assert "p. 526" in kramer["entire_citation"]
    assert kramer["entire_citation"].rstrip().endswith(")")
    assert 'data-role="bibr"' in kramer["entire_citation"]

    halbwachs = next(m for m in matches if m["text"] == "Halbwachs, 2011")
    assert "pp. 142" in halbwachs["entire_citation"]

    borg = next(m for m in matches if m["text"] == "Borg, 1991")
    assert borg["entire_citation"].startswith("(")
    after_link = borg["entire_citation"].split("</a>", 1)[-1]
    assert "p." not in after_link


def test_pattern_keys():
    extractor = ElementExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_sample(Path(tmp))
        matches = extractor.extract_bibr_citations(path)

    by_text = {m["text"]: m["pattern_key"] for m in matches}
    assert by_text["Anderson (1978)"] == "Single Author (Year)"
    assert by_text["Billig (1995)"] == "Single Author (Year)"
    assert by_text["Kramer, 1997"] == "Single Author, Year + p."
    assert by_text["Halbwachs, 2011"] == "Single Author, Year + pp."
    assert by_text["Borg, 1991"] == "Single Author, Year"
    assert by_text["Anderson 1978"] == "Single Author Year"
    assert by_text["ABS-CBN News, 2017"] == "Single Author (multi-word), Year"


def test_author_structure_pattern_keys():
    extractor = ElementExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_sample(Path(tmp))
        matches = extractor.extract_bibr_citations(path)

    by_text = {m["text"]: m["pattern_key"] for m in matches}

    assert by_text["Apinan Poshyananda, 1992"] == "Single Author (multi-word), Year"
    assert by_text["Baker & Pasuk Phongpaichit, 2014"] == "Dual Author (&), Year"
    assert by_text["Muzaini and Yeoh (2016)"] == "Dual Author (and) (Year)"
    assert by_text["Blair et al., 1991"] == "Author et al., Year"
    assert by_text["Schumacher’s (2019)"] == "Possessive Author (Year)"
    assert by_text["Mohamed & Chew, n.d."] == "Dual Author (&), n.d."


def test_generate_citation_type_report_html():
    extractor = ElementExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_sample(Path(tmp))
        scan_results, total_matches, total_files = extractor.scan_bibr_citations(path)
        report = extractor.generate_citation_type_report(
            str(path), scan_results, total_matches, total_files
        )

    assert isinstance(report, str)
    assert "Citation Type Report" in report
    assert "Direct:" in report
    assert "Indirect + p.:" in report
    assert "Indirect + pp.:" in report
    assert "#10b981" in report
    assert "#f59e0b" in report
    assert "Kramer, 1997" in report


def test_generate_entire_citation_report_dedupes_patterns():
    extractor = ElementExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_sample(Path(tmp))
        scan_results, total_matches, total_files = extractor.scan_bibr_citations(path)
        report = extractor.generate_entire_citation_report(
            str(path), scan_results, total_matches, total_files
        )

    assert isinstance(report, str)
    assert "Entire Citation Report" in report
    assert "Unique Patterns:" in report
    assert "Single Author (Year)" in report
    assert "Single Author, Year + p." in report
    assert "Single Author, Year + pp." in report
    # & is HTML-escaped in the report body
    assert "Dual Author (&amp;), Year" in report
    assert "Dual Author (and) (Year)" in report
    assert "Author et al., Year" in report
    assert "Possessive Author (Year)" in report
    assert "Dual Author (&amp;), n.d." in report
    # Two Direct Single Author (Year) instances collapse to one pattern row
    assert report.count('data-pattern="Single Author (Year)"') == 1
    assert "type:bibr" in report


MIXED_CITE_SAMPLE = """<!DOCTYPE html>
<html><body>
<p>See <a class="xref" data-role="bibr" ref-type="bibr" rid="r1">Wallace 2008</a>.</p>
<p>As in (<a class="xref" data-name="related-object" ref-type="bibr" object-type="bibr"
   rid="workid-ref-405">Wallace 2008</a>).</p>
<p>Figure cite (<a class="xref" ref-type="fig" rid="fig1">Fig. 1</a>).</p>
<p>Endnote <xref ref-type="endnote" rid="en1"><sup>1</sup></xref> here.</p>
</body></html>
"""


def test_cite_type_filter_bibr_ignores_fig():
    extractor = ElementExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "mixed.html"
        path.write_text(MIXED_CITE_SAMPLE, encoding="utf-8")
        matches = extractor.extract_bibr_citations(path, cite_type="bibr")

    types = {m["cite_type"] for m in matches}
    texts = {m["text"] for m in matches}
    assert types == {"bibr"}
    assert "Fig. 1" not in texts
    assert "1" not in texts or all(m["cite_type"] == "bibr" for m in matches)
    assert any("Wallace" in m["text"] for m in matches)


def test_cite_type_endnote_xref_xml():
    extractor = ElementExtractor()
    xml = """<?xml version="1.0"?>
<article><p>Note <xref ref-type="endnote" rid="en1"><sup>1</sup></xref>
and <xref ref-type="bibr" rid="r1">Smith, 1990</xref>.</p></article>
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "notes.xml"
        path.write_text(xml, encoding="utf-8")
        endnotes = extractor.extract_bibr_citations(path, cite_type="endnote")
        bibrs = extractor.extract_bibr_citations(path, cite_type="bibr")

    assert len(endnotes) == 1
    assert endnotes[0]["cite_type"] == "endnote"
    assert endnotes[0]["cite_type_source"] == "ref-type"
    assert len(bibrs) == 1
    assert bibrs[0]["cite_type"] == "bibr"


def test_cite_type_object_type_priority():
    extractor = ElementExtractor()
    html = """<html><body>
    <a class="xref" data-name="related-object" ref-type="bibr" object-type="bibr"
       data-role="bibr" rid="r1">Wallace 2008</a>
    </body></html>"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "obj.html"
        path.write_text(html, encoding="utf-8")
        matches = extractor.extract_bibr_citations(path, cite_type="bibr")

    assert len(matches) == 1
    assert matches[0]["cite_type_source"] == "object-type"


def test_cite_type_all_combined_report():
    extractor = ElementExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "mixed.html"
        path.write_text(MIXED_CITE_SAMPLE, encoding="utf-8")
        scan_results, total_matches, total_files = extractor.scan_bibr_citations(
            path, cite_type="all"
        )
        report = extractor.generate_citation_type_report(
            str(path), scan_results, total_matches, total_files, cite_type="all"
        )
        entire = extractor.generate_entire_citation_report(
            str(path), scan_results, total_matches, total_files, cite_type="all"
        )

    cite_types = {m["cite_type"] for data in scan_results.values() for m in data["matches"]}
    assert "bibr" in cite_types
    assert "fig" in cite_types
    assert "endnote" in cite_types
    assert total_matches >= 3
    assert "type:bibr" in report
    assert "type:fig" in report
    assert "type:endnote" in report
    assert "Selector:" in report
    assert "All" in report or "all" in report.lower()
    assert "type:bibr" in entire
    assert "type:fig" in entire
    # Combined = single HTML string outputs (not multiple files)
    assert isinstance(report, str) and isinstance(entire, str)


def test_scan_bibr_citations_directory():
    extractor = ElementExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_sample(root)
        (root / "empty.html").write_text("<html><body><p>No cites</p></body></html>", encoding="utf-8")
        scan_results, total_matches, total_files = extractor.scan_bibr_citations(root)

    assert total_files == 2
    assert total_matches == 14
    assert any(data.get("matches") for data in scan_results.values())


if __name__ == "__main__":
    test_classify_direct_indirect_unclassified()
    test_indirect_page_subcategories()
    test_entire_citation_wrap()
    test_pattern_keys()
    test_author_structure_pattern_keys()
    test_generate_citation_type_report_html()
    test_generate_entire_citation_report_dedupes_patterns()
    test_cite_type_filter_bibr_ignores_fig()
    test_cite_type_endnote_xref_xml()
    test_cite_type_object_type_priority()
    test_cite_type_all_combined_report()
    test_scan_bibr_citations_directory()
    print("All citation type report tests passed.")

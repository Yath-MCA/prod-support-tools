#!/usr/bin/env python3
"""Unit tests for cite-type-specific patterns, single vs range, and per-file dedupe."""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.citation_pattern_extractor import CitationPatternExtractor
from core.element_extractor import ElementExtractor


FN_HTML = """<!DOCTYPE html>
<html><body>
<p>Notes
  [<a class="xref" ref-type="fn" rid="fn1">1</a>],
  [<a class="xref" ref-type="fn" rid="fn2">2</a>],
  [<a class="xref" ref-type="fn" rid="fn3">3-5</a>],
  [<a class="xref" ref-type="fn" rid="fn6">6</a>]
</p>
<p>Sup bracket <sup>[<a class="xref" ref-type="fn" rid="fn7">7</a>]</sup></p>
<p>Sup only <sup><a class="xref" ref-type="fn" rid="fn8">8</a></sup></p>
<p>Sup range <sup>[<a class="xref" ref-type="fn" rid="fn9">9-11</a>]</sup></p>
</body></html>
"""

EQ_HTML = """<!DOCTYPE html>
<html><body>
<p>See (Equation <a class="xref" ref-type="equation" rid="e1">1</a>).</p>
<p>Also (Equations <a class="xref" ref-type="equation" rid="e2">1</a> and
   <a class="xref" ref-type="equation" rid="e3">2</a>).</p>
<p>Equation (<a class="xref" ref-type="equation" rid="e4">1</a>)</p>
<p>Eq (<a class="xref" ref-type="equation" rid="e5">1</a>)</p>
<p>Eq. (<a class="xref" ref-type="equation" rid="e6">2-3</a>)</p>
</body></html>
"""

FIG_HTML = """<!DOCTYPE html>
<html><body>
<p>See <a class="xref" ref-type="fig" rid="f1">Fig. 1</a>
and <a class="xref" ref-type="fig" rid="f2">Fig. 2</a>
and <a class="xref" ref-type="fig" rid="f3">Figs. 3-4</a>.</p>
<p>Paren (<a class="xref" ref-type="fig" rid="f4">Fig. 5</a>).</p>
</body></html>
"""


def test_fn_bracket_single_vs_range():
    extractor = ElementExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fn.html"
        path.write_text(FN_HTML, encoding="utf-8")
        matches = extractor.extract_bibr_citations(path, cite_type="fn")

    by_text = {m["text"]: m["pattern_key"] for m in matches}
    assert by_text["1"] == "bracket_number"
    assert by_text["2"] == "bracket_number"
    assert by_text["6"] == "bracket_number"
    assert by_text["3-5"] == "bracket_number_range"
    assert by_text["7"] == "sup_bracket_number"
    assert by_text["8"] == "sup_number"
    assert by_text["9-11"] == "sup_bracket_number_range"
    assert "Other" not in by_text.values()
    assert "Unclassified" not in by_text.values()


def test_fn_per_file_dedupe_keeps_single_and_range_once():
    extractor = ElementExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fn.html"
        path.write_text(FN_HTML, encoding="utf-8")
        matches = extractor.extract_bibr_citations(path, cite_type="fn")
        deduped = extractor.dedupe_matches_per_file_pattern(matches)

    keys = [m["pattern_key"] for m in deduped]
    assert keys.count("bracket_number") == 1
    assert keys.count("bracket_number_range") == 1
    bracket = next(m for m in deduped if m["pattern_key"] == "bracket_number")
    assert bracket["pattern_count"] == 3  # 1, 2, 6


def test_equation_patterns():
    extractor = ElementExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "eq.html"
        path.write_text(EQ_HTML, encoding="utf-8")
        matches = extractor.extract_bibr_citations(path, cite_type="equation")

    keys = {m["pattern_key"] for m in matches}
    assert "paren_equation" in keys or "paren_equations_and" in keys
    assert "equation_paren_number" in keys
    assert "eq_paren_number" in keys
    assert "eq_paren_number_range" in keys
    assert "Other" not in keys


def test_fig_single_vs_range_global():
    extractor = ElementExtractor()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fig.html"
        path.write_text(FIG_HTML, encoding="utf-8")
        matches = extractor.extract_bibr_citations(path, cite_type="fig")

    by_text = {m["text"]: m["pattern_key"] for m in matches}
    assert by_text["Fig. 1"] == "fig_number"
    assert by_text["Fig. 2"] == "fig_number"
    assert by_text["Figs. 3-4"] == "fig_number_range"
    assert by_text["Fig. 5"] == "paren_fig"
    deduped = extractor.dedupe_matches_per_file_pattern(matches)
    assert sum(1 for m in deduped if m["pattern_key"] == "fig_number") == 1


def test_bibr_pattern_names_unchanged_no_other():
    extractor = ElementExtractor()
    html = """<!DOCTYPE html><html><body>
    <p><a class="xref" ref-type="bibr" rid="r1">Anderson (1978)</a></p>
    <p>(<a class="xref" ref-type="bibr" rid="r2">Kramer, 1997</a>).</p>
    <p><a class="xref" ref-type="bibr" rid="r3">WeirdCite</a></p>
    </body></html>"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bibr.html"
        path.write_text(html, encoding="utf-8")
        matches = extractor.extract_bibr_citations(path, cite_type="bibr")

    by_text = {m["text"]: m["pattern_key"] for m in matches}
    assert by_text["Anderson (1978)"] == "Single Author (Year)"
    assert by_text["Kramer, 1997"] == "Single Author, Year"
    assert by_text["WeirdCite"] == "Bare Link Text"
    assert "Other" not in by_text.values()


def test_split_reports_by_cite_type_helpers():
    extractor = ElementExtractor()
    mixed = """<!DOCTYPE html><html><body>
    <p>[<a class="xref" ref-type="fn" rid="f1">1</a>]</p>
    <p><a class="xref" ref-type="fig" rid="g1">Fig. 1</a></p>
    <p><a class="xref" ref-type="bibr" rid="r1">Smith (1990)</a></p>
    </body></html>"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "mixed.html"
        path.write_text(mixed, encoding="utf-8")
        scan_results, total_matches, _files = extractor.scan_bibr_citations(
            path, cite_type="all"
        )

    types = extractor.discover_cite_types(scan_results)
    assert set(types) >= {"fn", "fig", "bibr"}
    assert total_matches >= 3

    for ct in types:
        filtered, n, _f = extractor.filter_scan_results_by_cite_type(scan_results, ct)
        report = extractor.generate_citation_type_report(
            str(path), filtered, n, 1, cite_type=ct
        )
        entire = extractor.generate_entire_citation_report(
            str(path), filtered, n, 1, cite_type=ct
        )
        assert n >= 1
        assert f"type:{ct}" in report or ct in report
        assert "Entire Citation Report" in entire
        assert 'data-pattern="Other"' not in entire
        assert 'data-pattern="Unclassified"' not in entire


def test_matrix_per_file_dedupe_and_split():
    extractor = CitationPatternExtractor()
    combined = """<!DOCTYPE html><html><body>
<p>Notes
  [<a class="xref" ref-type="fn" rid="fn1">1</a>],
  [<a class="xref" ref-type="fn" rid="fn2">2</a>],
  [<a class="xref" ref-type="fn" rid="fn3">3-5</a>],
  [<a class="xref" ref-type="fn" rid="fn6">6</a>]
</p>
<p>See (Equation <a class="xref" ref-type="equation" rid="e1">1</a>).</p>
</body></html>"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        doc_dir = root / "book1"
        doc_dir.mkdir()
        content = doc_dir / "book1_original.html"
        content.write_text(combined, encoding="utf-8")
        # ID scanner requires impact_config + an xml sibling
        (doc_dir / "impact_config.xml").write_text(
            '<?xml version="1.0"?><config><type>Books</type>'
            "<client>OUP</client><doc-title>book1</doc-title>"
            "<identifier>book1</identifier></config>",
            encoding="utf-8",
        )
        (doc_dir / "book1_original.xml").write_text(
            '<?xml version="1.0"?><article><p>x</p></article>',
            encoding="utf-8",
        )

        documents_by_client = {
            "Books|OUP": [{
                "folder": str(doc_dir),
                "content_file": str(content),
                "doc_title": "book1",
                "client": "OUP",
                "doc_type": "Books",
                "identifier": "book1",
            }],
        }
        rows, clients, _d, cite_details, _m = extractor.build_matrix_data(
            documents_by_client, cite_type="All"
        )
        out = root / "out"
        result = extractor.run_extraction(
            root_path=str(root),
            output_dir=str(out),
            doc_type="All",
            client_filter="All",
            cite_type="All",
            recursive=True,
        )

        assert clients == ["OUP"]
        cite_types = {r["cite_type"] for r in rows}
        assert "fn" in cite_types
        # Detail: one bracket_number row for the file, not three
        fn_bracket = [
            d for d in cite_details
            if d["cite_type"] == "fn" and d["pattern"] == "bracket_number"
        ]
        assert len(fn_bracket) == 1
        assert fn_bracket[0]["count"] == 3

        per_type = result.get("per_type_reports") or []
        assert len(per_type) >= 1
        html_paths = [p["html_path"] for p in per_type]
        assert len(html_paths) == len(set(html_paths))
        for p in per_type:
            html = Path(p["html_path"]).read_text(encoding="utf-8")
            assert "Citation Pattern Matrix (Cite Types × Clients)" in html


if __name__ == "__main__":
    test_fn_bracket_single_vs_range()
    test_fn_per_file_dedupe_keeps_single_and_range_once()
    test_equation_patterns()
    test_fig_single_vs_range_global()
    test_bibr_pattern_names_unchanged_no_other()
    test_split_reports_by_cite_type_helpers()
    test_matrix_per_file_dedupe_and_split()
    print("All cite-type pattern tests passed.")

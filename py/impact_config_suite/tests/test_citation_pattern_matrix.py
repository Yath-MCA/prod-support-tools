#!/usr/bin/env python3
"""Unit tests for Citation Pattern Matrix (Cite Types × Clients)."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.citation_pattern_extractor import CitationPatternExtractor


OUP_HTML = """<!DOCTYPE html>
<html><body>
<p>
  Direct
  <a class="xref" data-role="bibr" ref-type="bibr" rid="ref-1">Anderson (1978)</a>
  and figure
  <a class="xref" data-role="fig" ref-type="fig" rid="fig-1">Fig. 1</a>.
</p>
<p>
  Indirect
  (<a class="xref" data-role="bibr" ref-type="bibr" rid="ref-2">Kramer, 1997</a>).
</p>
</body></html>
"""

TNF_HTML = """<!DOCTYPE html>
<html><body>
<p>
  Dual
  (<a class="xref" data-role="bibr" ref-type="bibr" rid="ref-10">Baker &amp; Pasuk, 2014</a>).
</p>
<p>
  Another fig
  <a class="xref" data-role="fig" ref-type="fig" rid="fig-2">Figure 2</a>.
</p>
</body></html>
"""


def _make_doc(folder: Path, client: str, html: str, name: str) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    content = folder / f"{name}_original.html"
    content.write_text(html, encoding="utf-8")
    return {
        "folder": str(folder),
        "content_file": str(content),
        "doc_title": name,
        "client": client,
        "doc_type": "Books",
        "identifier": name,
    }


class TestCitationPatternMatrix(unittest.TestCase):
    def setUp(self):
        self.extractor = CitationPatternExtractor()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        oup_doc = _make_doc(self.root / "oup_doc", "OUP", OUP_HTML, "oup_doc")
        tnf_doc = _make_doc(self.root / "tnf_doc", "TNF", TNF_HTML, "tnf_doc")
        self.documents_by_client = {
            "Books|OUP": [oup_doc],
            "Books|TNF": [tnf_doc],
        }

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_matrix_shape_two_clients(self):
        rows, clients, _detail, cite_details, _meta = self.extractor.build_matrix_data(
            self.documents_by_client, cite_type="All"
        )
        self.assertEqual(clients, ["OUP", "TNF"])
        cite_types = [r["cite_type"] for r in rows]
        self.assertIn("bibr", cite_types)
        self.assertIn("fig", cite_types)
        self.assertGreaterEqual(len(cite_details), 4)

        bibr_row = next(r for r in rows if r["cite_type"] == "bibr")
        self.assertIsNotNone(bibr_row["OUP"])
        self.assertIsNotNone(bibr_row["TNF"])
        self.assertGreaterEqual(bibr_row["OUP"]["total_count"], 2)
        self.assertGreaterEqual(bibr_row["TNF"]["total_count"], 1)
        self.assertTrue(bibr_row["OUP"]["patterns"])
        self.assertTrue(bibr_row["TNF"]["patterns"])

    def test_cite_type_bibr_excludes_fig_rows(self):
        rows, clients, _detail, cite_details, _meta = self.extractor.build_matrix_data(
            self.documents_by_client, cite_type="bibr"
        )
        self.assertEqual(clients, ["OUP", "TNF"])
        cite_types = [r["cite_type"] for r in rows]
        self.assertIn("bibr", cite_types)
        self.assertNotIn("fig", cite_types)
        self.assertTrue(all(c["cite_type"] == "bibr" for c in cite_details))

    def test_html_report_title(self):
        rows, clients, detail, cite_details, meta = self.extractor.build_matrix_data(
            self.documents_by_client, cite_type="All"
        )
        html = self.extractor.generate_html_report(
            root_path=str(self.root),
            doc_type="Books",
            client_filter="All",
            cite_type="All",
            rows=rows,
            clients=clients,
            detail_data=detail,
            cite_details=cite_details,
            total_docs=2,
            doc_metadata=meta,
        )
        self.assertIn("Citation Pattern Matrix (Cite Types × Clients)", html)
        self.assertIn("Citation Pattern Extraction Report", html)


if __name__ == "__main__":
    unittest.main()

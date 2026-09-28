"""Tests for core.dtd_report - DOCTYPE parse, basename uniqueness, writers."""
from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from core import dtd_report as dr


BITS_SYSTEM = (
    '<!DOCTYPE book SYSTEM '
    '"//t-b-indmenu/AutoProofHub/oupbits/impact/BITS-book-oasis2-1.dtd">'
)

SAMPLE_BITS = f"""<?xml version="1.0" encoding="UTF-8"?>
{BITS_SYSTEM}
<book>
  <front-matter><book-meta><book-id>x</book-id></book-meta></front-matter>
  <book-body><book-part><body><p>hi</p></body></book-part></book-body>
</book>
"""

SAMPLE_JATS_PUBLIC = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Archiving and Interchange DTD v1.2 20190208//EN" "JATS-archivearticle1-mathml3.dtd">
<article>
  <front><article-meta><article-id>a1</article-id></article-meta></front>
  <body><p>x</p></body>
  <back><ref-list><ref><p>r</p></ref></ref-list></back>
</article>
"""

SAMPLE_NO_DTD = """<?xml version="1.0" encoding="UTF-8"?>
<article><front/><body><p>x</p></body></article>
"""

# Same basename, different SYSTEM host path -> still one unique key
SAMPLE_BITS_ALT_HOST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE book SYSTEM "//other-host/share/BITS-book-oasis2-1.dtd">
<book><front-matter/><book-body><p>y</p></book-body></book>
"""


class TestDTDReport(unittest.TestCase):
    def setUp(self):
        self._prev_root = dr.REPORT_ROOT
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        dr.REPORT_ROOT = self.tmp / "reports"

    def tearDown(self):
        dr.REPORT_ROOT = self._prev_root
        self._tmpdir.cleanup()

    def _write(self, name: str, content: str) -> Path:
        p = self.tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_parse_system_doctype_and_basename(self):
        parsed = dr.parse_doctype_text(BITS_SYSTEM)
        self.assertEqual(parsed["doctype_root"], "book")
        self.assertEqual(parsed["public_id"], "")
        self.assertIn("BITS-book-oasis2-1.dtd", parsed["system_id"])
        self.assertEqual(parsed["dtd_basename"], "BITS-book-oasis2-1.dtd")

    def test_parse_public_doctype(self):
        text = (
            '<!DOCTYPE article PUBLIC "-//NLM//DTD JATS//EN" '
            '"JATS-archivearticle1-mathml3.dtd">'
        )
        parsed = dr.parse_doctype_text(text)
        self.assertEqual(parsed["doctype_root"], "article")
        self.assertIn("NLM", parsed["public_id"])
        self.assertEqual(parsed["system_id"], "JATS-archivearticle1-mathml3.dtd")
        self.assertEqual(parsed["dtd_basename"], "JATS-archivearticle1-mathml3.dtd")

    def test_dtd_basename_unc_and_backslash(self):
        self.assertEqual(
            dr.dtd_basename(r"\\server\share\path\foo.dtd"),
            "foo.dtd",
        )
        self.assertEqual(
            dr.dtd_basename("//t-b-indmenu/AutoProofHub/oupbits/impact/BITS-book-oasis2-1.dtd"),
            "BITS-book-oasis2-1.dtd",
        )

    def test_extract_file_bits_and_jats(self):
        bits = self._write("bits.xml", SAMPLE_BITS)
        jats = self._write("jats.xml", SAMPLE_JATS_PUBLIC)
        none = self._write("none.xml", SAMPLE_NO_DTD)

        b = dr.extract_file(bits)
        self.assertTrue(b["has_doctype"])
        self.assertEqual(b["doctype_root"], "book")
        self.assertEqual(b["dtd_basename"], "BITS-book-oasis2-1.dtd")
        self.assertIsNone(b["error"])

        j = dr.extract_file(jats)
        self.assertEqual(j["doctype_root"], "article")
        self.assertEqual(j["dtd_basename"], "JATS-archivearticle1-mathml3.dtd")
        self.assertIn("NLM", j["public_id"])

        n = dr.extract_file(none)
        self.assertFalse(n["has_doctype"])
        self.assertEqual(n["dtd_basename"], "")

    def test_client_unique_merges_same_basename(self):
        a = self._write("a/doc.xml", SAMPLE_BITS)
        b = self._write("b/doc.xml", SAMPLE_BITS_ALT_HOST)
        rows = [
            {
                "client": "OUP",
                "docid": "d1",
                "file_id": "f1",
                "shortcode": "sc1",
                **dr.extract_file(a),
            },
            {
                "client": "OUP",
                "docid": "d2",
                "file_id": "f2",
                "shortcode": "sc2",
                **dr.extract_file(b),
            },
            {
                "client": "WK",
                "docid": "d3",
                "file_id": "f3",
                "shortcode": "sc3",
                **dr.extract_file(self._write("c/jats.xml", SAMPLE_JATS_PUBLIC)),
            },
        ]
        merged = dr._merge_client_unique(rows)
        self.assertEqual(len(merged["OUP"]), 1)
        oup = merged["OUP"][0]
        self.assertEqual(oup["dtd_basename"], "BITS-book-oasis2-1.dtd")
        self.assertEqual(oup["file_count"], 2)
        self.assertEqual(len(oup["system_ids"]), 2)  # full SYSTEM retained
        self.assertEqual(len(merged["WK"]), 1)
        self.assertEqual(merged["WK"][0]["dtd_basename"], "JATS-archivearticle1-mathml3.dtd")

    def test_run_writes_tsv_html_client_unique_digest(self):
        folder = self.tmp / "scan"
        folder.mkdir()
        (folder / "one.xml").write_text(SAMPLE_BITS, encoding="utf-8")
        (folder / "two.xml").write_text(SAMPLE_JATS_PUBLIC, encoding="utf-8")
        # meta.json keyed by parent folder name - flat scan uses stem when no meta
        result = dr.run_dtd_report(folder, folder_mode=True, report_dir=self.tmp / "out")
        self.assertEqual(result["n_files"], 2)
        tsv = Path(result["tsv_path"])
        html = Path(result["html_path"])
        cu_html = Path(result["client_unique_html"])
        cu_csv = Path(result["client_unique_csv"])
        digest_html = Path(result["unique_digest_html"])
        digest_txt = Path(result["unique_digest_txt"])
        for p in (tsv, html, cu_html, cu_csv, digest_html, digest_txt):
            self.assertTrue(p.is_file(), msg=str(p))

        with open(tsv, encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter="\t")
            headers = next(reader)
        self.assertEqual(headers, dr.TSV_HEADERS)
        self.assertIn("DocType", headers)
        self.assertIn("DTD_basename", headers)
        self.assertIn("SYSTEM", headers)
        self.assertIn("PUBLIC", headers)
        self.assertIn("Client", headers)
        self.assertIn("File_id_Docid", headers)

        html_text = html.read_text(encoding="utf-8")
        self.assertIn("BITS-book-oasis2-1.dtd", html_text)
        self.assertIn("JATS-archivearticle1-mathml3.dtd", html_text)

        digest = digest_txt.read_text(encoding="utf-8")
        self.assertIn("Unique Dig", digest)
        self.assertIn("BITS-book-oasis2-1.dtd", digest)

    def test_folder_meta_lookup_identity(self):
        """BITS/<docid>/file.xml + BITS/meta.json fills client / file-id."""
        bits = self.tmp / "BITS"
        doc_dir = bits / "DOC99"
        doc_dir.mkdir(parents=True)
        (doc_dir / "book.xml").write_text(SAMPLE_BITS, encoding="utf-8")
        meta = {
            "DOC99": {
                "client": "OUP",
                "file-id": "FID-99",
                "project-shortcode": "oupbits",
                "type": "book",
            }
        }
        (bits / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

        result = dr.run_dtd_report(bits, folder_mode=True, report_dir=self.tmp / "out2")
        self.assertEqual(result["n_files"], 1)
        row = result["rows"][0]
        self.assertEqual(row["client"], "OUP")
        self.assertEqual(row["file_id"], "FID-99")
        self.assertEqual(row["docid"], "DOC99")
        self.assertEqual(row["shortcode"], "oupbits")
        self.assertEqual(row["dtd_basename"], "BITS-book-oasis2-1.dtd")

    def test_tab_import(self):
        from tabs.dtd_report_tab import DTDReportTab

        self.assertEqual(DTDReportTab.history_tool_id, "dtd_report")


if __name__ == "__main__":
    unittest.main()

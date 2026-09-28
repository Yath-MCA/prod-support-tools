"""Tests for core.sectional_report — section scoping and unique keys."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from core import sectional_report as sr


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<article xmlns:xlink="http://www.w3.org/1999/xlink">
  <front>
    <article-meta>
      <article-id pub-id-type="doi">10.1000/front-doi</article-id>
      <ext-link ext-link-type="uri" xlink:href="https://example.com/front">Front URI</ext-link>
      <uri>https://example.com/front-uri</uri>
    </article-meta>
  </front>
  <body>
    <p>
      <ext-link ext-link-type="doi" xlink:href="https://doi.org/10.1000/body-doi">10.1000/body-doi</ext-link>
      <ext-link ext-link-type="uri" xlink:href="https://example.com/body">Body link</ext-link>
    </p>
  </body>
  <back>
    <ref-list>
      <ref>
        <pub-id pub-id-type="doi">10.1000/ref-doi</pub-id>
        <ext-link ext-link-type="doi" xlink:href="https://doi.org/10.1000/ref-ext">10.1000/ref-ext</ext-link>
        <uri>https://example.com/ref-uri</uri>
      </ref>
    </ref-list>
    <app-group>
      <app>
        <p>
          <pub-id pub-id-type="doi">10.1000/other-doi</pub-id>
          <ext-link ext-link-type="uri" xlink:href="https://example.com/other">Other</ext-link>
        </p>
      </app>
    </app-group>
  </back>
</article>
"""

# Two docs with different hrefs but same tag+type+section — must merge.
SAMPLE_XML_A = """<?xml version="1.0" encoding="UTF-8"?>
<article>
  <front><article-meta>
    <ext-link ext-link-type="uri" href="https://aaa.example/1">A1</ext-link>
  </article-meta></front>
  <body><p>x</p></body>
  <back><ref-list><ref><p>r</p></ref></ref-list></back>
</article>
"""

SAMPLE_XML_B = """<?xml version="1.0" encoding="UTF-8"?>
<article>
  <front><article-meta>
    <ext-link ext-link-type="uri" href="https://bbb.example/2">B2</ext-link>
  </article-meta></front>
  <body><p>y</p></body>
  <back><ref-list><ref><p>r</p></ref></ref-list></back>
</article>
"""



BITS_SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<book xmlns:xlink="http://www.w3.org/1999/xlink">
  <front-matter>
    <book-meta>
      <book-id book-id-type="doi">10.1000/bits-front-doi</book-id>
    </book-meta>
    <uri>https://example.com/bits-front-uri</uri>
  </front-matter>
  <book-body>
    <book-part>
      <body>
        <p>
          <ext-link ext-link-type="uri" xlink:href="https://example.com/bits-body">Body</ext-link>
        </p>
      </body>
      <back>
        <ref-list>
          <ref>
            <ext-link ext-link-type="doi" xlink:href="https://doi.org/10.1000/bits-ref">10.1000/bits-ref</ext-link>
          </ref>
        </ref-list>
        <ack>
          <p>thanks</p>
        </ack>
      </back>
    </book-part>
  </book-body>
</book>
"""


class TestSectionalReport(unittest.TestCase):
    def setUp(self):
        self._prev_root = sr.REPORT_ROOT
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        sr.REPORT_ROOT = self.tmp / "reports"

    def tearDown(self):
        sr.REPORT_ROOT = self._prev_root
        self._tmpdir.cleanup()

    def _write(self, name: str, content: str) -> Path:
        p = self.tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_section_counts_and_ref_vs_other_scoping(self):
        xml = self._write("doc1.xml", SAMPLE_XML)
        result = sr.extract_file(xml)

        self.assertIsNone(result["error"])
        self.assertEqual(result["section_counts"]["FRONT"], 1)
        self.assertEqual(result["section_counts"]["BODY"], 1)
        self.assertEqual(result["section_counts"]["REF"], 1)
        self.assertEqual(result["section_counts"]["OTHER"], 1)  # app-group only

        # REF gets ref-list DOIs; OTHER gets app-group DOI — not swapped
        self.assertEqual(result["per_section"]["REF"]["doi_id"]["count"], 1)
        self.assertEqual(result["per_section"]["OTHER"]["doi_id"]["count"], 1)
        ref_texts = [h["text"] for h in result["per_section"]["REF"]["doi_id"]["hits"]]
        other_texts = [h["text"] for h in result["per_section"]["OTHER"]["doi_id"]["hits"]]
        self.assertTrue(any("ref-doi" in t for t in ref_texts))
        self.assertTrue(any("other-doi" in t for t in other_texts))
        self.assertFalse(any("other-doi" in t for t in ref_texts))
        self.assertFalse(any("ref-doi" in t for t in other_texts))

        # FRONT doi_id
        self.assertEqual(result["per_section"]["FRONT"]["doi_id"]["count"], 1)
        # BODY extlink_doi
        self.assertEqual(result["per_section"]["BODY"]["extlink_doi"]["count"], 1)
        # REF also has extlink_doi
        self.assertEqual(result["per_section"]["REF"]["extlink_doi"]["count"], 1)

        # Aggregate query totals = sum across sections
        self.assertEqual(
            result["query_totals"]["doi_id"],
            result["per_section"]["FRONT"]["doi_id"]["count"]
            + result["per_section"]["BODY"]["doi_id"]["count"]
            + result["per_section"]["REF"]["doi_id"]["count"]
            + result["per_section"]["OTHER"]["doi_id"]["count"],
        )
        # front article-id, ref pub-id, other pub-id = 3
        self.assertEqual(result["query_totals"]["doi_id"], 3)

    def test_tsv_headers_and_row_sums(self):
        xml = self._write("folder/a.xml", SAMPLE_XML)
        out = sr.run_sectional_report(xml.parent, folder_mode=True, log=lambda m: None)
        tsv = Path(out["tsv_path"])
        self.assertTrue(tsv.is_file())
        with open(tsv, encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter="\t")
            headers = next(reader)
            row = next(reader)
        self.assertEqual(headers, sr.TSV_HEADERS)
        # Docid = stem, File_id empty in folder mode
        self.assertEqual(row[0], "a")
        self.assertEqual(row[1], "")
        # FRONT BODY REF OTHER
        self.assertEqual(int(row[2]), 1)
        self.assertEqual(int(row[3]), 1)
        self.assertEqual(int(row[4]), 1)
        self.assertEqual(int(row[5]), 1)
        # query cols
        self.assertEqual(int(row[6]), 3)  # doi_id sum
        self.assertGreaterEqual(int(row[7]), 1)  # extlink_doi
        self.assertGreaterEqual(int(row[8]), 1)  # extlink_uri
        self.assertGreaterEqual(int(row[9]), 1)  # uri

    def test_client_unique_merges_without_href(self):
        a = self._write("proj/JATS/D1/doc.xml", SAMPLE_XML_A)
        b = self._write("proj/JATS/D2/doc.xml", SAMPLE_XML_B)
        # Build minimal project
        proj = self.tmp / "proj"
        docs = {
            "D1": {"folder": "JATS/D1", "files": {"xml": "JATS/D1/doc.xml"}},
            "D2": {"folder": "JATS/D2", "files": {"xml": "JATS/D2/doc.xml"}},
        }
        metas = {
            "D1": {
                "dtd": "JATS",
                "client": "ClientX",
                "project-shortcode": "SC1",
                "file-id": "F1",
            },
            "D2": {
                "dtd": "JATS",
                "client": "ClientX",
                "project-shortcode": "SC1",
                "file-id": "F2",
            },
        }
        import json

        (proj / "documents.json").write_text(json.dumps(docs), encoding="utf-8")
        (proj / "meta.json").write_text(json.dumps(metas), encoding="utf-8")

        out = sr.run_sectional_report(proj, log=lambda m: None)
        self.assertEqual(out["n_files"], 2)
        rows = out["rows"]
        self.assertEqual(rows[0]["file_id"], "F1")
        self.assertEqual(rows[1]["file_id"], "F2")

        merged = sr._merge_client_unique(rows)
        self.assertIn("ClientX", merged)
        # Both FRONT ext-link uri should be one bucket despite different hrefs
        front_uri = [
            e
            for e in merged["ClientX"]
            if e["section"] == "FRONT"
            and e["tag"] == "ext-link"
            and e["type_attr"] == "ext-link-type"
            and e["type_value"] == "uri"
        ]
        self.assertEqual(len(front_uri), 1)
        self.assertEqual(front_uri[0]["count"], 2)
        self.assertEqual(sorted(front_uri[0]["sample_docids"]), ["D1", "D2"])

        # CSV exists and has no href column
        cu_csv = Path(out["client_unique_csv"])
        with open(cu_csv, encoding="utf-8", newline="") as f:
            headers = next(csv.reader(f))
        self.assertNotIn("href", headers)
        self.assertIn("type_attr", headers)
        self.assertIn("section", headers)

    def test_missing_file_id_still_emits_docid(self):
        xml = self._write("lonely.xml", SAMPLE_XML)
        result = sr.extract_file(xml)
        out_rows = [
            {
                "docid": "lonely",
                "file_id": "",
                "client": "",
                "shortcode": "",
                **result,
            }
        ]
        tsv = sr.write_tsv(out_rows, self.tmp / "out.tsv")
        with open(tsv, encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f, delimiter="\t"))
        self.assertEqual(rows[1][0], "lonely")
        self.assertEqual(rows[1][1], "")


    def test_bits_front_matter_and_ref_scoping(self):
        """BITS book: front-matter counts as FRONT; doi ext-link under ref-list is REF not OTHER."""
        xml = self._write("bits_book.xml", BITS_SAMPLE_XML)
        result = sr.extract_file(xml)

        self.assertIsNone(result["error"])
        # front-matter (+ nested book-meta also matches FRONT roots set)
        self.assertGreaterEqual(result["section_counts"]["FRONT"], 1)
        self.assertGreaterEqual(result["section_counts"]["BODY"], 1)
        self.assertEqual(result["section_counts"]["REF"], 1)
        self.assertEqual(result["section_counts"]["OTHER"], 1)  # ack under back

        # uri under front-matter counts under FRONT
        self.assertGreaterEqual(result["per_section"]["FRONT"]["uri"]["count"], 1)
        front_uri_texts = [h["text"] for h in result["per_section"]["FRONT"]["uri"]["hits"]]
        self.assertTrue(any("bits-front-uri" in t for t in front_uri_texts))

        # doi ext-link under ref-list -> REF, not OTHER
        self.assertEqual(result["per_section"]["REF"]["extlink_doi"]["count"], 1)
        self.assertEqual(result["per_section"]["OTHER"]["extlink_doi"]["count"], 0)
        ref_texts = [h["text"] for h in result["per_section"]["REF"]["extlink_doi"]["hits"]]
        self.assertTrue(any("bits-ref" in t for t in ref_texts))


if __name__ == "__main__":
    unittest.main()

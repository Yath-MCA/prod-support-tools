"""Tests for core.fn_group_report - pattern normalize, placement, enrich, uniqueness."""
from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from lxml import etree

from core import fn_group_report as fgr


TNF_CHAPTER = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE book SYSTEM "BITS.dtd">
<book id="book-001">
  <book-body>
    <book-part book-part-type="chapter" id="book-part-001">
      <body><p>text<xref ref-type="fn" rid="fn1">1</xref></p></body>
      <back>
        <fn-group content-type="endnotes" id="fn-group-001" class="fn-group">
          <fn id="fn1"><p>note</p></fn>
        </fn-group>
        <ref-list id="ref-list-001"><ref id="r1"><p>ref</p></ref></ref-list>
      </back>
    </book-part>
    <book-part book-part-type="chapter" id="book-part-002">
      <back>
        <fn-group content-type="endnotes" id="fn-group-002" class="fn-group">
          <fn id="fn2"><p>note2</p></fn>
        </fn-group>
      </back>
    </book-part>
  </book-body>
  <book-back>
    <ref-list id="book-ref-list"><ref id="br1"><p>book ref</p></ref></ref-list>
  </book-back>
</book>
"""

TNF_WITH_TABLE_FN = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE book SYSTEM "BITS.dtd">
<book id="book-001">
  <book-body>
    <book-part book-part-type="chapter" id="book-part-001">
      <back>
        <fn-group content-type="endnotes" id="fn-group-001">
          <fn id="fn1"><p>note</p></fn>
        </fn-group>
      </back>
    </book-part>
  </book-body>
  <book-back>
    <app-group>
      <app>
        <table-wrap>
          <table-wrap-foot>
            <fn-group content-type="table-fn" id="tfn-1">
              <fn id="t1"><p>table note</p></fn>
            </fn-group>
          </table-wrap-foot>
        </table-wrap>
        <fn-group content-type="endnotes" id="fn-group-book">
          <fn id="fnb"><p>book note</p></fn>
        </fn-group>
      </app>
    </app-group>
  </book-back>
</book>
"""

MULTI_BOOK_END = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE book SYSTEM "BITS.dtd">
<book>
  <book-back>
    <fn-group content-type="endnotes" id="fn-group-a"><fn id="a"><p>a</p></fn></fn-group>
    <fn-group content-type="endnotes" id="fn-group-b"><fn id="b"><p>b</p></fn></fn-group>
  </book-back>
</book>
"""

OSO_OASIS = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE book SYSTEM "//t-b-indmenu/AutoProofHub/oupbits/impact/BITS-book-oasis2-1.dtd">
<book>
  <front-matter>
    <front-matter-part book-part-type="introduction" id="fm-1">
      <named-book-part-body>
        <sec id="sec-1">
          <fn-group content-type="footnotes" id="workid-USAC0026086-fm-fn-group-1">
            <fn id="fn0"><p>front note</p></fn>
          </fn-group>
        </sec>
      </named-book-part-body>
    </front-matter-part>
  </front-matter>
  <book-body>
    <book-part book-part-type="chapter" id="workid-USAC0026086-book-part-2">
      <back>
        <fn-group content-type="footnotes" id="workid-USAC0026086-book-part-2-fn-group-1">
          <fn id="fn1"><p>ch note</p></fn>
        </fn-group>
      </back>
    </book-part>
  </book-body>
</book>
"""


class TestFnGroupReport(unittest.TestCase):
    def setUp(self):
        self._prev_root = fgr.REPORT_ROOT
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        fgr.REPORT_ROOT = self.tmp / "reports"

    def tearDown(self):
        fgr.REPORT_ROOT = self._prev_root
        self._tmpdir.cleanup()

    def _write(self, name: str, content: str) -> Path:
        p = self.tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_pattern_drops_id_keeps_stable_attrs(self):
        root = etree.fromstring(
            b"""<book id="book-001"><book-body>
            <book-part book-part-type="chapter" id="bp1">
              <back><fn-group content-type="endnotes" id="fn-group-001" class="fn-group"/>
              </back></book-part></book-body></book>"""
        )
        fg = root.xpath('//*[local-name()="fn-group"]')[0]
        pat = fgr.pattern_xpath_for_element(fg)
        self.assertNotIn("id=", pat)
        self.assertNotIn("fn-group-001", pat)
        self.assertIn('book-part[book-part-type="chapter"]', pat)
        self.assertIn('content-type="endnotes"', pat)
        self.assertIn('class="fn-group"', pat)
        self.assertIn(".fn-group", pat)

    def test_two_chapter_endnotes_one_unique_key(self):
        xml = self._write("tnf.xml", TNF_CHAPTER)
        targets, excl = fgr.extract_targets(xml)
        self.assertEqual(excl, 0)
        fns = [t for t in targets if t["kind"] == "fn-group"]
        self.assertEqual(len(fns), 2)
        self.assertEqual(fns[0]["pattern_xpath"], fns[1]["pattern_xpath"])
        self.assertEqual(fns[0]["placement"], "chapter-end")
        self.assertIn(".book-body", fns[0]["pattern_xpath"])
        detail = [
            {
                "client": "TNF",
                "dtd_basename": "BITS.dtd",
                "kind": t["kind"],
                "placement": t["placement"],
                "pattern_xpath": t["pattern_xpath"],
                "file_id": "f1",
                "docid": "d1",
                "element_id": t["element_id"],
                "dtd_mismatch": "",
                "error": "",
            }
            for t in fns
        ]
        unique = fgr.rollup_unique(detail)
        fn_unique = [u for u in unique if u["kind"] == "fn-group"]
        self.assertEqual(len(fn_unique), 1)
        self.assertEqual(fn_unique[0]["occurrence_count"], 2)

    def test_excludes_table_fn(self):
        xml = self._write("tablefn.xml", TNF_WITH_TABLE_FN)
        targets, excl = fgr.extract_targets(xml)
        self.assertEqual(excl, 1)
        fns = [t for t in targets if t["kind"] == "fn-group"]
        self.assertEqual(len(fns), 2)
        for t in fns:
            self.assertNotIn("table-fn", t["pattern_xpath"])
        book_end = [t for t in fns if t["placement"] == "book-end"]
        self.assertEqual(len(book_end), 1)
        self.assertIn(".book-back", book_end[0]["pattern_xpath"])
        self.assertNotIn(".book-body", book_end[0]["pattern_xpath"])

    def test_book_end_never_under_book_body(self):
        xml = self._write("tnf2.xml", TNF_CHAPTER)
        targets, _ = fgr.extract_targets(xml)
        for t in targets:
            if t["placement"] == "book-end":
                self.assertIn(".book-back", t["pattern_xpath"])
                self.assertNotIn(".book-body", t["pattern_xpath"])
            if t["placement"] == "chapter-end":
                self.assertIn(".book-body", t["pattern_xpath"])

    def test_multiple_book_end_fn_group_warning(self):
        xml = self._write("multi.xml", MULTI_BOOK_END)
        targets, _ = fgr.extract_targets(xml)
        detail = [
            {
                "client": "TNF",
                "dtd_basename": "BITS.dtd",
                "docid": "Nd1",
                "file_id": "f1",
                "kind": t["kind"],
                "placement": t["placement"],
                "pattern_xpath": t["pattern_xpath"],
                "element_id": t["element_id"],
                "cardinality_warning": "",
                "error": "",
            }
            for t in targets
            if t["kind"] == "fn-group"
        ]
        self.assertEqual(len(detail), 2)
        fgr.apply_book_end_cardinality_warnings(detail)
        self.assertTrue(
            all("multiple_book_end_fn_group" in (r.get("cardinality_warning") or "") for r in detail)
        )

    def test_book_back_ref_list_is_book_end(self):
        xml = self._write("tnf2b.xml", TNF_CHAPTER)
        targets, _ = fgr.extract_targets(xml)
        refs = [t for t in targets if t["kind"] == "ref-list"]
        placements = {t["placement"] for t in refs}
        self.assertIn("chapter-end", placements)
        self.assertIn("book-end", placements)
        book_end = [t for t in refs if t["placement"] == "book-end"]
        self.assertEqual(len(book_end), 1)
        self.assertIn(".book-back", book_end[0]["pattern_xpath"])

    def test_id_pattern_and_area_category(self):
        xml = self._write("oso_id.xml", OSO_OASIS)
        targets, _ = fgr.extract_targets(xml)
        chapter = [
            t
            for t in targets
            if t["kind"] == "fn-group" and t["placement"] == "chapter-end"
        ][0]
        self.assertEqual(chapter["area_category"], "body")
        self.assertIn("{work}", chapter["id_pattern"])
        self.assertIn("fn-group", chapter["id_pattern"])
        self.assertNotIn("USAC", chapter["id_pattern"])

        tnf = self._write("tnf_id.xml", TNF_CHAPTER)
        tnf_targets, _ = fgr.extract_targets(tnf)
        tnf_fn = [t for t in tnf_targets if t["kind"] == "fn-group"][0]
        self.assertEqual(tnf_fn["id_pattern"], "fn-group-{nnn}")
        self.assertEqual(tnf_fn["area_category"], "body")

    def test_oso_front_matter_and_oasis_basename(self):
        xml = self._write("oso.xml", OSO_OASIS)
        info = fgr.resolve_dtd_basename(xml)
        self.assertEqual(info["dtd_basename"], "BITS-book-oasis2-1.dtd")
        targets, _ = fgr.extract_targets(xml)
        fns = [t for t in targets if t["kind"] == "fn-group"]
        placements = {t["placement"] for t in fns}
        self.assertIn("front-matter", placements)
        self.assertIn("chapter-end", placements)
        for t in fns:
            self.assertIn('content-type="footnotes"', t["pattern_xpath"])
            self.assertNotIn("workid-", t["pattern_xpath"])

    def test_enrich_writes_meta_and_documents(self):
        project = self.tmp / "proj"
        bits_dir = project / "BITS" / "Ndoc1"
        bits_dir.mkdir(parents=True)
        xml = bits_dir / "Ndoc1_original.xml"
        xml.write_text(OSO_OASIS, encoding="utf-8")

        meta = {
            "Ndoc1": {
                "client": "OSO",
                "dtd": "BITS",
                "file-id": "9780197909348_Impact",
                "project-shortcode": "MRM",
                "type": "Books",
            }
        }
        documents = {
            "Ndoc1": {
                "docid": "Ndoc1",
                "folder": "BITS/Ndoc1",
                "meta": {
                    "client": "OSO",
                    "file-id": "9780197909348_Impact",
                    "project-shortcode": "MRM",
                    "type": "Books",
                },
                "files": {"xml": [str(xml.name)]},
            }
        }
        project.mkdir(parents=True, exist_ok=True)
        (project / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        (project / "documents.json").write_text(
            json.dumps(documents, indent=2), encoding="utf-8"
        )

        docs = [
            {
                "docid": "Ndoc1",
                "xml_path": str(xml),
                "client": "OSO",
                "file_id": "9780197909348_Impact",
                "doc_type": "Books",
                "dtd": "BITS",
            }
        ]
        stats = fgr.enrich_meta_dtd_basename(project, docs=docs)
        self.assertGreaterEqual(stats["updated_meta"], 1)

        metas = json.loads((project / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(metas["Ndoc1"]["dtd_basename"], "BITS-book-oasis2-1.dtd")
        self.assertEqual(metas["Ndoc1"]["dtd"], "BITS")

        docs_json = json.loads((project / "documents.json").read_text(encoding="utf-8"))
        self.assertEqual(
            docs_json["Ndoc1"]["meta"]["dtd_basename"], "BITS-book-oasis2-1.dtd"
        )

    def test_run_report_smoke_synthetic(self):
        project = self.tmp / "runproj"
        d1 = project / "BITS" / "Nd1"
        d2 = project / "BITS" / "Nd2"
        d1.mkdir(parents=True)
        d2.mkdir(parents=True)
        (d1 / "Nd1_original.xml").write_text(TNF_WITH_TABLE_FN, encoding="utf-8")
        (d2 / "Nd2_original.xml").write_text(OSO_OASIS, encoding="utf-8")

        meta = {
            "Nd1": {
                "client": "TNF",
                "dtd": "BITS",
                "file-id": "tnf1",
                "project-shortcode": "IPT",
                "type": "Books",
            },
            "Nd2": {
                "client": "OSO",
                "dtd": "BITS",
                "file-id": "oso1",
                "project-shortcode": "MRM",
                "type": "Books",
            },
        }
        documents = {
            "Nd1": {
                "docid": "Nd1",
                "folder": "BITS/Nd1",
                "meta": dict(meta["Nd1"]),
            },
            "Nd2": {
                "docid": "Nd2",
                "folder": "BITS/Nd2",
                "meta": dict(meta["Nd2"]),
            },
        }
        project.mkdir(parents=True, exist_ok=True)
        (project / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        (project / "documents.json").write_text(
            json.dumps(documents, indent=2), encoding="utf-8"
        )

        result = fgr.run_fn_group_report(project, update_meta=True)
        self.assertEqual(result["report_version"], 2)
        self.assertEqual(result["n_docs"], 2)
        self.assertGreaterEqual(result["excluded_table_fn"], 1)
        self.assertGreaterEqual(result["n_unique"], 2)
        self.assertTrue(Path(result["html_path"]).is_file())
        self.assertTrue(Path(result["csv_path"]).is_file())
        self.assertTrue(Path(result["id_patterns_csv_path"]).is_file())

        html = Path(result["html_path"]).read_text(encoding="utf-8")
        self.assertIn("Open File", html)
        self.assertIn("Copy Path", html)
        self.assertIn("copyFilePath", html)
        self.assertIn("ID patterns by category", html)
        # Pattern cells must not include table-fn content-type (meta may say "table-fn excluded")
        self.assertNotIn('content-type=&quot;table-fn&quot;', html)
        self.assertNotIn('content-type="table-fn"', html)

        with open(result["csv_path"], encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertTrue(all("table-fn" not in (r.get("pattern_xpath") or "") for r in rows))
        tnf_fn = [
            r
            for r in rows
            if r["client"] == "TNF"
            and r["kind"] == "fn-group"
            and r["placement"] == "chapter-end"
        ]
        self.assertTrue(tnf_fn)
        self.assertIn("endnotes", tnf_fn[0]["pattern_xpath"])
        book_end = [
            r
            for r in rows
            if r["kind"] == "fn-group" and r["placement"] == "book-end"
        ]
        for r in book_end:
            self.assertIn(".book-back", r["pattern_xpath"])
            self.assertNotIn(".book-body", r["pattern_xpath"])

        with open(result["id_patterns_csv_path"], encoding="utf-8", newline="") as f:
            id_rows = list(csv.DictReader(f))
        self.assertTrue(id_rows)
        self.assertTrue(any(r.get("area_category") for r in id_rows))

        metas = json.loads((project / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(metas["Nd1"]["dtd_basename"], "BITS.dtd")
        self.assertEqual(metas["Nd2"]["dtd_basename"], "BITS-book-oasis2-1.dtd")

    def test_dtd_mismatch_warning(self):
        self.assertEqual(fgr.dtd_mismatch_warning("TNF", "BITS.dtd"), "")
        self.assertIn("expected", fgr.dtd_mismatch_warning("TNF", "BITS-book-oasis2-1.dtd"))
        self.assertEqual(fgr.dtd_mismatch_warning("OSO", "BITS-book-oasis2-1.dtd"), "")


if __name__ == "__main__":
    unittest.main()

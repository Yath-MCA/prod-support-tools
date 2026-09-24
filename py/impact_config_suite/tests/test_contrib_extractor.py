#!/usr/bin/env python3
"""Unit tests for core.contrib_extractor helpers and shortcode processing."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import contrib_extractor as ce


MINIMAL_CONTRIB_XML = """<?xml version="1.0" encoding="UTF-8"?>
<article>
  <front>
    <article-meta>
      <contrib-group>
        <contrib contrib-type="author">
          <name><surname>Doe</surname><given-names>Jane</given-names></name>
        </contrib>
        <contrib contrib-type="author">
          <name><surname>Smith</surname><given-names>John</given-names></name>
        </contrib>
        <contrib contrib-type="author">
          <name><surname>Lee</surname><given-names>A</given-names></name>
        </contrib>
      </contrib-group>
    </article-meta>
  </front>
</article>
"""

BROKEN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<article><front><article-meta><p>no contrib group</p></article-meta></front></article>
"""


class TestStatusOf(unittest.TestCase):
    def test_new_when_missing(self):
        st, n = ce.status_of({}, "LWW", "INF", ["a", "b"])
        self.assertEqual(st, "new")
        self.assertEqual(n, 0)

    def test_done_when_all_recorded(self):
        done = {
            "JATS": {
                "LWW": {
                    "INF": {
                        "generated_at": "2026-09-23 19:10",
                        "version": ce.SCRIPT_VERSION,
                        "failed": 0,
                        "docids": {"a": {"status": "ok"}, "b": {"status": "ok"}},
                    }
                }
            }
        }
        st, n = ce.status_of(done, "LWW", "INF", ["a", "b"])
        self.assertEqual(st, "done")
        self.assertEqual(n, 0)
        self.assertIn("filled", ce.status_note(done, "LWW", "INF", ["a", "b"]))

    def test_update_when_fresh_docs(self):
        done = {
            "JATS": {
                "LWW": {
                    "INF": {
                        "generated_at": "2026-09-23 19:10",
                        "failed": 0,
                        "docids": {"a": {"status": "ok"}},
                    }
                }
            }
        }
        st, n = ce.status_of(done, "LWW", "INF", ["a", "b", "c"])
        self.assertEqual(st, "update")
        self.assertEqual(n, 2)
        note = ce.status_note(done, "LWW", "INF", ["a", "b", "c"])
        self.assertIn("update", note)
        self.assertIn("+2", note)

    def test_update_when_older_version(self):
        done = {
            "JATS": {
                "LWW": {
                    "INF": {
                        "generated_at": "2026-09-23 19:10",
                        "version": 1,
                        "failed": 0,
                        "docids": {"a": {"status": "ok"}, "b": {"status": "ok"}},
                    }
                }
            }
        }
        st, n = ce.status_of(done, "LWW", "INF", ["a", "b"])
        self.assertEqual(st, "update")
        self.assertEqual(n, 0)
        note = ce.status_note(done, "LWW", "INF", ["a", "b"])
        self.assertEqual(note, "update (older script version, regenerate)")

    def test_update_when_version_missing(self):
        done = {
            "JATS": {
                "LWW": {
                    "INF": {
                        "generated_at": "2026-09-23 19:10",
                        "failed": 0,
                        "docids": {"a": {"status": "ok"}, "b": {"status": "ok"}},
                    }
                }
            }
        }
        st, n = ce.status_of(done, "LWW", "INF", ["a", "b"])
        self.assertEqual(st, "update")
        self.assertEqual(n, 0)
        self.assertIn("older script version", ce.status_note(done, "LWW", "INF", ["a", "b"]))

    def test_update_when_version_2_under_v9(self):
        """SCRIPT_VERSION=9 treats prior version=2/8 (and legacy logic-only) reports as updates."""
        self.assertEqual(ce.SCRIPT_VERSION, 9)
        done = {
            "JATS": {
                "LWW": {
                    "INF": {
                        "generated_at": "2026-09-23 19:10",
                        "version": 2,
                        "failed": 0,
                        "docids": {"a": {"status": "ok"}, "b": {"status": "ok"}},
                    }
                }
            }
        }
        st, n = ce.status_of(done, "LWW", "INF", ["a", "b"])
        self.assertEqual(st, "update")
        self.assertEqual(n, 0)
        self.assertEqual(
            ce.status_note(done, "LWW", "INF", ["a", "b"]),
            "update (older script version, regenerate)",
        )

    def test_update_when_legacy_logic_field_only(self):
        """Older meta entries with logic=3 but no version still count as update."""
        done = {
            "JATS": {
                "LWW": {
                    "INF": {
                        "generated_at": "2026-09-23 19:10",
                        "logic": 3,
                        "failed": 0,
                        "docids": {"a": {"status": "ok"}, "b": {"status": "ok"}},
                    }
                }
            }
        }
        st, n = ce.status_of(done, "LWW", "INF", ["a", "b"])
        self.assertEqual(st, "update")
        self.assertEqual(n, 0)


class TestXrefHelpers(unittest.TestCase):
    def _contrib(self, xml: str):
        import xml.etree.ElementTree as ET
        return ET.fromstring(xml)

    def test_xref_key_buckets_0_1_2_3plus(self):
        c0 = self._contrib("<contrib><name><surname>A</surname></name></contrib>")
        c1 = self._contrib(
            '<contrib><name><surname>A</surname></name>'
            '<xref ref-type="aff" rid="a1">1</xref></contrib>'
        )
        c2 = self._contrib(
            '<contrib><name><surname>A</surname></name>'
            '<xref ref-type="aff" rid="a1">1</xref>'
            '<xref ref-type="fn" rid="f1">*</xref></contrib>'
        )
        c4 = self._contrib(
            '<contrib><name><surname>A</surname></name>'
            + ''.join(f'<xref ref-type="aff" rid="a{i}">{i}</xref>' for i in range(4))
            + '</contrib>'
        )
        self.assertEqual(ce.xref_key(c0), 0)
        self.assertEqual(ce.xref_key(c1), 1)
        self.assertEqual(ce.xref_key(c2), 2)
        self.assertEqual(ce.xref_key(c4), 3)  # 3+ bucket
        self.assertEqual(ce.xref_label(0), "xref 0")
        self.assertEqual(ce.xref_label(2), "xref 2")
        self.assertEqual(ce.xref_label(3), "xref 3+")

    def test_xref_role_first_middle_last_before_last(self):
        # 1 xref -> last only
        self.assertEqual(ce.xref_role(0, 1), "last")
        # 2 xrefs -> last-before, last
        self.assertEqual(ce.xref_role(0, 2), "last-before")
        self.assertEqual(ce.xref_role(1, 2), "last")
        # 3+ -> first, middle..., last-before, last
        self.assertEqual(ce.xref_role(0, 4), "first")
        self.assertEqual(ce.xref_role(1, 4), "middle")
        self.assertEqual(ce.xref_role(2, 4), "last-before")
        self.assertEqual(ce.xref_role(3, 4), "last")

    def test_contrib_class(self):
        self.assertEqual(ce.contrib_class(0, 1), "last")
        self.assertEqual(ce.contrib_class(0, 2), "before")
        self.assertEqual(ce.contrib_class(1, 2), "last")
        self.assertEqual(ce.contrib_class(0, 3), "other")
        self.assertEqual(ce.contrib_class(1, 3), "before")
        self.assertEqual(ce.contrib_class(2, 3), "last")


class TestBuildStatsSubgroups(unittest.TestCase):
    def test_subgroups_structure(self):
        """build_stats cards expose xref subgroups without needing full HTML."""
        import xml.etree.ElementTree as ET

        def row_for(xml: str, docid: str):
            c = ET.fromstring(xml)
            gaps = ce.analyze(c)
            hits = ce.pattern_hits(gaps)
            xk = ce.xref_key(c)
            return {
                "docid": docid,
                "file_id": docid,
                "contribs": [c],
                "gaps": [gaps],
                "hits": [hits],
                "xkeys": [xk],
                "cmp_cls": [("last", xk)],
                "seqs": [ce.pi_sequences(hits)],
                "pat": {},
                "xk": {},
            }

        bare = "<contrib><name><surname>A</surname></name></contrib>"
        with_xref = (
            '<contrib><name><surname>B</surname></name>'
            '<xref ref-type="aff" rid="a1">1</xref></contrib>'
        )
        rows = [
            row_for(bare, "d0a"),
            row_for(bare, "d0b"),
            row_for(with_xref, "d1a"),
        ]
        stats = ce.build_stats(rows, ["last"])  # g1 tab roles
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["roles"], ["last"])
        card = stats["cards"][("last", "attr")]
        self.assertIn("subgroups", card)
        # last column has two xref groups: 0 and 1
        xks = [sg["xk"] for sg in card["subgroups"]]
        self.assertEqual(xks, [0, 1])
        by_xk = {sg["xk"]: sg for sg in card["subgroups"]}
        self.assertEqual(by_xk[0]["files"], 2)
        self.assertEqual(by_xk[1]["files"], 1)
        for sg in card["subgroups"]:
            self.assertTrue(sg["patterns"])
            self.assertEqual(sg["patterns"][0]["n"], 1)
            self.assertEqual(sum(len(p["rows"]) for p in sg["patterns"]), sg["files"])

    def test_seq_diff_slot_by_slot(self):
        base = (",", " and ")
        seq = (",", ", ")
        bad, html_l, plain = ce.seq_diff(base, seq, "attr")
        self.assertEqual(bad, {1})
        self.assertEqual(len(html_l), 1)
        self.assertIn("differs</b> #2", html_l[0])
        self.assertIn("expected", html_l[0])
        self.assertIn("found", html_l[0])
        self.assertTrue(plain)

    def test_pattern_hits_skips_middle_xref(self):
        """Middle xref separators are excluded from patterns (covered by all-contrib PI check)."""
        xml = (
            "<contrib-group>"
            "<contrib>"
            "<name><surname>A</surname></name>"
            '<?pistart xml:space=","?>'
            '<xref ref-type="aff" rid="a1">1</xref>'
            '<?pistart xml:space=" "?>'
            '<xref ref-type="aff" rid="a2">2</xref>'
            '<?pistart xml:space="x"?>'
            '<xref ref-type="aff" rid="a3">3</xref>'
            '<?pistart xml:space="."?>'
            "</contrib>"
            "</contrib-group>"
        )
        root = ce.parse_group(xml)
        c = list(root.iter("contrib"))[0]
        gaps = ce.analyze(c)
        hits = ce.pattern_hits(gaps)
        roles = [g.key[1] for g in hits if isinstance(g.key, tuple) and str(g.key[1]).startswith("xref@")]
        self.assertNotIn("xref@middle", roles)
        for role in roles:
            self.assertIn(role, {"xref@first", "xref@last-before", "xref@last"})


    def test_off_pattern_rows(self):
        rows = [
            {"pat": {("last", "attr"): 1, ("last", "pos"): 1}},
            {"pat": {("last", "attr"): 2, ("last", "pos"): 1}},
            {"pat": {("last", "attr"): None, ("last", "pos"): None}},
        ]
        off = ce.off_pattern_rows(rows)
        self.assertEqual(len(off), 1)
        self.assertEqual(off[0]["pat"][("last", "attr")], 2)


class TestRoleIndex(unittest.TestCase):
    def test_one_contrib_last_only(self):
        self.assertIsNone(ce.role_index(1, "first"))
        self.assertIsNone(ce.role_index(1, "before"))
        self.assertEqual(ce.role_index(1, "last"), 0)

    def test_two_contribs_before_and_last(self):
        self.assertIsNone(ce.role_index(2, "first"))
        self.assertEqual(ce.role_index(2, "before"), 0)
        self.assertEqual(ce.role_index(2, "last"), 1)

    def test_three_plus_first_before_last(self):
        self.assertEqual(ce.role_index(3, "first"), 0)
        self.assertEqual(ce.role_index(3, "before"), 1)
        self.assertEqual(ce.role_index(3, "last"), 2)
        self.assertEqual(ce.role_index(5, "first"), 0)
        self.assertEqual(ce.role_index(5, "before"), 3)
        self.assertEqual(ce.role_index(5, "last"), 4)

    def test_zero_contribs(self):
        self.assertIsNone(ce.role_index(0, "first"))
        self.assertIsNone(ce.role_index(0, "before"))
        self.assertIsNone(ce.role_index(0, "last"))


class TestBuildOverview(unittest.TestCase):
    def setUp(self):
        self.docs = {
            "d1": {"folder": "JATS/d1"},
            "d2": {"folder": "JATS/d2"},
            "d3": {"folder": "BITS/d3"},
            "d4": {"folder": "JATS/d4"},
            "orphan": {"folder": "JATS/orphan"},
        }
        self.metas = {
            "d1": {"dtd": "JATS", "client": "LWW", "project-shortcode": "INF", "file-id": "F1"},
            "d2": {"dtd": "JATS", "client": "LWW", "project-shortcode": "INF", "file-id": "F2"},
            "d3": {"dtd": "BITS", "client": "LWW", "project-shortcode": "BK", "file-id": "F3"},
            "d4": {"dtd": "JATS", "client": "PLOS", "project-shortcode": "PBIO", "file-id": "F4"},
            # orphan doc in docs but no meta — counted in ignored
        }
        self.index = ce.build_index(self.docs, self.metas)
        self.done = {
            "JATS": {
                "LWW": {
                    "INF": {
                        "generated_at": "2026-09-23 19:10",
                        "failed": 0,
                        "docids": {"d1": {"status": "ok"}},
                    }
                }
            }
        }

    def test_index_jats_only(self):
        self.assertIn("LWW", self.index)
        self.assertIn("PLOS", self.index)
        self.assertEqual(sorted(self.index["LWW"]["INF"]), ["d1", "d2"])
        self.assertNotIn("BK", self.index.get("LWW", {}))

    def test_overview_counts(self):
        ov = ce.build_overview(self.docs, self.metas, self.index, self.done)
        self.assertEqual(ov["dtd"], "JATS")
        self.assertEqual(ov["clients"], 2)
        self.assertEqual(ov["shortcodes"], 2)
        self.assertEqual(ov["docs"], 3)  # d1,d2,d4
        self.assertEqual(ov["filled"], 0)  # INF is update (d2 missing)
        self.assertEqual(ov["not_filled"], 1)  # PBIO
        self.assertEqual(ov["update"], 1)  # INF
        notes = " ".join(ov["ignored_notes"])
        self.assertIn("BITS", notes)
        self.assertIn("without a meta.json entry", notes)
        text = ce.format_overview_text(ov)
        self.assertIn("not filled", text)
        self.assertIn("ignored / check", text)


class TestProcessGroupAndMeta(unittest.TestCase):
    def setUp(self):
        # Redirect reports away from real Documents/impact-support-log
        self._report_td = tempfile.TemporaryDirectory()
        self._old_report_root = ce.REPORT_ROOT
        ce.REPORT_ROOT = Path(self._report_td.name) / "Documents" / "impact-support-log"
        Path(ce.REPORT_ROOT).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        ce.REPORT_ROOT = self._old_report_root
        self._report_td.cleanup()

    def _make_project(self, tmp: Path, with_contrib: bool = True):
        docs = {
            "N001": {"folder": "JATS/N001", "files": {"xml": "JATS/N001/article.xml"}},
            "N002": {"folder": "JATS/N002", "files": {"xml": "JATS/N002/article.xml"}},
        }
        metas = {
            "N001": {
                "dtd": "JATS",
                "client": "LWW",
                "project-shortcode": "INF",
                "file-id": "INF-1",
            },
            "N002": {
                "dtd": "JATS",
                "client": "LWW",
                "project-shortcode": "INF",
                "file-id": "INF-2",
            },
        }
        (tmp / "documents.json").write_text(json.dumps(docs), encoding="utf-8")
        (tmp / "meta.json").write_text(json.dumps(metas), encoding="utf-8")
        for docid in ("N001", "N002"):
            folder = tmp / "JATS" / docid
            folder.mkdir(parents=True)
            body = MINIMAL_CONTRIB_XML if with_contrib else BROKEN_XML
            (folder / "article.xml").write_text(body, encoding="utf-8")
        return docs, metas

    def test_process_group_writes_report_and_meta(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            docs, metas = self._make_project(tmp, with_contrib=True)
            logs = []
            entry = ce.process_group(
                tmp, docs, metas, "LWW", "INF", ["N001", "N002"], log=logs.append
            )
            self.assertEqual(entry["documents"], 2)
            self.assertEqual(entry["failed"], 0)
            self.assertEqual(ce.SCRIPT_VERSION, 9)
            self.assertEqual(entry.get("version"), 9)
            report = Path(entry["report"])
            self.assertTrue(report.is_absolute(), entry["report"])
            self.assertTrue(report.exists(), entry["report"])
            report_norm = str(report).replace("\\", "/")
            self.assertIn("_contrib_reports", report_norm)
            self.assertIn("/JATS/", report_norm)
            self.assertTrue(
                str(report.resolve()).startswith(str(Path(ce.REPORT_ROOT).resolve()))
            )
            self.assertFalse((tmp / "contrib_reports").exists())
            self.assertIn("_contrib_v9.html", report_norm)
            html = report.read_text(encoding="utf-8")
            self.assertIn("Script version", html)
            self.assertIn("v9", html)
            self.assertTrue(entry.get("elements_report"))
            elements = Path(entry["elements_report"])
            self.assertTrue(elements.is_absolute())
            self.assertTrue(elements.exists())
            self.assertIn("_elements_v9.html", str(elements).replace("\\", "/"))
            el_html = elements.read_text(encoding="utf-8")
            self.assertNotIn("Default elements not listed", el_html)
            self.assertIn("Elements", el_html)
            # v9 always writes issues csv
            self.assertTrue(entry.get("issues_csv"))
            issues = Path(entry["issues_csv"])
            self.assertTrue(issues.is_absolute())
            self.assertTrue(issues.exists())
            self.assertIn("_issues_v9.csv", str(issues).replace("\\", "/"))
            # Per-doc outputs stay on project
            self.assertTrue((tmp / "JATS" / "N001" / ce.OUT_XML).exists())
            self.assertTrue((tmp / "JATS" / "N001" / ce.OUT_HTML).exists())

            # v9 meta: groups + cross_group_differences
            self.assertIn("groups", entry)
            self.assertIn("cross_group_differences", entry)
            self.assertIsInstance(entry["cross_group_differences"], int)
            for gid in ("g1", "g2", "g3"):
                if gid in entry["groups"]:
                    g = entry["groups"][gid]
                    self.assertIn("files", g)
                    self.assertIn("off_pattern", g)
                    self.assertIn("pi_issues", g)
            # MINIMAL_CONTRIB_XML has 3 contribs -> g3 tab
            self.assertEqual(entry["groups"].get("g3", {}).get("files"), 2)

            # v9 HTML: tabs (fixture is 3+ contribs only -> g3; cross-group needs 2+ groups)
            self.assertIn('role="tablist"', html)
            self.assertIn('data-tab="g3"', html)
            self.assertIn("3+ contribs", html)
            self.assertIn("Statistics", html)
            self.assertIn('id="q"', html)  # search box
            self.assertIn("Only files with issues", html)
            self.assertIn("Copy", html)  # copy-IDs in pattern file lists
            self.assertEqual(entry["cross_group_differences"], 0)

            # issues.csv gains contrib_group + contribs
            csv_text = Path(entry["issues_csv"]).read_text(encoding="utf-8-sig")
            header = csv_text.splitlines()[0]
            self.assertIn("contrib_group", header)
            self.assertIn("contribs", header)

            # Simulate run_contrib_extract meta write
            done = {}
            done.setdefault(ce.RUN_DTD, {}).setdefault("LWW", {})["INF"] = entry
            ce.save_done(tmp, done)
            loaded = ce.load_done(tmp)
            self.assertIn("INF", loaded["JATS"]["LWW"])
            self.assertEqual(loaded["JATS"]["LWW"]["INF"].get("version"), 9)
            st, n = ce.status_of(loaded, "LWW", "INF", ["N001", "N002"])
            self.assertEqual(st, "done")
            self.assertEqual(n, 0)

    def test_all_fail_not_marked_filled(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            docs, metas = self._make_project(tmp, with_contrib=False)
            result = ce.run_contrib_extract(
                tmp,
                shortcodes=[("LWW", "INF")],
                delay_sc=0,
                delay_cl=0,
                log_callback=lambda m: None,
            )
            self.assertEqual(len(result["finished"]), 1)
            _, _, entry = result["finished"][0]
            self.assertEqual(entry["failed"], entry["documents"])
            # meta-contrib should NOT contain INF
            done = ce.load_done(tmp)
            self.assertEqual(done.get("JATS", {}).get("LWW", {}).get("INF"), None)

    def test_run_ordered_and_cancel_keeps_finished(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            docs = {
                "A1": {"folder": "JATS/A1", "files": {"xml": "JATS/A1/article.xml"}},
                "B1": {"folder": "JATS/B1", "files": {"xml": "JATS/B1/article.xml"}},
            }
            metas = {
                "A1": {"dtd": "JATS", "client": "LWW", "project-shortcode": "AAA", "file-id": "A"},
                "B1": {"dtd": "JATS", "client": "LWW", "project-shortcode": "BBB", "file-id": "B"},
            }
            (tmp / "documents.json").write_text(json.dumps(docs), encoding="utf-8")
            (tmp / "meta.json").write_text(json.dumps(metas), encoding="utf-8")
            for docid in ("A1", "B1"):
                folder = tmp / "JATS" / docid
                folder.mkdir(parents=True)
                (folder / "article.xml").write_text(MINIMAL_CONTRIB_XML, encoding="utf-8")

            state = {"n": 0}

            def cancel():
                # cancel after first shortcode completes (checked before next)
                return state["n"] >= 1

            def progress(cur, tot, msg):
                if "done" in msg:
                    state["n"] += 1

            result = ce.run_contrib_extract(
                tmp,
                shortcodes=[("LWW", "AAA"), ("LWW", "BBB")],
                delay_sc=0,
                delay_cl=0,
                log_callback=lambda m: None,
                progress_callback=progress,
                cancel_check=cancel,
            )
            self.assertTrue(result["cancelled"])
            self.assertEqual(len(result["finished"]), 1)
            done = ce.load_done(tmp)
            self.assertIn("AAA", done["JATS"]["LWW"])
            self.assertNotIn("BBB", done.get("JATS", {}).get("LWW", {}))

    def test_shortcode_error_continues_to_next(self):
        """One shortcode exception must not abort the multi-shortcode run."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            docs = {
                "A1": {"folder": "JATS/A1", "files": {"xml": "JATS/A1/article.xml"}},
                "B1": {"folder": "JATS/B1", "files": {"xml": "JATS/B1/article.xml"}},
            }
            metas = {
                "A1": {"dtd": "JATS", "client": "LWW", "project-shortcode": "AAA", "file-id": "A"},
                "B1": {"dtd": "JATS", "client": "LWW", "project-shortcode": "BBB", "file-id": "B"},
            }
            (tmp / "documents.json").write_text(json.dumps(docs), encoding="utf-8")
            (tmp / "meta.json").write_text(json.dumps(metas), encoding="utf-8")
            for docid in ("A1", "B1"):
                folder = tmp / "JATS" / docid
                folder.mkdir(parents=True)
                (folder / "article.xml").write_text(MINIMAL_CONTRIB_XML, encoding="utf-8")

            real_pg = ce.process_group
            calls = {"n": 0}

            def boom_then_ok(*args, **kwargs):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise FileNotFoundError("simulated missing report parent")
                return real_pg(*args, **kwargs)

            logs = []
            old = ce.process_group
            ce.process_group = boom_then_ok
            try:
                result = ce.run_contrib_extract(
                    tmp,
                    shortcodes=[("LWW", "AAA"), ("LWW", "BBB")],
                    delay_sc=0,
                    delay_cl=0,
                    log_callback=logs.append,
                )
            finally:
                ce.process_group = old

            self.assertEqual(len(result["finished"]), 2)
            c0, sc0, e0 = result["finished"][0]
            self.assertEqual((c0, sc0), ("LWW", "AAA"))
            self.assertIn("ERROR", str(e0.get("report", "")))
            c1, sc1, e1 = result["finished"][1]
            self.assertEqual((c1, sc1), ("LWW", "BBB"))
            self.assertTrue(Path(e1["report"]).exists())
            done = ce.load_done(tmp)
            # failed shortcode not marked filled
            self.assertNotIn("AAA", done.get("JATS", {}).get("LWW", {}))
            self.assertIn("BBB", done["JATS"]["LWW"])
            self.assertTrue(any("[ERROR] LWW/AAA:" in m for m in logs))


class TestElementInventoryV9(unittest.TestCase):
    def test_inventory_lists_all_elements_including_defaults(self):
        """v9 shows ALL elements (no DEFAULT_ELEMENTS hide)."""
        import xml.etree.ElementTree as ET
        xml = (
            "<contrib-group>"
            '<contrib contrib-type="author">'
            "<name><surname>Doe</surname><given-names>Jane</given-names></name>"
            '<xref ref-type="aff" rid="a1">1</xref>'
            "<email></email>"
            "</contrib>"
            "</contrib-group>"
        )
        root = ce.parse_group(xml)
        contribs = list(root.iter("contrib"))
        row = {
            "docid": "d1",
            "file_id": "F1",
            "contribs": contribs,
            "group_root": root,
            "raw_group": xml,
            "gaps": [ce.analyze(c) for c in contribs],
            "xkeys": [ce.xref_key(c) for c in contribs],
        }
        inv = ce.build_inventory([row])
        for name in ("contrib", "name", "surname", "given-names", "xref", "email", "contrib-group"):
            self.assertIn(name, inv["elems"], msg=f"{name} should be listed in v9")
        self.assertFalse(hasattr(ce, "DEFAULT_ELEMENTS"))
        self.assertFalse(hasattr(ce, "visible_elements"))



class TestGroupsAndCrossGroupV9(unittest.TestCase):
    def test_group_of(self):
        self.assertEqual(ce.group_of(1), "g1")
        self.assertEqual(ce.group_of(2), "g2")
        self.assertEqual(ce.group_of(3), "g3")
        self.assertEqual(ce.group_of(10), "g3")

    def test_cross_group_same_pattern(self):
        """Pattern-1 identical across tabs -> cross entries marked same."""
        import xml.etree.ElementTree as ET

        def one_row(n_contribs: int, docid: str):
            xml = "<contrib-group>" + (
                "<contrib><name><surname>X</surname></name></contrib>" * n_contribs
            ) + "</contrib-group>"
            root = ce.parse_group(xml)
            contribs = list(root.iter("contrib"))
            gaps = [ce.analyze(c) for c in contribs]
            hits = [ce.pattern_hits(g) for g in gaps]
            xkeys = [ce.xref_key(c) for c in contribs]
            seqs = [ce.pi_sequences(h) for h in hits]
            return {
                "docid": docid,
                "file_id": docid,
                "contribs": contribs,
                "raws": ["<contrib/>"] * n_contribs,
                "gaps": gaps,
                "hits": hits,
                "xkeys": xkeys,
                "cmp_cls": [(ce.contrib_class(i, n_contribs), xkeys[i]) for i in range(n_contribs)],
                "seqs": seqs,
                "pat": {},
                "xk": {},
                "issues": [],
            }

        # two files in g1 and two in g2 with empty (no pistart) patterns -> same base
        g1 = [one_row(1, "a1"), one_row(1, "a2")]
        g2 = [one_row(2, "b1"), one_row(2, "b2")]
        stats_by = {
            "g1": ce.build_stats(g1, ["last"]),
            "g2": ce.build_stats(g2, ["before", "last"]),
        }
        cross = ce.cross_group(stats_by)
        self.assertTrue(cross)
        # last/attr/xref0 should appear and be same
        last_attr = [c for c in cross if c["role"] == "last" and c["kind"] == "attr" and c["xk"] == 0]
        self.assertTrue(last_attr)
        self.assertTrue(all(c["same"] for c in last_attr))

    def test_group_summary_keys(self):
        rows = [
            {"contribs": [1], "pat": {("last", "attr"): 1}, "issues": []},
            {"contribs": [1, 2], "pat": {("before", "attr"): 1, ("last", "attr"): 2}, "issues": [{"n": 1}]},
        ]
        # off_pattern_rows needs pat values
        gs = ce.group_summary(rows)
        self.assertEqual(gs["g1"]["files"], 1)
        self.assertEqual(gs["g2"]["files"], 1)
        self.assertEqual(gs["g3"]["files"], 0)
        self.assertEqual(gs["g2"]["off_pattern"], 1)
        self.assertEqual(gs["g2"]["pi_issues"], 1)


class TestOlderVersionUpdateV9(unittest.TestCase):
    def test_update_when_version_8_under_v9(self):
        """SCRIPT_VERSION=9 treats prior version=8 reports as updates."""
        self.assertEqual(ce.SCRIPT_VERSION, 9)
        done = {
            "JATS": {
                "LWW": {
                    "INF": {
                        "version": 8,
                        "docids": {"N001": {"status": "ok"}},
                    }
                }
            }
        }
        st, n = ce.status_of(done, "LWW", "INF", ["N001"])
        self.assertEqual(st, "update")
        self.assertEqual(n, 0)



class TestReportPathDefaults(unittest.TestCase):
    def test_make_contrib_report_dir_under_report_root(self):
        with tempfile.TemporaryDirectory() as td:
            old = ce.REPORT_ROOT
            root = Path(td) / "Documents" / "impact-support-log"
            ce.REPORT_ROOT = root
            try:
                d = ce.make_contrib_report_dir(timestamp="20260924_114100")
                self.assertEqual(
                    d,
                    root / "20260924_114100_contrib_reports" / ce.RUN_DTD,
                )
                self.assertTrue(d.is_dir())
                self.assertEqual(ce.default_report_root(), root)
            finally:
                ce.REPORT_ROOT = old

    def test_resolve_meta_path_absolute_and_relative(self):
        base = Path("/proj")
        abs_p = Path("/tmp/foo.html")
        self.assertEqual(ce.resolve_meta_path(base, str(abs_p)), abs_p)
        self.assertEqual(
            ce.resolve_meta_path(base, "contrib_reports/JATS/x.html"),
            base / "contrib_reports/JATS/x.html",
        )
        self.assertIsNone(ce.resolve_meta_path(base, None))
        self.assertIsNone(ce.resolve_meta_path(base, ""))

    def test_ensure_dir_creates_parents(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "a" / "b" / "c"
            self.assertFalse(target.exists())
            got = ce.ensure_dir(target)
            self.assertEqual(got, target)
            self.assertTrue(target.is_dir())

    def test_build_elements_report_creates_missing_parent(self):
        """Regression: write must not FileNotFoundError when report_dir parent is gone."""
        with tempfile.TemporaryDirectory() as td:
            missing_parent = Path(td) / "gone" / "JATS"
            # deliberately do NOT mkdir; ensure_dir inside build_elements_report must create it
            inv = {
                "total": 1,
                "n_contribs": 1,
                "ids": {},
                "elems": {},
                "pis": {},
                "comments": {"files": set(), "occ": 0},
            }
            out = ce.build_elements_report("LWW", "ANE", inv, missing_parent)
            self.assertTrue(out.exists())
            self.assertTrue(missing_parent.is_dir())
            self.assertIn("_elements_v9.html", out.name)


class TestTabImport(unittest.TestCase):
    def test_tab_module_imports(self):
        # Avoid instantiating Tk widgets; skip when tkinter is unavailable (e.g. headless box).
        try:
            import tkinter  # noqa: F401
        except ModuleNotFoundError:
            self.skipTest("tkinter not installed")
        from tabs.contrib_extractor_tab import ContribExtractorTab
        self.assertTrue(callable(ContribExtractorTab))


if __name__ == "__main__":
    unittest.main()

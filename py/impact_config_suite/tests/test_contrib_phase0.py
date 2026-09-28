"""Tests for Phase 0 pi-config load and separator regen."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.contrib_phase0 import (
    OUT_XML_REGEN,
    OUT_XML_STRIP_PI,
    load_pi_config,
    make_pistart,
    regen_contrib_group,
    resolve_pi_config_path,
    write_phase0_chain,
)

SUITE_ROOT = Path(__file__).resolve().parent.parent


class TestLoadPiConfig(unittest.TestCase):
    def test_load_lww_md_from_suite(self):
        cfg = load_pi_config("LWW", "MD", project_base=None, suite_root=SUITE_ROOT)
        self.assertIsNotNone(cfg)
        assert cfg is not None
        self.assertEqual(cfg.client, "LWW")
        self.assertEqual(cfg.shortcode, "MD")
        self.assertEqual(cfg.dtd, "JATS")
        self.assertFalse(cfg.elements.get("prefix"))
        self.assertTrue(cfg.elements.get("degrees"))
        self.assertFalse(cfg.ques.get("author-notes"))
        self.assertTrue(cfg.ques.get("aff"))
        kinds = [s.kind for s in cfg.separators]
        self.assertIn("given-names", kinds)
        self.assertIn("between-xrefs", kinds)
        self.assertIn("between-contribs", kinds)
        gn = cfg.separators_of("given-names")[0]
        self.assertEqual(gn.value, "\u00a0")
        self.assertEqual(gn.pos, "inner")

    def test_project_override_preferred(self):
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td)
            (proj / "contrib_config").mkdir()
            (proj / "contrib_config" / "LWW_MD.xml").write_text(
                '<pi-config client="LWW" shortcode="MD">'
                "<contrib><separators>"
                '<given-names value="X" pos="inner"/>'
                "</separators></contrib></pi-config>",
                encoding="utf-8",
            )
            path = resolve_pi_config_path(
                "LWW", "MD", project_base=proj, suite_root=SUITE_ROOT
            )
            self.assertEqual(path, proj / "contrib_config" / "LWW_MD.xml")
            cfg = load_pi_config("LWW", "MD", project_base=proj, suite_root=SUITE_ROOT)
            self.assertEqual(cfg.separators_of("given-names")[0].value, "X")

    def test_missing_returns_none(self):
        cfg = load_pi_config("NOPE", "ZZ", project_base=None, suite_root=SUITE_ROOT)
        self.assertIsNone(cfg)


class TestRegenSeparators(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_pi_config("LWW", "MD", suite_root=SUITE_ROOT)
        assert cls.cfg is not None

    def test_given_names_inner_nbsp(self):
        strip = (
            "<contrib-group>"
            "<contrib><name><surname>Doe</surname>"
            "<given-names>Jane</given-names></name></contrib>"
            "</contrib-group>"
        )
        out = regen_contrib_group(strip, self.cfg)
        self.assertIn(
            "<given-names>Jane" + make_pistart("\u00a0") + "</given-names>",
            out,
        )
        # Round-trip with strip remover: only the inserted PI should vanish
        from core.contrib_phase0 import strip_processing_instructions

        stripped_again = strip_processing_instructions(out)
        self.assertNotIn("<?", stripped_again)
        self.assertIn("<given-names>Jane</given-names>", stripped_again)

    def test_three_contribs_comma_and_empty(self):
        strip = (
            "<contrib-group>"
            "<contrib><name><surname>A</surname></name></contrib>"
            "<contrib><name><surname>B</surname></name></contrib>"
            "<contrib><name><surname>C</surname></name></contrib>"
            "</contrib-group>"
        )
        out = regen_contrib_group(strip, self.cfg)
        # After first: comma; after second (last-before): and; after third (last): empty
        self.assertIn(
            "</contrib>" + make_pistart(",") + "<contrib>",
            out,
        )
        self.assertIn(
            "</contrib>" + make_pistart("and") + "<contrib>",
            out,
        )
        self.assertTrue(out.rstrip().endswith("</contrib>" + make_pistart("") + "</contrib-group>"))

    def test_two_contribs_and_between(self):
        strip = (
            "<contrib-group>"
            "<contrib><name><surname>A</surname></name></contrib>"
            "<contrib><name><surname>B</surname></name></contrib>"
            "</contrib-group>"
        )
        out = regen_contrib_group(strip, self.cfg)
        self.assertIn(
            "</contrib>" + make_pistart("and") + "<contrib>",
            out,
        )
        self.assertNotIn(make_pistart(","), out)
        self.assertTrue(out.rstrip().endswith("</contrib>" + make_pistart("") + "</contrib-group>"))

    def test_between_xrefs_after_non_last(self):
        strip = (
            "<contrib-group><contrib>"
            '<xref ref-type="aff" rid="a1">1</xref>'
            '<xref ref-type="aff" rid="a2">2</xref>'
            '<xref ref-type="aff" rid="a3"/>'
            "</contrib></contrib-group>"
        )
        out = regen_contrib_group(strip, self.cfg)
        pi = make_pistart(",")
        self.assertIn(f">1</xref>{pi}<xref", out)
        self.assertIn(f">2</xref>{pi}<xref", out)
        # no PI after last xref before </contrib>
        self.assertIn('rid="a3"/>' + "</contrib>", out)


class TestWritePhase0WithConfig(unittest.TestCase):
    def test_write_phase0_chain_regen_differs_with_config(self):
        raw = (
            "<contrib-group>"
            "<contrib><name><surname>A</surname>"
            "<given-names>Ann</given-names></name></contrib>"
            "<contrib><name><surname>B</surname>"
            "<given-names>Bob</given-names></name></contrib>"
            "<contrib><name><surname>C</surname>"
            "<given-names>Cat</given-names></name></contrib>"
            "</contrib-group>"
        )
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            paths = write_phase0_chain(
                folder,
                raw,
                client="LWW",
                shortcode="MD",
                suite_root=SUITE_ROOT,
            )
            strip = (folder / OUT_XML_STRIP_PI).read_text(encoding="utf-8")
            regen = (folder / OUT_XML_REGEN).read_text(encoding="utf-8")
            self.assertEqual(paths["regen"].name, OUT_XML_REGEN)
            self.assertNotEqual(regen, strip)
            self.assertIn("<?pistart", regen)
            self.assertIn(make_pistart("and"), regen)
            self.assertIn(make_pistart("\u00a0"), regen)
            compare = paths["compare_html"].read_text(encoding="utf-8")
            self.assertIn("regen built from strip_pi + pi-config", compare)

    def test_write_phase0_chain_stub_without_client(self):
        raw = "<contrib-group><contrib><name/></contrib></contrib-group>"
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            write_phase0_chain(folder, raw)
            strip = (folder / OUT_XML_STRIP_PI).read_text(encoding="utf-8")
            regen = (folder / OUT_XML_REGEN).read_text(encoding="utf-8")
            self.assertEqual(regen, strip)


if __name__ == "__main__":
    unittest.main()

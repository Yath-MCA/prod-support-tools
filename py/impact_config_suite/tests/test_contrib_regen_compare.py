"""Tests for regen/compare KPI band + cause-chart HTML."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.contrib_regen_compare import (
    CATEGORY_LABELS,
    REPORT_VERSION,
    build_batch_regen_compare_html,
    category_chart,
    enrich_compare_stub_html,
    lightweight_compare_row,
    result_categories,
    summary_kpis,
    write_batch_regen_compare_report,
)


def _unmatched_row(docid: str, categories: set[str], file_id: str | None = None) -> dict:
    return {
        "docid": docid,
        "file_id": file_id or docid,
        "match": 0,
        "total": 1,
        "pct": 0.0,
        "categories": set(categories),
        "mismatches": [{"categories": set(categories)}],
        "error": None,
    }


class TestKpiAndCauseChartHtml(unittest.TestCase):
    def test_summary_kpis_markup(self):
        html = summary_kpis(12, 83.3, 4)
        self.assertIn('class="kpi-band"', html)
        self.assertIn('class="kpi"', html)
        self.assertIn("Documents", html)
        self.assertIn("83.3%", html)
        self.assertIn("Not matched", html)
        self.assertIn(">4<", html)

    def test_category_chart_bars_and_filter_status(self):
        unmatched = [
            _unmatched_row("a", {"space-nbsp"}),
            _unmatched_row("b", {"space-nbsp", "other-value-difference"}),
            _unmatched_row("c", {"processing-error"}),
            {
                "docid": "d",
                "file_id": "d",
                "error": "boom",
                "match": 0,
                "total": 0,
                "pct": 0.0,
            },
        ]
        # processing-error from error row + explicit
        html = category_chart(unmatched)
        self.assertIn('class="cause-chart"', html)
        self.assertIn('class="cause-bar"', html)
        self.assertIn("cause-bar-track", html)
        self.assertIn('data-category="space-nbsp"', html)
        self.assertIn('data-category="other-value-difference"', html)
        self.assertIn('data-category="processing-error"', html)
        self.assertIn('id="categoryFilterStatus"', html)
        self.assertIn('id="clearCategoryFilter"', html)
        self.assertIn(CATEGORY_LABELS["space-nbsp"], html)

    def test_batch_html_contains_kpi_chart_and_filter_js(self):
        rows = [
            {
                "docid": "m1",
                "file_id": "F-m1",
                "match": 1,
                "total": 1,
                "pct": 100.0,
                "categories": set(),
                "mismatches": [],
                "error": None,
            },
            _unmatched_row("u1", {"space-nbsp"}, "F-u1"),
            _unmatched_row("u2", {"other-value-difference"}, "F-u2"),
            {
                "docid": "e1",
                "file_id": "F-e1",
                "error": "parse failed",
                "match": 0,
                "total": 0,
                "pct": 0.0,
            },
        ]
        html = build_batch_regen_compare_html("LWW", "MD", rows)
        for needle in (
            "kpi-band",
            "cause-chart",
            "cause-bar",
            "category-filter-status",
            "categoryFilterStatus",
            "clearCategoryFilter",
            "activeCategory",
            'data-rt-tab="files-unmatched"',
            "data-categories=",
            f"v{REPORT_VERSION}",
        ):
            self.assertIn(needle, html, msg=f"missing {needle}")
        self.assertIn("Space vs NBSP", html)
        self.assertIn("Other value difference", html)
        self.assertIn("Processing error", html)

    def test_write_batch_report_file(self):
        rows = [_unmatched_row("x", {"extra-in-original"})]
        with tempfile.TemporaryDirectory() as td:
            out = write_batch_regen_compare_report("C", "SC", rows, Path(td))
            self.assertTrue(out.is_file())
            self.assertIn(f"_regen_compare_v{REPORT_VERSION}.html", out.name)
            text = out.read_text(encoding="utf-8")
            self.assertIn("kpi-band", text)
            self.assertIn("cause-chart", text)

    def test_lightweight_compare_categories(self):
        ok = lightweight_compare_row(
            docid="d", original_clean="<a/>", regen="<a/>"
        )
        self.assertEqual(ok["pct"], 100.0)
        self.assertEqual(result_categories(ok), set())

        nbsp = lightweight_compare_row(
            docid="d", original_clean="a\xa0b", regen="a b"
        )
        self.assertEqual(result_categories(nbsp), {"space-nbsp"})

        other = lightweight_compare_row(
            docid="d", original_clean="<a/>", regen="<b/>"
        )
        self.assertEqual(result_categories(other), {"other-value-difference"})

        err = lightweight_compare_row(docid="d", error="nope")
        self.assertEqual(result_categories(err), {"processing-error"})

    def test_enrich_stub_injects_kpi(self):
        stub = (
            "<!DOCTYPE html><html><body>"
            "<h1>contrib_group_compare</h1><p>stub</p></body></html>"
        )
        enriched = enrich_compare_stub_html(
            stub, matched=False, categories={"other-value-difference"}
        )
        self.assertIn("kpi-band", enriched)
        self.assertIn("cause-chart", enriched)
        self.assertIn("cause-bar", enriched)
        self.assertIn("activeCategory", enriched)


if __name__ == "__main__":
    unittest.main()

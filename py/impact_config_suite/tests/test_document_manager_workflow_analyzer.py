from __future__ import annotations

import tempfile
import unittest
import logging
from pathlib import Path

from manage_documents_v3.modules.analyzer import WorkflowAnalyzer
from manage_documents_v3.modules.database import DocumentDatabase
from manage_documents_v3.modules.reporter import ReportManager


class WorkflowAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name)
        for folder in ("originalhtml", "originalxml", "updatedhtmlfiles"):
            (self.project / folder).mkdir()
        self.db = DocumentDatabase(self.project)

    def tearDown(self) -> None:
        logger = logging.getLogger("docmanager")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
        self.temp_dir.cleanup()

    def _write_source_files(self, docid: str, updated_suffix: str = ".html") -> None:
        (self.project / "originalhtml" / f"{docid}.html").write_text("<html/>", encoding="utf-8")
        (self.project / "originalxml" / f"{docid}_original.xml").write_text("<root/>", encoding="utf-8")
        (self.project / "updatedhtmlfiles" / f"{docid}_updated{updated_suffix}").write_text(
            "<root/>",
            encoding="utf-8",
        )

    def _add_source_document(self, docid: str, updated_suffix: str = ".html") -> None:
        self.db.add_document(
            docid,
            {
                "original_html": f"{docid}.html",
                "original_xml": f"{docid}_original.xml",
                "updated_html": f"{docid}_updated{updated_suffix}",
                "config_xml": None,
                "compare_report": None,
            },
        )

    def test_ready_to_organize_uses_source_folder_files(self) -> None:
        self._write_source_files("N10001")
        self._add_source_document("N10001")

        analysis = WorkflowAnalyzer(self.db).analyze()

        self.assertEqual(analysis["counts"]["total"], 1)
        self.assertEqual(analysis["counts"]["ready_to_organize"], 1)
        self.assertEqual(analysis["next_action"], "Run Organize")
        self.assertEqual(analysis["documents"][0]["analysis_status"], "ready")

    def test_missing_required_file_blocks_document(self) -> None:
        self._write_source_files("N10002")
        (self.project / "updatedhtmlfiles" / "N10002_updated.html").unlink()
        self._add_source_document("N10002")

        document = WorkflowAnalyzer(self.db).analyze()["documents"][0]

        self.assertEqual(document["analysis_status"], "blocked")
        self.assertEqual(document["missing_files"], ["updated_html"])
        self.assertIn("Missing updated_html", document["issue"])

    def test_meta_entries_are_ignored(self) -> None:
        self._write_source_files("N10003")
        self._add_source_document("N10003")
        self.db._data["_meta"] = {"process": {"report_generated": True}}

        analysis = WorkflowAnalyzer(self.db).analyze()

        self.assertEqual(analysis["counts"]["total"], 1)
        self.assertEqual([doc["docid"] for doc in analysis["documents"]], ["N10003"])

    def test_html_updated_file_is_reported_as_compare_blocker(self) -> None:
        docid = "N10004"
        doc_folder = self.project / docid
        doc_folder.mkdir()
        (doc_folder / f"{docid}.html").write_text("<html/>", encoding="utf-8")
        (doc_folder / f"{docid}_original.xml").write_text("<root/>", encoding="utf-8")
        (doc_folder / f"{docid}_updated.html").write_text("<html/>", encoding="utf-8")
        (doc_folder / "impact_config.xml").write_text("<config/>", encoding="utf-8")
        self.db.add_document(
            docid,
            {
                "original_html": f"{docid}/{docid}.html",
                "original_xml": f"{docid}/{docid}_original.xml",
                "updated_html": f"{docid}/{docid}_updated.html",
                "config_xml": f"{docid}/impact_config.xml",
                "compare_report": None,
            },
            process={
                "organized": True,
                "config_downloaded": True,
                "compared": False,
                "report_generated": False,
            },
        )

        analysis = WorkflowAnalyzer(self.db).analyze()
        document = analysis["documents"][0]

        self.assertTrue(document["html_compare_blocked"])
        self.assertEqual(document["analysis_status"], "blocked")
        self.assertEqual(analysis["counts"]["html_compare_blocked"], 1)
        self.assertEqual(analysis["next_action"], "Review HTML compare blockers")

    def test_error_status_is_preserved_in_analysis(self) -> None:
        self._write_source_files("N10005")
        self._add_source_document("N10005")
        self.db.mark_error("N10005", "download", "HTTP 404")

        document = WorkflowAnalyzer(self.db).analyze()["documents"][0]

        self.assertEqual(document["analysis_status"], "error")
        self.assertEqual(document["error"], "HTTP 404")
        self.assertEqual(document["last_step"], "download")
        self.assertEqual(document["retry_count"], 1)

    def test_summary_report_includes_analysis_columns(self) -> None:
        self._write_source_files("N10006")
        self._add_source_document("N10006")

        reporter = ReportManager(self.db)
        csv_path = reporter.generate_csv(self.project / "summary.csv")
        html_path = reporter.generate_html_summary(self.project / "summary.html")

        csv_text = csv_path.read_text(encoding="utf-8")
        html_text = html_path.read_text(encoding="utf-8")
        self.assertIn("Analysis Status", csv_text)
        self.assertIn("Blocker / Next Step", csv_text)
        self.assertIn("Ready to organize", csv_text)
        self.assertIn("<th>Analysis</th>", html_text)
        self.assertIn("Ready to organize", html_text)


if __name__ == "__main__":
    unittest.main()

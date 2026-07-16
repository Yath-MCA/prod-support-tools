from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path

from manage_documents_v3.modules.database import DocumentDatabase
from manage_documents_v3.modules.dtd_organizer import DTDOrganizer


class DTDOrganizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name)
        self.db = DocumentDatabase(self.project)

    def tearDown(self) -> None:
        logger = logging.getLogger("docmanager")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
        self.temp_dir.cleanup()

    def _add_document_folder(self, docid: str, dtd: str) -> None:
        folder = self.project / docid
        folder.mkdir()
        (folder / f"{docid}.html").write_text("<html/>", encoding="utf-8")
        (folder / f"{docid}_original.xml").write_text("<root/>", encoding="utf-8")
        (folder / f"{docid}_updated.html").write_text("<html/>", encoding="utf-8")
        (folder / "impact_config.xml").write_text(
            f"<impact-config><dtd name='{dtd}'/></impact-config>",
            encoding="utf-8",
        )
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

    def test_moves_jats_document_folder_and_updates_json_paths(self) -> None:
        self._add_document_folder("N20001", "JATS")

        result = DTDOrganizer(self.db).organize_by_dtd()

        self.assertEqual(result, (1, 0, 0, 0))
        self.assertFalse((self.project / "N20001").exists())
        self.assertTrue((self.project / "JATS" / "N20001" / "impact_config.xml").exists())
        doc = self.db.get_document("N20001")
        self.assertEqual(doc["folder"], "JATS/N20001")
        self.assertEqual(doc["files"]["config_xml"], "JATS/N20001/impact_config.xml")
        self.assertEqual(doc["files"]["original_xml"], "JATS/N20001/N20001_original.xml")

    def test_moves_bits_document_folder(self) -> None:
        self._add_document_folder("N20002", "BITS")

        result = DTDOrganizer(self.db).organize_by_dtd()

        self.assertEqual(result, (1, 0, 0, 0))
        self.assertTrue((self.project / "BITS" / "N20002" / "impact_config.xml").exists())
        self.assertEqual(self.db.get_document("N20002")["folder"], "BITS/N20002")

    def test_skips_document_already_in_matching_dtd_folder(self) -> None:
        self._add_document_folder("N20003", "JATS")
        DTDOrganizer(self.db).organize_by_dtd()

        result = DTDOrganizer(self.db).organize_by_dtd()

        self.assertEqual(result, (0, 1, 0, 0))
        self.assertTrue((self.project / "JATS" / "N20003").exists())
        doc = self.db.get_document("N20003")
        self.assertEqual(self.db.resolve_document_folder("N20003", doc), self.project / "JATS" / "N20003")
        self.assertEqual(
            self.db.resolve_file_path("N20003", "config_xml", doc),
            self.project / "JATS" / "N20003" / "impact_config.xml",
        )

    def test_unknown_dtd_is_reported_without_move(self) -> None:
        self._add_document_folder("N20004", "OTHER")

        result = DTDOrganizer(self.db).organize_by_dtd()

        self.assertEqual(result, (0, 0, 0, 1))
        self.assertTrue((self.project / "N20004").exists())
        doc = self.db.get_document("N20004")
        self.assertEqual(doc["last_step"], "dtd_organize")
        self.assertIn("Unsupported or missing DTD", doc["error"])


if __name__ == "__main__":
    unittest.main()

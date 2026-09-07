#!/usr/bin/env python3
"""Unit and integration tests for the DOI Extractor."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.doi_extractor import DOIExtractor


SAMPLE_XML = """<article>
<front>
<article-id pub-id-type="doi">10.1097/MD.0000000000047654</article-id>
</front>
<body>
<pub-id pub-id-type="doi">10.1074/jbc.R116.731661</pub-id>
<fig><object-id pub-id-type="doi">10.1371/journal.pone.0341961.g010</object-id></fig>
<p><ext-link xmlns:xlink="http://www.w3.org/1999/xlink" ext-link-type="doi" xlink:href="https://doi.org/10.1016/j.sleep.2020.08.034">10.1016/j.sleep.2020.08.034</ext-link></p>
</body>
</article>
"""

NO_DOI_XML = """<article><body><p>No DOI here.</p></body></article>"""


class TestNormalizeDoi(unittest.TestCase):
    def setUp(self):
        self.extractor = DOIExtractor()

    def test_bare_doi_text(self):
        self.assertEqual(
            self.extractor.normalize_doi("10.1097/MD.0000000000047654", {}),
            "10.1097/MD.0000000000047654",
        )

    def test_ext_link_href_fallback(self):
        attrs = {"{http://www.w3.org/1999/xlink}href": "https://doi.org/10.5/x"}
        self.assertEqual(self.extractor.normalize_doi("", attrs), "10.5/x")

    def test_ext_link_text_matches_href(self):
        attrs = {"{http://www.w3.org/1999/xlink}href": "https://doi.org/10.1016/j.sleep.2020.08.034"}
        self.assertEqual(
            self.extractor.normalize_doi("10.1016/j.sleep.2020.08.034", attrs),
            "10.1016/j.sleep.2020.08.034",
        )

    def test_doi_colon_prefix(self):
        self.assertEqual(self.extractor.normalize_doi("doi:10.1234/x", {}), "10.1234/x")

    def test_url_prefix_stripped(self):
        self.assertEqual(
            self.extractor.normalize_doi("https://doi.org/10.1016/j.sleep.2020.08.034", {}),
            "10.1016/j.sleep.2020.08.034",
        )

    def test_empty_input_returns_none(self):
        self.assertIsNone(self.extractor.normalize_doi("", {}))
        self.assertIsNone(self.extractor.normalize_doi("   ", {}))


class TestIsValidDoi(unittest.TestCase):
    def setUp(self):
        self.extractor = DOIExtractor()

    def test_valid_doi(self):
        self.assertTrue(self.extractor.is_valid_doi("10.1097/MD.0000000000047654"))

    def test_valid_doi_with_object_suffix(self):
        # object-id sub-DOIs (figures/tables) carry a trailing suffix -- must still validate.
        self.assertTrue(self.extractor.is_valid_doi("10.1371/journal.pone.0341961.g010"))

    def test_invalid_doi(self):
        self.assertFalse(self.extractor.is_valid_doi("not-a-doi"))

    def test_empty_string_invalid(self):
        self.assertFalse(self.extractor.is_valid_doi(""))


class TestExtractDoisFromMatches(unittest.TestCase):
    def setUp(self):
        self.extractor = DOIExtractor()

    def test_dedup_same_tag_and_doi(self):
        matches = [
            {"tag": "article-id", "text": "10.1/x", "attributes": {}, "line": 1},
            {"tag": "article-id", "text": "10.1/x", "attributes": {}, "line": 2},
        ]
        results = self.extractor.extract_dois_from_matches(matches)
        self.assertEqual(len(results), 1)

    def test_different_tags_not_deduped(self):
        matches = [
            {"tag": "article-id", "text": "10.1/x", "attributes": {}, "line": 1},
            {"tag": "object-id", "text": "10.1/x", "attributes": {}, "line": 2},
        ]
        results = self.extractor.extract_dois_from_matches(matches)
        self.assertEqual(len(results), 2)


class TestScanAndRunExtractionEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.source_dir = Path(self.tmpdir.name) / "source"
        self.source_dir.mkdir()
        (self.source_dir / "sample_original.xml").write_text(SAMPLE_XML, encoding="utf-8")
        (self.source_dir / "no_doi_original.xml").write_text(NO_DOI_XML, encoding="utf-8")
        self.output_dir = Path(self.tmpdir.name) / "output"
        self.extractor = DOIExtractor()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_scan_directory_finds_all_four_shapes(self):
        doi_results, total_dois, total_files = self.extractor.scan_directory(
            self.source_dir, recursive=True
        )
        self.assertEqual(total_files, 2)
        self.assertEqual(total_dois, 4)

        sample_path = str((self.source_dir / "sample_original.xml").resolve())
        found_tags = {m["tag"] for m in doi_results[sample_path]["dois"]}
        self.assertEqual(found_tags, {"article-id", "pub-id", "object-id", "ext-link"})

        no_doi_path = str((self.source_dir / "no_doi_original.xml").resolve())
        self.assertEqual(doi_results[no_doi_path]["dois"], [])

    def test_run_extraction_writes_reports(self):
        result = self.extractor.run_extraction(str(self.source_dir), str(self.output_dir))

        html_path = Path(result["html_path"])
        csv_path = Path(result["csv_path"])
        self.assertTrue(html_path.exists())
        self.assertTrue(csv_path.exists())

        self.assertEqual(result["total_files"], 2)
        self.assertEqual(result["total_dois"], 4)
        self.assertEqual(result["files_with_doi"], 1)
        self.assertEqual(result["files_without_doi"], 1)
        self.assertEqual(result["unique_doi_count"], 4)
        self.assertEqual(result["invalid_doi_count"], 0)

        csv_lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(csv_lines), 5)  # header + 4 data rows


if __name__ == "__main__":
    unittest.main()

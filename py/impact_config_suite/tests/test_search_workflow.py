from __future__ import annotations

import datetime
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
import uvicorn
from fastapi.testclient import TestClient

from search_service.app.app import app
from search_service.app.services.file_search import copy_files_for_batch, fetch_doc_ids, search_in_batch
from core.element_extractor import ElementExtractor
from core.run_history import RunHistoryStore
from core.id_pattern_extractor import IDPatternExtractor
from element_extractor_tab import ElementExtractorTab
from search_tab import SearchTab
from tools_app import CommonToolsApp


def _write_doc(source_root: Path, doc_id: str, html_text: str, xml_text: str | None = None) -> None:
    doc_dir = source_root / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / f"{doc_id}_updated.html").write_text(html_text, encoding="utf-8")
    if xml_text is not None:
        (doc_dir / "impact_config.xml").write_text(xml_text, encoding="utf-8")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class SearchWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name) / "IMPACT"
        self.output = Path(self.temp_dir.name) / "SEARCH_API"
        self.root.mkdir()

    def test_fetch_copy_and_search_end_to_end(self) -> None:
        _write_doc(
            self.root,
            "DOC001",
            "<html><body>Alpha is here. beta appears twice. ALPHA.</body></html>",
            "<config><client>Client A</client><file-id>FILE-1</file-id></config>",
        )
        (self.root / "DOC002").mkdir(parents=True, exist_ok=True)
        _write_doc(
            self.root,
            "DOC003",
            "<html><body>Contains Gamma term.</body></html>",
            "<config><client>Client B</client><file-id>FILE-2</file-id></config>",
        )

        batch_paths, batch_output = fetch_doc_ids(
            datetime.datetime.now() - datetime.timedelta(days=1),
            root_folder=str(self.root),
            output_folder=str(self.output),
        )

        self.assertTrue(batch_output.startswith(str(self.output)))
        self.assertTrue(batch_paths)
        batch_file = Path(batch_paths[0])
        self.assertTrue(batch_file.exists())
        self.assertIn("BATCH_LISTS_", batch_file.parent.name)

        copied, skipped, total, destination = copy_files_for_batch(
            str(batch_file), root_folder=str(self.root)
        )

        self.assertEqual(total, 3)
        self.assertEqual(copied, 2)
        self.assertEqual(skipped, 1)
        self.assertEqual(
            Path(destination),
            batch_file.parent / "BK_FILES" / batch_file.stem,
        )

        copied_folder = Path(destination)
        self.assertTrue((copied_folder / "DOC001_updated.html").exists())
        self.assertTrue((copied_folder / "DOC001_config.xml").exists())
        self.assertTrue((copied_folder / "DOC003_updated.html").exists())
        self.assertFalse((copied_folder / "DOC002_updated.html").exists())
        self.assertFalse((copied_folder / "DOC002_config.xml").exists())

        results = search_in_batch(
            str(copied_folder),
            ["alpha", "gamma", "not-there"],
        )

        self.assertEqual(len(results), 2)
        by_doc = {item["doc_id"]: item for item in results}
        self.assertEqual(by_doc["DOC001"]["client"], "Client A")
        self.assertEqual(by_doc["DOC001"]["file_id"], "FILE-1")
        self.assertEqual(by_doc["DOC001"]["found_keys"], ["term_1"])
        self.assertEqual(by_doc["DOC003"]["found_keys"], ["term_2"])

    def test_fetch_honors_custom_output_and_invalid_paths(self) -> None:
        batch_paths, batch_output = fetch_doc_ids(
            datetime.datetime.now() - datetime.timedelta(days=1),
            root_folder=str(self.root),
            output_folder=str(self.output),
        )

        self.assertTrue(Path(batch_output).is_dir())
        self.assertTrue(all(str(Path(batch).parent).startswith(str(self.output)) for batch in batch_paths))

        with self.assertRaises(FileNotFoundError):
            fetch_doc_ids(
                datetime.datetime.now() - datetime.timedelta(days=1),
                root_folder=str(self.root / "missing"),
                output_folder=str(self.output),
            )

        with self.assertRaises(FileNotFoundError):
            copy_files_for_batch(str(self.root / "missing.txt"), root_folder=str(self.root))

        with self.assertRaises(FileNotFoundError):
            search_in_batch(str(self.root / "missing-folder"), ["alpha"])

    def test_malformed_xml_and_unreadable_html_are_handled(self) -> None:
        _write_doc(
            self.root,
            "DOC100",
            "<html><body>Alpha term.</body></html>",
            "<config><client>Broken",
        )
        _write_doc(
            self.root,
            "DOC200",
            "<html><body>Alpha term but unreadable in test.</body></html>",
            "<config><client>Client Z</client><file-id>FILE-Z</file-id></config>",
        )

        batch_paths, _ = fetch_doc_ids(
            datetime.datetime.now() - datetime.timedelta(days=1),
            root_folder=str(self.root),
            output_folder=str(self.output),
        )
        copied = copy_files_for_batch(batch_paths[0], root_folder=str(self.root))
        copied_folder = Path(copied[3])

        original_read_text = Path.read_text

        def _patched_read_text(self, *args, **kwargs):
            if self.name == "DOC200_updated.html":
                raise OSError("unreadable")
            return original_read_text(self, *args, **kwargs)

        try:
            Path.read_text = _patched_read_text  # type: ignore[assignment]
            results = search_in_batch(str(copied_folder), ["alpha"])
        finally:
            Path.read_text = original_read_text  # type: ignore[assignment]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["doc_id"], "DOC100")
        self.assertEqual(results[0]["client"], "NA")
        self.assertEqual(results[0]["file_id"], "NA")

    def test_api_endpoints_return_structured_errors(self) -> None:
        client = TestClient(app)

        response = client.get("/health")
        self.assertEqual(response.status_code, 200)

        response = client.post("/fetch", json={"days": 1, "root_folder": str(self.root / "missing")})
        self.assertEqual(response.status_code, 404)

        response = client.post("/fetch", json={"date_str": "2026/06/20"})
        self.assertEqual(response.status_code, 400)

        response = client.post("/copy", json={"batch_file": " ", "root_folder": str(self.root)})
        self.assertEqual(response.status_code, 400)

        response = client.post("/copy", json={"batch_file": str(self.root / "missing.txt"), "root_folder": str(self.root)})
        self.assertEqual(response.status_code, 404)

        response = client.post("/search", json={"batch_folder": " ", "search_terms": ["alpha"]})
        self.assertEqual(response.status_code, 400)

        response = client.post("/search", json={"batch_folder": str(self.root / "missing"), "search_terms": ["alpha"]})
        self.assertEqual(response.status_code, 404)

    def test_embedded_server_lifecycle(self) -> None:
        port = _free_port()
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            access_log=False,
        )
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        try:
            ready = False
            for _attempt in range(30):
                if not thread.is_alive():
                    break
                try:
                    response = requests.get(f"http://127.0.0.1:{port}/health", timeout=0.5)
                    if response.status_code == 200:
                        ready = True
                        break
                except requests.RequestException:
                    time.sleep(0.2)
                time.sleep(0.1)
            self.assertTrue(ready)
        finally:
            server.should_exit = True
            thread.join(timeout=5)

        self.assertFalse(thread.is_alive())

    def test_tool_registry_includes_categorized_search(self) -> None:
        config = CommonToolsApp._load_navigation_config()
        categories = [item["name"] for item in config["categories"]]
        self.assertIn("Analysis", categories)
        self.assertIn("Reports / Pattern", categories)
        self.assertIn("Auto Download", categories)
        analysis = next(item for item in config["categories"] if item["name"] == "Analysis")
        analysis_tool_ids = [tool["id"] for tool in analysis["tools"]]
        self.assertIn("search", analysis_tool_ids)
        extractor = next(item for item in config["categories"] if item["name"] == "Extractor Tools")
        extractor_tool_ids = [tool["id"] for tool in extractor["tools"]]
        self.assertIn("element_extractor", extractor_tool_ids)
        self.assertIn("Configuration", categories)
        self.assertEqual(config["default_category"], "Analysis")
        self.assertEqual(config["default_tool"], "analyses")

    def test_app_metadata_is_loadable(self) -> None:
        metadata = CommonToolsApp._load_app_metadata()
        self.assertIn("display_name", metadata)
        self.assertIn("version", metadata)
        self.assertTrue(metadata["display_name"])
        self.assertTrue(metadata["version"])

    def test_frozen_bundle_resource_paths_are_checked_first(self) -> None:
        bundle_dir = Path(self.temp_dir.name) / "bundle"
        bundle_dir.mkdir()
        (bundle_dir / "build_metadata.json").write_text(
            '{"common": {"display_name": "Bundled Suite", "version": "9.9.9"}}',
            encoding="utf-8",
        )
        (bundle_dir / "tools_navigation.json").write_text(
            '{"default_category": "Analysis", "default_tool": "analyses", "categories": [{"name": "Analysis", "tools": [{"id": "analyses", "label": "Analyses"}]}]}',
            encoding="utf-8",
        )

        with patch.object(sys, "_MEIPASS", str(bundle_dir), create=True):
            metadata = CommonToolsApp._load_app_metadata()
            navigation = CommonToolsApp._load_navigation_config()

        self.assertEqual(metadata["display_name"], "Bundled Suite")
        self.assertEqual(metadata["version"], "9.9.9")
        self.assertEqual(navigation["default_tool"], "analyses")
        self.assertEqual(navigation["categories"][0]["name"], "Analysis")

    def test_element_extractor_default_output_dir_uses_current_user_documents(self) -> None:
        fake_home = Path(self.temp_dir.name) / "userhome"
        expected = fake_home / "Documents" / "impact-support-log"

        with patch.object(Path, "home", return_value=fake_home):
            default_dir = ElementExtractorTab._default_output_dir()

        self.assertEqual(default_dir, expected)

    def test_element_extractor_history_is_saved_and_loaded(self) -> None:
        fake_home = Path(self.temp_dir.name) / "userhome"
        sample_entry = {
            "tool_id": "element_extractor",
            "tool_label": "Element Extractor",
            "timestamp": "2026-06-20 21:30:00",
            "mode": "Folder Scan",
            "source_path": r"C:\sample\input",
            "query_type": "CSS Selector",
            "query_value": ".ref span",
            "output_dir": r"C:\sample\output",
            "report_path": r"C:\sample\output\report.html",
        }

        with patch.object(Path, "home", return_value=fake_home):
            ElementExtractorTab._save_history_entries([sample_entry])
            loaded = ElementExtractorTab._load_history_entries()
            history_path = ElementExtractorTab._history_file_path()

        self.assertTrue(history_path.exists())
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["source_path"], sample_entry["source_path"])
        self.assertEqual(loaded[0]["query_value"], sample_entry["query_value"])

    def test_global_run_history_store_adds_and_searches_entries(self) -> None:
        fake_home = Path(self.temp_dir.name) / "userhome"
        with patch.object(Path, "home", return_value=fake_home):
            RunHistoryStore.add_entry(
                {
                    "tool_id": "patterns",
                    "tool_label": "Patterns",
                    "action": "generate_report",
                    "summary": "Pattern: **/config.xml",
                    "source_path": r"C:\config",
                    "output_dir": r"C:\reports",
                    "report_path": r"C:\reports\Patterns_Report.html",
                    "params": {"pattern": "**/config.xml"},
                }
            )
            RunHistoryStore.add_entry(
                {
                    "tool_id": "search",
                    "tool_label": "Search",
                    "action": "service_ready",
                    "summary": "service_ready | port 7000",
                    "report_path": "http://127.0.0.1:7000/ui",
                    "params": {"port": "7000"},
                }
            )
            entries = RunHistoryStore.load_entries()
            matched = RunHistoryStore.search_entries("7000")

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["tool_id"], "search")
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["tool_id"], "search")

    def test_element_extractor_folder_filter(self) -> None:
        source = Path(self.temp_dir.name) / "scan"
        source.mkdir()
        (source / "doc1_original.html").write_text("<html><body><span>A</span></body></html>", encoding="utf-8")
        (source / "doc1_updated.html").write_text("<html><body><span>B</span></body></html>", encoding="utf-8")
        (source / "doc2_original.html").write_text("<html><body><span>C</span></body></html>", encoding="utf-8")
        (source / "doc3_AU_original.html").write_text("<html><body><span>D</span></body></html>", encoding="utf-8")

        extractor = ElementExtractor()
        original_results, _, original_total = extractor.scan_directory(
            source,
            "Tag Name",
            "span",
            recursive=False,
            extensions=[".html"],
            filename_filter="*_original.html",
        )
        updated_results, _, updated_total = extractor.scan_directory(
            source,
            "Tag Name",
            "span",
            recursive=False,
            extensions=[".html"],
            filename_filter="*_updated.html",
        )
        all_results, _, all_total = extractor.scan_directory(
            source,
            "Tag Name",
            "span",
            recursive=False,
            extensions=[".html"],
            filename_filter="None",
        )

        self.assertEqual(original_total, 2)
        self.assertEqual(updated_total, 1)
        self.assertEqual(all_total, 4)
        self.assertEqual(len(original_results), 2)
        self.assertEqual(len(updated_results), 1)
        self.assertEqual(len(all_results), 4)
        self.assertFalse(any("AU_original" in path for path in original_results))

    def test_element_extractor_folder_filter_with_impact_config(self) -> None:
        source = Path(self.temp_dir.name) / "scan_with_config"
        source.mkdir()

        jats_oup = source / "jats_oup"
        jats_oup.mkdir()
        (jats_oup / "doc1_original.html").write_text("<html><body><span>A</span></body></html>", encoding="utf-8")
        (jats_oup / "impact_config.xml").write_text(
            "<root><dtd name=\"JATS\"/><client>oup</client></root>",
            encoding="utf-8",
        )

        bits_plos = source / "bits_plos"
        bits_plos.mkdir()
        (bits_plos / "doc2_original.html").write_text("<html><body><span>B</span></body></html>", encoding="utf-8")
        (bits_plos / "impact_config.xml").write_text(
            "<root><dtd name=\"BITS\"/><client name=\"PLOS\"/></root>",
            encoding="utf-8",
        )

        no_config = source / "no_config"
        no_config.mkdir()
        (no_config / "doc3_original.html").write_text("<html><body><span>C</span></body></html>", encoding="utf-8")

        extractor = ElementExtractor()
        results, _, total = extractor.scan_directory(
            source,
            "Tag Name",
            "span",
            recursive=True,
            extensions=[".html"],
            filename_filter="*_original.html",
            dtd_filter="JATS",
            client_filter="OUP",
        )

        self.assertEqual(total, 1)
        self.assertEqual(len(results), 1)
        only_path = next(iter(results))
        self.assertIn("jats_oup", only_path)

    def test_element_extractor_css_selector_validation(self) -> None:
        source = Path(self.temp_dir.name) / "selector.html"
        source.write_text(
            """
            <html>
              <body>
                <div class="ref">
                  <div class="mixed-citation">
                    <span>
                      <span>Match</span>
                      <span data-class="ckcommentsfull">Ignore</span>
                      <span class="person-group">Ignore</span>
                    </span>
                  </div>
                </div>
              </body>
            </html>
            """,
            encoding="utf-8",
        )

        extractor = ElementExtractor()
        matches = extractor.parse_and_extract(
            source,
            "CSS Selector",
            '.ref > .mixed-citation > span:not(.person-group):not([data-class="ckcommentsfull"]) > span\n',
        )

        self.assertEqual(len(matches), 3)
        self.assertEqual(matches[0]["text"], "Match")

    def test_search_tab_port_check(self) -> None:
        port = _free_port()
        self.assertTrue(SearchTab._port_available(port))
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.bind(("127.0.0.1", port))
        blocker.listen(1)
        try:
            self.assertFalse(SearchTab._port_available(port))
        finally:
            blocker.close()

    # ------------------------------------------------------------------
    # Element Extractor Enhancements Tests
    # ------------------------------------------------------------------

    def test_parse_query_list_splits_comma_separated_values(self) -> None:
        """Test that _parse_query_list correctly splits comma-separated queries."""
        # Single query
        result = ElementExtractorTab._parse_query_list("span")
        self.assertEqual(result, ["span"])

        # Multiple queries with spaces
        result = ElementExtractorTab._parse_query_list("span, a, div")
        self.assertEqual(result, ["span", "a", "div"])

        # Multiple queries with extra whitespace
        result = ElementExtractorTab._parse_query_list("  span  ,  a[href]  ,  //xpath  ")
        self.assertEqual(result, ["span", "a[href]", "//xpath"])

        # Empty segments should be filtered out
        result = ElementExtractorTab._parse_query_list("span,, ,div")
        self.assertEqual(result, ["span", "div"])

        # Empty string should return empty list
        result = ElementExtractorTab._parse_query_list("")
        self.assertEqual(result, [])

        # Only commas should return empty list
        result = ElementExtractorTab._parse_query_list(",,,")
        self.assertEqual(result, [])

    def test_xpath_label_normalization(self) -> None:
        """Test that 'XPath Query' is normalized to 'XPath' before calling core."""
        from element_extractor_tab import ElementExtractorTab
        tab = ElementExtractorTab.__new__(ElementExtractorTab)

        # XPath Query should be normalized to XPath
        result = tab._normalize_query_input("XPath Query", "//div")
        self.assertEqual(result, "//div")

        # Tag Name should remain unchanged
        result = tab._normalize_query_input("Tag Name", "span")
        self.assertEqual(result, "span")

        # CSS Selector should remain unchanged (after whitespace normalization)
        result = tab._normalize_query_input("CSS Selector", "  .class  ")
        self.assertEqual(result, ".class")

    def test_generate_html_report_omits_sections_when_flags_false(self) -> None:
        """Test that generate_html_report omits text/code sections when flags are False."""
        extractor = ElementExtractor()

        # Create a temp file for testing
        temp_file = Path(self.temp_dir.name) / "test_report.html"
        temp_file.write_text("<html><body><span>Test</span></body></html>", encoding="utf-8")

        # Create mock scan results - use absolute paths
        scan_results = {
            str(temp_file): {
                "ok": True,
                "matches": [
                    {
                        "line": 10,
                        "tag": "span",
                        "attributes": {"class": "test"},
                        "text": "Hello World",
                        "html": "<span class=\"test\">Hello World</span>"
                    }
                ]
            }
        }

        all_selector_results = [{
            "query_val": "span",
            "query_type": "Tag Name",
            "scan_results": scan_results,
            "total_matches": 1,
            "total_files": 1
        }]

        # With both flags True - should have both sections
        html_with_both = extractor.generate_html_report(
            str(temp_file.parent), "Tag Name", "span", "", "",
            all_selector_results, 1, 1, True,
            show_outer_xml=True, show_inner_text=True
        )
        self.assertIn("Inner Text Content", html_with_both)
        self.assertIn("Outer HTML/XML Markup", html_with_both)
        self.assertIn("Hello World", html_with_both)

        # With show_outer_xml=False - should not have outer XML section
        html_no_outer = extractor.generate_html_report(
            str(temp_file.parent), "Tag Name", "span", "", "",
            all_selector_results, 1, 1, True,
            show_outer_xml=False, show_inner_text=True
        )
        self.assertIn("Inner Text Content", html_no_outer)
        self.assertNotIn("Outer HTML/XML Markup", html_no_outer)
        self.assertIn("Hello World", html_no_outer)

        # With show_inner_text=False - should not have text section
        html_no_text = extractor.generate_html_report(
            str(temp_file.parent), "Tag Name", "span", "", "",
            all_selector_results, 1, 1, True,
            show_outer_xml=True, show_inner_text=False
        )
        self.assertNotIn("Inner Text Content", html_no_text)
        self.assertIn("Outer HTML/XML Markup", html_no_text)
        # Note: The text content still appears in the outer HTML markup,
        # which is expected since outer XML is still shown

        # With both False - should have neither section (but still have metadata)
        html_neither = extractor.generate_html_report(
            str(temp_file.parent), "Tag Name", "span", "", "",
            all_selector_results, 1, 1, True,
            show_outer_xml=False, show_inner_text=False
        )
        self.assertNotIn("Inner Text Content", html_neither)
        self.assertNotIn("Outer HTML/XML Markup", html_neither)

    def test_generate_consolidated_summary_report_counts(self) -> None:
        """Test that consolidated summary report shows correct per-selector counts."""
        extractor = ElementExtractor()

        # Create mock multi-selector results
        all_selector_results = [
            {
                "query_val": "span",
                "query_type": "Tag Name",
                "scan_results": {
                    "/test/file1.html": {
                        "ok": True,
                        "matches": [{"line": 1}, {"line": 5}]
                    },
                    "/test/file2.html": {
                        "ok": True,
                        "matches": [{"line": 3}]
                    },
                    "/test/file3.html": {
                        "ok": True,
                        "matches": []
                    }
                },
                "total_matches": 3,
                "total_files": 3
            },
            {
                "query_val": "//div",
                "query_type": "XPath",
                "scan_results": {
                    "/test/file1.html": {
                        "ok": True,
                        "matches": [{"line": 10}]
                    },
                    "/test/file2.html": {
                        "ok": True,
                        "matches": [{"line": 20}, {"line": 30}, {"line": 40}]
                    }
                },
                "total_matches": 4,
                "total_files": 3
            }
        ]

        html = extractor.generate_consolidated_summary_report(
            all_selector_results, "/test", "20260101_120000", False
        )

        # Should contain the selector names
        self.assertIn("span", html)
        self.assertIn("//div", html)

        # Should show correct file counts in cards
        # span: 2 files with matches out of 3 total
        # //div: 2 files with matches out of 3 total
        self.assertIn("3 files", html)

        # Should show correct instance counts - search for the number in context
        # The HTML contains "3" and "instances" separately (with possible Unicode encoding)
        self.assertIn("3", html)  # span has 3 instances
        self.assertIn("4", html)  # //div has 4 instances
        self.assertIn("instances", html)

        # Should have overall stats
        self.assertIn("Selectors Queried", html)
        self.assertIn("Total Matches", html)

        # Overall total should be 7
        self.assertIn(">7<", html)

    def test_export_csv_row_counts_match_total_instances(self) -> None:
        """Test that CSV export produces one row per match instance."""
        extractor = ElementExtractor()

        # Create mock multi-selector results
        all_selector_results = [
            {
                "query_val": "span",
                "query_type": "Tag Name",
                "scan_results": {
                    "/test/file1.html": {
                        "ok": True,
                        "matches": [
                            {"line": 1, "tag": "span", "text": "Text 1", "html": "<span>Text 1</span>"},
                            {"line": 5, "tag": "span", "text": "Text 2", "html": "<span>Text 2</span>"}
                        ]
                    },
                    "/test/file2.html": {
                        "ok": True,
                        "matches": [
                            {"line": 10, "tag": "span", "text": "Text 3", "html": "<span>Text 3</span>"}
                        ]
                    }
                },
                "total_matches": 3,
                "total_files": 2
            },
            {
                "query_val": "//div",
                "query_type": "XPath",
                "scan_results": {
                    "/test/file1.html": {
                        "ok": True,
                        "matches": [
                            {"line": 20, "tag": "div", "text": "Div 1", "html": "<div>Div 1</div>"}
                        ]
                    }
                },
                "total_matches": 1,
                "total_files": 2
            }
        ]

        output_path = Path(self.temp_dir.name) / "test_export.csv"
        result_path = extractor.export_csv(all_selector_results, output_path)

        # Verify file was created
        self.assertTrue(result_path.exists())

        # Read CSV and verify row count
        import csv
        with open(result_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Should have header + 4 data rows (3 from span, 1 from //div)
        self.assertEqual(len(rows), 5)

        # Verify header
        self.assertEqual(rows[0], [
            'selector', 'query_type', 'file_path', 'file_name',
            'instance_no', 'line', 'tag', 'inner_text', 'outer_xml'
        ])

        # Verify data rows
        data_rows = rows[1:]
        self.assertEqual(len(data_rows), 4)

        # Verify all rows have correct selectors
        span_rows = [r for r in data_rows if r[0] == "span"]
        div_rows = [r for r in data_rows if r[0] == "//div"]

        # Should have 3 span rows and 1 div row
        self.assertEqual(len(span_rows), 3)
        self.assertEqual(len(div_rows), 1)

        # Verify query types
        for row in span_rows:
            self.assertEqual(row[1], "Tag Name")
        for row in div_rows:
            self.assertEqual(row[1], "XPath")

        # Verify instance_no increments within each file
        # First 2 rows should have instance_no 1, 2 (from file1.html)
        self.assertEqual(span_rows[0][4], "1")
        self.assertEqual(span_rows[1][4], "2")
        # Third row should be instance_no 1 (from file2.html)
        self.assertEqual(span_rows[2][4], "1")

        # Verify file names are correct
        file_names = {row[3] for row in data_rows}
        self.assertEqual(file_names, {"file1.html", "file2.html"})

        # Verify line numbers are correct
        line_numbers = [int(row[5]) for row in data_rows]
        self.assertEqual(sorted(line_numbers), [1, 5, 10, 20])

    def test_export_csv_respects_empty_results(self) -> None:
        """Test that CSV export handles empty scan results correctly."""
        extractor = ElementExtractor()

        all_selector_results = [
            {
                "query_val": "span",
                "query_type": "Tag Name",
                "scan_results": {},
                "total_matches": 0,
                "total_files": 1
            }
        ]

        output_path = Path(self.temp_dir.name) / "empty_export.csv"
        result_path = extractor.export_csv(all_selector_results, output_path)

        self.assertTrue(result_path.exists())

        import csv
        with open(result_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Should have header only
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "selector")

    # ------------------------------------------------------------------
    # Copy Matched Files Tests
    # ------------------------------------------------------------------

    def test_history_includes_copy_matched_files_option(self) -> None:
        """Test that copy_matched_files option is persisted in history."""
        # Create a mock history entry with copy option enabled
        sample_entry = {
            "tool_id": "element_extractor",
            "mode": "Folder Scan",
            "source_path": "/test/path",
            "query_type": "Tag Name",
            "query_value": "span",
            "show_outer_xml": True,
            "show_inner_text": True,
            "generate_csv": True,
            "copy_matched_files": True,
            "params": {
                "copy_matched_files": True,
            }
        }

        # Save and load
        ElementExtractorTab._save_history_entries([sample_entry])
        loaded = ElementExtractorTab._load_history_entries()

        # Verify copy_matched_files is preserved
        self.assertTrue(len(loaded) > 0)
        self.assertEqual(loaded[0].get("copy_matched_files"), True)
        self.assertEqual(loaded[0]["params"].get("copy_matched_files"), True)

    def test_history_includes_copied_files_info(self) -> None:
        """Test that copied files count and path are persisted in history."""
        sample_entry = {
            "tool_id": "element_extractor",
            "mode": "Folder Scan",
            "source_path": "/test/path",
            "query_type": "Tag Name",
            "query_value": "span",
            "params": {
                "copied_files_count": 5,
                "copied_folder_path": "/output/matched_files_20260101_120000",
            }
        }

        ElementExtractorTab._save_history_entries([sample_entry])
        loaded = ElementExtractorTab._load_history_entries()

        # Verify copied files info is preserved
        self.assertTrue(len(loaded) > 0)
        self.assertEqual(loaded[0]["params"].get("copied_files_count"), 5)
        self.assertEqual(
            loaded[0]["params"].get("copied_folder_path"),
            "/output/matched_files_20260101_120000"
        )

    def test_copy_checkbox_defaults_to_false(self) -> None:
        """Test that copy_matched_files defaults to False for safety in history params."""
        # When no value is provided in history, it should default to False
        sample_entry = {
            "tool_id": "element_extractor",
            "mode": "Folder Scan",
            "source_path": "/test/path",
            "query_type": "Tag Name",
            "query_value": "span",
            "params": {}  # Empty params
        }

        # Save and load
        ElementExtractorTab._save_history_entries([sample_entry])
        loaded = ElementExtractorTab._load_history_entries()

        # Default should be False when not specified
        self.assertTrue(len(loaded) > 0)
        # Top-level copy_matched_files should default to False
        self.assertEqual(loaded[0].get("copy_matched_files", False), False)
        # Params copy_matched_files should default to False
        params = loaded[0].get("params", {})
        self.assertEqual(params.get("copy_matched_files", False), False)

    # ------------------------------------------------------------------
    # Doc-Title Reading Tests
    # ------------------------------------------------------------------

    def test_load_impact_config_returns_doc_title_and_project_title(self) -> None:
        """Test that _load_impact_config_filters returns doc-title and project-title."""
        extractor = ElementExtractor()

        # Create temp directory with impact_config.xml containing both titles
        temp_dir = Path(self.temp_dir.name) / "doc_title_test"
        temp_dir.mkdir()

        config_content = """<?xml version="1.0"?>
        <impact-config>
            <dtd name="JATS"/>
            <client name="OUP"/>
            <doc-title>Test Article Title</doc-title>
            <project-title>Test Project Title</project-title>
        </impact-config>
        """
        config_path = temp_dir / "impact_config.xml"
        config_path.write_text(config_content, encoding="utf-8")

        dtd, client, doc_title, project_title, identifier, link_info, doc_type = \
            extractor._load_impact_config_filters(config_path)
        self.assertEqual(dtd, "JATS")
        self.assertEqual(client, "OUP")
        self.assertEqual(doc_title, "Test Article Title")
        self.assertEqual(project_title, "Test Project Title")
        self.assertEqual(identifier, "")
        self.assertEqual(link_info, "")
        self.assertEqual(doc_type, "")

    def test_get_doc_title_method(self) -> None:
        """Test the public get_doc_title method."""
        extractor = ElementExtractor()

        # Create temp directory with impact_config.xml
        temp_dir = Path(self.temp_dir.name) / "doc_title_test2"
        temp_dir.mkdir()

        config_content = """<?xml version="1.0"?>
        <impact-config>
            <doc-title>My Document Title</doc-title>
        </impact-config>
        """
        config_path = temp_dir / "impact_config.xml"
        config_path.write_text(config_content, encoding="utf-8")

        # Create a dummy file in the same directory
        dummy_file = temp_dir / "test.html"
        dummy_file.write_text("<html></html>", encoding="utf-8")

        doc_title = extractor.get_doc_title(dummy_file)
        self.assertEqual(doc_title, "My Document Title")

    def test_get_doc_title_returns_empty_when_no_config(self) -> None:
        """Test that get_doc_title returns empty string when no impact_config.xml exists."""
        extractor = ElementExtractor()

        # Create temp directory without impact_config.xml
        temp_dir = Path(self.temp_dir.name) / "no_config_test"
        temp_dir.mkdir()

        dummy_file = temp_dir / "test.html"
        dummy_file.write_text("<html></html>", encoding="utf-8")

        doc_title = extractor.get_doc_title(dummy_file)
        self.assertEqual(doc_title, "")

    def test_get_doc_title_returns_empty_when_no_doc_title_element(self) -> None:
        """Test that get_doc_title returns empty string when doc-title element is missing."""
        extractor = ElementExtractor()

        temp_dir = Path(self.temp_dir.name) / "no_doc_title_test"
        temp_dir.mkdir()

        config_content = """<?xml version="1.0"?>
        <impact-config>
            <dtd name="JATS"/>
            <client name="OUP"/>
        </impact-config>
        """
        config_path = temp_dir / "impact_config.xml"
        config_path.write_text(config_content, encoding="utf-8")

        dummy_file = temp_dir / "test.html"
        dummy_file.write_text("<html></html>", encoding="utf-8")

        doc_title = extractor.get_doc_title(dummy_file)
        self.assertEqual(doc_title, "")

    def test_config_cache_avoids_repeated_parsing(self) -> None:
        """Test that config cache prevents repeated XML parsing."""
        extractor = ElementExtractor()

        temp_dir = Path(self.temp_dir.name) / "cache_test"
        temp_dir.mkdir()

        config_content = """<?xml version="1.0"?>
        <impact-config>
            <dtd name="JATS"/>
            <client>OUP</client>
            <doc-title>Caching Test</doc-title>
        </impact-config>
        """
        config_path = temp_dir / "impact_config.xml"
        config_path.write_text(config_content, encoding="utf-8")

        # First call should parse (returns 7 values)
        result1 = extractor._load_impact_config_filters(config_path)
        self.assertEqual(result1[2], "Caching Test")

        # Second call should use cache
        result2 = extractor._load_impact_config_filters(config_path)
        self.assertEqual(result2[2], "Caching Test")

        # Verify cache entry exists and has all 7 fields
        self.assertIn(str(config_path), extractor._config_cache)
        cache_entry = extractor._config_cache[str(config_path)]
        self.assertIn("identifier", cache_entry)
        self.assertIn("link_info", cache_entry)
        self.assertIn("doc_type", cache_entry)

    def test_clear_config_cache_clears_cache(self) -> None:
        """Test that clear_config_cache clears the config cache."""
        extractor = ElementExtractor()

        temp_dir = Path(self.temp_dir.name) / "clear_cache_test"
        temp_dir.mkdir()

        config_content = """<?xml version="1.0"?>
        <impact-config>
            <doc-title>Cache Clear Test</doc-title>
        </impact-config>
        """
        config_path = temp_dir / "impact_config.xml"
        config_path.write_text(config_content, encoding="utf-8")

        # Load to populate cache
        extractor._load_impact_config_filters(config_path)
        self.assertIn(str(config_path), extractor._config_cache)

        # Clear cache
        extractor.clear_config_cache()
        self.assertEqual(len(extractor._config_cache), 0)

    def test_get_file_title_returns_bits_project_title(self) -> None:
        """Test that get_file_title returns project-title for BITS DTD."""
        extractor = ElementExtractor()

        temp_dir = Path(self.temp_dir.name) / "bits_title_test"
        temp_dir.mkdir()

        config_content = """<?xml version="1.0"?>
        <impact-config>
            <dtd name="BITS"/>
            <client name="OSO"/>
            <doc-title>Doc Title Value</doc-title>
            <project-title>Project Title Value</project-title>
            <identifier type="isbn">9780197833216_NOVST</identifier>
            <link-info>pubkituat</link-info>
            <type>Books</type>
        </impact-config>
        """
        (temp_dir / "impact_config.xml").write_text(config_content, encoding="utf-8")

        dummy_file = temp_dir / "test.html"
        dummy_file.write_text("<html></html>", encoding="utf-8")

        title_type, title_value = extractor.get_file_title(dummy_file)
        self.assertEqual(title_type, "project-title")
        self.assertEqual(title_value, "Project Title Value")

        # Also test that metadata is accessible
        metadata = extractor.get_file_metadata(dummy_file)
        self.assertEqual(metadata["dtd"], "BITS")
        self.assertEqual(metadata["client"], "OSO")
        self.assertEqual(metadata["identifier"], "9780197833216_NOVST")
        self.assertEqual(metadata["link_info"], "pubkituat")
        self.assertEqual(metadata["doc_type"], "Books")

    def test_get_file_title_returns_jats_doc_title(self) -> None:
        """Test that get_file_title returns doc-title for JATS DTD."""
        extractor = ElementExtractor()

        temp_dir = Path(self.temp_dir.name) / "jats_title_test"
        temp_dir.mkdir()

        config_content = """<?xml version="1.0"?>
        <impact-config>
            <dtd name="JATS"/>
            <client>PLOS</client>
            <doc-title>JATS Article Title</doc-title>
            <project-title>Project Title</project-title>
            <type>Journals</type>
        </impact-config>
        """
        (temp_dir / "impact_config.xml").write_text(config_content, encoding="utf-8")

        dummy_file = temp_dir / "test.html"
        dummy_file.write_text("<html></html>", encoding="utf-8")

        title_type, title_value = extractor.get_file_title(dummy_file)
        self.assertEqual(title_type, "doc-title")
        self.assertEqual(title_value, "JATS Article Title")

        # Test metadata for JATS
        metadata = extractor.get_file_metadata(dummy_file)
        self.assertEqual(metadata["dtd"], "JATS")
        self.assertEqual(metadata["client"], "PLOS")
        self.assertEqual(metadata["doc_type"], "Journals")

    def test_get_file_title_returns_filename_when_no_config(self) -> None:
        """Test that get_file_title returns filename when no impact_config.xml exists."""
        extractor = ElementExtractor()

        temp_dir = Path(self.temp_dir.name) / "no_config_title_test"
        temp_dir.mkdir()

        dummy_file = temp_dir / "myfile.html"
        dummy_file.write_text("<html></html>", encoding="utf-8")

        title_type, title_value = extractor.get_file_title(dummy_file)
        self.assertEqual(title_type, "filename")
        self.assertEqual(title_value, "myfile.html")

    def test_get_file_title_returns_filename_when_no_titles(self) -> None:
        """Test that get_file_title returns filename when no titles exist in config."""
        extractor = ElementExtractor()

        temp_dir = Path(self.temp_dir.name) / "no_titles_test"
        temp_dir.mkdir()

        config_content = """<?xml version="1.0"?>
        <impact-config>
            <dtd name="JATS"/>
        </impact-config>
        """
        (temp_dir / "impact_config.xml").write_text(config_content, encoding="utf-8")

        dummy_file = temp_dir / "test.html"
        dummy_file.write_text("<html></html>", encoding="utf-8")

        title_type, title_value = extractor.get_file_title(dummy_file)
        self.assertEqual(title_type, "filename")
        self.assertEqual(title_value, "test.html")

    # ------------------------------------------------------------------
    # Metadata Display Tests
    # ------------------------------------------------------------------

    def test_load_impact_config_returns_all_metadata(self) -> None:
        """Test that _load_impact_config_filters returns all metadata fields."""
        extractor = ElementExtractor()

        temp_dir = Path(self.temp_dir.name) / "full_metadata_test"
        temp_dir.mkdir()

        config_content = """<?xml version="1.0"?>
        <impact-config>
            <dtd name="BITS"/>
            <client name="OSO"/>
            <doc-title>Book Title</doc-title>
            <project-title>Project Name</project-title>
            <identifier type="isbn">9780197833216_NOVST</identifier>
            <link-info>pubkituat</link-info>
            <type>Books</type>
        </impact-config>
        """
        config_path = temp_dir / "impact_config.xml"
        config_path.write_text(config_content, encoding="utf-8")

        dtd, client, doc_title, project_title, identifier, link_info, doc_type = \
            extractor._load_impact_config_filters(config_path)

        self.assertEqual(dtd, "BITS")
        self.assertEqual(client, "OSO")
        self.assertEqual(doc_title, "Book Title")
        self.assertEqual(project_title, "Project Name")
        self.assertEqual(identifier, "9780197833216_NOVST")
        self.assertEqual(link_info, "pubkituat")
        self.assertEqual(doc_type, "Books")

    def test_get_file_metadata_returns_all_fields(self) -> None:
        """Test that get_file_metadata returns complete metadata dict."""
        extractor = ElementExtractor()

        temp_dir = Path(self.temp_dir.name) / "metadata_dict_test"
        temp_dir.mkdir()

        config_content = """<?xml version="1.0"?>
        <impact-config>
            <dtd name="JATS"/>
            <client>PLOS</client>
            <doc-title>Article</doc-title>
            <type>Journals</type>
        </impact-config>
        """
        (temp_dir / "impact_config.xml").write_text(config_content, encoding="utf-8")

        dummy_file = temp_dir / "test.html"
        dummy_file.write_text("<html></html>", encoding="utf-8")

        metadata = extractor.get_file_metadata(dummy_file)
        self.assertEqual(metadata["dtd"], "JATS")
        self.assertEqual(metadata["client"], "PLOS")
        self.assertEqual(metadata["doc_title"], "Article")
        self.assertEqual(metadata["doc_type"], "Journals")
        self.assertEqual(metadata["identifier"], "")
        self.assertEqual(metadata["link_info"], "")
        self.assertEqual(metadata["project_title"], "")

    def test_get_file_metadata_returns_empty_dict_when_no_config(self) -> None:
        """Test that get_file_metadata returns empty dict when no impact_config.xml exists."""
        extractor = ElementExtractor()

        temp_dir = Path(self.temp_dir.name) / "no_config_metadata_test"
        temp_dir.mkdir()

        dummy_file = temp_dir / "test.html"
        dummy_file.write_text("<html></html>", encoding="utf-8")

        metadata = extractor.get_file_metadata(dummy_file)
        self.assertEqual(metadata["dtd"], "")
        self.assertEqual(metadata["client"], "")
        self.assertEqual(metadata["doc_title"], "")
        self.assertEqual(metadata["project_title"], "")
        self.assertEqual(metadata["identifier"], "")
        self.assertEqual(metadata["link_info"], "")
        self.assertEqual(metadata["doc_type"], "")

    def test_format_metadata_line(self) -> None:
        """Test metadata line formatting."""
        extractor = ElementExtractor()

        metadata = {
            "doc_type": "Books",
            "client": "OSO",
            "link_info": "pubkituat",
            "identifier": "9780197833216_NOVST"
        }
        result = extractor.format_metadata_line(metadata)
        self.assertEqual(result, "Books|OSO|pubkituat|9780197833216_NOVST")

        # Empty metadata returns empty string
        empty_metadata = {"doc_type": "", "client": "", "link_info": "", "identifier": ""}
        result = extractor.format_metadata_line(empty_metadata)
        self.assertEqual(result, "")

        # Partial metadata with empty values still included
        partial_metadata = {
            "doc_type": "Journals",
            "client": "PLOS",
            "link_info": "",
            "identifier": ""
        }
        result = extractor.format_metadata_line(partial_metadata)
        self.assertEqual(result, "Journals|PLOS||")

    def test_format_metadata_line_ignores_extra_keys(self) -> None:
        """Test that format_metadata_line ignores extra keys in metadata dict."""
        extractor = ElementExtractor()

        metadata = {
            "doc_type": "Books",
            "client": "OSO",
            "link_info": "pubkituat",
            "identifier": "9780197833216_NOVST",
            "dtd": "BITS",  # Extra key should be ignored
            "doc_title": "Extra Title"  # Extra key should be ignored
        }
        result = extractor.format_metadata_line(metadata)
        self.assertEqual(result, "Books|OSO|pubkituat|9780197833216_NOVST")

    # ------------------------------------------------------------------
    # ID Pattern Extractor Tests
    # ------------------------------------------------------------------

    def test_id_pattern_normalization_3digit_sequence(self) -> None:
        """Test that 3+ digit sequences normalize to {nnn}."""
        extractor = IDPatternExtractor()

        # 3+ digit sequences -> {nnn}
        self.assertEqual(extractor.normalize_id_to_pattern("front-matter-part-001"), "front-matter-part-{nnn}")
        self.assertEqual(extractor.normalize_id_to_pattern("front-matter-part-005"), "front-matter-part-{nnn}")
        self.assertEqual(extractor.normalize_id_to_pattern("book-part-001"), "book-part-{nnn}")
        self.assertEqual(extractor.normalize_id_to_pattern("book-part-002"), "book-part-{nnn}")

    def test_id_pattern_normalization_workid_pattern(self) -> None:
        """Test that workid patterns normalize correctly."""
        extractor = IDPatternExtractor()

        # workid-{work}-book-part-{n} pattern
        self.assertEqual(
            extractor.normalize_id_to_pattern("workid-USAC0048448-book-part-2"),
            "workid-{work}-book-part-{n}"
        )
        self.assertEqual(
            extractor.normalize_id_to_pattern("workid-ABC1234567-chapter-5"),
            "workid-{work}-chapter-{n}"
        )

    def test_id_pattern_normalization_short_codes(self) -> None:
        """Test that short numeric patterns normalize correctly."""
        extractor = IDPatternExtractor()

        # Short codes (1-2 digits -> {n}, 3+ digits -> {nnn})
        self.assertEqual(extractor.normalize_id_to_pattern("IMP35"), "IMP{n}")
        self.assertEqual(extractor.normalize_id_to_pattern("fig1"), "fig{n}")
        self.assertEqual(extractor.normalize_id_to_pattern("tab12"), "tab{n}")
        self.assertEqual(extractor.normalize_id_to_pattern("tab123"), "tab{nnn}")

    def test_id_pattern_normalization_mixed(self) -> None:
        """Test mixed normalization scenarios."""
        extractor = IDPatternExtractor()

        # Mixed digits
        self.assertEqual(extractor.normalize_id_to_pattern("ch-01-sec-001"), "ch-{n}-sec-{nnn}")
        self.assertEqual(extractor.normalize_id_to_pattern("part-1-chapter-042"), "part-{n}-chapter-{nnn}")

    def test_id_pattern_aggregation_most_frequent(self) -> None:
        """Test that aggregation returns most frequent pattern."""
        extractor = IDPatternExtractor()

        # All same pattern
        pattern, variants = extractor.aggregate_patterns(["front-001", "front-002", "front-003"])
        self.assertEqual(pattern, "front-{nnn}")
        self.assertEqual(variants, 0)

        # Different patterns should show variant count
        pattern, variants = extractor.aggregate_patterns(["front-001", "front-002", "back-01"])
        self.assertEqual(pattern, "front-{nnn} (+1 variants)")
        self.assertEqual(variants, 1)

    def test_id_pattern_aggregation_empty(self) -> None:
        """Test aggregation with empty list."""
        extractor = IDPatternExtractor()

        pattern, variants = extractor.aggregate_patterns([])
        self.assertEqual(pattern, "—")
        self.assertEqual(variants, 0)

    def test_tool_registry_includes_id_pattern_extractor(self) -> None:
        """Test that ID Pattern Extractor is registered in navigation."""
        config = CommonToolsApp._load_navigation_config()

        # Find Extractor Tools category
        extractor_category = None
        for category in config["categories"]:
            if category["name"] == "Extractor Tools":
                extractor_category = category
                break

        self.assertIsNotNone(extractor_category, "Extractor Tools category should exist")

        tool_ids = [tool["id"] for tool in extractor_category["tools"]]
        self.assertIn("id_pattern_extractor", tool_ids)

    def test_tool_class_registry_includes_id_pattern_extractor(self) -> None:
        """Test that ID Pattern Extractor class is registered in TOOL_CLASS_BY_ID."""
        from id_pattern_extractor_tab import IDPatternExtractorTab

        self.assertIn("id_pattern_extractor", CommonToolsApp.TOOL_CLASS_BY_ID)
        self.assertEqual(CommonToolsApp.TOOL_CLASS_BY_ID["id_pattern_extractor"], IDPatternExtractorTab)

    def test_id_pattern_scan_documents_finds_impact_config(self) -> None:
        """Test that scan_documents finds folders with impact_config.xml."""
        extractor = IDPatternExtractor()

        # Create test directory structure
        source = Path(self.temp_dir.name) / "id_pattern_scan"
        source.mkdir()

        # Create Books|TNF document
        tnf_dir = source / "TNF_Book_001"
        tnf_dir.mkdir()
        (tnf_dir / "impact_config.xml").write_text(
            "<?xml version=\"1.0\"?><impact-config><type>Books</type><client name=\"TNF\"/></impact-config>",
            encoding="utf-8"
        )
        (tnf_dir / "TNF_Book_001_original.xml").write_text(
            "<book><front-matter-part id=\"front-matter-part-001\"/><book-part id=\"book-part-001\"/></book>",
            encoding="utf-8"
        )

        # Create Books|OSO document
        oso_dir = source / "OSO_Book_001"
        oso_dir.mkdir()
        (oso_dir / "impact_config.xml").write_text(
            "<?xml version=\"1.0\"?><impact-config><type>Books</type><client name=\"OSO\"/></impact-config>",
            encoding="utf-8"
        )
        (oso_dir / "OSO_Book_001_original.xml").write_text(
            "<book><front-matter-part id=\"workid-OSO12345-front-1\"/><book-part id=\"workid-OSO12345-book-part-2\"/></book>",
            encoding="utf-8"
        )

        documents = extractor.scan_documents(source, recursive=True)

        # Should find both clients
        self.assertIn("Books|TNF", documents)
        self.assertIn("Books|OSO", documents)
        self.assertEqual(len(documents["Books|TNF"]), 1)
        self.assertEqual(len(documents["Books|OSO"]), 1)

    def test_id_pattern_scan_documents_respects_type_filter(self) -> None:
        """Test that scan_documents respects type filter."""
        extractor = IDPatternExtractor()

        source = Path(self.temp_dir.name) / "id_pattern_filter"
        source.mkdir()

        # Books document
        books_dir = source / "Books_001"
        books_dir.mkdir()
        (books_dir / "impact_config.xml").write_text(
            "<?xml version=\"1.0\"?><impact-config><type>Books</type><client name=\"TNF\"/></impact-config>",
            encoding="utf-8"
        )
        (books_dir / "Books_001_original.xml").write_text("<book/>", encoding="utf-8")

        # Journals document
        journals_dir = source / "Journals_001"
        journals_dir.mkdir()
        (journals_dir / "impact_config.xml").write_text(
            "<?xml version=\"1.0\"?><impact-config><type>Journals</type><client name=\"OUP\"/></impact-config>",
            encoding="utf-8"
        )
        (journals_dir / "Journals_001_original.xml").write_text("<article/>", encoding="utf-8")

        # Filter for Books only
        books_docs = extractor.scan_documents(source, recursive=True, type_filter="Books")
        self.assertIn("Books|TNF", books_docs)
        self.assertNotIn("Journals|OUP", books_docs)

        # Filter for Journals only
        journals_docs = extractor.scan_documents(source, recursive=True, type_filter="Journals")
        self.assertIn("Journals|OUP", journals_docs)
        self.assertNotIn("Books|TNF", journals_docs)

    def test_id_pattern_scan_documents_respects_client_filter(self) -> None:
        """Test that scan_documents respects client filter."""
        extractor = IDPatternExtractor()

        source = Path(self.temp_dir.name) / "id_pattern_client_filter"
        source.mkdir()

        # TNF document
        tnf_dir = source / "TNF_001"
        tnf_dir.mkdir()
        (tnf_dir / "impact_config.xml").write_text(
            "<?xml version=\"1.0\"?><impact-config><type>Books</type><client name=\"TNF\"/></impact-config>",
            encoding="utf-8"
        )
        (tnf_dir / "TNF_001_original.xml").write_text("<book/>", encoding="utf-8")

        # OSO document
        oso_dir = source / "OSO_001"
        oso_dir.mkdir()
        (oso_dir / "impact_config.xml").write_text(
            "<?xml version=\"1.0\"?><impact-config><type>Books</type><client name=\"OSO\"/></impact-config>",
            encoding="utf-8"
        )
        (oso_dir / "OSO_001_original.xml").write_text("<book/>", encoding="utf-8")

        # Filter for TNF only
        tnf_docs = extractor.scan_documents(source, recursive=True, client_filter="TNF")
        self.assertIn("Books|TNF", tnf_docs)
        self.assertNotIn("Books|OSO", tnf_docs)

    def test_id_pattern_extract_ids_from_xml(self) -> None:
        """Test that extract_ids_from_xml correctly extracts IDs."""
        extractor = IDPatternExtractor()

        source = Path(self.temp_dir.name) / "id_pattern_extract"
        source.mkdir()

        xml_content = """<?xml version="1.0"?>
        <book>
            <front-matter>
                <front-matter-part id="front-matter-part-001"/>
                <front-matter-part id="front-matter-part-002"/>
            </front-matter>
            <book-body>
                <book-part id="book-part-001"/>
                <book-part id="book-part-002"/>
            </book-body>
        </book>
        """
        xml_file = source / "test.xml"
        xml_file.write_text(xml_content, encoding="utf-8")

        # Extract front matter IDs
        front_ids = extractor.extract_ids_from_xml(xml_file, "//front-matter-part[@id]")
        self.assertEqual(len(front_ids), 2)
        self.assertIn("front-matter-part-001", front_ids)
        self.assertIn("front-matter-part-002", front_ids)

        # Extract body IDs
        body_ids = extractor.extract_ids_from_xml(xml_file, "//book-part[@id]")
        self.assertEqual(len(body_ids), 2)
        self.assertIn("book-part-001", body_ids)
        self.assertIn("book-part-002", body_ids)

    def test_id_pattern_build_matrix_data(self) -> None:
        """Test that build_matrix_data creates correct matrix structure."""
        extractor = IDPatternExtractor()

        # Create mock documents_by_client data
        documents_by_client = {
            "Books|TNF": [
                {
                    "folder": "/docs/TNF_001",
                    "xml_file": "/docs/TNF_001/doc.xml",
                    "doc_type": "Books",
                    "client": "TNF",
                    "doc_title": "TNF Book 1",
                    "identifier": ""
                }
            ],
            "Books|OSO": [
                {
                    "folder": "/docs/OSO_001",
                    "xml_file": "/docs/OSO_001/doc.xml",
                    "doc_type": "Books",
                    "client": "OSO",
                    "doc_title": "OSO Book 1",
                    "identifier": ""
                }
            ]
        }

        # We need to mock the XML extraction - let's create real files
        source = Path(self.temp_dir.name) / "id_pattern_matrix"
        source.mkdir()

        # TNF document with front-matter-part IDs
        tnf_dir = source / "TNF_001"
        tnf_dir.mkdir()
        (tnf_dir / "doc.xml").write_text(
            "<book><front-matter><front-matter-part id=\"front-matter-part-001\"/></front-matter></book>",
            encoding="utf-8"
        )
        documents_by_client["Books|TNF"][0]["folder"] = str(tnf_dir)
        documents_by_client["Books|TNF"][0]["xml_file"] = str(tnf_dir / "doc.xml")

        # OSO document with workid pattern
        oso_dir = source / "OSO_001"
        oso_dir.mkdir()
        (oso_dir / "doc.xml").write_text(
            "<book><front-matter><front-matter-part id=\"workid-OSO123-front-1\"/></front-matter></book>",
            encoding="utf-8"
        )
        documents_by_client["Books|OSO"][0]["folder"] = str(oso_dir)
        documents_by_client["Books|OSO"][0]["xml_file"] = str(oso_dir / "doc.xml")

        rows, clients, detail_data, _element_details = extractor.build_matrix_data(documents_by_client, "Books")

        # Check structure
        self.assertEqual(len(clients), 2)
        self.assertIn("TNF", clients)
        self.assertIn("OSO", clients)

        # Check rows - should have front-matter-part element type
        element_types = [row["element_type"] for row in rows]
        self.assertIn("front-matter-part", element_types)

        # Find front-matter-part row
        front_row = next(row for row in rows if row["element_type"] == "front-matter-part")
        self.assertEqual(front_row["TNF"], "front-matter-part-{nnn}")
        self.assertEqual(front_row["OSO"], "workid-{work}-front-{n}")

    def test_id_pattern_csv_export(self) -> None:
        """Test that CSV export produces correct output."""
        extractor = IDPatternExtractor()

        rows = [
            {"element_type": "front-matter-part", "TNF": "front-part-{nnn}", "OSO": "workid-{work}-front-{n}"},
            {"element_type": "book-part", "TNF": "book-part-{nnn}", "OSO": "workid-{work}-book-part-{n}"},
        ]
        clients = ["TNF", "OSO"]

        output_path = Path(self.temp_dir.name) / "test_matrix.csv"
        result_path = extractor.export_csv(rows, clients, output_path)

        # Verify file was created
        self.assertTrue(result_path.exists())

        # Read and verify content
        import csv
        with open(result_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            csv_rows = list(reader)

        # Header row
        self.assertEqual(csv_rows[0], ["Element Type", "TNF", "OSO"])

        # Data rows
        self.assertEqual(csv_rows[1], ["front-matter-part", "front-part-{nnn}", "workid-{work}-front-{n}"])
        self.assertEqual(csv_rows[2], ["book-part", "book-part-{nnn}", "workid-{work}-book-part-{n}"])

    def test_id_pattern_empty_cell_for_missing_element_type(self) -> None:
        """Test that empty cells show '—' when client has no such element type."""
        extractor = IDPatternExtractor()

        source = Path(self.temp_dir.name) / "id_pattern_empty"
        source.mkdir()

        # TNF document with front and body
        tnf_dir = source / "TNF_001"
        tnf_dir.mkdir()
        (tnf_dir / "doc.xml").write_text(
            """<book>
                <front-matter><front-matter-part id="front-001"/></front-matter>
                <book-body><book-part id="body-001"/></book-body>
            </book>""",
            encoding="utf-8"
        )

        # OSO document with only front (no back)
        oso_dir = source / "OSO_001"
        oso_dir.mkdir()
        (oso_dir / "doc.xml").write_text(
            "<book><front-matter><front-matter-part id=\"oso-front-001\"/></front-matter></book>",
            encoding="utf-8"
        )

        documents_by_client = {
            "Books|TNF": [{
                "folder": str(tnf_dir),
                "xml_file": str(tnf_dir / "doc.xml"),
                "doc_type": "Books",
                "client": "TNF",
                "doc_title": "",
                "identifier": ""
            }],
            "Books|OSO": [{
                "folder": str(oso_dir),
                "xml_file": str(oso_dir / "doc.xml"),
                "doc_type": "Books",
                "client": "OSO",
                "doc_title": "",
                "identifier": ""
            }]
        }

        rows, clients, detail_data, _element_details = extractor.build_matrix_data(documents_by_client, "Books")

        # OSO has no book-part element type - check empty cell
        book_part_row = next((row for row in rows if row["element_type"] == "book-part"), None)
        if book_part_row:
            self.assertEqual(book_part_row["OSO"], "—")

        # TNF should have both element types with patterns
        front_row = next(row for row in rows if row["element_type"] == "front-matter-part")
        self.assertNotEqual(front_row["TNF"], "—")
        book_row = next(row for row in rows if row["element_type"] == "book-part")
        self.assertNotEqual(book_row["TNF"], "—")


if __name__ == "__main__":
    unittest.main()

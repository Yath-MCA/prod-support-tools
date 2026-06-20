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


if __name__ == "__main__":
    unittest.main()

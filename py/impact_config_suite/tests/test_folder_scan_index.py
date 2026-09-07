# -*- coding: utf-8 -*-
"""Tests for durable Folder Scan JSON index."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from core.folder_scan_index import (
    index_path_for,
    load_index,
    make_file_entry,
    refresh_entry,
)
from core.element_extractor import ElementExtractor


CONFIG_XML = """<?xml version="1.0" encoding="UTF-8"?>
<impact-config>
  <dtd name="JATS"/>
  <client name="OUP"/>
  <doc-title>Sample Doc</doc-title>
  <type>Article</type>
  <identifier type="doi">10.1234/example</identifier>
  <link-info>https://example.test</link-info>
</impact-config>
"""

HTML_STUB = "<html><body><p>hello</p></body></html>\n"


@pytest.fixture
def sample_tree(tmp_path, monkeypatch):
    src = tmp_path / "source"
    doc1 = src / "doc1"
    doc1.mkdir(parents=True)
    (doc1 / "impact_config.xml").write_text(CONFIG_XML, encoding="utf-8")
    html = doc1 / "N10001_original.html"
    html.write_text(HTML_STUB, encoding="utf-8")

    doc2 = src / "doc2"
    doc2.mkdir()
    (doc2 / "impact_config.xml").write_text(
        CONFIG_XML.replace("OUP", "TNF").replace("JATS", "BITS"),
        encoding="utf-8",
    )
    (doc2 / "B20002_original.html").write_text(HTML_STUB, encoding="utf-8")

    idx_root = tmp_path / "indexes"
    idx_root.mkdir()
    monkeypatch.setattr("core.folder_scan_index.indexes_dir", lambda: idx_root)
    return src, html, idx_root


def test_build_and_reuse_index_skips_full_metadata_rediscovery(sample_tree, monkeypatch):
    src, html, idx_root = sample_tree
    ee = ElementExtractor()

    files1 = ee.collect_matching_files(
        src,
        recursive=True,
        extensions=[".html"],
        filename_filter="*_original.html",
        use_index=True,
        discover_new=True,
    )
    assert len(files1) == 2
    idx_path = index_path_for(src)
    assert idx_path.is_file()
    data = load_index(source_root=src)
    assert data is not None
    assert len(data["files"]) == 2
    clients = {e["client"] for e in data["files"]}
    assert clients == {"OUP", "TNF"}

    calls = {"n": 0}
    real_meta = ee.get_file_metadata

    def counting_meta(path):
        calls["n"] += 1
        return real_meta(path)

    monkeypatch.setattr(ee, "get_file_metadata", counting_meta)

    files2 = ee.collect_matching_files(
        src,
        recursive=True,
        extensions=[".html"],
        filename_filter="*_original.html",
        use_index=True,
        discover_new=False,
    )
    assert len(files2) == 2
    assert calls["n"] == 0


def test_mtime_change_refreshes_entry(sample_tree):
    src, html, idx_root = sample_tree
    ee = ElementExtractor()
    ee.collect_matching_files(
        src, recursive=True, extensions=[".html"], use_index=True, discover_new=True
    )

    cfg = html.parent / "impact_config.xml"
    cfg.write_text(CONFIG_XML.replace("OUP", "PLOS"), encoding="utf-8")
    time.sleep(0.05)
    html.write_text(HTML_STUB + "<!-- changed -->\n", encoding="utf-8")

    files = ee.collect_matching_files(
        src,
        recursive=True,
        extensions=[".html"],
        client_filter="PLOS",
        use_index=True,
        discover_new=False,
    )
    assert len(files) == 1
    data = load_index(source_root=src)
    by_name = {Path(e["path"]).name: e for e in data["files"]}
    assert by_name[html.name]["client"] == "PLOS"


def test_client_filter_from_index(sample_tree):
    src, html, idx_root = sample_tree
    ee = ElementExtractor()
    ee.collect_matching_files(src, recursive=True, extensions=[".html"], use_index=True)
    only_tnf = ee.collect_matching_files(
        src,
        recursive=True,
        extensions=[".html"],
        client_filter="TNF",
        use_index=True,
        discover_new=False,
    )
    assert len(only_tnf) == 1
    assert "doc2" in str(only_tnf[0])


def test_refresh_entry_missing_file(sample_tree):
    src, html, _ = sample_tree
    entry = make_file_entry(html, src, client="OUP", dtd="JATS")
    html.unlink()
    assert refresh_entry(entry) is None

import time
from pathlib import Path

from core.ee_docid_cache import (
    SCHEMA_VERSION,
    build_cache_payload,
    cache_path,
    try_load_cache,
    write_cache,
)


def test_cache_path_under_docid_ee_cache(tmp_path):
    doc = tmp_path / "N1"
    doc.mkdir()
    f = doc / "a.xml"
    f.write_text("<x/>", encoding="utf-8")
    p = cache_path(f)
    assert p.parent.name == "ee_cache"
    assert p.parent.parent == doc
    assert p.suffix == ".json"


def test_write_and_hit_same_mtime_size(tmp_path):
    doc = tmp_path / "N1"
    doc.mkdir()
    f = doc / "a.xml"
    f.write_text("<x/>", encoding="utf-8")
    buckets = [{"bucket": 1, "element_kind": "doi", "html": "<a/>"}]
    payload = build_cache_payload(f, buckets=buckets)
    out = write_cache(f, payload)
    assert out is not None and out.is_file()
    loaded = try_load_cache(f)
    assert loaded is not None
    assert loaded["buckets"] == buckets
    assert loaded["schema_version"] == SCHEMA_VERSION


def test_miss_when_mtime_changes(tmp_path):
    doc = tmp_path / "N1"
    doc.mkdir()
    f = doc / "a.xml"
    f.write_text("<x/>", encoding="utf-8")
    write_cache(f, build_cache_payload(f, buckets=[]))
    time.sleep(0.05)
    f.write_text("<x/>y", encoding="utf-8")
    assert try_load_cache(f) is None

import json
from pathlib import Path

from core.meta_json_filters import load_meta_map, lookup_meta_entry


def test_load_meta_map_caches_by_mtime(tmp_path):
    meta_path = tmp_path / "meta.json"
    meta_path.write_text(json.dumps({"N1": {"client": "TNF", "dtd": "BITS"}}), encoding="utf-8")
    cache = {}
    m1 = load_meta_map(meta_path, cache)
    m2 = load_meta_map(meta_path, cache)
    assert m1 == {"N1": {"client": "TNF", "dtd": "BITS"}}
    assert m2 is m1
    assert str(meta_path.resolve()) in cache


def test_load_meta_map_returns_none_on_bad_json(tmp_path):
    meta_path = tmp_path / "meta.json"
    meta_path.write_text("{not-json", encoding="utf-8")
    assert load_meta_map(meta_path, {}) is None


def test_lookup_prefers_bits_meta_then_root(tmp_path):
    root = tmp_path
    bits = root / "BITS"
    doc = bits / "Nabc"
    doc.mkdir(parents=True)
    (doc / "x.html").write_text("<p/>", encoding="utf-8")
    (bits / "meta.json").write_text(
        json.dumps({"Nabc": {"client": "TNF", "dtd": "BITS"}}), encoding="utf-8"
    )
    (root / "meta.json").write_text(
        json.dumps({"Nabc": {"client": "OTHER", "dtd": "JATS"}}), encoding="utf-8"
    )
    entry = lookup_meta_entry(doc / "x.html", {})
    assert entry["client"] == "TNF"
    assert entry["dtd"] == "BITS"


def test_lookup_falls_through_to_root_when_key_missing_in_bits(tmp_path):
    root = tmp_path
    bits = root / "BITS"
    doc = bits / "Nabc"
    doc.mkdir(parents=True)
    html = doc / "x.html"
    html.write_text("<p/>", encoding="utf-8")
    (bits / "meta.json").write_text(
        json.dumps({"Nother": {"client": "X", "dtd": "BITS"}}), encoding="utf-8"
    )
    (root / "meta.json").write_text(
        json.dumps({"Nabc": {"client": "PLOS", "dtd": "JATS"}}), encoding="utf-8"
    )
    entry = lookup_meta_entry(html, {})
    assert entry["client"] == "PLOS"
    assert entry["dtd"] == "JATS"


def test_lookup_returns_none_when_no_meta(tmp_path):
    doc = tmp_path / "BITS" / "Nabc"
    doc.mkdir(parents=True)
    html = doc / "x.html"
    html.write_text("<p/>", encoding="utf-8")
    assert lookup_meta_entry(html, {}) is None


def test_matches_filters_via_bits_meta_without_impact_config(tmp_path):
    from core.element_extractor import ElementExtractor

    bits = tmp_path / "BITS"
    doc = bits / "Nabc"
    doc.mkdir(parents=True)
    html = doc / "x.html"
    html.write_text("<p/>", encoding="utf-8")
    (bits / "meta.json").write_text(
        json.dumps({"Nabc": {"client": "TNF", "dtd": "BITS"}}), encoding="utf-8"
    )
    ee = ElementExtractor()
    assert ee._matches_config_filters(html, "BITS", "TNF") is True
    assert ee._matches_config_filters(html, "BITS", "PLOS") is False
    assert ee._matches_config_filters(html, "JATS", "TNF") is False


def test_matches_filters_falls_back_to_impact_config(tmp_path):
    from core.element_extractor import ElementExtractor

    bits = tmp_path / "BITS"
    doc = bits / "Nabc"
    doc.mkdir(parents=True)
    html = doc / "x.html"
    html.write_text("<p/>", encoding="utf-8")
    (doc / "impact_config.xml").write_text(
        """<?xml version="1.0"?>
        <config>
          <dtd name="BITS"/>
          <client name="TNF"/>
        </config>
        """,
        encoding="utf-8",
    )
    ee = ElementExtractor()
    assert ee._matches_config_filters(html, "BITS", "TNF") is True
    assert ee._matches_config_filters(html, "", "PLOS") is False


def test_matches_filters_empty_filters_true_without_meta(tmp_path):
    from core.element_extractor import ElementExtractor

    doc = tmp_path / "BITS" / "Nabc"
    doc.mkdir(parents=True)
    html = doc / "x.html"
    html.write_text("<p/>", encoding="utf-8")
    ee = ElementExtractor()
    assert ee._matches_config_filters(html, "", "") is True


def test_matches_filters_root_meta_when_bits_key_missing(tmp_path):
    from core.element_extractor import ElementExtractor

    root = tmp_path
    bits = root / "BITS"
    doc = bits / "Nabc"
    doc.mkdir(parents=True)
    html = doc / "x.html"
    html.write_text("<p/>", encoding="utf-8")
    (bits / "meta.json").write_text(json.dumps({}), encoding="utf-8")
    (root / "meta.json").write_text(
        json.dumps({"Nabc": {"client": "lww", "dtd": "bits"}}), encoding="utf-8"
    )
    ee = ElementExtractor()
    assert ee._matches_config_filters(html, "BITS", "LWW") is True


def test_clear_config_cache_clears_meta_cache(tmp_path):
    from core.element_extractor import ElementExtractor

    bits = tmp_path / "BITS"
    doc = bits / "Nabc"
    doc.mkdir(parents=True)
    html = doc / "x.html"
    html.write_text("<p/>", encoding="utf-8")
    (bits / "meta.json").write_text(
        json.dumps({"Nabc": {"client": "TNF", "dtd": "BITS"}}), encoding="utf-8"
    )
    ee = ElementExtractor()
    assert ee._matches_config_filters(html, "", "TNF") is True
    assert ee._meta_json_cache
    ee.clear_config_cache()
    assert ee._meta_json_cache == {}

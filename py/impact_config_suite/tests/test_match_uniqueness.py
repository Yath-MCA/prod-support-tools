from core.match_uniqueness import (
    attrs_for_uniqueness,
    annotate_unique_matches,
    filter_unique_matches,
    annotate_selector_results,
)

XLINK = "{http://www.w3.org/1999/xlink}href"


def test_attrs_for_uniqueness_drops_xlink_forms():
    attrs = {
        "class": "ext-link",
        "xlink:href": "a",
        XLINK: "b",
        "ext-link-type": "uri",
    }
    out = attrs_for_uniqueness(attrs)
    assert out == {"class": "ext-link", "ext-link-type": "uri"}
    assert "xlink:href" not in out
    assert XLINK not in out


def test_annotate_keeps_first_when_only_href_differs():
    matches = [
        {"tag": "ext-link", "attributes": {"class": "ext-link", XLINK: "http://a"}, "line": 1, "text": "A", "html": "<a/>"},
        {"tag": "ext-link", "attributes": {"class": "ext-link", XLINK: "http://b"}, "line": 2, "text": "B", "html": "<b/>"},
        {"tag": "ext-link", "attributes": {"class": "ext-link", "xlink:href": "http://c"}, "line": 3, "text": "C", "html": "<c/>"},
    ]
    annotate_unique_matches(matches)
    assert [m["is_unique"] for m in matches] == [True, False, False]
    assert all(m["unique_group_size"] == 3 for m in matches)
    assert filter_unique_matches(matches)[0]["line"] == 1


def test_different_class_are_distinct():
    matches = [
        {"tag": "a", "attributes": {"class": "one", XLINK: "u1"}, "line": 1},
        {"tag": "a", "attributes": {"class": "two", XLINK: "u2"}, "line": 2},
    ]
    annotate_unique_matches(matches)
    assert [m["is_unique"] for m in matches] == [True, True]
    assert [m["unique_group_size"] for m in matches] == [1, 1]


def test_annotate_selector_results_is_per_file():
    results = [{
        "query_val": "ext-link",
        "scan_results": {
            "C:/a.xml": {
                "ok": True,
                "matches": [
                    {"tag": "a", "attributes": {XLINK: "1"}, "line": 1},
                    {"tag": "a", "attributes": {XLINK: "2"}, "line": 2},
                ],
            },
            "C:/b.xml": {
                "ok": True,
                "matches": [
                    {"tag": "a", "attributes": {XLINK: "1"}, "line": 9},
                ],
            },
        },
    }]
    annotate_selector_results(results)
    a = results[0]["scan_results"]["C:/a.xml"]["matches"]
    b = results[0]["scan_results"]["C:/b.xml"]["matches"]
    assert [m["is_unique"] for m in a] == [True, False]
    assert a[0]["unique_group_size"] == 2
    assert b[0]["is_unique"] is True and b[0]["unique_group_size"] == 1

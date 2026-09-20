"""Six-bucket first-hit DOI / pub-id / URI extraction (in vs out of .ref)."""

from __future__ import annotations

import csv
import html as html_lib
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from core.mixed_citation_direct_hits import is_comment_element

CSV_HEADER = [
    "file_path",
    "file_name",
    "doc_type",
    "client",
    "link_info",
    "identifier",
    "bucket",
    "element_kind",
    "in_ref",
    "under_comment",
    "doi_org_in_href",
    "doi_org_in_text",
    "line",
    "text",
    "href",
    "outer_xml",
]


def _class_tokens(node: Tag) -> list[str]:
    classes = node.get("class") or []
    if isinstance(classes, str):
        return classes.split()
    return list(classes)


def is_ref_element(node: Tag) -> bool:
    if not isinstance(node, Tag):
        return False
    if node.name == "ref":
        return True
    if node.get("data-name") == "ref" or node.get("data-role") == "ref":
        return True
    return "ref" in _class_tokens(node)


def is_inside_ref(node: Tag) -> bool:
    parent = getattr(node, "parent", None)
    while isinstance(parent, Tag):
        if is_ref_element(parent):
            return True
        parent = parent.parent
    return False


def is_pub_id_element(node: Tag) -> bool:
    if not isinstance(node, Tag):
        return False
    if node.name == "pub-id":
        return True
    if node.get("data-name") == "pub-id":
        return True
    return "pub-id" in _class_tokens(node)


def is_ext_link_of_type(node: Tag, link_type: str) -> bool:
    if not isinstance(node, Tag):
        return False
    is_ext = (
        node.name == "ext-link"
        or node.get("data-name") == "ext-link"
        or "ext-link" in _class_tokens(node)
    )
    if not is_ext:
        return False
    return (node.get("ext-link-type") or "") == link_type


def get_href(node: Tag) -> str:
    for key, val in (node.attrs or {}).items():
        if key == "href" or key == "xlink:href" or (
            isinstance(key, str) and key.endswith("}href")
        ):
            return str(val or "")
    return ""


def _under_comment(node: Tag) -> bool:
    parent = node.parent
    return isinstance(parent, Tag) and is_comment_element(parent)


def _row(bucket: int, kind: str, node: Tag, in_ref: bool) -> dict:
    text = node.get_text(" ", strip=True)
    href = get_href(node)
    under = _under_comment(node) if kind in ("doi", "uri") else False
    doi_href = ("doi.org" in href.lower()) if kind == "uri" else False
    doi_text = ("doi.org" in text.lower()) if kind == "uri" else False
    try:
        outer = str(node)
    except Exception:
        outer = ""
    return {
        "bucket": bucket,
        "element_kind": kind,
        "in_ref": in_ref,
        "under_comment": under,
        "doi_org_in_href": doi_href,
        "doi_org_in_text": doi_text,
        "line": getattr(node, "sourceline", "") or "",
        "text": text,
        "href": href,
        "html": outer,
    }


def extract_buckets_from_soup(soup: Any) -> list[dict]:
    """Return up to six first-hit bucket rows in bucket-number order."""
    filled: dict[int, dict] = {}
    for node in soup.descendants:
        if not isinstance(node, Tag):
            continue
        in_ref = is_inside_ref(node)
        if is_pub_id_element(node):
            kind = "pub-id"
            bucket = 1 if in_ref else 2
        elif is_ext_link_of_type(node, "doi"):
            kind = "doi"
            bucket = 3 if in_ref else 4
        elif is_ext_link_of_type(node, "uri"):
            kind = "uri"
            bucket = 5 if in_ref else 6
        else:
            continue
        if bucket not in filled:
            filled[bucket] = _row(bucket, kind, node, in_ref)
    return [filled[k] for k in sorted(filled)]


def extract_buckets_from_file(file_path: Path) -> dict:
    """Parse one file; return {ok, error?, buckets}."""
    file_path = Path(file_path)
    try:
        raw = file_path.read_bytes()
    except Exception as exc:
        return {"ok": False, "error": str(exc), "buckets": []}

    suffix = file_path.suffix.lower()
    parser = "lxml-xml" if suffix == ".xml" else "lxml"
    try:
        text = raw.decode("utf-8", errors="ignore")
        soup = BeautifulSoup(text, parser)
        if soup is None:
            raise ValueError("empty parse")
        return {"ok": True, "error": "", "buckets": extract_buckets_from_soup(soup)}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "buckets": []}


def write_doi_pubid_by_ref_csv(file_results: list[dict], output_path: Path) -> Path:
    output_path = Path(output_path)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for item in file_results:
            if not item.get("ok", True):
                continue
            buckets = item.get("buckets") or []
            if not buckets:
                continue
            path_str = str(item.get("path", ""))
            file_name = os.path.basename(path_str)
            for row in buckets:
                writer.writerow([
                    path_str,
                    file_name,
                    item.get("doc_type", ""),
                    item.get("client", ""),
                    item.get("link_info", ""),
                    item.get("identifier", ""),
                    row.get("bucket", ""),
                    row.get("element_kind", ""),
                    "True" if row.get("in_ref") else "False",
                    "True" if row.get("under_comment") else "False",
                    "True" if row.get("doi_org_in_href") else "False",
                    "True" if row.get("doi_org_in_text") else "False",
                    row.get("line", ""),
                    row.get("text", ""),
                    row.get("href", ""),
                    row.get("html", ""),
                ])
    return output_path


def generate_doi_pubid_by_ref_html(
    file_results: list[dict],
    target_path: str,
    ts: str | None = None,
) -> str:
    """Return thin DOI shell HTML (data loaded from sibling report-data.js at runtime)."""
    from core.ee_report_store import doi_shell_html

    target_name = os.path.basename(target_path)
    return doi_shell_html(f"DOI / pub-id by ref — {target_name}")

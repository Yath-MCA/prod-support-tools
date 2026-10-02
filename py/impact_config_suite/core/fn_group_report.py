"""Footnotes Group Report (BITS) - unique fn-group / ref-list patterns by client x DTD.

Scans BITS books only. Enriches meta.json + documents.json with dtd_basename from
DOCTYPE. Rolls up CSS-like structural patterns (id dropped) with chapter-end /
book-end / front-matter / other placement.
"""
from __future__ import annotations

import csv
import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from lxml import etree

from core.dtd_report import extract_file as extract_doctype

REPORT_VERSION = 2
REPORT_DIR = "fn_group_reports"
SUPPORT_LOG_NAME = "impact-support-log"
REPORT_ROOT: Path | None = None

SAMPLE_LIMIT = 8
STABLE_ATTRS = frozenset({"book-part-type", "content-type", "class"})
TARGET_KINDS = ("fn-group", "ref-list")
# fn-group content-type values excluded from scan/rollup (table footnotes).
EXCLUDED_FN_CONTENT_TYPES = frozenset({"table-fn"})
BOOKS_AREA_KEYS = ["front", "body", "back"]

# Soft expected DTD family by client (warning only).
CLIENT_EXPECTED_DTD: dict[str, frozenset[str]] = {
    "OSO": frozenset({"BITS-book-oasis2-1.dtd"}),
    "OHO": frozenset({"BITS-book-oasis2-1.dtd"}),
    "OXMEDO": frozenset({"BITS-book-oasis2-1.dtd"}),
    "LSE": frozenset({"BITS.dtd"}),
    "TNF": frozenset({"BITS.dtd"}),
}

UNIQUE_CSV_HEADERS = [
    "client",
    "dtd_basename",
    "kind",
    "placement",
    "pattern_xpath",
    "file_count",
    "occurrence_count",
    "sample_file_ids",
    "sample_docids",
    "sample_ids",
    "dtd_mismatch_warning",
    "cardinality_warning",
]

ID_PATTERN_CSV_HEADERS = [
    "client",
    "dtd_basename",
    "kind",
    "area_category",
    "id_pattern",
    "file_count",
    "occurrence_count",
    "sample_file_ids",
    "sample_docids",
    "sample_ids",
]

DETAIL_TSV_HEADERS = [
    "Client",
    "File_id",
    "Docid",
    "DTD_basename",
    "Kind",
    "Placement",
    "Pattern_xpath",
    "Element_id",
    "Id_pattern",
    "Area_category",
    "Shortcode",
    "DTD_mismatch",
    "Cardinality_warning",
    "Xml_path",
    "Error",
]

_id_extractor = None

LogFn = Callable[[str], None]
ProgressFn = Callable[[int, int, str], None]
CancelFn = Callable[[], bool]


def _noop_log(msg: str) -> None:
    pass


def _noop_progress(current: int, total: int, message: str) -> None:
    pass


def _noop_cancel() -> bool:
    return False


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_report_root() -> Path:
    if REPORT_ROOT is not None:
        return Path(REPORT_ROOT)
    return Path.home() / "Documents" / SUPPORT_LOG_NAME


def make_report_dir(timestamp: str | None = None) -> Path:
    ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = default_report_root() / f"{ts}_{REPORT_DIR}"
    return ensure_dir(report_dir)


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def local_name(tag: Any) -> str:
    if not isinstance(tag, str):
        return "?"
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _attr_local(key: str) -> str:
    return key.split("}", 1)[-1] if "}" in str(key) else str(key)


def _stable_attr_selector(el: etree._Element) -> str:
    parts: list[str] = []
    for key, value in sorted(el.attrib.items(), key=lambda kv: _attr_local(kv[0])):
        name = _attr_local(key)
        if name in STABLE_ATTRS and value is not None and str(value) != "":
            parts.append(f'[{name}="{value}"]')
    return "".join(parts)


def pattern_xpath_for_element(el: etree._Element) -> str:
    """CSS-like path from root to el; keep stable attrs; drop id."""
    chain: list[etree._Element] = []
    cur: etree._Element | None = el
    while cur is not None:
        chain.append(cur)
        parent = cur.getparent()
        cur = parent if isinstance(parent, etree._Element) else None
    chain.reverse()
    # Drop synthetic document wrappers if any; keep from first real element.
    parts: list[str] = []
    for node in chain:
        ln = local_name(node.tag)
        if ln in {"?", ""}:
            continue
        parts.append(f".{ln}{_stable_attr_selector(node)}")
    return " ".join(parts)


def _ancestor_local_names(el: etree._Element) -> list[str]:
    """Element local-name then ancestors outward (parent-first)."""
    names: list[str] = []
    cur: etree._Element | None = el
    while cur is not None:
        names.append(local_name(cur.tag))
        parent = cur.getparent()
        cur = parent if isinstance(parent, etree._Element) else None
    return names


def classify_placement(el: etree._Element) -> str:
    """chapter-end | book-end | front-matter | other.

    book-end only when under book-back (never book-body).
    chapter-end when under book-body / book-part ... back.
    """
    names = _ancestor_local_names(el)
    ancestors = names[1:]
    # book-end: must be under book-back; book-back wins even if also nested oddly
    if "book-back" in ancestors:
        return "book-end"
    if "front-matter" in ancestors or "front-matter-part" in ancestors:
        return "front-matter"
    # Never treat book-body targets as book-end
    if "book-part" in ancestors and "back" in ancestors:
        return "chapter-end"
    if "book-body" in ancestors and "back" in ancestors:
        return "chapter-end"
    return "other"


def content_type_of(el: etree._Element) -> str:
    for key, value in el.attrib.items():
        if _attr_local(key) == "content-type":
            return str(value or "")
    return ""


def is_excluded_fn_group(el: etree._Element) -> bool:
    """True for fn-group content-type=table-fn (excluded from report)."""
    if local_name(el.tag) != "fn-group":
        return False
    return content_type_of(el) in EXCLUDED_FN_CONTENT_TYPES


def _get_id_extractor():
    global _id_extractor
    if _id_extractor is None:
        from core.id_pattern_extractor import IDPatternExtractor

        _id_extractor = IDPatternExtractor()
    return _id_extractor


def id_pattern_for(element_id: str, kind: str = "") -> str:
    if not element_id:
        return ""
    return _get_id_extractor().normalize_id_to_pattern(element_id, kind)


def area_category_for(el: etree._Element) -> str:
    area = _get_id_extractor()._determine_area(el, None, BOOKS_AREA_KEYS)
    return area or "unknown"


def apply_book_end_cardinality_warnings(
    detail_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Soft-warn when a doc has more than one book-end fn-group (expect one)."""
    counts: dict[str, int] = {}
    for r in detail_rows:
        if r.get("kind") != "fn-group" or r.get("placement") != "book-end":
            continue
        if r.get("error"):
            continue
        did = r.get("docid") or ""
        counts[did] = counts.get(did, 0) + 1
    multi = {did for did, n in counts.items() if n > 1}
    for r in detail_rows:
        if (
            r.get("kind") == "fn-group"
            and r.get("placement") == "book-end"
            and (r.get("docid") or "") in multi
        ):
            prev = (r.get("cardinality_warning") or "").strip()
            warn = "multiple_book_end_fn_group"
            r["cardinality_warning"] = f"{prev}; {warn}" if prev else warn
    return detail_rows


def dtd_mismatch_warning(client: str, dtd_basename: str) -> str:
    expected = CLIENT_EXPECTED_DTD.get((client or "").strip().upper())
    if not expected:
        return ""
    bas = (dtd_basename or "").strip()
    if not bas or bas == "NO_DTD":
        return f"expected one of {sorted(expected)}; got {bas or 'empty'}"
    if bas not in expected:
        return f"expected one of {sorted(expected)}; got {bas}"
    return ""


def is_bits_book_doc(doc: dict[str, Any], meta: dict[str, Any] | None = None) -> bool:
    """True when doc is a BITS book (folder dtd or type Books)."""
    m = meta or {}
    dtd = str(m.get("dtd") or doc.get("dtd") or "").strip().upper()
    doc_type = str(
        m.get("type") or doc.get("doc_type") or doc.get("type") or ""
    ).strip()
    folder = str(doc.get("folder") or "")
    if dtd == "BITS":
        return True
    if doc_type.lower() == "books":
        return True
    if folder.replace("\\", "/").startswith("BITS/") or "/BITS/" in folder.replace(
        "\\", "/"
    ):
        return True
    # collect_docs may not expose folder; xml_path under .../BITS/...
    xml = str(doc.get("xml_path") or "").replace("\\", "/")
    if "/BITS/" in xml:
        return True
    return False


def resolve_dtd_basename(xml_path: Path | str | None) -> dict[str, str]:
    """Return doctype fields; dtd_basename is NO_DTD when missing."""
    if not xml_path or not Path(xml_path).is_file():
        return {
            "doctype_root": "",
            "system_id": "",
            "dtd_basename": "NO_DTD",
            "has_doctype": "0",
            "error": "xml not found",
        }
    info = extract_doctype(xml_path)
    bas = (info.get("dtd_basename") or "").strip()
    if not bas:
        bas = "NO_DTD"
    return {
        "doctype_root": info.get("doctype_root") or "",
        "system_id": info.get("system_id") or "",
        "dtd_basename": bas,
        "has_doctype": "1" if info.get("has_doctype") else "0",
        "error": info.get("error") or "",
    }


def _parse_xml(xml_path: Path) -> etree._Element:
    parser = etree.XMLParser(
        recover=True,
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        huge_tree=True,
    )
    return etree.parse(str(xml_path), parser).getroot()


def extract_targets(xml_path: Path | str) -> tuple[list[dict[str, Any]], int]:
    """Find fn-group and ref-list; return (rows, excluded_table_fn_count).

    Skips fn-group with content-type=table-fn.
    Each row includes kind, placement, pattern_xpath, element_id, id_pattern, area_category.
    """
    root = _parse_xml(Path(xml_path))
    rows: list[dict[str, Any]] = []
    excluded_table_fn = 0
    for kind in TARGET_KINDS:
        for el in root.xpath(f'//*[local-name()="{kind}"]'):
            if kind == "fn-group" and is_excluded_fn_group(el):
                excluded_table_fn += 1
                continue
            eid = el.attrib.get("id") or ""
            placement = classify_placement(el)
            pattern = pattern_xpath_for_element(el)
            rows.append(
                {
                    "kind": kind,
                    "placement": placement,
                    "pattern_xpath": pattern,
                    "element_id": eid,
                    "id_pattern": id_pattern_for(eid, kind),
                    "area_category": area_category_for(el),
                }
            )
    return rows, excluded_table_fn


def _pick_bits_xml(folder: Path, item: dict[str, Any] | None = None) -> Path | None:
    """Prefer *_original.xml; skip impact_config.xml. No full-doc parse."""
    skip = {"impact_config.xml"}
    candidates: list[Path] = []
    if folder.is_dir():
        candidates.extend(sorted(folder.glob("*.xml")))
    if item:
        for rel in (item.get("files") or {}).values():
            if not isinstance(rel, str):
                continue
            for trial in (folder / Path(rel).name, folder / rel):
                if trial.is_file() and trial not in candidates:
                    candidates.append(trial)

    xmls = [
        p
        for p in candidates
        if p.is_file() and p.suffix.lower() == ".xml" and p.name.lower() not in skip
    ]
    if not xmls:
        return None
    originals = [p for p in xmls if p.name.endswith("_original.xml")]
    if originals:
        return originals[0]
    return xmls[0]


def collect_bits_docs(
    project_root: Path | str,
    shortcodes: Optional[Iterable[str]] = None,
    clients: Optional[Iterable[str]] = None,
    folder_mode: bool = False,
) -> list[dict[str, Any]]:
    """BITS-book docs only — filter meta first (avoid scanning full JATS corpus)."""
    root = Path(project_root)
    client_filter: set[str] | None = None
    if clients:
        client_filter = {c.strip().upper() for c in clients if c and str(c).strip()}
    sc_filter: set[str] | None = None
    if shortcodes:
        sc_filter = {s.strip() for s in shortcodes if s and str(s).strip()}

    meta_path = root / "meta.json"
    docs_path = root / "documents.json"
    metas: dict[str, Any] = {}
    documents: dict[str, Any] = {}
    if meta_path.is_file():
        with open(meta_path, encoding="utf-8") as f:
            metas = json.load(f)
    if docs_path.is_file():
        with open(docs_path, encoding="utf-8") as f:
            documents = json.load(f)

    out: list[dict[str, Any]] = []

    if folder_mode or not metas:
        # Folder scan: BITS/ subdirs or flat *.xml under a BITS tree
        bits_root = root / "BITS" if (root / "BITS").is_dir() else root
        for folder in sorted(p for p in bits_root.iterdir() if p.is_dir()):
            docid = folder.name
            meta = metas.get(docid) or {}
            item = documents.get(docid) or {}
            if meta and not is_bits_book_doc({"dtd": meta.get("dtd"), "doc_type": meta.get("type"), "folder": item.get("folder") or f"BITS/{docid}"}, meta):
                # If meta says not BITS, skip; if no meta, keep (folder under BITS)
                if meta.get("dtd") and str(meta.get("dtd")).upper() != "BITS":
                    continue
            client = meta.get("client") or ""
            shortcode = meta.get("project-shortcode") or ""
            if client_filter is not None and client.strip().upper() not in client_filter:
                continue
            if sc_filter is not None and shortcode not in sc_filter:
                continue
            xml_path = _pick_bits_xml(folder, item if isinstance(item, dict) else None)
            out.append(
                {
                    "docid": docid,
                    "file_id": meta.get("file-id", "") or "",
                    "client": client,
                    "shortcode": shortcode,
                    "doc_type": meta.get("type", "") or "Books",
                    "dtd": meta.get("dtd") or "BITS",
                    "xml_path": xml_path,
                    "meta": meta,
                }
            )
        return out

    # Project mode: only meta entries that are BITS books
    for docid, meta in metas.items():
        if not isinstance(meta, dict):
            continue
        item = documents.get(docid) or {}
        if not isinstance(item, dict):
            item = {}
        probe = {
            "dtd": meta.get("dtd") or "",
            "doc_type": meta.get("type") or "",
            "folder": item.get("folder") or "",
            "xml_path": "",
        }
        if not is_bits_book_doc(probe, meta):
            continue
        client = meta.get("client") or ""
        shortcode = meta.get("project-shortcode") or ""
        if client_filter is not None and client.strip().upper() not in client_filter:
            continue
        if sc_filter is not None and shortcode not in sc_filter:
            continue
        folder_rel = item.get("folder") or f"BITS/{docid}"
        folder = root / folder_rel
        xml_path = _pick_bits_xml(folder, item)
        out.append(
            {
                "docid": docid,
                "file_id": meta.get("file-id", "") or "",
                "client": client,
                "shortcode": shortcode,
                "doc_type": meta.get("type", "") or "",
                "dtd": meta.get("dtd") or "BITS",
                "xml_path": xml_path,
                "meta": meta,
            }
        )
    return out


def enrich_meta_dtd_basename(
    project_root: Path | str,
    *,
    docs: list[dict[str, Any]] | None = None,
    log: LogFn = _noop_log,
) -> dict[str, Any]:
    """Write dtd_basename into meta.json and documents.json for BITS books.

    Returns stats: updated_meta, updated_docs, skipped, errors.
    """
    root = Path(project_root)
    meta_path = root / "meta.json"
    docs_path = root / "documents.json"
    if not meta_path.is_file():
        raise FileNotFoundError(f"meta.json not found under {root}")

    with open(meta_path, encoding="utf-8") as f:
        metas: dict[str, Any] = json.load(f)

    documents: dict[str, Any] | None = None
    if docs_path.is_file():
        with open(docs_path, encoding="utf-8") as f:
            documents = json.load(f)

    bit_docs = docs if docs is not None else collect_bits_docs(root)
    updated_meta = 0
    updated_docs = 0
    skipped = 0
    errors: list[str] = []

    for doc in bit_docs:
        docid = doc.get("docid") or ""
        if not docid:
            skipped += 1
            continue
        xml_path = doc.get("xml_path")
        info = resolve_dtd_basename(xml_path)
        if info.get("error") and info["error"] != "":
            if info["error"] == "xml not found":
                skipped += 1
            else:
                errors.append(f"{docid}: {info['error']}")
            # Still write NO_DTD when xml missing? Prefer skip write on missing xml.
            if info["error"] == "xml not found":
                continue

        bas = info["dtd_basename"] or "NO_DTD"
        entry = metas.setdefault(docid, {})
        if not isinstance(entry, dict):
            entry = {}
            metas[docid] = entry
        if entry.get("dtd_basename") != bas:
            entry["dtd_basename"] = bas
            updated_meta += 1
        else:
            entry["dtd_basename"] = bas  # ensure present

        if documents is not None and docid in documents:
            item = documents[docid]
            if not isinstance(item, dict):
                continue
            emb = item.setdefault("meta", {})
            if not isinstance(emb, dict):
                emb = {}
                item["meta"] = emb
            if emb.get("dtd_basename") != bas:
                updated_docs += 1
            emb["dtd_basename"] = bas

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metas, f, indent=2)
        f.write("\n")

    if documents is not None:
        with open(docs_path, "w", encoding="utf-8") as f:
            json.dump(documents, f, indent=2)
            f.write("\n")

    log(
        f"Enrich: meta fields set/updated for {updated_meta} doc(s); "
        f"documents.json meta for {updated_docs}; skipped={skipped}; errors={len(errors)}"
    )
    return {
        "updated_meta": updated_meta,
        "updated_docs": updated_docs,
        "skipped": skipped,
        "errors": errors,
    }


def uniqueness_key(row: dict[str, Any]) -> tuple:
    return (
        row.get("client") or "unknown",
        row.get("dtd_basename") or "NO_DTD",
        row.get("kind") or "",
        row.get("placement") or "",
        row.get("pattern_xpath") or "",
    )


def rollup_unique(detail_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple, dict[str, Any]] = {}
    order: list[tuple] = []
    for r in detail_rows:
        if r.get("error") and not r.get("pattern_xpath"):
            continue
        key = uniqueness_key(r)
        if key not in groups:
            groups[key] = {
                "client": key[0],
                "dtd_basename": key[1],
                "kind": key[2],
                "placement": key[3],
                "pattern_xpath": key[4],
                "file_ids": set(),
                "docids": set(),
                "sample_ids": [],
                "occurrence_count": 0,
                "dtd_mismatch_warning": r.get("dtd_mismatch") or "",
                "cardinality_warning": r.get("cardinality_warning") or "",
            }
            order.append(key)
        g = groups[key]
        g["occurrence_count"] += 1
        fid = r.get("file_id") or ""
        did = r.get("docid") or ""
        if fid:
            g["file_ids"].add(fid)
        if did:
            g["docids"].add(did)
        eid = r.get("element_id") or ""
        if eid and eid not in g["sample_ids"] and len(g["sample_ids"]) < SAMPLE_LIMIT:
            g["sample_ids"].append(eid)
        if not g["dtd_mismatch_warning"] and r.get("dtd_mismatch"):
            g["dtd_mismatch_warning"] = r["dtd_mismatch"]
        if not g["cardinality_warning"] and r.get("cardinality_warning"):
            g["cardinality_warning"] = r["cardinality_warning"]

    out: list[dict[str, Any]] = []
    for key in order:
        g = groups[key]
        out.append(
            {
                "client": g["client"],
                "dtd_basename": g["dtd_basename"],
                "kind": g["kind"],
                "placement": g["placement"],
                "pattern_xpath": g["pattern_xpath"],
                "file_count": len(g["file_ids"]) or len(g["docids"]),
                "occurrence_count": g["occurrence_count"],
                "sample_file_ids": sorted(g["file_ids"])[:SAMPLE_LIMIT],
                "sample_docids": sorted(g["docids"])[:SAMPLE_LIMIT],
                "sample_ids": g["sample_ids"],
                "dtd_mismatch_warning": g["dtd_mismatch_warning"],
                "cardinality_warning": g["cardinality_warning"],
            }
        )
    return out


def id_pattern_uniqueness_key(row: dict[str, Any]) -> tuple:
    return (
        row.get("client") or "unknown",
        row.get("dtd_basename") or "NO_DTD",
        row.get("kind") or "",
        row.get("area_category") or "unknown",
        row.get("id_pattern") or "",
    )


def rollup_id_patterns(detail_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple, dict[str, Any]] = {}
    order: list[tuple] = []
    for r in detail_rows:
        if r.get("error") and not r.get("id_pattern"):
            continue
        if not r.get("id_pattern") and not r.get("element_id"):
            continue
        key = id_pattern_uniqueness_key(r)
        if key not in groups:
            groups[key] = {
                "client": key[0],
                "dtd_basename": key[1],
                "kind": key[2],
                "area_category": key[3],
                "id_pattern": key[4],
                "file_ids": set(),
                "docids": set(),
                "sample_ids": [],
                "occurrence_count": 0,
            }
            order.append(key)
        g = groups[key]
        g["occurrence_count"] += 1
        fid = r.get("file_id") or ""
        did = r.get("docid") or ""
        if fid:
            g["file_ids"].add(fid)
        if did:
            g["docids"].add(did)
        eid = r.get("element_id") or ""
        if eid and eid not in g["sample_ids"] and len(g["sample_ids"]) < SAMPLE_LIMIT:
            g["sample_ids"].append(eid)
    out: list[dict[str, Any]] = []
    for key in order:
        g = groups[key]
        out.append(
            {
                "client": g["client"],
                "dtd_basename": g["dtd_basename"],
                "kind": g["kind"],
                "area_category": g["area_category"],
                "id_pattern": g["id_pattern"],
                "file_count": len(g["file_ids"]) or len(g["docids"]),
                "occurrence_count": g["occurrence_count"],
                "sample_file_ids": sorted(g["file_ids"])[:SAMPLE_LIMIT],
                "sample_docids": sorted(g["docids"])[:SAMPLE_LIMIT],
                "sample_ids": g["sample_ids"],
            }
        )
    return out


def write_unique_csv(rows: list[dict[str, Any]], out_path: Path) -> Path:
    ensure_dir(out_path.parent)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(UNIQUE_CSV_HEADERS)
        for r in rows:
            w.writerow(
                [
                    r.get("client", ""),
                    r.get("dtd_basename", ""),
                    r.get("kind", ""),
                    r.get("placement", ""),
                    r.get("pattern_xpath", ""),
                    r.get("file_count", 0),
                    r.get("occurrence_count", 0),
                    ";".join(r.get("sample_file_ids") or []),
                    ";".join(r.get("sample_docids") or []),
                    ";".join(r.get("sample_ids") or []),
                    r.get("dtd_mismatch_warning", ""),
                    r.get("cardinality_warning", ""),
                ]
            )
    return out_path


def write_id_patterns_csv(rows: list[dict[str, Any]], out_path: Path) -> Path:
    ensure_dir(out_path.parent)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(ID_PATTERN_CSV_HEADERS)
        for r in rows:
            w.writerow(
                [
                    r.get("client", ""),
                    r.get("dtd_basename", ""),
                    r.get("kind", ""),
                    r.get("area_category", ""),
                    r.get("id_pattern", ""),
                    r.get("file_count", 0),
                    r.get("occurrence_count", 0),
                    ";".join(r.get("sample_file_ids") or []),
                    ";".join(r.get("sample_docids") or []),
                    ";".join(r.get("sample_ids") or []),
                ]
            )
    return out_path


def write_detail_tsv(rows: list[dict[str, Any]], out_path: Path) -> Path:
    ensure_dir(out_path.parent)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(DETAIL_TSV_HEADERS)
        for r in rows:
            w.writerow(
                [
                    r.get("client", ""),
                    r.get("file_id", ""),
                    r.get("docid", ""),
                    r.get("dtd_basename", ""),
                    r.get("kind", ""),
                    r.get("placement", ""),
                    r.get("pattern_xpath", ""),
                    r.get("element_id", ""),
                    r.get("id_pattern", ""),
                    r.get("area_category", ""),
                    r.get("shortcode", ""),
                    r.get("dtd_mismatch", ""),
                    r.get("cardinality_warning", ""),
                    r.get("xml_path", ""),
                    r.get("error", ""),
                ]
            )
    return out_path


def _file_url(path_str: str) -> str:
    if not path_str:
        return ""
    p = Path(path_str)
    try:
        return p.resolve().as_uri()
    except Exception:
        s = str(path_str).replace("\\", "/")
        if len(s) >= 2 and s[1] == ":":
            return "file:///" + s
        return "file://" + s


def _doc_actions_html(xml_path: str) -> str:
    if not xml_path:
        return ""
    open_href = _file_url(xml_path)
    open_btn = (
        f"<a class='file-action-btn' href='{_esc(open_href)}' target='_blank' "
        f"rel='noopener noreferrer'>Open File</a>"
        if open_href
        else ""
    )
    copy_btn = (
        f"<button class='file-action-btn' "
        f"onclick='copyFilePath({_esc(json.dumps(xml_path))}, this, event)'>"
        f"Copy Path</button>"
    )
    return f'<div class="file-actions">{open_btn}{copy_btn}</div>'


def _scanned_docs_from_detail(detail_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for r in detail_rows:
        did = r.get("docid") or r.get("file_id") or ""
        if not did or did in seen:
            continue
        seen[did] = {
            "docid": r.get("docid") or "",
            "file_id": r.get("file_id") or "",
            "client": r.get("client") or "",
            "xml_path": r.get("xml_path") or "",
            "cardinality_warning": r.get("cardinality_warning") or "",
        }
        order.append(did)
    # Prefer strongest cardinality warning if later rows add it
    for r in detail_rows:
        did = r.get("docid") or r.get("file_id") or ""
        if did in seen and r.get("cardinality_warning"):
            seen[did]["cardinality_warning"] = r["cardinality_warning"]
    return [seen[k] for k in order]


def write_html_report(
    unique_rows: list[dict[str, Any]],
    detail_rows: list[dict[str, Any]],
    out_path: Path,
    *,
    title: str = "Footnotes Group Report (BITS)",
    stats: dict[str, Any] | None = None,
    id_pattern_rows: list[dict[str, Any]] | None = None,
) -> Path:
    ensure_dir(out_path.parent)
    stats = stats or {}
    id_pattern_rows = id_pattern_rows or []
    clients = sorted({(r.get("client") or "unknown") for r in unique_rows}, key=str.lower)
    dtds = sorted({(r.get("dtd_basename") or "") for r in unique_rows}, key=str.lower)
    kinds = sorted({(r.get("kind") or "") for r in unique_rows})
    placements = sorted({(r.get("placement") or "") for r in unique_rows})
    areas = sorted({(r.get("area_category") or "") for r in id_pattern_rows})

    body_rows = "".join(
        (
            "<tr"
            f' data-client="{_esc(r.get("client") or "")}"'
            f' data-dtd="{_esc(r.get("dtd_basename") or "")}"'
            f' data-kind="{_esc(r.get("kind") or "")}"'
            f' data-placement="{_esc(r.get("placement") or "")}">'
            f'<td>{_esc(r.get("client") or "")}</td>'
            f'<td><code>{_esc(r.get("dtd_basename") or "")}</code></td>'
            f'<td>{_esc(r.get("kind") or "")}</td>'
            f'<td>{_esc(r.get("placement") or "")}</td>'
            f'<td><code class="pat">{_esc(r.get("pattern_xpath") or "")}</code></td>'
            f'<td>{int(r.get("file_count") or 0)}</td>'
            f'<td>{int(r.get("occurrence_count") or 0)}</td>'
            f'<td>{_esc(", ".join(r.get("sample_file_ids") or []))}</td>'
            f'<td class="warn">{_esc(r.get("dtd_mismatch_warning") or "")}'
            f'{(" / " + _esc(r.get("cardinality_warning") or "")) if r.get("cardinality_warning") else ""}</td>'
            "</tr>"
        )
        for r in unique_rows
    ) or "<tr><td colspan='9'><em>No unique patterns.</em></td></tr>"

    id_rows_html = "".join(
        (
            "<tr"
            f' data-client="{_esc(r.get("client") or "")}"'
            f' data-kind="{_esc(r.get("kind") or "")}"'
            f' data-area="{_esc(r.get("area_category") or "")}">'
            f'<td>{_esc(r.get("client") or "")}</td>'
            f'<td><code>{_esc(r.get("dtd_basename") or "")}</code></td>'
            f'<td>{_esc(r.get("kind") or "")}</td>'
            f'<td>{_esc(r.get("area_category") or "")}</td>'
            f'<td><code class="pat">{_esc(r.get("id_pattern") or "")}</code></td>'
            f'<td>{int(r.get("file_count") or 0)}</td>'
            f'<td>{int(r.get("occurrence_count") or 0)}</td>'
            f'<td>{_esc(", ".join(r.get("sample_ids") or []))}</td>'
            "</tr>"
        )
        for r in id_pattern_rows
    ) or "<tr><td colspan='8'><em>No ID patterns.</em></td></tr>"

    scanned = _scanned_docs_from_detail(detail_rows)
    doc_rows = "".join(
        (
            "<tr>"
            f'<td>{_esc(d.get("client") or "")}</td>'
            f'<td>{_esc(d.get("file_id") or "")}</td>'
            f'<td>{_esc(d.get("docid") or "")}</td>'
            f'<td class="warn">{_esc(d.get("cardinality_warning") or "")}</td>'
            f'<td>{_doc_actions_html(d.get("xml_path") or "")}</td>'
            "</tr>"
        )
        for d in scanned[:500]
    ) or "<tr><td colspan='5'><em>None</em></td></tr>"

    err_rows = [r for r in detail_rows if r.get("error")]
    err_html = "".join(
        f"<tr><td>{_esc(r.get('docid') or '')}</td>"
        f"<td>{_esc(r.get('file_id') or '')}</td>"
        f"<td class='warn'>{_esc(r.get('error') or '')}</td>"
        f"<td>{_doc_actions_html(r.get('xml_path') or '')}</td></tr>"
        for r in err_rows[:200]
    ) or "<tr><td colspan='4'><em>None</em></td></tr>"

    def _opts(values: list[str]) -> str:
        return "".join(f'<option value="{_esc(v)}">{_esc(v)}</option>' for v in values)

    n_docs = int(stats.get("n_docs") or 0)
    n_with = int(stats.get("n_with_targets") or 0)
    n_unique = len(unique_rows)
    n_occ = sum(int(r.get("occurrence_count") or 0) for r in unique_rows)
    n_excl = int(stats.get("excluded_table_fn") or 0)
    n_id = len(id_pattern_rows)

    html_doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>{_esc(title)}</title>
<style>
body{{font-family:Segoe UI,system-ui,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:24px}}
h1,h2{{color:#a5b4fc}}.meta{{color:#94a3b8;margin-bottom:12px}}
.kpi-row{{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0 18px}}
.kpi{{background:#1e293b;border-radius:10px;padding:14px 18px;min-width:110px;border-left:4px solid #6366f1}}
.kpi-n{{font-size:22px;font-weight:700;color:#34d399}}.kpi-l{{font-size:12px;color:#94a3b8}}
.filters{{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 16px;align-items:center}}
.filters input,.filters select{{background:#334155;color:#e2e8f0;border:1px solid #475569;border-radius:6px;padding:6px 10px}}
table{{width:100%;border-collapse:collapse;font-size:13px;background:#1e293b;border-radius:8px;overflow:hidden;margin-bottom:24px}}
th,td{{border-bottom:1px solid #334155;padding:8px 10px;text-align:left;vertical-align:top}}
th{{color:#94a3b8;font-size:11px;text-transform:uppercase}}
code{{color:#c4b5fd}} code.pat{{color:#67e8f9;font-size:12px;word-break:break-all}}
.warn{{color:#fbbf24;font-size:12px}}
.file-actions{{display:flex;gap:6px;flex-wrap:wrap}}
.file-action-btn{{background:#334155;border:1px solid #475569;color:#e2e8f0;border-radius:6px;
padding:4px 10px;font-size:12px;cursor:pointer;text-decoration:none;display:inline-block}}
.file-action-btn:hover{{border-color:#818cf8;color:#c7d2fe}}
.file-action-btn.copied{{background:rgba(16,185,129,0.2);border-color:#10b981}}
#toast{{position:fixed;bottom:20px;right:20px;background:#10b981;color:#0f172a;padding:10px 16px;
border-radius:8px;opacity:0;transition:opacity .2s;pointer-events:none}}
#toast.show{{opacity:1}}
</style></head><body>
<h1>{_esc(title)}</h1>
<p class="meta">Report v{REPORT_VERSION} · generated {datetime.now().strftime("%Y-%m-%d %H:%M")} · BITS books only · table-fn excluded</p>
<div class="kpi-row">
  <div class="kpi"><div class="kpi-n">{n_docs}</div><div class="kpi-l">BITS docs</div></div>
  <div class="kpi"><div class="kpi-n">{n_with}</div><div class="kpi-l">with fn/ref targets</div></div>
  <div class="kpi"><div class="kpi-n">{n_unique}</div><div class="kpi-l">unique patterns</div></div>
  <div class="kpi"><div class="kpi-n">{n_occ}</div><div class="kpi-l">occurrences</div></div>
  <div class="kpi"><div class="kpi-n">{n_excl}</div><div class="kpi-l">table-fn skipped</div></div>
  <div class="kpi"><div class="kpi-n">{n_id}</div><div class="kpi-l">ID pattern keys</div></div>
</div>
<div class="filters">
  <input id="q" type="search" placeholder="Search pattern, client, DTD..." oninput="applyFilters()"/>
  <select id="filterClient" onchange="applyFilters()"><option value="">All clients</option>{_opts(clients)}</select>
  <select id="filterDtd" onchange="applyFilters()"><option value="">All DTDs</option>{_opts(dtds)}</select>
  <select id="filterKind" onchange="applyFilters()"><option value="">All kinds</option>{_opts(kinds)}</select>
  <select id="filterPlacement" onchange="applyFilters()"><option value="">All placements</option>{_opts(placements)}</select>
</div>
<h2>Unique structural patterns</h2>
<table id="patTable">
<thead><tr>
<th>Client</th><th>DTD</th><th>Kind</th><th>Placement</th><th>Pattern</th>
<th>Files</th><th>Occ</th><th>Sample file-ids</th><th>Warnings</th>
</tr></thead>
<tbody>{body_rows}</tbody>
</table>
<h2>ID patterns by category</h2>
<div class="filters">
  <select id="filterIdKind" onchange="applyIdFilters()"><option value="">All kinds</option>{_opts(kinds)}</select>
  <select id="filterArea" onchange="applyIdFilters()"><option value="">All areas</option>{_opts(areas)}</select>
</div>
<table id="idTable">
<thead><tr>
<th>Client</th><th>DTD</th><th>Kind</th><th>Area</th><th>ID pattern</th>
<th>Files</th><th>Occ</th><th>Sample ids</th>
</tr></thead>
<tbody>{id_rows_html}</tbody>
</table>
<h2>Scanned documents</h2>
<table><thead><tr><th>Client</th><th>File_id</th><th>Docid</th><th>Warning</th><th>Actions</th></tr></thead>
<tbody>{doc_rows}</tbody></table>
<h2>Errors / skips</h2>
<table><thead><tr><th>Docid</th><th>File_id</th><th>Error</th><th>Actions</th></tr></thead>
<tbody>{err_html}</tbody></table>
<div id="toast">Copied</div>
<script>
function applyFilters(){{
  const q=(document.getElementById('q').value||'').toLowerCase();
  const client=document.getElementById('filterClient').value;
  const dtd=document.getElementById('filterDtd').value;
  const kind=document.getElementById('filterKind').value;
  const placement=document.getElementById('filterPlacement').value;
  document.querySelectorAll('#patTable tbody tr').forEach(tr=>{{
    if(!tr.getAttribute('data-client')) return;
    const hay=tr.innerText.toLowerCase();
    let ok=true;
    if(client && tr.getAttribute('data-client')!==client) ok=false;
    if(dtd && tr.getAttribute('data-dtd')!==dtd) ok=false;
    if(kind && tr.getAttribute('data-kind')!==kind) ok=false;
    if(placement && tr.getAttribute('data-placement')!==placement) ok=false;
    if(q && !hay.includes(q)) ok=false;
    tr.style.display=ok?'':'none';
  }});
}}
function applyIdFilters(){{
  const kind=document.getElementById('filterIdKind').value;
  const area=document.getElementById('filterArea').value;
  document.querySelectorAll('#idTable tbody tr').forEach(tr=>{{
    if(!tr.getAttribute('data-client')) return;
    let ok=true;
    if(kind && tr.getAttribute('data-kind')!==kind) ok=false;
    if(area && tr.getAttribute('data-area')!==area) ok=false;
    tr.style.display=ok?'':'none';
  }});
}}
function copyFilePath(path, btn, evt) {{
  if (evt) evt.stopPropagation();
  const done = () => {{
    if (btn) {{ btn.classList.add('copied'); btn.textContent = 'Copied';
      setTimeout(() => {{ btn.classList.remove('copied'); btn.textContent = 'Copy Path'; }}, 1200); }}
    const t = document.getElementById('toast');
    if (t) {{ t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 1200); }}
  }};
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(path).then(done).catch(() => {{
      const ta = document.createElement('textarea'); ta.value = path; document.body.appendChild(ta);
      ta.select(); try {{ document.execCommand('copy'); }} catch (e) {{}}
      document.body.removeChild(ta); done();
    }});
  }} else {{
    const ta = document.createElement('textarea'); ta.value = path; document.body.appendChild(ta);
    ta.select(); try {{ document.execCommand('copy'); }} catch (e) {{}}
    document.body.removeChild(ta); done();
  }}
}}
</script>
</body></html>
"""
    out_path.write_text(html_doc, encoding="utf-8")
    return out_path


def run_fn_group_report(
    project_root: Path | str,
    shortcodes: Optional[Iterable[str]] = None,
    clients: Optional[Iterable[str]] = None,
    report_dir: Path | str | None = None,
    *,
    folder_mode: bool = False,
    update_meta: bool = True,
    log: LogFn = _noop_log,
    progress: ProgressFn = _noop_progress,
    cancel_check: CancelFn = _noop_cancel,
) -> dict[str, Any]:
    """Scan BITS books for unique fn-group / ref-list patterns; optional meta enrich."""
    root = Path(project_root)
    out_dir = Path(report_dir) if report_dir else make_report_dir()
    ensure_dir(out_dir)

    docs = collect_bits_docs(
        root, shortcodes=shortcodes, clients=clients, folder_mode=folder_mode
    )
    log(f"Footnotes Group Report v{REPORT_VERSION}: {len(docs)} BITS book(s) from {root}")

    enrich_stats: dict[str, Any] = {}
    if update_meta:
        try:
            enrich_stats = enrich_meta_dtd_basename(root, docs=docs, log=log)
        except Exception as exc:  # noqa: BLE001
            log(f"Enrich failed: {exc}")
            enrich_stats = {"error": str(exc)}

    detail_rows: list[dict[str, Any]] = []
    n_with_targets = 0
    excluded_table_fn = 0
    total = len(docs)
    for i, doc in enumerate(docs, start=1):
        if cancel_check():
            log("Cancelled.")
            break
        docid = doc.get("docid") or ""
        progress(i, total, docid)
        xml_path = doc.get("xml_path")
        xml_str = str(xml_path) if xml_path else ""
        identity = {
            "docid": docid,
            "file_id": doc.get("file_id") or "",
            "client": doc.get("client") or "",
            "shortcode": doc.get("shortcode") or "",
            "xml_path": xml_str,
        }
        info = resolve_dtd_basename(xml_path)
        bas = info["dtd_basename"] or "NO_DTD"
        mismatch = dtd_mismatch_warning(identity["client"], bas)

        if not xml_path or not Path(xml_path).is_file():
            detail_rows.append(
                {
                    **identity,
                    "dtd_basename": bas,
                    "kind": "",
                    "placement": "",
                    "pattern_xpath": "",
                    "element_id": "",
                    "id_pattern": "",
                    "area_category": "",
                    "dtd_mismatch": mismatch,
                    "cardinality_warning": "",
                    "error": info.get("error") or "xml not found",
                }
            )
            continue

        try:
            targets, excl = extract_targets(xml_path)
            excluded_table_fn += excl
        except Exception as exc:  # noqa: BLE001
            detail_rows.append(
                {
                    **identity,
                    "dtd_basename": bas,
                    "kind": "",
                    "placement": "",
                    "pattern_xpath": "",
                    "element_id": "",
                    "id_pattern": "",
                    "area_category": "",
                    "dtd_mismatch": mismatch,
                    "cardinality_warning": "",
                    "error": str(exc),
                }
            )
            continue

        if not targets:
            continue

        n_with_targets += 1
        for t in targets:
            detail_rows.append(
                {
                    **identity,
                    "dtd_basename": bas,
                    "kind": t["kind"],
                    "placement": t["placement"],
                    "pattern_xpath": t["pattern_xpath"],
                    "element_id": t["element_id"],
                    "id_pattern": t.get("id_pattern") or "",
                    "area_category": t.get("area_category") or "",
                    "dtd_mismatch": mismatch,
                    "cardinality_warning": "",
                    "error": "",
                }
            )

    apply_book_end_cardinality_warnings(detail_rows)
    unique_rows = rollup_unique(detail_rows)
    id_rows = rollup_id_patterns(detail_rows)
    csv_path = write_unique_csv(unique_rows, out_dir / "unique_patterns.csv")
    id_csv_path = write_id_patterns_csv(id_rows, out_dir / "unique_id_patterns.csv")
    tsv_path = write_detail_tsv(detail_rows, out_dir / "detail.tsv")
    html_path = write_html_report(
        unique_rows,
        detail_rows,
        out_dir / "summary.html",
        stats={
            "n_docs": len(docs),
            "n_with_targets": n_with_targets,
            "excluded_table_fn": excluded_table_fn,
        },
        id_pattern_rows=id_rows,
    )

    log(
        f"Unique patterns: {len(unique_rows)}; ID patterns: {len(id_rows)}; "
        f"detail rows: {len(detail_rows)}; table-fn skipped: {excluded_table_fn}"
    )
    log(f"Report folder: {out_dir}")

    return {
        "report_dir": str(out_dir),
        "html_path": str(html_path),
        "csv_path": str(csv_path),
        "tsv_path": str(tsv_path),
        "id_patterns_csv_path": str(id_csv_path),
        "n_docs": len(docs),
        "n_with_targets": n_with_targets,
        "n_unique": len(unique_rows),
        "n_id_patterns": len(id_rows),
        "n_detail": len(detail_rows),
        "excluded_table_fn": excluded_table_fn,
        "unique_rows": unique_rows,
        "id_pattern_rows": id_rows,
        "detail_rows": detail_rows,
        "enrich": enrich_stats,
        "report_version": REPORT_VERSION,
    }

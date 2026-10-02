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

REPORT_VERSION = 1
REPORT_DIR = "fn_group_reports"
SUPPORT_LOG_NAME = "impact-support-log"
REPORT_ROOT: Path | None = None

SAMPLE_LIMIT = 8
STABLE_ATTRS = frozenset({"book-part-type", "content-type", "class"})
TARGET_KINDS = ("fn-group", "ref-list")

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
    "Shortcode",
    "DTD_mismatch",
    "Error",
]

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


def classify_placement(el: etree._Element) -> str:
    """chapter-end | book-end | front-matter | other."""
    names: list[str] = []
    cur: etree._Element | None = el
    while cur is not None:
        names.append(local_name(cur.tag))
        parent = cur.getparent()
        cur = parent if isinstance(parent, etree._Element) else None
    # names[0] is the element itself; walk ancestors
    ancestors = names[1:]
    if "book-back" in ancestors:
        return "book-end"
    if "front-matter" in ancestors or "front-matter-part" in ancestors:
        return "front-matter"
    # chapter-end: under book-part ... back ... target
    if "book-part" in ancestors and "back" in ancestors:
        # Ensure back is between book-part and the element in the ancestor chain
        try:
            i_part = ancestors.index("book-part")
            i_back = ancestors.index("back")
            if i_back < i_part:  # closer to element than book-part is farther... ancestors are parent-first
                # ancestors: [parent, ..., root] so smaller index = closer to el
                # back should be closer (smaller index) than book-part (farther)
                return "chapter-end"
        except ValueError:
            pass
        return "chapter-end"
    return "other"


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


def extract_targets(xml_path: Path | str) -> list[dict[str, Any]]:
    """Find all fn-group and ref-list; return pattern/placement/id rows."""
    root = _parse_xml(Path(xml_path))
    rows: list[dict[str, Any]] = []
    for kind in TARGET_KINDS:
        for el in root.xpath(f'//*[local-name()="{kind}"]'):
            rows.append(
                {
                    "kind": kind,
                    "placement": classify_placement(el),
                    "pattern_xpath": pattern_xpath_for_element(el),
                    "element_id": el.attrib.get("id") or "",
                }
            )
    return rows


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
                    r.get("shortcode", ""),
                    r.get("dtd_mismatch", ""),
                    r.get("error", ""),
                ]
            )
    return out_path


def write_html_report(
    unique_rows: list[dict[str, Any]],
    detail_rows: list[dict[str, Any]],
    out_path: Path,
    *,
    title: str = "Footnotes Group Report (BITS)",
    stats: dict[str, Any] | None = None,
) -> Path:
    ensure_dir(out_path.parent)
    stats = stats or {}
    clients = sorted({(r.get("client") or "unknown") for r in unique_rows}, key=str.lower)
    dtds = sorted({(r.get("dtd_basename") or "") for r in unique_rows}, key=str.lower)
    kinds = sorted({(r.get("kind") or "") for r in unique_rows})
    placements = sorted({(r.get("placement") or "") for r in unique_rows})

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
            f'<td class="warn">{_esc(r.get("dtd_mismatch_warning") or "")}</td>'
            "</tr>"
        )
        for r in unique_rows
    ) or "<tr><td colspan='9'><em>No unique patterns.</em></td></tr>"

    err_rows = [r for r in detail_rows if r.get("error")]
    err_html = "".join(
        f"<tr><td>{_esc(r.get('docid') or '')}</td>"
        f"<td>{_esc(r.get('file_id') or '')}</td>"
        f"<td class='warn'>{_esc(r.get('error') or '')}</td></tr>"
        for r in err_rows[:200]
    ) or "<tr><td colspan='3'><em>None</em></td></tr>"

    def _opts(values: list[str]) -> str:
        return "".join(f'<option value="{_esc(v)}">{_esc(v)}</option>' for v in values)

    n_docs = int(stats.get("n_docs") or 0)
    n_with = int(stats.get("n_with_targets") or 0)
    n_unique = len(unique_rows)
    n_occ = sum(int(r.get("occurrence_count") or 0) for r in unique_rows)

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
table{{width:100%;border-collapse:collapse;font-size:13px;background:#1e293b;border-radius:8px;overflow:hidden}}
th,td{{border-bottom:1px solid #334155;padding:8px 10px;text-align:left;vertical-align:top}}
th{{color:#94a3b8;font-size:11px;text-transform:uppercase}}
code{{color:#c4b5fd}} code.pat{{color:#67e8f9;font-size:12px;word-break:break-all}}
.warn{{color:#fbbf24;font-size:12px}}
</style></head><body>
<h1>{_esc(title)}</h1>
<p class="meta">Report v{REPORT_VERSION} · generated {datetime.now().strftime("%Y-%m-%d %H:%M")} · BITS books only</p>
<div class="kpi-row">
  <div class="kpi"><div class="kpi-n">{n_docs}</div><div class="kpi-l">BITS docs</div></div>
  <div class="kpi"><div class="kpi-n">{n_with}</div><div class="kpi-l">with fn/ref targets</div></div>
  <div class="kpi"><div class="kpi-n">{n_unique}</div><div class="kpi-l">unique patterns</div></div>
  <div class="kpi"><div class="kpi-n">{n_occ}</div><div class="kpi-l">occurrences</div></div>
</div>
<div class="filters">
  <input id="q" type="search" placeholder="Search pattern, client, DTD..." oninput="applyFilters()"/>
  <select id="filterClient" onchange="applyFilters()"><option value="">All clients</option>{_opts(clients)}</select>
  <select id="filterDtd" onchange="applyFilters()"><option value="">All DTDs</option>{_opts(dtds)}</select>
  <select id="filterKind" onchange="applyFilters()"><option value="">All kinds</option>{_opts(kinds)}</select>
  <select id="filterPlacement" onchange="applyFilters()"><option value="">All placements</option>{_opts(placements)}</select>
</div>
<h2>Unique patterns</h2>
<table id="patTable">
<thead><tr>
<th>Client</th><th>DTD</th><th>Kind</th><th>Placement</th><th>Pattern</th>
<th>Files</th><th>Occ</th><th>Sample file-ids</th><th>DTD warning</th>
</tr></thead>
<tbody>{body_rows}</tbody>
</table>
<h2>Errors / skips</h2>
<table><thead><tr><th>Docid</th><th>File_id</th><th>Error</th></tr></thead>
<tbody>{err_html}</tbody></table>
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
    total = len(docs)
    for i, doc in enumerate(docs, start=1):
        if cancel_check():
            log("Cancelled.")
            break
        docid = doc.get("docid") or ""
        progress(i, total, docid)
        xml_path = doc.get("xml_path")
        identity = {
            "docid": docid,
            "file_id": doc.get("file_id") or "",
            "client": doc.get("client") or "",
            "shortcode": doc.get("shortcode") or "",
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
                    "dtd_mismatch": mismatch,
                    "error": info.get("error") or "xml not found",
                }
            )
            continue

        try:
            targets = extract_targets(xml_path)
        except Exception as exc:  # noqa: BLE001
            detail_rows.append(
                {
                    **identity,
                    "dtd_basename": bas,
                    "kind": "",
                    "placement": "",
                    "pattern_xpath": "",
                    "element_id": "",
                    "dtd_mismatch": mismatch,
                    "error": str(exc),
                }
            )
            continue

        if not targets:
            # No targets is not an error; record a sentinel? Skip detail — counted via n_docs
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
                    "dtd_mismatch": mismatch,
                    "error": "",
                }
            )

    unique_rows = rollup_unique(detail_rows)
    csv_path = write_unique_csv(unique_rows, out_dir / "unique_patterns.csv")
    tsv_path = write_detail_tsv(detail_rows, out_dir / "detail.tsv")
    html_path = write_html_report(
        unique_rows,
        detail_rows,
        out_dir / "summary.html",
        stats={
            "n_docs": len(docs),
            "n_with_targets": n_with_targets,
        },
    )

    log(f"Unique patterns: {len(unique_rows)}; detail rows: {len(detail_rows)}")
    log(f"Report folder: {out_dir}")

    return {
        "report_dir": str(out_dir),
        "html_path": str(html_path),
        "csv_path": str(csv_path),
        "tsv_path": str(tsv_path),
        "n_docs": len(docs),
        "n_with_targets": n_with_targets,
        "n_unique": len(unique_rows),
        "n_detail": len(detail_rows),
        "unique_rows": unique_rows,
        "detail_rows": detail_rows,
        "enrich": enrich_stats,
        "report_version": REPORT_VERSION,
    }

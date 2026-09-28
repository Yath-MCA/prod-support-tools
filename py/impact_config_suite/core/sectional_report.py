"""Sectional Report — FRONT/BODY/REF/OTHER section + DOI/URI query counts.

Supports JATS articles (<front>/<body>/<back>) and BITS books
(<front-matter>/<book-meta>/<book-body> with nested book-part body/back/ref-list).

REPORT_VERSION is bumped on every behaviour change that affects outputs.
"""
from __future__ import annotations

import csv
import html
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from lxml import etree

REPORT_VERSION = 4
REPORT_DIR = "sectional_reports"
SUPPORT_LOG_NAME = "impact-support-log"
# Tests / callers may set REPORT_ROOT to redirect away from ~/Documents/...
REPORT_ROOT: Path | None = None

SECTIONS = ("FRONT", "BODY", "REF", "OTHER")
QUERY_KEYS = ("doi_id", "extlink_doi", "extlink_uri", "uri")

# Relative XPath under each section root (namespace-safe via local-name()).
QUERY_XPATH: dict[str, str] = {
    "doi_id": ".//*[@pub-id-type='doi']",
    "extlink_doi": ".//*[local-name()='ext-link' and @ext-link-type='doi']",
    "extlink_uri": ".//*[local-name()='ext-link' and @ext-link-type='uri']",
    "uri": ".//*[local-name()='uri']",
}

# Unique-key type metadata per query (never includes href).
QUERY_TYPE_META: dict[str, tuple[str, str]] = {
    # type_attr, type_value  (tag comes from the matched element)
    "doi_id": ("pub-id-type", "doi"),
    "extlink_doi": ("ext-link-type", "doi"),
    "extlink_uri": ("ext-link-type", "uri"),
    "uri": ("", ""),
}

TSV_HEADERS = [
    "Docid",
    "File_id",
    "FRONT",
    "BODY",
    "REF",
    "OTHER",
    "doi_id",
    "extlink_doi",
    "extlink_uri",
    "uri",
]

SAMPLE_LIMIT = 5
MAX_SAMPLE_TEXT = 200

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


def local_name(tag: str | None) -> str:
    if not tag:
        return ""
    if isinstance(tag, bytes):
        tag = tag.decode("utf-8", errors="replace")
    return tag.rsplit("}", 1)[-1]


def _parse_xml(xml_path: Path) -> etree._Element:
    parser = etree.XMLParser(recover=True, resolve_entities=False, huge_tree=True)
    tree = etree.parse(str(xml_path), parser)
    return tree.getroot()


def _find_all_by_local(root: etree._Element, name: str) -> list[etree._Element]:
    return [el for el in root.iter() if isinstance(el.tag, str) and local_name(el.tag) == name]


def _direct_children(el: etree._Element) -> list[etree._Element]:
    return [c for c in el if isinstance(c.tag, str)]


def _section_roots(root: etree._Element) -> dict[str, list[etree._Element]]:
    # FRONT: JATS <front> / BITS <front-matter> / BITS <book-meta>
    front: list[etree._Element] = []
    for name in ("front", "front-matter", "book-meta"):
        front.extend(_find_all_by_local(root, name))
    # BODY: <body> only (nested book-part bodies are fine; non-overlapping with back)
    body = _find_all_by_local(root, "body")
    backs = _find_all_by_local(root, "back")
    ref: list[etree._Element] = []
    other: list[etree._Element] = []
    for back in backs:
        for child in _direct_children(back):
            if local_name(child.tag) == "ref-list":
                ref.append(child)
            else:
                other.append(child)
    return {"FRONT": front, "BODY": body, "REF": ref, "OTHER": other}



def _element_text(el: etree._Element) -> str:
    text = "".join(el.itertext())
    text = " ".join(text.split())
    if len(text) > MAX_SAMPLE_TEXT:
        text = text[: MAX_SAMPLE_TEXT - 1] + "…"
    return text


def _unique_key(section: str, query_key: str, el: etree._Element) -> tuple[str, str, str, str]:
    type_attr, type_value = QUERY_TYPE_META[query_key]
    tag = local_name(el.tag)
    if query_key == "doi_id":
        # Prefer actual element tag; type is always pub-id-type=doi
        return (section, tag, type_attr, type_value)
    if query_key == "uri":
        return (section, "uri", "", "")
    # ext-link variants
    return (section, "ext-link", type_attr, type_value)


def _run_query(
    section_root: etree._Element,
    query_key: str,
) -> list[etree._Element]:
    xpath = QUERY_XPATH[query_key]
    try:
        hits = section_root.xpath(xpath)
    except etree.XPathError:
        hits = []
    return [h for h in hits if isinstance(h, etree._Element)]


def extract_file(xml_path: str | Path) -> dict[str, Any]:
    """Extract section counts, per-section query hits, aggregates, and unique keys.

    Returns a dict:
      section_counts: {FRONT|BODY|REF|OTHER: int}
      per_section: {section: {query_key: {count, hits:[{tag,text}]}}}
      query_totals: {query_key: int}  # sum across sections
      unique: {(section, tag, type_attr, type_value): {count, sample_texts: [...]}}
      error: optional str
    """
    path = Path(xml_path)
    empty_section = {
        qk: {"count": 0, "hits": []} for qk in QUERY_KEYS
    }
    result: dict[str, Any] = {
        "xml_path": str(path),
        "section_counts": {s: 0 for s in SECTIONS},
        "per_section": {s: {qk: {"count": 0, "hits": []} for qk in QUERY_KEYS} for s in SECTIONS},
        "query_totals": {qk: 0 for qk in QUERY_KEYS},
        "unique": {},
        "error": None,
    }
    try:
        root = _parse_xml(path)
    except Exception as exc:  # noqa: BLE001 — surface parse errors in row
        result["error"] = str(exc)
        return result

    roots = _section_roots(root)
    unique: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    for section in SECTIONS:
        section_els = roots[section]
        result["section_counts"][section] = len(section_els)
        for sec_el in section_els:
            for qk in QUERY_KEYS:
                hits = _run_query(sec_el, qk)
                bucket = result["per_section"][section][qk]
                for el in hits:
                    text = _element_text(el)
                    tag = local_name(el.tag)
                    bucket["hits"].append({"tag": tag, "text": text})
                    key = _unique_key(section, qk, el)
                    entry = unique.setdefault(
                        key, {"count": 0, "sample_texts": [], "query_key": qk}
                    )
                    entry["count"] += 1
                    if len(entry["sample_texts"]) < SAMPLE_LIMIT and text:
                        if text not in entry["sample_texts"]:
                            entry["sample_texts"].append(text)
                bucket["count"] += len(hits)
                result["query_totals"][qk] += len(hits)

    # Serialize unique keys as list of dicts for JSON-friendliness
    result["unique"] = [
        {
            "section": k[0],
            "tag": k[1],
            "type_attr": k[2],
            "type_value": k[3],
            "count": v["count"],
            "sample_texts": v["sample_texts"],
            "query_key": v["query_key"],
        }
        for k, v in sorted(unique.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2], kv[0][3]))
    ]
    return result


def _iter_project_docs(
    project_root: Path,
    shortcodes: Optional[Iterable[str]] = None,
) -> list[dict[str, Any]]:
    """Load project docs for all DTDs (JATS + BITS); return doc descriptors.

    Unlike contrib_extractor.build_index (JATS-only via RUN_DTD), sectional report
    includes BITS books so front-matter / book-body documents are covered.
    """
    from core import contrib_extractor as ce

    base = Path(project_root)
    docs = ce.load_json(base / ce.DOCS_NAME)
    metas = ce.load_json(base / ce.META_NAME)
    sc_filter: set[str] | None = None
    if shortcodes:
        sc_filter = {s.strip() for s in shortcodes if s and str(s).strip()}

    # Index all DTDs: {client: {shortcode: [docid, ...]}}
    index: dict[str, dict[str, list[str]]] = {}
    for docid, meta in metas.items():
        item = docs.get(docid)
        if item is None:
            continue
        client = meta.get("client") or "unknown"
        shortcode = meta.get("project-shortcode") or "unknown"
        index.setdefault(client, {}).setdefault(shortcode, []).append(docid)

    rows: list[dict[str, Any]] = []
    for client, sc_map in index.items():
        for shortcode, docids in sc_map.items():
            if sc_filter is not None and shortcode not in sc_filter:
                continue
            for docid in docids:
                meta = metas.get(docid) or {}
                item = docs.get(docid) or {}
                folder = ce.doc_folder(base, docid, item, meta)
                candidates = ce.candidate_xml_files(base, folder, item)
                xml_path = _pick_document_xml(candidates)
                rows.append(
                    {
                        "docid": docid,
                        "file_id": meta.get("file-id", "") or "",
                        "client": meta.get("client") or client or "",
                        "shortcode": meta.get("project-shortcode") or shortcode or "",
                        "xml_path": xml_path,
                    }
                )
    return rows



def _pick_document_xml(candidates: list[Path]) -> Path | None:
    if not candidates:
        return None
    # Prefer a full document: JATS front/body or BITS front-matter/book-meta/book-body.
    prefer_names = ("front", "front-matter", "book-meta", "body", "book-body")
    for p in candidates:
        try:
            root = _parse_xml(p)
            if any(_find_all_by_local(root, name) for name in prefer_names):
                return p
        except Exception:
            continue
    return candidates[0]



def _iter_folder_xmls(folder: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in sorted(folder.rglob("*.xml")):
        if not p.is_file():
            continue
        name = p.name.lower()
        if name in {"impact_config.xml", "contrib_group.xml"}:
            continue
        rows.append(
            {
                "docid": p.stem,
                "file_id": "",
                "client": "",
                "shortcode": "",
                "xml_path": p,
            }
        )
    return rows


def collect_docs(
    project_root: Path | str,
    shortcodes: Optional[Iterable[str]] = None,
    folder_mode: bool = False,
) -> list[dict[str, Any]]:
    """Return list of {docid, file_id, client, shortcode, xml_path}."""
    root = Path(project_root)
    if folder_mode:
        return _iter_folder_xmls(root)
    docs_json = root / "documents.json"
    meta_json = root / "meta.json"
    if docs_json.is_file() and meta_json.is_file():
        try:
            return _iter_project_docs(root, shortcodes=shortcodes)
        except Exception:
            # Fall through to folder scan if project load fails
            pass
    return _iter_folder_xmls(root)


def write_tsv(rows: list[dict[str, Any]], out_path: Path) -> Path:
    ensure_dir(out_path.parent)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(TSV_HEADERS)
        for r in rows:
            sc = r.get("section_counts") or {}
            qt = r.get("query_totals") or {}
            writer.writerow(
                [
                    r.get("docid", ""),
                    r.get("file_id", ""),
                    sc.get("FRONT", 0),
                    sc.get("BODY", 0),
                    sc.get("REF", 0),
                    sc.get("OTHER", 0),
                    qt.get("doi_id", 0),
                    qt.get("extlink_doi", 0),
                    qt.get("extlink_uri", 0),
                    qt.get("uri", 0),
                ]
            )
    return out_path


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def write_html_report(
    rows: list[dict[str, Any]],
    out_path: Path,
    *,
    title: str = "Sectional Report",
) -> Path:
    ensure_dir(out_path.parent)
    n_files = len(rows)
    n_ok = sum(1 for r in rows if not r.get("error"))
    totals = {qk: sum((r.get("query_totals") or {}).get(qk, 0) for r in rows) for qk in QUERY_KEYS}
    sec_totals = {s: sum((r.get("section_counts") or {}).get(s, 0) for r in rows) for s in SECTIONS}

    # Aggregate hits per section/query for the tab panels
    agg: dict[str, dict[str, list[dict]]] = {
        s: {qk: [] for qk in QUERY_KEYS} for s in SECTIONS
    }
    agg_counts: dict[str, dict[str, int]] = {
        s: {qk: 0 for qk in QUERY_KEYS} for s in SECTIONS
    }
    for r in rows:
        per = r.get("per_section") or {}
        for s in SECTIONS:
            for qk in QUERY_KEYS:
                bucket = (per.get(s) or {}).get(qk) or {}
                agg_counts[s][qk] += int(bucket.get("count") or 0)
                for hit in (bucket.get("hits") or [])[:SAMPLE_LIMIT]:
                    if len(agg[s][qk]) < SAMPLE_LIMIT * 3:
                        agg[s][qk].append(
                            {
                                "docid": r.get("docid", ""),
                                "tag": hit.get("tag", ""),
                                "text": hit.get("text", ""),
                            }
                        )

    tab_buttons = "".join(
        f'<button class="tab-btn{" active" if i == 0 else ""}" data-tab="{s}">{s}'
        f' <span class="badge">{sec_totals[s]}</span></button>'
        for i, s in enumerate(SECTIONS)
    )

    panels = []
    for i, s in enumerate(SECTIONS):
        subsections = []
        for qk in QUERY_KEYS:
            count = agg_counts[s][qk]
            samples = agg[s][qk]
            sample_rows = "".join(
                f"<tr><td>{_esc(h['docid'])}</td><td>{_esc(h['tag'])}</td>"
                f"<td>{_esc(h['text'])}</td></tr>"
                for h in samples
            ) or "<tr><td colspan='3'><em>No hits</em></td></tr>"
            subsections.append(
                f"""
                <div class="sub">
                  <h3>{_esc(qk)} <span class="badge">{count}</span></h3>
                  <table>
                    <thead><tr><th>Docid</th><th>Tag</th><th>Text sample</th></tr></thead>
                    <tbody>{sample_rows}</tbody>
                  </table>
                </div>"""
            )
        panels.append(
            f'<div class="tab-panel{" active" if i == 0 else ""}" id="panel-{s}">'
            + "".join(subsections)
            + "</div>"
        )

    file_rows = "".join(
        f"<tr>"
        f"<td>{_esc(r.get('docid',''))}</td>"
        f"<td>{_esc(r.get('file_id',''))}</td>"
        f"<td>{(r.get('section_counts') or {}).get('FRONT',0)}</td>"
        f"<td>{(r.get('section_counts') or {}).get('BODY',0)}</td>"
        f"<td>{(r.get('section_counts') or {}).get('REF',0)}</td>"
        f"<td>{(r.get('section_counts') or {}).get('OTHER',0)}</td>"
        f"<td>{(r.get('query_totals') or {}).get('doi_id',0)}</td>"
        f"<td>{(r.get('query_totals') or {}).get('extlink_doi',0)}</td>"
        f"<td>{(r.get('query_totals') or {}).get('extlink_uri',0)}</td>"
        f"<td>{(r.get('query_totals') or {}).get('uri',0)}</td>"
        f"<td class='err'>{_esc(r.get('error') or '')}</td>"
        f"</tr>"
        for r in rows
    )

    kpi = "".join(
        f'<div class="kpi"><div class="kpi-n">{totals[qk]}</div><div class="kpi-l">{qk}</div></div>'
        for qk in QUERY_KEYS
    )

    page = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<title>{_esc(title)} v{REPORT_VERSION}</title>
<style>
body {{ font-family: Segoe UI, system-ui, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:24px; }}
h1 {{ color:#a5b4fc; margin:0 0 8px; }}
.meta {{ color:#94a3b8; margin-bottom:20px; }}
.kpis {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:20px; }}
.kpi {{ background:#1e293b; border-radius:10px; padding:14px 18px; min-width:110px; }}
.kpi-n {{ font-size:22px; font-weight:700; color:#34d399; }}
.kpi-l {{ font-size:12px; color:#94a3b8; }}
.tabs {{ display:flex; gap:6px; margin-bottom:12px; flex-wrap:wrap; }}
.tab-btn {{ background:#334155; color:#e2e8f0; border:0; border-radius:8px 8px 0 0; padding:10px 16px; cursor:pointer; font-weight:600; }}
.tab-btn.active {{ background:#4f46e5; }}
.badge {{ background:#0f172a; color:#a5b4fc; border-radius:999px; padding:1px 8px; font-size:11px; margin-left:6px; }}
.tab-panel {{ display:none; background:#1e293b; border-radius:0 10px 10px 10px; padding:16px; }}
.tab-panel.active {{ display:block; }}
.sub {{ margin-bottom:18px; }}
.sub h3 {{ margin:0 0 8px; color:#c7d2fe; font-size:14px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th, td {{ border-bottom:1px solid #334155; padding:6px 8px; text-align:left; vertical-align:top; }}
th {{ color:#94a3b8; font-weight:600; }}
.err {{ color:#f87171; }}
.summary {{ margin-top:28px; }}
</style>
</head><body>
<h1>{_esc(title)}</h1>
<div class="meta">REPORT_VERSION={REPORT_VERSION} · files={n_files} (ok={n_ok}) · generated {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
<div class="kpis">{kpi}
  <div class="kpi"><div class="kpi-n">{n_files}</div><div class="kpi-l">files</div></div>
</div>
<div class="tabs">{tab_buttons}</div>
{"".join(panels)}
<div class="summary">
  <h2>Per-file summary</h2>
  <table>
    <thead><tr>
      <th>Docid</th><th>File_id</th><th>FRONT</th><th>BODY</th><th>REF</th><th>OTHER</th>
      <th>doi_id</th><th>extlink_doi</th><th>extlink_uri</th><th>uri</th><th>Error</th>
    </tr></thead>
    <tbody>{file_rows}</tbody>
  </table>
</div>
<script>
document.querySelectorAll('.tab-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
  }});
}});
</script>
</body></html>
"""
    out_path.write_text(page, encoding="utf-8")
    return out_path


def _merge_client_unique(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Per client: merge unique keys by (section, tag, type_attr, type_value)."""
    by_client: dict[str, dict[tuple, dict[str, Any]]] = defaultdict(dict)
    for r in rows:
        client = r.get("client") or "unknown"
        docid = r.get("docid") or ""
        shortcode = r.get("shortcode") or ""
        for u in r.get("unique") or []:
            key = (u["section"], u["tag"], u["type_attr"], u["type_value"])
            entry = by_client[client].setdefault(
                key,
                {
                    "section": u["section"],
                    "tag": u["tag"],
                    "type_attr": u["type_attr"],
                    "type_value": u["type_value"],
                    "count": 0,
                    "sample_docids": [],
                    "shortcodes": set(),
                    "sample_texts": [],
                },
            )
            entry["count"] += int(u.get("count") or 0)
            if docid and docid not in entry["sample_docids"] and len(entry["sample_docids"]) < 20:
                entry["sample_docids"].append(docid)
            if shortcode:
                entry["shortcodes"].add(shortcode)
            for t in u.get("sample_texts") or []:
                if t not in entry["sample_texts"] and len(entry["sample_texts"]) < SAMPLE_LIMIT:
                    entry["sample_texts"].append(t)

    out: dict[str, list[dict[str, Any]]] = {}
    for client, keyed in by_client.items():
        items = []
        for entry in keyed.values():
            items.append(
                {
                    **{k: entry[k] for k in ("section", "tag", "type_attr", "type_value", "count", "sample_docids", "sample_texts")},
                    "shortcodes": sorted(entry["shortcodes"]),
                }
            )
        items.sort(key=lambda e: (e["section"], e["tag"], e["type_attr"], e["type_value"]))
        out[client] = items
    return out


def write_client_unique(
    rows: list[dict[str, Any]],
    report_dir: Path,
    *,
    basename: str = "client_unique",
) -> tuple[Path, Path]:
    merged = _merge_client_unique(rows)
    html_path = report_dir / f"{basename}.html"
    csv_path = report_dir / f"{basename}.csv"

    # CSV
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "client",
                "section",
                "tag",
                "type_attr",
                "type_value",
                "count",
                "sample_docids",
                "shortcodes",
            ]
        )
        for client, items in sorted(merged.items()):
            for e in items:
                w.writerow(
                    [
                        client,
                        e["section"],
                        e["tag"],
                        e["type_attr"],
                        e["type_value"],
                        e["count"],
                        ";".join(e["sample_docids"]),
                        ";".join(e["shortcodes"]),
                    ]
                )

    # HTML
    sections_html = []
    for client, items in sorted(merged.items()):
        rows_html = "".join(
            f"<tr>"
            f"<td>{_esc(e['section'])}</td>"
            f"<td>{_esc(e['tag'])}</td>"
            f"<td>{_esc(e['type_attr'])}</td>"
            f"<td>{_esc(e['type_value'])}</td>"
            f"<td>{e['count']}</td>"
            f"<td>{_esc(', '.join(e['sample_docids']))}</td>"
            f"<td>{_esc(', '.join(e['shortcodes']))}</td>"
            f"</tr>"
            for e in items
        ) or "<tr><td colspan='7'><em>No unique keys</em></td></tr>"
        sections_html.append(
            f"<h2>{_esc(client)}</h2>"
            f"<table><thead><tr>"
            f"<th>section</th><th>tag</th><th>type_attr</th><th>type_value</th>"
            f"<th>count</th><th>sample docids</th><th>shortcodes</th>"
            f"</tr></thead><tbody>{rows_html}</tbody></table>"
        )

    page = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<title>Client Unique — Sectional Report v{REPORT_VERSION}</title>
<style>
body {{ font-family: Segoe UI, system-ui, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:24px; }}
h1 {{ color:#a5b4fc; }} h2 {{ color:#c7d2fe; margin-top:28px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; background:#1e293b; border-radius:8px; }}
th, td {{ border-bottom:1px solid #334155; padding:6px 8px; text-align:left; }}
th {{ color:#94a3b8; }}
.meta {{ color:#94a3b8; margin-bottom:16px; }}
</style></head><body>
<h1>Client Unique</h1>
<div class="meta">Keyed by (section, tag, type_attr, type_value) — href never included · v{REPORT_VERSION}</div>
{"".join(sections_html) or "<p>No data.</p>"}
</body></html>
"""
    html_path.write_text(page, encoding="utf-8")
    return html_path, csv_path


def run_sectional_report(
    project_root: Path | str,
    shortcodes: Optional[Iterable[str]] = None,
    report_dir: Path | str | None = None,
    *,
    folder_mode: bool = False,
    log: LogFn = _noop_log,
    progress: ProgressFn = _noop_progress,
    cancel_check: CancelFn = _noop_cancel,
) -> dict[str, Any]:
    """Run extraction over a project (or folder of XMLs) and write reports.

    Returns dict with report_dir, tsv_path, html_path, client_unique_html,
    client_unique_csv, rows, n_files.
    """
    root = Path(project_root)
    out_dir = Path(report_dir) if report_dir else make_report_dir()
    ensure_dir(out_dir)

    docs = collect_docs(root, shortcodes=shortcodes, folder_mode=folder_mode)
    log(f"Sectional Report v{REPORT_VERSION}: {len(docs)} file(s) from {root}")

    rows: list[dict[str, Any]] = []
    total = len(docs)
    for i, doc in enumerate(docs, start=1):
        if cancel_check():
            log("Cancelled.")
            break
        xml_path = doc.get("xml_path")
        progress(i, total, f"{doc.get('docid', '')}")
        if not xml_path or not Path(xml_path).is_file():
            row = {
                **{k: doc.get(k, "") for k in ("docid", "file_id", "client", "shortcode")},
                "xml_path": str(xml_path) if xml_path else "",
                "section_counts": {s: 0 for s in SECTIONS},
                "per_section": {
                    s: {qk: {"count": 0, "hits": []} for qk in QUERY_KEYS} for s in SECTIONS
                },
                "query_totals": {qk: 0 for qk in QUERY_KEYS},
                "unique": [],
                "error": "xml not found",
            }
            rows.append(row)
            log(f"[MISSING] {doc.get('docid')} — xml not found")
            continue
        extracted = extract_file(xml_path)
        row = {
            **{k: doc.get(k, "") for k in ("docid", "file_id", "client", "shortcode")},
            **extracted,
        }
        rows.append(row)
        if extracted.get("error"):
            log(f"[ERROR] {doc.get('docid')} — {extracted['error']}")
        else:
            log(
                f"[OK] {doc.get('docid')} FRONT={extracted['section_counts']['FRONT']} "
                f"BODY={extracted['section_counts']['BODY']} "
                f"REF={extracted['section_counts']['REF']} "
                f"OTHER={extracted['section_counts']['OTHER']}"
            )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tsv_path = write_tsv(rows, out_dir / f"sectional_summary_{ts}_v{REPORT_VERSION}.tsv")
    html_path = write_html_report(rows, out_dir / f"sectional_report_{ts}_v{REPORT_VERSION}.html")
    cu_html, cu_csv = write_client_unique(rows, out_dir, basename=f"client_unique_{ts}_v{REPORT_VERSION}")

    log(f"Wrote TSV: {tsv_path}")
    log(f"Wrote HTML: {html_path}")
    log(f"Wrote client unique: {cu_html}")

    return {
        "report_dir": str(out_dir),
        "tsv_path": str(tsv_path),
        "html_path": str(html_path),
        "client_unique_html": str(cu_html),
        "client_unique_csv": str(cu_csv),
        "rows": rows,
        "n_files": len(rows),
        "report_version": REPORT_VERSION,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m core.sectional_report <project_or_folder> [--folder] [shortcode ...]")
        raise SystemExit(2)
    target = sys.argv[1]
    folder = "--folder" in sys.argv
    scs = [a for a in sys.argv[2:] if a != "--folder"]
    result = run_sectional_report(
        target,
        shortcodes=scs or None,
        folder_mode=folder,
        log=print,
    )
    print(json.dumps({k: result[k] for k in ("report_dir", "tsv_path", "html_path", "n_files")}, indent=2))

"""DTD Report - extract DOCTYPE declarations from XML and roll up by DTD basename.

Per file: DocType root name, SYSTEM path, DTD basename, PUBLIC (if any),
Client + File_id/Docid from meta.json (same project/folder scan as sectional).

Uniqueness key: DTD basename (full SYSTEM retained in detail reports).

Outputs under Documents/impact-support-log/{timestamp}_dtd_reports/:
  - summary TSV + HTML
  - client unique (unique DTD basename per client) HTML + CSV
  - mail-sized unique digest (HTML + TXT) optional rollup

REPORT_VERSION is bumped on every behaviour change that affects outputs.
"""
from __future__ import annotations

import csv
import html
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

REPORT_VERSION = 1
REPORT_DIR = "dtd_reports"
SUPPORT_LOG_NAME = "impact-support-log"
REPORT_ROOT: Path | None = None

TSV_HEADERS = [
    "Client",
    "File_id_Docid",
    "DocType",
    "PUBLIC",
    "SYSTEM",
    "DTD_basename",
    "Shortcode",
]

CLIENT_UNIQUE_HEADERS = [
    "client",
    "DTD_basename",
    "DocType",
    "file_count",
    "SYSTEM_paths",
    "PUBLIC_ids",
    "sample_docids",
    "sample_file_ids",
    "shortcodes",
]

UNIQUE_DIGEST_HEADERS = [
    "#",
    "DTD_basename",
    "DocType",
    "clients",
    "file_count",
    "sample_SYSTEM",
    "example_file_ids",
]

SAMPLE_LIMIT = 8
_HEAD_BYTES = 32768

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


def _combined_id_text(file_id: str, docid: str) -> str:
    file_id = file_id or ""
    docid = docid or ""
    if file_id and docid:
        return f"{file_id}\n{docid}"
    return file_id or docid


def _combined_id_cell(file_id: str, docid: str) -> str:
    file_id = file_id or ""
    docid = docid or ""
    if file_id and docid:
        return f"{_esc(file_id)}<br/><span class='muted'>{_esc(docid)}</span>"
    return _esc(file_id or docid)


# PUBLIC then SYSTEM, or SYSTEM alone; optional internal subset.
_DOCTYPE_RE = re.compile(
    r"<!DOCTYPE\s+(?P<root>[\w:.-]+)"
    r"(?:"
    r"\s+PUBLIC\s+(?P<pq>[\"'])(?P<public>.*?)(?P=pq)"
    r"\s+(?P<sq1>[\"'])(?P<sys_pub>.*?)(?P=sq1)"
    r"|"
    r"\s+SYSTEM\s+(?P<sq2>[\"'])(?P<sys>.*?)(?P=sq2)"
    r")?"
    r"(?:\s*\[[^\]]*\])?"
    r"\s*>",
    re.IGNORECASE | re.DOTALL,
)


def dtd_basename(system: str) -> str:
    """Basename of a SYSTEM path (handles //host/... and backslashes)."""
    if not system:
        return ""
    s = str(system).strip().replace("\\", "/")
    return s.rsplit("/", 1)[-1] if s else ""


def parse_doctype_text(text: str) -> dict[str, str]:
    """Parse a DOCTYPE declaration from XML/text. Missing fields are empty strings."""
    empty = {
        "doctype_root": "",
        "public_id": "",
        "system_id": "",
        "dtd_basename": "",
        "raw_doctype": "",
    }
    if not text:
        return dict(empty)
    m = _DOCTYPE_RE.search(text)
    if not m:
        return dict(empty)
    root = m.group("root") or ""
    public_id = m.group("public") or ""
    system_id = (m.group("sys_pub") or m.group("sys") or "") or ""
    raw = m.group(0) or ""
    # Collapse internal whitespace in raw for display
    raw_one = re.sub(r"\s+", " ", raw).strip()
    return {
        "doctype_root": root,
        "public_id": public_id,
        "system_id": system_id,
        "dtd_basename": dtd_basename(system_id),
        "raw_doctype": raw_one,
    }


def _read_xml_head(xml_path: Path, nbytes: int = _HEAD_BYTES) -> str:
    raw = xml_path.read_bytes()[:nbytes]
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _doctype_via_lxml(xml_path: Path) -> dict[str, str] | None:
    """Fallback via lxml docinfo when regex misses (unusual encodings / layout).

    Only returns a hit when docinfo.doctype is present. root_name alone is the
    document element and must not be treated as a DOCTYPE declaration.
    """
    try:
        from lxml import etree
    except ImportError:
        return None
    try:
        parser = etree.XMLParser(recover=True, resolve_entities=False, huge_tree=True)
        tree = etree.parse(str(xml_path), parser)
        info = tree.docinfo
        if info is None:
            return None
        raw = (info.doctype or "").strip()
        if not raw:
            return None
        # Prefer re-parse of the doctype string so PUBLIC/SYSTEM split matches regex path.
        parsed = parse_doctype_text(raw)
        if parsed.get("doctype_root") or parsed.get("system_id"):
            return parsed
        root_name = info.root_name or ""
        public_id = info.public_id or ""
        system_id = info.system_url or ""
        return {
            "doctype_root": root_name or "",
            "public_id": public_id or "",
            "system_id": system_id or "",
            "dtd_basename": dtd_basename(system_id or ""),
            "raw_doctype": raw,
        }
    except Exception:
        return None



def extract_file(xml_path: str | Path) -> dict[str, Any]:
    """Extract DOCTYPE fields from one XML file."""
    path = Path(xml_path)
    result: dict[str, Any] = {
        "xml_path": str(path),
        "doctype_root": "",
        "public_id": "",
        "system_id": "",
        "dtd_basename": "",
        "raw_doctype": "",
        "has_doctype": False,
        "error": None,
    }
    try:
        head = _read_xml_head(path)
        parsed = parse_doctype_text(head)
        if not parsed["doctype_root"] and not parsed["system_id"]:
            fallback = _doctype_via_lxml(path)
            if fallback:
                parsed = fallback
        result.update(parsed)
        result["has_doctype"] = bool(parsed.get("doctype_root") or parsed.get("system_id"))
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
    return result


def collect_docs(
    project_root: Path | str,
    shortcodes: Optional[Iterable[str]] = None,
    folder_mode: bool = False,
) -> list[dict[str, Any]]:
    """Delegate to sectional collect_docs (project meta + folder scan)."""
    from core.sectional_report import collect_docs as _sr_collect

    return _sr_collect(project_root, shortcodes=shortcodes, folder_mode=folder_mode)


def write_tsv(rows: list[dict[str, Any]], out_path: Path) -> Path:
    ensure_dir(out_path.parent)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(TSV_HEADERS)
        for r in rows:
            writer.writerow(
                [
                    r.get("client", ""),
                    _combined_id_text(r.get("file_id", "") or "", r.get("docid", "") or ""),
                    r.get("doctype_root", ""),
                    r.get("public_id", ""),
                    r.get("system_id", ""),
                    r.get("dtd_basename", ""),
                    r.get("shortcode", ""),
                ]
            )
    return out_path


def _merge_client_unique(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Per client: unique by DTD basename; retain full SYSTEM / PUBLIC sets."""
    by_client: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for r in rows:
        client = r.get("client") or "unknown"
        basename = (r.get("dtd_basename") or "").strip()
        if not basename and not r.get("doctype_root"):
            basename = "(no DOCTYPE)"
        elif not basename:
            basename = "(no SYSTEM)"
        entry = by_client[client].setdefault(
            basename,
            {
                "dtd_basename": basename,
                "doctype_roots": set(),
                "system_ids": set(),
                "public_ids": set(),
                "file_count": 0,
                "sample_docids": [],
                "sample_file_ids": [],
                "shortcodes": set(),
            },
        )
        entry["file_count"] += 1
        if r.get("doctype_root"):
            entry["doctype_roots"].add(r["doctype_root"])
        if r.get("system_id"):
            entry["system_ids"].add(r["system_id"])
        if r.get("public_id"):
            entry["public_ids"].add(r["public_id"])
        docid = r.get("docid") or ""
        file_id = r.get("file_id") or ""
        shortcode = r.get("shortcode") or ""
        if docid and docid not in entry["sample_docids"] and len(entry["sample_docids"]) < 20:
            entry["sample_docids"].append(docid)
        if file_id and file_id not in entry["sample_file_ids"] and len(entry["sample_file_ids"]) < 20:
            entry["sample_file_ids"].append(file_id)
        if shortcode:
            entry["shortcodes"].add(shortcode)

    out: dict[str, list[dict[str, Any]]] = {}
    for client, keyed in by_client.items():
        items = []
        for entry in keyed.values():
            roots = sorted(entry["doctype_roots"])
            items.append(
                {
                    "dtd_basename": entry["dtd_basename"],
                    "doctype_root": ", ".join(roots),
                    "file_count": entry["file_count"],
                    "system_ids": sorted(entry["system_ids"]),
                    "public_ids": sorted(entry["public_ids"]),
                    "sample_docids": entry["sample_docids"],
                    "sample_file_ids": entry["sample_file_ids"],
                    "shortcodes": sorted(entry["shortcodes"]),
                }
            )
        items.sort(key=lambda e: (e["dtd_basename"].lower(), e["doctype_root"]))
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

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(CLIENT_UNIQUE_HEADERS)
        for client, items in sorted(merged.items()):
            for e in items:
                w.writerow(
                    [
                        client,
                        e["dtd_basename"],
                        e["doctype_root"],
                        e["file_count"],
                        " | ".join(e["system_ids"]),
                        " | ".join(e["public_ids"]),
                        ";".join(e["sample_docids"]),
                        ";".join(e["sample_file_ids"]),
                        ";".join(e["shortcodes"]),
                    ]
                )

    sections_html: list[str] = []
    for client, items in sorted(merged.items()):
        rows_html = "".join(
            f"<tr>"
            f"<td><code>{_esc(e['dtd_basename'])}</code></td>"
            f"<td>{_esc(e['doctype_root'])}</td>"
            f"<td>{e['file_count']}</td>"
            f"<td class='sys'>{'<br/>'.join(_esc(s) for s in e['system_ids']) or '<em>-</em>'}</td>"
            f"<td class='pub'>{'<br/>'.join(_esc(p) for p in e['public_ids']) or '<em>-</em>'}</td>"
            f"<td>{_esc(', '.join(e['sample_file_ids'][:SAMPLE_LIMIT]))}</td>"
            f"<td>{_esc(', '.join(e['sample_docids'][:SAMPLE_LIMIT]))}</td>"
            f"<td>{_esc(', '.join(e['shortcodes']))}</td>"
            f"</tr>"
            for e in items
        ) or "<tr><td colspan='8'><em>No DTDs</em></td></tr>"
        sections_html.append(
            f'<div class="client-block" data-client="{_esc(client)}">'
            f"<h2>{_esc(client)} <span class='badge'>{len(items)} unique DTD(s)</span></h2>"
            f"<table><thead><tr>"
            f"<th>DTD basename</th><th>DocType</th><th>files</th>"
            f"<th>SYSTEM path(s)</th><th>PUBLIC</th>"
            f"<th>sample file-ids</th><th>sample docids</th><th>shortcodes</th>"
            f"</tr></thead><tbody>{rows_html}</tbody></table></div>"
        )

    client_options = "".join(
        f'<option value="{_esc(c)}">{_esc(c)}</option>' for c in sorted(merged.keys())
    )
    n_clients = len(merged)
    n_unique = sum(len(v) for v in merged.values())
    css = (
        "body{font-family:Segoe UI,system-ui,sans-serif;background:#0f172a;color:#e2e8f0;"
        "margin:0;padding:24px}"
        "h1{color:#a5b4fc}h2{color:#c7d2fe;margin-top:28px}"
        "table{width:100%;border-collapse:collapse;font-size:13px;background:#1e293b;border-radius:8px}"
        "th,td{border-bottom:1px solid #334155;padding:6px 8px;text-align:left;vertical-align:top}"
        "th{color:#94a3b8}.meta{color:#94a3b8;margin-bottom:16px}"
        "code{background:#334155;padding:1px 5px;border-radius:4px;font-size:12px;word-break:break-all}"
        ".sys,.pub{font-size:12px;word-break:break-all;color:#cbd5e1}"
        ".badge{background:#334155;color:#a5b4fc;border-radius:999px;padding:2px 8px;"
        "font-size:12px;margin-left:8px}"
        ".controls-panel{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:16px;"
        "background:#1e293b;border:1px solid #334155;border-radius:10px;padding:12px 16px}"
        ".filter-select,.search-input{background:#0f172a;color:#e2e8f0;border:1px solid #334155;"
        "border-radius:8px;padding:8px 10px}.search-input{min-width:220px;flex:1}"
        ".kpi-row{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}"
        ".kpi{background:#1e293b;border-radius:10px;padding:14px 18px;min-width:110px;"
        "border-left:4px solid #6366f1}.kpi-n{font-size:22px;font-weight:700;color:#34d399}"
        ".kpi-l{font-size:12px;color:#94a3b8}"
    )
    page = "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="en"><head><meta charset="utf-8"/>',
            f"<title>Client Unique DTD - v{REPORT_VERSION}</title>",
            f"<style>{css}</style></head><body>",
            "<h1>Client Unique - DTD Report</h1>",
            f'<div class="meta">Unique key = DTD basename '
            f"(full SYSTEM listed in detail) - v{REPORT_VERSION}</div>",
            '<div class="kpi-row">',
            f'<div class="kpi"><div class="kpi-n">{n_clients}</div>'
            '<div class="kpi-l">clients</div></div>',
            f'<div class="kpi"><div class="kpi-n">{n_unique}</div>'
            '<div class="kpi-l">client x DTD rows</div></div>',
            "</div>",
            '<div class="controls-panel">',
            '<input id="searchInput" class="search-input" '
            'placeholder="Search client, DTD, SYSTEM..." oninput="applyFilters()"/>',
            '<select id="filterClient" class="filter-select" onchange="applyFilters()">',
            '<option value="">All clients</option>',
            client_options,
            "</select></div>",
            "".join(sections_html) or "<p>No data.</p>",
            "<script>",
            "function applyFilters(){",
            "  const q=(document.getElementById('searchInput').value||'').toLowerCase().trim();",
            "  const client=document.getElementById('filterClient').value;",
            "  document.querySelectorAll('.client-block').forEach(block=>{",
            "    if(client && block.getAttribute('data-client')!==client){",
            "      block.style.display='none'; return;}",
            "    const hay=(block.textContent||'').toLowerCase();",
            "    block.style.display=(!q||hay.includes(q))?'block':'none';",
            "  });",
            "}",
            "</script></body></html>",
        ]
    )
    html_path.write_text(page, encoding="utf-8")
    return html_path, csv_path


def compute_unique_digest(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Global unique by DTD basename (mail-sized digest)."""
    keyed: dict[str, dict[str, Any]] = {}
    for r in rows:
        basename = (r.get("dtd_basename") or "").strip()
        if not basename and not r.get("doctype_root"):
            basename = "(no DOCTYPE)"
        elif not basename:
            basename = "(no SYSTEM)"
        entry = keyed.setdefault(
            basename,
            {
                "dtd_basename": basename,
                "doctype_roots": set(),
                "clients": set(),
                "system_ids": set(),
                "file_count": 0,
                "sample_file_ids": [],
            },
        )
        entry["file_count"] += 1
        if r.get("doctype_root"):
            entry["doctype_roots"].add(r["doctype_root"])
        client = r.get("client") or ""
        if client:
            entry["clients"].add(client)
        if r.get("system_id"):
            entry["system_ids"].add(r["system_id"])
        fid = r.get("file_id") or r.get("docid") or ""
        if fid and fid not in entry["sample_file_ids"] and len(entry["sample_file_ids"]) < 3:
            entry["sample_file_ids"].append(fid)

    findings = []
    for i, basename in enumerate(sorted(keyed.keys(), key=str.lower), start=1):
        e = keyed[basename]
        systems = sorted(e["system_ids"])
        findings.append(
            {
                "num": i,
                "dtd_basename": e["dtd_basename"],
                "doctype_root": ", ".join(sorted(e["doctype_roots"])),
                "clients": sorted(e["clients"], key=str.lower),
                "file_count": e["file_count"],
                "sample_system": systems[0] if systems else "",
                "system_count": len(systems),
                "example_file_ids": e["sample_file_ids"],
            }
        )
    return findings


def format_unique_digest_mail_body(
    findings: list[dict[str, Any]],
    *,
    generated: str | None = None,
) -> str:
    when = generated or datetime.now().strftime("%Y-%m-%d %H:%M")
    clients = sorted(
        {c for f in findings for c in (f.get("clients") or [])},
        key=str.lower,
    )
    lines = [
        f"DTD Report - Unique Digest v{REPORT_VERSION}",
        f"Generated: {when}",
        (
            f"Unique DTD basenames: {len(findings)}  |  "
            f"Files covered: {sum(int(f['file_count']) for f in findings)}  |  "
            f"Clients: {len(clients)}"
        ),
        "Unique key = DTD basename (full SYSTEM in detail / client unique reports).",
        "",
        "\t".join(UNIQUE_DIGEST_HEADERS),
    ]
    if not findings:
        lines.append("(no DOCTYPE / DTD found)")
    for f in findings:
        sample = f.get("sample_system") or ""
        if int(f.get("system_count") or 0) > 1:
            sample = f"{sample} (+{int(f['system_count']) - 1} more)"
        lines.append(
            "\t".join(
                [
                    str(f["num"]),
                    str(f["dtd_basename"]),
                    str(f["doctype_root"]),
                    ", ".join(f.get("clients") or []),
                    str(f["file_count"]),
                    sample,
                    ", ".join(f.get("example_file_ids") or []),
                ]
            )
        )
    lines.append("")
    lines.append("Full summary / client unique reports remain on disk.")
    return "\n".join(lines) + "\n"


def write_unique_digest(
    rows: list[dict[str, Any]],
    report_dir: Path,
    *,
    basename: str = "unique_digest",
) -> tuple[Path, Path]:
    """Mail-sized unique DTD digest: HTML + plain-text body."""
    ensure_dir(report_dir)
    findings = compute_unique_digest(rows)
    html_path = report_dir / f"{basename}.html"
    txt_path = report_dir / f"{basename}.txt"
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    mail_body = format_unique_digest_mail_body(findings, generated=generated)
    txt_path.write_text(mail_body, encoding="utf-8")

    table_rows = "".join(
        (
            f"<tr>"
            f"<td>{int(f['num'])}</td>"
            f"<td><code>{_esc(f['dtd_basename'])}</code></td>"
            f"<td>{_esc(f['doctype_root'])}</td>"
            f"<td>{_esc(', '.join(f.get('clients') or []))}</td>"
            f"<td>{int(f['file_count'])}</td>"
            f"<td class='sys'>{_esc(f.get('sample_system') or '')}</td>"
            f"<td>{_esc(', '.join(f.get('example_file_ids') or []))}</td>"
            f"</tr>"
        )
        for f in findings
    ) or f"<tr><td colspan='{len(UNIQUE_DIGEST_HEADERS)}'><em>No DTDs.</em></td></tr>"
    headers = "".join(f"<th>{_esc(h)}</th>" for h in UNIQUE_DIGEST_HEADERS)
    css = (
        "body{font-family:Segoe UI,system-ui,sans-serif;background:#0f172a;color:#e2e8f0;"
        "margin:0;padding:24px}"
        "h1,h2{color:#a5b4fc}.meta,.note{color:#94a3b8;margin-bottom:12px}"
        ".kpi-row{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0 18px}"
        ".kpi{background:#1e293b;border-radius:10px;padding:14px 18px;min-width:110px;"
        "border-left:4px solid #6366f1}.kpi-n{font-size:22px;font-weight:700;color:#34d399}"
        ".kpi-l{font-size:12px;color:#94a3b8}"
        "table{width:100%;border-collapse:collapse;font-size:13px;background:#1e293b;"
        "border-radius:8px;overflow:hidden}"
        "th,td{border-bottom:1px solid #334155;padding:8px 10px;text-align:left;vertical-align:top}"
        "th{color:#94a3b8;font-weight:600}"
        "code{background:#334155;padding:1px 5px;border-radius:4px;font-size:12px;word-break:break-all}"
        ".sys{font-size:12px;word-break:break-all}"
        "pre.mail-body{background:#0f172a;border:1px solid #334155;border-radius:8px;"
        "padding:14px;white-space:pre-wrap;font-size:12px;color:#cbd5e1;margin-top:18px}"
    )
    page = "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="en"><head><meta charset="utf-8"/>',
            f"<title>DTD Unique Digest v{REPORT_VERSION}</title>",
            f"<style>{css}</style></head><body>",
            "<h1>DTD Unique Digest</h1>",
            f'<div class="meta">REPORT_VERSION={REPORT_VERSION} - mail-sized - '
            "full summary / client unique on disk</div>",
            '<p class="note">Unique key = DTD basename.</p>',
            '<div class="kpi-row">',
            f'<div class="kpi"><div class="kpi-n">{len(findings)}</div>'
            '<div class="kpi-l">unique DTDs</div></div>',
            f'<div class="kpi"><div class="kpi-n">'
            f'{sum(int(f["file_count"]) for f in findings)}</div>'
            '<div class="kpi-l">files</div></div>',
            "</div>",
            f'<table><thead><tr>{headers}</tr></thead><tbody>{table_rows}</tbody></table>',
            "<h2>Plain-text body (paste into mail)</h2>",
            f'<pre class="mail-body">{_esc(mail_body)}</pre>',
            "</body></html>",
        ]
    )
    html_path.write_text(page, encoding="utf-8")
    return html_path, txt_path


def write_html_report(
    rows: list[dict[str, Any]],
    out_path: Path,
    *,
    title: str = "DTD Report",
) -> Path:
    ensure_dir(out_path.parent)
    n_files = len(rows)
    n_ok = sum(1 for r in rows if not r.get("error"))
    n_with = sum(1 for r in rows if r.get("has_doctype"))
    unique_basenames = sorted(
        {
            (r.get("dtd_basename") or "").strip() or (
                "(no DOCTYPE)" if not r.get("doctype_root") else "(no SYSTEM)"
            )
            for r in rows
        },
        key=str.lower,
    )
    clients = sorted({(r.get("client") or "unknown") for r in rows}, key=str.lower)

    body_rows = "".join(
        (
            "<tr"
            f' data-client="{_esc(r.get("client") or "")}"'
            f' data-dtd="{_esc(r.get("dtd_basename") or "")}">'
            f'<td>{_esc(r.get("client") or "")}</td>'
            f'<td>{_combined_id_cell(r.get("file_id") or "", r.get("docid") or "")}</td>'
            f'<td>{_esc(r.get("doctype_root") or "")}</td>'
            f'<td class="pub">{_esc(r.get("public_id") or "") or "<em>-</em>"}</td>'
            f'<td class="sys">{_esc(r.get("system_id") or "") or "<em>-</em>"}</td>'
            f'<td><code>{_esc(r.get("dtd_basename") or "")}</code></td>'
            f'<td>{_esc(r.get("shortcode") or "")}</td>'
            f'<td class="err">{_esc(r.get("error") or "")}</td>'
            "</tr>"
        )
        for r in rows
    ) or "<tr><td colspan='8'><em>No files</em></td></tr>"

    client_options = "".join(
        f'<option value="{_esc(c)}">{_esc(c)}</option>' for c in clients
    )
    dtd_options = "".join(
        f'<option value="{_esc(d)}">{_esc(d)}</option>' for d in unique_basenames
    )
    css = (
        "body{font-family:Segoe UI,system-ui,sans-serif;background:#0f172a;color:#e2e8f0;"
        "margin:0;padding:24px}"
        "h1{color:#a5b4fc}.meta{color:#94a3b8;margin-bottom:12px}"
        ".kpi-row{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0 18px}"
        ".kpi{background:#1e293b;border-radius:10px;padding:14px 18px;min-width:110px;"
        "border-left:4px solid #6366f1}.kpi-n{font-size:22px;font-weight:700;color:#34d399}"
        ".kpi-l{font-size:12px;color:#94a3b8}"
        "table{width:100%;border-collapse:collapse;font-size:13px;background:#1e293b;"
        "border-radius:8px;overflow:hidden}"
        "th,td{border-bottom:1px solid #334155;padding:8px 10px;text-align:left;vertical-align:top}"
        "th{color:#94a3b8}.muted{color:#64748b;font-size:12px}"
        "code{background:#334155;padding:1px 5px;border-radius:4px;font-size:12px;word-break:break-all}"
        ".sys,.pub{font-size:12px;word-break:break-all}.err{color:#f87171;font-size:12px}"
        ".controls-panel{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:16px;"
        "background:#1e293b;border:1px solid #334155;border-radius:10px;padding:12px 16px}"
        ".filter-select,.search-input{background:#0f172a;color:#e2e8f0;border:1px solid #334155;"
        "border-radius:8px;padding:8px 10px}.search-input{min-width:220px;flex:1}"
    )
    page = "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="en"><head><meta charset="utf-8"/>',
            f"<title>{_esc(title)} v{REPORT_VERSION}</title>",
            f"<style>{css}</style></head><body>",
            f"<h1>{_esc(title)}</h1>",
            f'<div class="meta">REPORT_VERSION={REPORT_VERSION} - '
            "DOCTYPE root / SYSTEM / DTD basename / PUBLIC + meta identity</div>",
            '<div class="kpi-row">',
            f'<div class="kpi"><div class="kpi-n">{n_files}</div><div class="kpi-l">files</div></div>',
            f'<div class="kpi"><div class="kpi-n">{n_with}</div><div class="kpi-l">with DOCTYPE</div></div>',
            f'<div class="kpi"><div class="kpi-n">{n_ok}</div><div class="kpi-l">ok</div></div>',
            f'<div class="kpi"><div class="kpi-n">{len(unique_basenames)}</div>'
            '<div class="kpi-l">unique DTD basenames</div></div>',
            f'<div class="kpi"><div class="kpi-n">{len(clients)}</div><div class="kpi-l">clients</div></div>',
            "</div>",
            '<div class="controls-panel">',
            '<input id="searchInput" class="search-input" '
            'placeholder="Search..." oninput="applyFilters()"/>',
            '<select id="filterClient" class="filter-select" onchange="applyFilters()">',
            '<option value="">All clients</option>',
            client_options,
            "</select>",
            '<select id="filterDtd" class="filter-select" onchange="applyFilters()">',
            '<option value="">All DTD basenames</option>',
            dtd_options,
            "</select></div>",
            "<table><thead><tr>",
            "<th>Client</th><th>File-id / Docid</th><th>DocType</th>"
            "<th>PUBLIC</th><th>SYSTEM</th><th>DTD basename</th>"
            "<th>Shortcode</th><th>Error</th>",
            "</tr></thead><tbody id='mainBody'>",
            body_rows,
            "</tbody></table>",
            "<script>",
            "function applyFilters(){",
            "  const q=(document.getElementById('searchInput').value||'').toLowerCase().trim();",
            "  const client=document.getElementById('filterClient').value;",
            "  const dtd=document.getElementById('filterDtd').value;",
            "  document.querySelectorAll('#mainBody tr').forEach(tr=>{",
            "    if(client && tr.getAttribute('data-client')!==client){",
            "      tr.style.display='none'; return;}",
            "    if(dtd && tr.getAttribute('data-dtd')!==dtd){",
            "      tr.style.display='none'; return;}",
            "    const hay=(tr.textContent||'').toLowerCase();",
            "    tr.style.display=(!q||hay.includes(q))?'':'none';",
            "  });",
            "}",
            "</script></body></html>",
        ]
    )
    out_path.write_text(page, encoding="utf-8")
    return out_path


def run_dtd_report(
    project_root: Path | str,
    shortcodes: Optional[Iterable[str]] = None,
    report_dir: Path | str | None = None,
    *,
    folder_mode: bool = False,
    log: LogFn = _noop_log,
    progress: ProgressFn = _noop_progress,
    cancel_check: CancelFn = _noop_cancel,
) -> dict[str, Any]:
    """Run DOCTYPE extraction over a project (or folder of XMLs) and write reports."""
    root = Path(project_root)
    out_dir = Path(report_dir) if report_dir else make_report_dir()
    ensure_dir(out_dir)

    docs = collect_docs(root, shortcodes=shortcodes, folder_mode=folder_mode)
    log(f"DTD Report v{REPORT_VERSION}: {len(docs)} file(s) from {root}")

    rows: list[dict[str, Any]] = []
    total = len(docs)
    for i, doc in enumerate(docs, start=1):
        if cancel_check():
            log("Cancelled.")
            break
        xml_path = doc.get("xml_path")
        progress(i, total, f"{doc.get('docid', '')}")
        identity = {
            k: doc.get(k, "") for k in ("docid", "file_id", "client", "shortcode", "doc_type")
        }
        if not xml_path or not Path(xml_path).is_file():
            row = {
                **identity,
                "xml_path": str(xml_path) if xml_path else "",
                "doctype_root": "",
                "public_id": "",
                "system_id": "",
                "dtd_basename": "",
                "raw_doctype": "",
                "has_doctype": False,
                "error": "xml not found",
            }
            rows.append(row)
            log(f"[MISSING] {doc.get('docid')} - xml not found")
            continue
        extracted = extract_file(xml_path)
        row = {**identity, **extracted}
        rows.append(row)
        if extracted.get("error"):
            log(f"[ERROR] {doc.get('docid')} - {extracted['error']}")
        elif not extracted.get("has_doctype"):
            log(f"[NO-DTD] {doc.get('docid')}")
        else:
            log(
                f"[OK] {doc.get('docid')} "
                f"DocType={extracted.get('doctype_root')} "
                f"DTD={extracted.get('dtd_basename')}"
            )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tsv_path = write_tsv(rows, out_dir / f"dtd_summary_{ts}_v{REPORT_VERSION}.tsv")
    html_path = write_html_report(rows, out_dir / f"dtd_report_{ts}_v{REPORT_VERSION}.html")
    cu_html, cu_csv = write_client_unique(
        rows, out_dir, basename=f"client_unique_{ts}_v{REPORT_VERSION}"
    )
    digest_html, digest_txt = write_unique_digest(
        rows, out_dir, basename=f"unique_digest_{ts}_v{REPORT_VERSION}"
    )

    log(f"Wrote TSV: {tsv_path}")
    log(f"Wrote HTML: {html_path}")
    log(f"Wrote client unique: {cu_html}")
    log(f"Wrote unique digest: {digest_html}")

    return {
        "report_dir": str(out_dir),
        "tsv_path": str(tsv_path),
        "html_path": str(html_path),
        "client_unique_html": str(cu_html),
        "client_unique_csv": str(cu_csv),
        "unique_digest_html": str(digest_html),
        "unique_digest_txt": str(digest_txt),
        "rows": rows,
        "n_files": len(rows),
        "report_version": REPORT_VERSION,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m core.dtd_report <project_or_folder> [--folder] [shortcode ...]")
        raise SystemExit(2)
    target = sys.argv[1]
    folder = "--folder" in sys.argv
    scs = [a for a in sys.argv[2:] if a != "--folder"]
    result = run_dtd_report(
        target,
        shortcodes=scs or None,
        folder_mode=folder,
        log=print,
    )
    print(
        json.dumps(
            {k: result[k] for k in ("report_dir", "tsv_path", "html_path", "n_files")},
            indent=2,
        )
    )

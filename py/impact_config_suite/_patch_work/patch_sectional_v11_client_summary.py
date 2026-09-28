# -*- coding: utf-8 -*-
"""Bump sectional report to v11: shareable client-wise scanned/issue summary + chart."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite")
SRC = ROOT / "core" / "sectional_report.py"
TEST = ROOT / "tests" / "test_sectional_report.py"

src = SRC.read_text(encoding="utf-8")

old_ver = "REPORT_VERSION = 10"
assert old_ver in src, "REPORT_VERSION = 10 not found"
src = src.replace(old_ver, "REPORT_VERSION = 11", 1)

MARKER = "def find_cross_query_inconsistencies(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:"
assert MARKER in src

HELPERS = r'''CLIENT_SUMMARY_HEADERS = [
    "Client",
    "Scanned document count",
    "Issue document count",
]


def _doc_identity(row_or_issue: dict[str, Any]) -> tuple[str, str, str]:
    """Stable identity for counting unique documents."""
    return (
        str(row_or_issue.get("file_id") or ""),
        str(row_or_issue.get("docid") or ""),
        str(row_or_issue.get("xml_path") or ""),
    )


def compute_client_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-client scanned docs vs docs with cross-query DOI inconsistencies.

    Returns list of dicts with keys:
      client, scanned_document_count, issue_document_count
    sorted by issue_document_count desc, then client name.
    """
    issues = find_cross_query_inconsistencies(rows)
    scanned: dict[str, int] = defaultdict(int)
    for row in rows:
        scanned[str(row.get("client") or "unknown")] += 1
    issue_docs: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    for issue in issues:
        client = str(issue.get("client") or "unknown")
        issue_docs[client].add(_doc_identity(issue))
    clients = sorted(set(scanned) | set(issue_docs), key=lambda c: c.lower())
    summary = [
        {
            "client": client,
            "scanned_document_count": scanned.get(client, 0),
            "issue_document_count": len(issue_docs.get(client, set())),
        }
        for client in clients
    ]
    summary.sort(key=lambda item: (-item["issue_document_count"], item["client"].lower()))
    return summary


def _client_summary_panel_html(
    summary: list[dict[str, Any]],
    *,
    title: str = "Client-wise summary",
) -> str:
    """Shareable table + bar chart: scanned docs vs issue docs per client."""
    total_scanned = sum(int(item["scanned_document_count"]) for item in summary)
    total_issues = sum(int(item["issue_document_count"]) for item in summary)
    n_clients = len(summary)
    max_scanned = max((int(item["scanned_document_count"]) for item in summary), default=1) or 1

    kpi = (
        '<div class="client-summary-kpis">'
        f'<div class="kpi"><div class="kpi-n">{n_clients}</div><div class="kpi-l">clients</div></div>'
        f'<div class="kpi"><div class="kpi-n">{total_scanned}</div><div class="kpi-l">scanned docs</div></div>'
        f'<div class="kpi warn"><div class="kpi-n">{total_issues}</div>'
        '<div class="kpi-l">issue docs</div></div>'
        "</div>"
    )

    if summary:
        bars = "".join(
            (
                f'<div class="cause-bar" style="--pct-scanned:'
                f'{round(int(item["scanned_document_count"]) / max_scanned * 100, 1)}%;'
                f'--pct-issue:'
                f'{round(int(item["issue_document_count"]) / max_scanned * 100, 1)}%">'
                f'<span class="cause-bar-label">{_esc(item["client"])}</span>'
                f'<span class="cause-bar-track">'
                f'<span class="cause-bar-fill scanned"></span>'
                f'<span class="cause-bar-fill issue"></span>'
                f"</span>"
                f'<span class="cause-bar-value">'
                f'{int(item["issue_document_count"])} issue / '
                f'{int(item["scanned_document_count"])} scanned'
                f"</span></div>"
            )
            for item in summary
        )
    else:
        bars = "<p><em>No documents scanned.</em></p>"

    chart = (
        f'<div class="cause-chart"><h3>{_esc(title)} chart</h3>'
        '<p class="cause-chart-note">Amber = issue documents; teal track fill = scanned scale. '
        "Issue document = any file with a cross-query DOI inconsistency.</p>"
        f"{bars}</div>"
    )

    table_rows = "".join(
        f'<tr><td>{_esc(item["client"])}</td>'
        f'<td>{int(item["scanned_document_count"])}</td>'
        f'<td>{int(item["issue_document_count"])}</td></tr>'
        for item in summary
    ) or "<tr><td colspan='3'><em>No clients.</em></td></tr>"

    table = (
        '<table class="client-summary-table"><thead><tr>'
        "<th>Client</th><th>Scanned document count</th><th>Issue document count</th>"
        f"</tr></thead><tbody>{table_rows}</tbody></table>"
    )

    return (
        f'<section class="client-summary-panel" aria-label="{_esc(title)}">'
        f"<h2>{_esc(title)}</h2>"
        '<p class="inconsistency-note">Shareable overview for production / XML teams: '
        "scanned documents vs documents with DOI cross-query inconsistencies.</p>"
        f"{kpi}{chart}{table}</section>"
    )


def write_client_summary(
    rows: list[dict[str, Any]],
    report_dir: Path,
    *,
    basename: str = "client_summary",
) -> tuple[Path, Path]:
    """Write shareable client-wise scanned/issue summary HTML + CSV."""
    ensure_dir(report_dir)
    summary = compute_client_summary(rows)
    html_path = report_dir / f"{basename}.html"
    csv_path = report_dir / f"{basename}.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CLIENT_SUMMARY_HEADERS)
        for item in summary:
            writer.writerow(
                [
                    item["client"],
                    item["scanned_document_count"],
                    item["issue_document_count"],
                ]
            )
    css = (
        "body{font-family:Segoe UI,system-ui,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:24px}"
        "h1,h2,h3{color:#a5b4fc}.meta,.inconsistency-note,.cause-chart-note{color:#94a3b8}"
        ".client-summary-panel{background:#1e293b;border-radius:10px;padding:16px;max-width:960px}"
        ".client-summary-kpis{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0 18px}"
        ".kpi{background:#0f172a;border-radius:10px;padding:14px 18px;min-width:110px;"
        "border-left:4px solid #6366f1}.kpi.warn{border-left-color:#f59e0b}"
        ".kpi-n{font-size:22px;font-weight:700;color:#34d399}.kpi.warn .kpi-n{color:#fbbf24}"
        ".kpi-l{font-size:12px;color:#94a3b8}"
        ".cause-chart{margin:0 0 20px}.cause-bar{display:grid;"
        "grid-template-columns:minmax(120px,180px) 1fr auto;align-items:center;gap:10px;margin:8px 0}"
        ".cause-bar-label{font-size:13px;font-weight:600}"
        ".cause-bar-track{height:18px;background:#334155;position:relative;overflow:hidden;border-radius:6px}"
        ".cause-bar-fill{display:block;height:100%;position:absolute;left:0;top:0;border-radius:6px}"
        ".cause-bar-fill.scanned{width:var(--pct-scanned);background:#0ea5e9;opacity:.35}"
        ".cause-bar-fill.issue{width:var(--pct-issue);background:#f59e0b}"
        ".cause-bar-value{font-size:12px;color:#94a3b8;white-space:nowrap}"
        "table{width:100%;border-collapse:collapse;font-size:13px;background:#0f172a}"
        "th,td{border-bottom:1px solid #334155;padding:8px 10px;text-align:left}"
        "th{color:#94a3b8;font-weight:600}"
    )
    page = "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="en"><head><meta charset="utf-8"/>',
            f"<title>Sectional Report Client Summary v{REPORT_VERSION}</title>",
            f"<style>{css}</style></head><body>",
            "<h1>Sectional Report — Client-wise summary</h1>",
            f'<div class="meta">REPORT_VERSION={REPORT_VERSION}</div>',
            _client_summary_panel_html(summary),
            "</body></html>",
        ]
    )
    html_path.write_text(page, encoding="utf-8")
    return html_path, csv_path


'''

src = src.replace(MARKER, HELPERS + MARKER, 1)

OLD_INC_FN_START = 'def _inconsistency_section_html(issues: list[dict[str, Any]], *, title: str = "Cross-query DOI inconsistencies") -> str:'
OLD_INC_FN_END = 'def write_inconsistency_report('
assert OLD_INC_FN_START in src
assert OLD_INC_FN_END in src
idx_start = src.index(OLD_INC_FN_START)
idx_end = src.index(OLD_INC_FN_END)

NEW_INC_FN = r'''def _inconsistency_section_html(
    issues: list[dict[str, Any]],
    *,
    title: str = "Cross-query DOI inconsistencies",
    rows: list[dict[str, Any]] | None = None,
    summary: list[dict[str, Any]] | None = None,
) -> str:
    """Render client summary (scanned vs issue docs) + issue-count bars + detail table."""
    if summary is None:
        if rows is not None:
            summary = compute_client_summary(rows)
        elif issues:
            issue_docs: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
            for issue in issues:
                client = str(issue.get("client") or "unknown")
                issue_docs[client].add(_doc_identity(issue))
            summary = [
                {
                    "client": client,
                    "scanned_document_count": len(docs),
                    "issue_document_count": len(docs),
                }
                for client, docs in sorted(
                    issue_docs.items(), key=lambda kv: (-len(kv[1]), kv[0].lower())
                )
            ]
        else:
            summary = []

    summary_panel = (
        _client_summary_panel_html(summary) if (summary or rows is not None) else ""
    )

    counts: dict[str, int] = defaultdict(int)
    for issue in issues:
        counts[str(issue.get("client") or "unknown")] += 1
    max_count = max(counts.values(), default=1)
    bars = "".join(
        f'<div class="client-bar"><span class="client-bar-label">{_esc(client)}</span>'
        f'<span class="client-bar-track"><span class="client-bar-fill" style="width:{round(count / max_count * 100)}%"></span></span>'
        f'<b>{count}</b></div>'
        for client, count in sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
    ) or "<p><em>No cross-query DOI overlaps found.</em></p>"
    detail_rows = "".join(
        f'<tr><td>{_esc(issue["client"])}</td>'
        f'<td>{_combined_id_cell(issue["file_id"], issue["docid"])}</td>'
        f'<td>{_esc(issue["doi"])}</td>'
        f'<td>{_esc(", ".join(issue["queries"]))}</td>'
        f'<td>{_esc(", ".join(issue["sections"]))}</td>'
        f'<td>{_esc(" | ".join((s["text"] or s["href"]) for s in issue["samples"]))}</td></tr>'
        for issue in issues
    ) or "<tr><td colspan='6'><em>No inconsistencies.</em></td></tr>"
    return (
        f"{summary_panel}"
        f'<section class="inconsistency-report"><h2>{_esc(title)} '
        f'<span class="badge">{len(issues)}</span></h2>'
        '<p class="inconsistency-note">A DOI appearing in multiple query buckets in one document is flagged as cross-bucket inconsistent.</p>'
        f'<div class="client-bars"><h3>Client-wise inconsistency count</h3>{bars}</div>'
        '<table><thead><tr><th>Client</th><th>File-id / Docid</th><th>DOI</th>'
        '<th>Queries</th><th>Sections</th><th>Samples</th></tr></thead>'
        f'<tbody>{detail_rows}</tbody></table></section>'
    )


'''

src = src[:idx_start] + NEW_INC_FN + src[idx_end:]

assert "_inconsistency_section_html(issues)," in src
src = src.replace(
    "_inconsistency_section_html(issues),",
    "_inconsistency_section_html(issues, rows=rows),",
    1,
)

OLD_CSS_SNIPPET = (
    ".meta,.inconsistency-note{color:#94a3b8}"
    ".client-bar{display:flex;gap:10px;align-items:center;margin:6px 0}"
    ".client-bar-label{width:160px}"
    ".client-bar-track{background:#334155;display:inline-block;flex:1;height:12px;border-radius:8px}"
    ".client-bar-fill{background:#f59e0b;display:block;height:100%;border-radius:8px}"
    "table{width:100%;border-collapse:collapse;font-size:13px;background:#1e293b}"
)
NEW_CSS_SNIPPET = (
    ".meta,.inconsistency-note,.cause-chart-note{color:#94a3b8}"
    ".client-summary-panel{background:#1e293b;border-radius:10px;padding:16px;margin-bottom:24px}"
    ".client-summary-kpis{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0 18px}"
    ".kpi{background:#0f172a;border-radius:10px;padding:14px 18px;min-width:110px;border-left:4px solid #6366f1}"
    ".kpi.warn{border-left-color:#f59e0b}.kpi-n{font-size:22px;font-weight:700;color:#34d399}"
    ".kpi.warn .kpi-n{color:#fbbf24}.kpi-l{font-size:12px;color:#94a3b8}"
    ".cause-chart{margin:0 0 20px}.cause-bar{display:grid;grid-template-columns:minmax(120px,180px) 1fr auto;"
    "align-items:center;gap:10px;margin:8px 0}.cause-bar-label{font-size:13px;font-weight:600}"
    ".cause-bar-track{height:18px;background:#334155;position:relative;overflow:hidden;border-radius:6px}"
    ".cause-bar-fill{display:block;height:100%;position:absolute;left:0;top:0;border-radius:6px}"
    ".cause-bar-fill.scanned{width:var(--pct-scanned);background:#0ea5e9;opacity:.35}"
    ".cause-bar-fill.issue{width:var(--pct-issue);background:#f59e0b}"
    ".cause-bar-value{font-size:12px;color:#94a3b8;white-space:nowrap}"
    ".client-bar{display:flex;gap:10px;align-items:center;margin:6px 0}"
    ".client-bar-label{width:160px}"
    ".client-bar-track{background:#334155;display:inline-block;flex:1;height:12px;border-radius:8px}"
    ".client-bar-fill{background:#f59e0b;display:block;height:100%;border-radius:8px}"
    "table{width:100%;border-collapse:collapse;font-size:13px;background:#1e293b}"
)
assert OLD_CSS_SNIPPET in src, "inconsistency CSS snippet not found"
src = src.replace(OLD_CSS_SNIPPET, NEW_CSS_SNIPPET, 1)

old_call = "inconsistency_html = _inconsistency_section_html(inconsistencies)"
new_call = "inconsistency_html = _inconsistency_section_html(inconsistencies, rows=rows)"
assert old_call in src
src = src.replace(old_call, new_call, 1)

OLD_MAIN_CSS = """.inconsistency-report {{ margin-top:28px; background:#1e293b; border-radius:10px; padding:16px; }}
.inconsistency-report h2 {{ color:#fbbf24; }}
.client-bar {{ display:flex; gap:10px; align-items:center; margin:6px 0; }}
.client-bar-label {{ width:160px; }}
.client-bar-track {{ background:#334155; display:inline-block; flex:1; height:12px; border-radius:8px; }}
.client-bar-fill {{ background:#f59e0b; display:block; height:100%; border-radius:8px; }}"""

NEW_MAIN_CSS = """.client-summary-panel {{ margin-top:28px; background:#1e293b; border-radius:10px; padding:16px; }}
.client-summary-kpis {{ display:flex; gap:12px; flex-wrap:wrap; margin:12px 0 18px; }}
.kpi.warn {{ border-left:4px solid #f59e0b; }}
.kpi.warn .kpi-n {{ color:#fbbf24; }}
.cause-chart {{ margin:0 0 20px; }}
.cause-chart-note {{ color:#94a3b8; font-size:12px; }}
.cause-bar {{ display:grid; grid-template-columns:minmax(120px,180px) 1fr auto; align-items:center; gap:10px; margin:8px 0; }}
.cause-bar-label {{ font-size:13px; font-weight:600; }}
.cause-bar-track {{ height:18px; background:#334155; position:relative; overflow:hidden; border-radius:6px; }}
.cause-bar-fill {{ display:block; height:100%; position:absolute; left:0; top:0; border-radius:6px; }}
.cause-bar-fill.scanned {{ width:var(--pct-scanned); background:#0ea5e9; opacity:.35; }}
.cause-bar-fill.issue {{ width:var(--pct-issue); background:#f59e0b; }}
.cause-bar-value {{ font-size:12px; color:#94a3b8; white-space:nowrap; }}
.inconsistency-report {{ margin-top:28px; background:#1e293b; border-radius:10px; padding:16px; }}
.inconsistency-report h2 {{ color:#fbbf24; }}
.client-bar {{ display:flex; gap:10px; align-items:center; margin:6px 0; }}
.client-bar-label {{ width:160px; }}
.client-bar-track {{ background:#334155; display:inline-block; flex:1; height:12px; border-radius:8px; }}
.client-bar-fill {{ background:#f59e0b; display:block; height:100%; border-radius:8px; }}"""

assert OLD_MAIN_CSS in src, "main HTML CSS block not found"
src = src.replace(OLD_MAIN_CSS, NEW_MAIN_CSS, 1)

OLD_RUN = '''    cu_html, cu_csv = write_client_unique(rows, out_dir, basename=f"client_unique_{ts}_v{REPORT_VERSION}")
    inc_html, inc_csv = write_inconsistency_report(rows, out_dir, basename=f"inconsistency_{ts}_v{REPORT_VERSION}")

    log(f"Wrote TSV: {tsv_path}")
    log(f"Wrote HTML: {html_path}")
    log(f"Wrote client unique: {cu_html}")
    log(f"Wrote inconsistency report: {inc_html}")

    return {
        "report_dir": str(out_dir),
        "tsv_path": str(tsv_path),
        "html_path": str(html_path),
        "client_unique_html": str(cu_html),
        "client_unique_csv": str(cu_csv),
        "inconsistency_html": str(inc_html),
        "inconsistency_csv": str(inc_csv),
        "rows": rows,
        "n_files": len(rows),
        "report_version": REPORT_VERSION,
    }'''

NEW_RUN = '''    cu_html, cu_csv = write_client_unique(rows, out_dir, basename=f"client_unique_{ts}_v{REPORT_VERSION}")
    inc_html, inc_csv = write_inconsistency_report(rows, out_dir, basename=f"inconsistency_{ts}_v{REPORT_VERSION}")
    cs_html, cs_csv = write_client_summary(rows, out_dir, basename=f"client_summary_{ts}_v{REPORT_VERSION}")

    log(f"Wrote TSV: {tsv_path}")
    log(f"Wrote HTML: {html_path}")
    log(f"Wrote client unique: {cu_html}")
    log(f"Wrote inconsistency report: {inc_html}")
    log(f"Wrote client summary: {cs_html}")

    return {
        "report_dir": str(out_dir),
        "tsv_path": str(tsv_path),
        "html_path": str(html_path),
        "client_unique_html": str(cu_html),
        "client_unique_csv": str(cu_csv),
        "inconsistency_html": str(inc_html),
        "inconsistency_csv": str(inc_csv),
        "client_summary_html": str(cs_html),
        "client_summary_csv": str(cs_csv),
        "rows": rows,
        "n_files": len(rows),
        "report_version": REPORT_VERSION,
    }'''

assert OLD_RUN in src, "run_sectional_report return block not found"
src = src.replace(OLD_RUN, NEW_RUN, 1)

src = src.replace(
    "Returns dict with report_dir, tsv_path, html_path, client_unique_html,\n"
    "    client_unique_csv, inconsistency_html, inconsistency_csv, rows, n_files.",
    "Returns dict with report_dir, tsv_path, html_path, client_unique_html,\n"
    "    client_unique_csv, inconsistency_html, inconsistency_csv,\n"
    "    client_summary_html, client_summary_csv, rows, n_files.",
    1,
)

SRC.write_text(src, encoding="utf-8")
print("Updated", SRC)

test = TEST.read_text(encoding="utf-8")
assert "self.assertEqual(sr.REPORT_VERSION, 10)" in test
test = test.replace(
    "self.assertEqual(sr.REPORT_VERSION, 10)",
    "self.assertEqual(sr.REPORT_VERSION, 11)",
    1,
)

OLD_TEST_TAIL = '''        inc_html, inc_csv = sr.write_inconsistency_report([row], self.tmp / "reports")
        self.assertTrue(inc_html.is_file())
        self.assertTrue(inc_csv.is_file())
        self.assertIn("ClientA", inc_html.read_text(encoding="utf-8"))
if __name__ == "__main__":
    unittest.main()
'''

NEW_TEST_TAIL = '''        inc_html, inc_csv = sr.write_inconsistency_report([row], self.tmp / "reports")
        self.assertTrue(inc_html.is_file())
        self.assertTrue(inc_csv.is_file())
        inc_text = inc_html.read_text(encoding="utf-8")
        self.assertIn("ClientA", inc_text)
        self.assertIn("Client-wise summary", inc_text)
        self.assertIn("Scanned document count", inc_text)
        self.assertIn("Issue document count", inc_text)

        clean = {
            "client": "ClientB",
            "file_id": "F2",
            "docid": "D2",
            "xml_path": str(self.tmp / "D2.xml"),
            "per_section": {
                section: {query: {"count": 0, "hits": []} for query in sr.QUERY_KEYS}
                for section in sr.SECTIONS
            },
            "section_counts": {section: 0 for section in sr.SECTIONS},
            "query_totals": {query: 0 for query in sr.QUERY_KEYS},
            "error": None,
        }
        summary = sr.compute_client_summary([row, clean])
        by_client = {item["client"]: item for item in summary}
        self.assertEqual(by_client["ClientA"]["scanned_document_count"], 1)
        self.assertEqual(by_client["ClientA"]["issue_document_count"], 1)
        self.assertEqual(by_client["ClientB"]["scanned_document_count"], 1)
        self.assertEqual(by_client["ClientB"]["issue_document_count"], 0)
        self.assertEqual(
            sr.CLIENT_SUMMARY_HEADERS,
            ["Client", "Scanned document count", "Issue document count"],
        )

        cs_html, cs_csv = sr.write_client_summary([row, clean], self.tmp / "reports")
        self.assertTrue(cs_html.is_file())
        self.assertTrue(cs_csv.is_file())
        cs_text = cs_html.read_text(encoding="utf-8")
        self.assertIn("Client-wise summary", cs_text)
        self.assertIn("cause-bar", cs_text)
        self.assertIn("ClientA", cs_text)
        self.assertIn("ClientB", cs_text)
        csv_text = cs_csv.read_text(encoding="utf-8")
        self.assertIn("Client,Scanned document count,Issue document count", csv_text)
        self.assertIn("ClientA,1,1", csv_text)
        self.assertIn("ClientB,1,0", csv_text)

        # Main sectional HTML also embeds the shareable summary panel
        self.assertIn("Client-wise summary", page)
        self.assertIn("Scanned document count", page)


if __name__ == "__main__":
    unittest.main()
'''

assert OLD_TEST_TAIL in test, "test tail not found exactly"
test = test.replace(OLD_TEST_TAIL, NEW_TEST_TAIL, 1)
TEST.write_text(test, encoding="utf-8")
print("Updated", TEST)
print("OK")
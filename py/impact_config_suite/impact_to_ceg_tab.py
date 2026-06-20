from core.impact_to_ceg_processor import ImpactToCEGProcessor
from pgm_processor_tab import PGMProcessorTab
from datetime import datetime


class ImpactToCEGTab(PGMProcessorTab):
    processor_cls = ImpactToCEGProcessor
    cache_filename = "impact_to_ceg_cache.json"
    header_text = "IMPACT TO CEG/PGM CONVERTER"
    description_text = (
        "Converts IMPACT HTML → CEG/PGM-compatible HTML.\n"
        "Scoped to <body> only · renames attrs to data-impact-* · adds paragraph class / data-label / data-name.\n"
        "Removes: span[data-bkmark] · Unwraps: whitespace-only font spans · Skips: header, style, title, meta, link, del, ins, insert"
    )
    process_button_text = "🚀  RUN IMPACT TO CEG"
    output_token = "CEG"
    output_extension = ".xhtml"
    archive_token = "IMPACT_to_CEG"
    report_title = "IMPACT to CEG Cleanup Report"
    start_log_message = "Starting IMPACT to CEG/PGM conversion…"
    cleanup_log_message = "Cleanup   : preserves original attrs as data-impact-* · applies CEG paragraph styles"

    def _write_cleanup_report(self, results, src, out, mode, ts):
        # Call parent method but override to add IMPACT-specific sections
        report_path = self._cleanup_report_path(src, out, mode, ts)

        totals = {
            "files": len(results),
            "cleanup_total": 0,
            "remove_attribute": 0,
            "remove_element": 0,
            "unwrap_element": 0,
            "apply_rule": 0,
            "hide_element": 0,
        }

        segment_rows = []
        detail_rows = []
        action_detail_rows = {
            "remove_attribute": [],
            "remove_element": [],
            "unwrap_element": [],
            "apply_rule": [],
            "hide_element": [],
        }
        error_rows = []

        for item in results:
            file_label = item.get("relative_path") or item.get("input_path") or ""
            if not item.get("ok"):
                error_rows.append(
                    f"<tr><td>{self._h(file_label)}</td><td>{self._h(item.get('error', ''))}</td></tr>"
                )
                continue

            for segment in item.get("cleanup_segments", []):
                segment_rows.append(
                    "<tr>"
                    f"<td>{self._h(file_label)}</td>"
                    f"<td>{self._h(segment.get('segment', ''))}</td>"
                    f"<td>{segment.get('remove_attribute', 0)}</td>"
                    f"<td>{segment.get('remove_element', 0)}</td>"
                    f"<td>{segment.get('unwrap_element', 0)}</td>"
                    f"<td>{segment.get('total', 0)}</td>"
                    "</tr>"
                )

            for detail in item.get("cleanup_details", []):
                detail_row = (
                    "<tr>"
                    f"<td>{self._h(file_label)}</td>"
                    f"<td>{self._h(detail.get('segment', ''))}</td>"
                    f"<td>{self._format_action(detail.get('action', ''))}</td>"
                    f"<td>{self._h(detail.get('target', ''))}</td>"
                    f"<td>{self._h(detail.get('tag', ''))}</td>"
                    f"<td>{self._h(detail.get('path', ''))}</td>"
                    f"<td>{self._h(detail.get('value', ''))}</td>"
                    f"<td>{self._h(detail.get('text', ''))}</td>"
                    "</tr>"
                )
                detail_rows.append(detail_row)
                action = detail.get("action")
                if action in action_detail_rows:
                    action_detail_rows[action].append(detail_row)
                    totals[action] += 1
                    totals["cleanup_total"] += 1

        segment_count = len(segment_rows)
        if not segment_rows:
            segment_rows.append(
                "<tr><td colspan='6' class='empty'>No removed attributes, removed elements, or unwrapped elements.</td></tr>"
            )
        if not detail_rows:
            detail_rows.append("<tr><td colspan='8' class='empty'>No cleanup details.</td></tr>")
        for action, rows in action_detail_rows.items():
            if not rows:
                action_detail_rows[action].append(
                    f"<tr><td colspan='8' class='empty'>No {self._h(self._action_label(action).lower())} details.</td></tr>"
                )
        if not error_rows:
            error_rows.append("<tr><td colspan='2' class='empty'>No errors.</td></tr>")

        error_count = len(error_rows) - 1 if error_rows else 0  # Subtract the empty row

        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{self._h(self.report_title)} {self._h(ts)}</title>
<style>
body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #f8fafc; color: #0f172a; }}
header {{ background: #0f172a; color: white; padding: 24px 32px; }}
h1 {{ margin: 0 0 8px; font-size: 24px; }}
h2 {{ margin-top: 28px; font-size: 18px; }}
main {{ padding: 24px 32px 40px; }}
.meta {{ color: #cbd5e1; font-size: 13px; line-height: 1.7; }}
.cards {{ display: grid; grid-template-columns: repeat(7, minmax(120px, 1fr)); gap: 12px; margin: 20px 0; }}
.card {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; }}
.card b {{ display: block; font-size: 24px; margin-bottom: 4px; }}
.card span {{ color: #64748b; font-size: 12px; text-transform: uppercase; }}
table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #e2e8f0; }}
th, td {{ border-bottom: 1px solid #e2e8f0; padding: 9px 10px; text-align: left; vertical-align: top; font-size: 13px; }}
th {{ background: #e2e8f0; font-size: 12px; text-transform: uppercase; color: #334155; }}
td {{ word-break: break-word; }}
.empty {{ color: #64748b; text-align: center; }}
.pill {{ display: inline-block; border-radius: 999px; padding: 2px 8px; background: #e0f2fe; color: #075985; font-size: 12px; white-space: nowrap; }}
.report-panel {{ margin-top: 16px; background: white; border: 1px solid #dbe4ef; border-radius: 8px; overflow: hidden; }}
.report-panel summary {{ cursor: pointer; display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 14px 16px; background: #f1f5f9; font-weight: 700; color: #0f172a; }}
.report-panel summary::-webkit-details-marker {{ display: none; }}
.report-panel summary::after {{ content: '+'; width: 24px; height: 24px; border-radius: 50%; background: #cbd5e1; color: #0f172a; display: inline-grid; place-items: center; flex: 0 0 auto; }}
.report-panel[open] summary::after {{ content: '-'; }}
.panel-body {{ padding: 14px; overflow-x: auto; }}
.panel-note {{ margin: 0 0 10px; color: #64748b; font-size: 13px; }}
.quick-panels {{ display: grid; grid-template-columns: repeat(5, minmax(180px, 1fr)); gap: 12px; margin-top: 18px; }}
.quick-panels .report-panel {{ margin-top: 0; }}
.quick-panels table {{ min-width: 760px; }}
.count {{ display: inline-block; min-width: 28px; padding: 2px 8px; border-radius: 999px; background: #0f172a; color: white; text-align: center; font-size: 12px; }}
@media (max-width: 900px) {{ .cards, .quick-panels {{ grid-template-columns: 1fr; }} main {{ padding: 18px; }} }}
</style>
</head>
<body>
<header>
<h1>{self._h(self.report_title)}</h1>
<div class="meta">
<div><b>Timestamp:</b> {self._h(ts)}</div>
<div><b>Generated:</b> {self._h(generated_at)}</div>
<div><b>Source:</b> {self._h(src)}</div>
<div><b>Output:</b> {self._h(out)}</div>
<div><b>Conversion Type:</b> IMPACT to CEG/PGM</div>
</div>
</header>
<main>
<section class="cards">
<div class="card"><b>{totals['files']}</b><span>Files processed</span></div>
<div class="card"><b>{totals['cleanup_total']}</b><span>Total transformations</span></div>
<div class="card"><b>{totals['apply_rule']}</b><span>Rules applied</span></div>
<div class="card"><b>{totals['hide_element']}</b><span>Elements hidden</span></div>
<div class="card"><b>{totals['remove_attribute']}</b><span>Remove attributes</span></div>
<div class="card"><b>{totals['remove_element']}</b><span>Remove elements</span></div>
<div class="card"><b>{totals['unwrap_element']}</b><span>Unwrap</span></div>
</section>

<details class="report-panel" open>
<summary><span>Segment-wise Summary</span><span class="count">{segment_count}</span></summary>
<div class="panel-body">
<p class="panel-note">Counts are grouped by segment so cleanup volume is easy to review chapter or section wise.</p>
<table>
<thead><tr><th>File</th><th>Segment</th><th>Remove attributes</th><th>Remove elements</th><th>Unwrap</th><th>Total</th></tr></thead>
<tbody>{''.join(segment_rows)}</tbody>
</table>
</div>
</details>

<section class="quick-panels">
<details class="report-panel">
<summary><span>Rules Applied</span><span class="count">{totals['apply_rule']}</span></summary>
<div class="panel-body"><table>
<thead><tr><th>File</th><th>Segment</th><th>Action</th><th>Target</th><th>Tag</th><th>Path</th><th>Details</th><th>Text preview</th></tr></thead>
<tbody>{''.join(action_detail_rows['apply_rule'])}</tbody>
</table></div>
</details>
<details class="report-panel">
<summary><span>Elements Hidden</span><span class="count">{totals['hide_element']}</span></summary>
<div class="panel-body"><table>
<thead><tr><th>File</th><th>Segment</th><th>Action</th><th>Target</th><th>Tag</th><th>Path</th><th>Details</th><th>Text preview</th></tr></thead>
<tbody>{''.join(action_detail_rows['hide_element'])}</tbody>
</table></div>
</details>
<details class="report-panel">
<summary><span>Remove attributes</span><span class="count">{totals['remove_attribute']}</span></summary>
<div class="panel-body"><table>
<thead><tr><th>File</th><th>Segment</th><th>Action</th><th>Target</th><th>Tag</th><th>Path</th><th>Removed value</th><th>Text preview</th></tr></thead>
<tbody>{''.join(action_detail_rows['remove_attribute'])}</tbody>
</table></div>
</details>
<details class="report-panel">
<summary><span>Remove elements</span><span class="count">{totals['remove_element']}</span></summary>
<div class="panel-body"><table>
<thead><tr><th>File</th><th>Segment</th><th>Action</th><th>Target</th><th>Tag</th><th>Path</th><th>Removed value</th><th>Text preview</th></tr></thead>
<tbody>{''.join(action_detail_rows['remove_element'])}</tbody>
</table></div>
</details>
<details class="report-panel">
<summary><span>Unwrap</span><span class="count">{totals['unwrap_element']}</span></summary>
<div class="panel-body"><table>
<thead><tr><th>File</th><th>Segment</th><th>Action</th><th>Target</th><th>Tag</th><th>Path</th><th>Removed value</th><th>Text preview</th></tr></thead>
<tbody>{''.join(action_detail_rows['unwrap_element'])}</tbody>
</table></div>
</details>
</section>

<details class="report-panel">
<summary><span>All Cleanup Details</span><span class="count">{totals['cleanup_total']}</span></summary>
<div class="panel-body">
<table>
<thead><tr><th>File</th><th>Segment</th><th>Action</th><th>Target</th><th>Tag</th><th>Path</th><th>Details</th><th>Text preview</th></tr></thead>
<tbody>{''.join(detail_rows)}</tbody>
</table>
</div>
</details>

<details class="report-panel">
<summary><span>Errors</span><span class="count">{error_count}</span></summary>
<div class="panel-body">
<table>
<thead><tr><th>File</th><th>Error</th></tr></thead>
<tbody>{''.join(error_rows)}</tbody>
</table>
</div>
</details>
</main>
</body>
</html>"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        return report_path

    def _action_label(self, action: str) -> str:
        labels = {
            "remove_attribute": "Remove attributes",
            "remove_element": "Remove elements",
            "unwrap_element": "Unwrap",
            "apply_rule": "Apply rule",
            "hide_element": "Hide element",
        }
        return labels.get(action, action)

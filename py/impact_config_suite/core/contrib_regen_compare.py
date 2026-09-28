"""
contrib_regen_compare.py - KPI band + cause-chart UI for regen/compare reports.

Ports the package regen_compare_v1 chart UX (KPI band, cause bar chart with
click-to-filter Not matched, category filter status) into the Impact Config Suite.

Phase 0 still writes a per-doc compare page; this module builds the batch
regen-compare summary HTML (and helpers) once compare result rows exist.
Real slot-level PI compare categories can replace lightweight equality rows later.
"""
from __future__ import annotations

import html
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

REPORT_VERSION = 1

CATEGORY_LABELS: Dict[str, str] = {
    "space-nbsp": "Space vs NBSP",
    "original-value-not-configured": "Original value not configured",
    "original-pi-different-position": "Original PI at different position",
    "missing-at-configured-position": "Missing at configured position",
    "extra-in-original": "Extra in original",
    "other-value-difference": "Other value difference",
    "processing-error": "Processing error",
}


def esc(s: Any) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def esc_attr(s: Any) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def safe_name(s: str) -> str:
    out = []
    for ch in (s or "").strip():
        if ch.isalnum() or ch in "-_.":
            out.append(ch)
        else:
            out.append("_")
    return "".join(out) or "report"


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def result_categories(r: dict) -> Set[str]:
    """Categories for one compare result row (doc-level)."""
    if r.get("error"):
        return {"processing-error"}
    categories = set(r.get("categories") or set())
    if not categories:
        categories.update(
            category
            for mismatch in r.get("mismatches") or []
            for category in (mismatch.get("categories") or set())
        )
    return categories


def lightweight_compare_row(
    *,
    docid: str,
    file_id: str = "",
    original_clean: str = "",
    regen: str = "",
    error: Optional[str] = None,
    compare_href: Optional[str] = None,
) -> dict:
    """Build a compare row from Phase0 artifacts (byte equality + simple categories).

    Slot-level PI compare can replace this later; until then the batch chart
    still renders from these rows.
    """
    fid = file_id or docid
    if error:
        return {
            "docid": docid,
            "file_id": fid,
            "match": 0,
            "total": 0,
            "pct": 0.0,
            "mismatches": [],
            "categories": {"processing-error"},
            "error": error,
            "compare_href": compare_href,
        }
    if original_clean == regen:
        return {
            "docid": docid,
            "file_id": fid,
            "match": 1,
            "total": 1,
            "pct": 100.0,
            "mismatches": [],
            "categories": set(),
            "error": None,
            "compare_href": compare_href,
        }
    categories: Set[str] = set()
    if original_clean.replace("\xa0", " ") == regen.replace("\xa0", " "):
        categories.add("space-nbsp")
    else:
        categories.add("other-value-difference")
    mismatch = {
        "key": "document",
        "slot": "document",
        "expected": "(original_clean)",
        "found": "(regen)",
        "categories": set(categories),
    }
    return {
        "docid": docid,
        "file_id": fid,
        "match": 0,
        "total": 1,
        "pct": 0.0,
        "mismatches": [mismatch],
        "categories": categories,
        "error": None,
        "compare_href": compare_href,
    }


def _relpath(target: Path, start: Path) -> str:
    try:
        return str(target.resolve().relative_to(start.resolve()))
    except ValueError:
        return os.path.relpath(str(target), str(start))


def collect_compare_rows_from_folders(
    rows: Sequence[dict],
    *,
    report_dir: Optional[Path] = None,
) -> List[dict]:
    """Read Phase0 original_clean + regen from each row folder into compare rows."""
    from core.contrib_phase0 import OUT_COMPARE_HTML, OUT_XML_ORIGINAL_CLEAN, OUT_XML_REGEN

    out: List[dict] = []
    for r in rows:
        folder = Path(r["folder"])
        docid = r.get("docid") or folder.name
        file_id = r.get("file_id") or docid
        href = None
        if report_dir is not None:
            try:
                href = Path(_relpath(folder / OUT_COMPARE_HTML, Path(report_dir))).as_posix()
            except Exception:
                href = None
        clean_path = folder / OUT_XML_ORIGINAL_CLEAN
        regen_path = folder / OUT_XML_REGEN
        if not clean_path.is_file() or not regen_path.is_file():
            out.append(
                lightweight_compare_row(
                    docid=docid,
                    file_id=file_id,
                    error=f"missing {OUT_XML_ORIGINAL_CLEAN} or {OUT_XML_REGEN}",
                    compare_href=href,
                )
            )
            continue
        try:
            original_clean = clean_path.read_text(encoding="utf-8")
            regen = regen_path.read_text(encoding="utf-8")
        except OSError as exc:
            out.append(
                lightweight_compare_row(
                    docid=docid,
                    file_id=file_id,
                    error=str(exc),
                    compare_href=href,
                )
            )
            continue
        out.append(
            lightweight_compare_row(
                docid=docid,
                file_id=file_id,
                original_clean=original_clean,
                regen=regen,
                compare_href=href,
            )
        )
    return out


# --------------------------------------------------------------------------- CSS / JS

REGEN_COMPARE_CSS = """
<style>
body{font-family:system-ui,Segoe UI,sans-serif;margin:0;color:#1f2328;background:#fff}
header{padding:16px 20px;border-bottom:1px solid #d0d7de;background:#f6f8fa}
header .ttl{font-size:20px;font-weight:700;margin:0 0 8px}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{font-size:12px;border:1px solid #d0d7de;background:#fff;border-radius:999px;padding:3px 10px}
.chip b{margin-right:4px}
.chip.warn{border-color:#ff8182;background:#ffebe9}
.chip.good{border-color:#4ac26b;background:#dafbe1}
main{padding:20px;max-width:1100px}
.note{background:#fff8c5;border:1px solid #d4a72c;padding:10px 12px;border-radius:6px;margin:0 0 16px;font-size:13px}
.okbox{background:#dafbe1;border:1px solid #4ac26b;padding:10px 12px;border-radius:6px;color:#1a7f37}
.okmark{color:#1a7f37;font-weight:600}
.bad-remark{color:#b42318;font-weight:600}
.err{color:#b42318}
.na{color:#8c959f}
.docid{font-size:11px;color:#57606a;margin-top:2px}
.cause-tags{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:5px}
.cause-tag{font-size:11px;border:1px solid #f0a39e;background:#ffebe9;color:#8f1f18;border-radius:4px;padding:1px 5px}
.report-tools{display:flex;gap:18px;align-items:center;margin:0 0 14px;font-size:13px}
.report-tools input[type=search]{padding:5px 8px;border:1px solid #d0d7de;border-radius:6px;width:240px}
.kpi-band{display:grid;grid-template-columns:repeat(3,minmax(150px,1fr));gap:10px;margin:0 0 20px;max-width:760px}
.kpi{border-left:4px solid #0969da;background:#f6f8fa;padding:12px 16px;min-height:82px}
.kpi.warn{border-left-color:#cf222e;background:#fff5f5}
.kpi-label{font-size:13px;color:#57606a;font-weight:600}
.kpi-value{font-size:30px;line-height:1.15;font-weight:750;margin-top:3px}
.cause-chart{max-width:900px;margin:0 0 24px}
.cause-chart h2{font-size:16px;margin:0 0 4px}
.cause-chart-note{font-size:12px;color:#57606a;margin:0 0 12px}
.cause-bar{display:grid;grid-template-columns:minmax(180px,280px) 1fr auto;align-items:center;gap:10px;width:100%;border:0;background:transparent;padding:5px 0;cursor:pointer;text-align:left;color:#1f2328}
.cause-bar-track{height:18px;background:#eaeef2;position:relative;overflow:hidden;border-radius:3px}
.cause-bar-fill{display:block;width:var(--pct);height:100%;background:#2f81f7}
.cause-bar.on .cause-bar-fill{background:#cf222e}
.cause-bar-label{font-size:13px;font-weight:600}
.cause-bar-value{font-size:12px;color:#57606a;white-space:nowrap}
.category-filter-status{display:flex;align-items:center;gap:8px;min-height:28px;font-size:13px;margin-bottom:8px}
.category-filter-status[hidden]{display:none}
.category-filter-status button{border:1px solid #d0d7de;background:#fff;border-radius:6px;padding:4px 8px;cursor:pointer}
.rt-tabs{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}
.rt-tabs button{border:1px solid #d0d7de;background:#f6f8fa;border-radius:6px;padding:6px 10px;cursor:pointer;font-size:13px}
.rt-tabs button.on{background:#0969da;color:#fff;border-color:#0969da}
.rt-count{margin-left:6px;opacity:.85}
.rt-warn{margin-left:6px;color:#cf222e}
.rt-tabs button.on .rt-warn{color:#ffebe9}
.rt-pane{display:none}
.rt-pane.on{display:block}
.regen-table{width:100%;border-collapse:collapse;font-size:13px}
.regen-table th,.regen-table td{border:1px solid #d0d7de;padding:8px 10px;vertical-align:top;text-align:left}
.regen-table th{background:#f6f8fa}
.regen-table tr.hid{display:none}
.cg-n{font-size:11px;color:#57606a}
.report-section{margin:0 0 28px}
@media(max-width:650px){.kpi-band{grid-template-columns:1fr}.cause-bar{grid-template-columns:1fr auto}.cause-bar-track{grid-column:1/-1}}
</style>
"""

REGEN_COMPARE_JS = """<script>
(function(){
  document.querySelectorAll('[data-regen-tabs]').forEach(function(section){
    var buttons=[].slice.call(section.querySelectorAll('[data-rt-tab]'));
    var panes=[].slice.call(section.querySelectorAll('[data-rt-pane]'));
    buttons.forEach(function(button){button.addEventListener('click',function(){
      var id=button.getAttribute('data-rt-tab');
      buttons.forEach(function(b){b.classList.toggle('on',b===button);});
      panes.forEach(function(p){p.classList.toggle('on',p.getAttribute('data-rt-pane')===id);});
    });});
  });
  var q=document.getElementById('regenSearch'), only=document.getElementById('regenOnlyIssues');
  var activeCategory='', categoryStatus=document.getElementById('categoryFilterStatus');
  function activateUnmatched(){
    var button=document.querySelector('[data-rt-tab="files-unmatched"]');
    if(button)button.click();
  }
  function filter(){
    var term=q ? q.value.trim().toLowerCase() : '', issues=only && only.checked;
    document.querySelectorAll('tr[data-row]').forEach(function(row){
      var inUnmatched=row.closest('[data-rt-pane="files-unmatched"]');
      var categoryHidden=activeCategory && inUnmatched && (' '+(row.getAttribute('data-categories')||'')+' ').indexOf(' '+activeCategory+' ')<0;
      var hide=(issues && !row.hasAttribute('data-issue')) || (term && (row.getAttribute('data-s')||'').indexOf(term)<0) || categoryHidden;
      row.classList.toggle('hid',hide);
    });
  }
  if(q)q.addEventListener('input',filter);if(only)only.addEventListener('change',filter);
  document.querySelectorAll('[data-category]').forEach(function(button){
    button.addEventListener('click',function(){
      activeCategory=button.getAttribute('data-category');
      document.querySelectorAll('[data-category]').forEach(function(item){
        item.classList.toggle('on',item===button);
        item.setAttribute('aria-pressed',item===button?'true':'false');
      });
      if(categoryStatus){
        categoryStatus.hidden=false;
        categoryStatus.querySelector('span').textContent='Filtered by: '+button.getAttribute('data-label');
      }
      activateUnmatched();filter();
    });
  });
  var clearCategory=document.getElementById('clearCategoryFilter');
  if(clearCategory)clearCategory.addEventListener('click',function(){
    activeCategory='';
    document.querySelectorAll('[data-category]').forEach(function(item){
      item.classList.remove('on');item.setAttribute('aria-pressed','false');
    });
    if(categoryStatus)categoryStatus.hidden=true;
    filter();
  });
})();
</script>"""


def summary_kpis(documents: int, overall: float, unmatched: int) -> str:
    return (
        '<section class="kpi-band" aria-label="Report summary">'
        f'<div class="kpi"><div class="kpi-label">Documents</div><div class="kpi-value">{documents}</div></div>'
        f'<div class="kpi"><div class="kpi-label">Overall match</div><div class="kpi-value">{overall:.1f}%</div></div>'
        f'<div class="kpi warn"><div class="kpi-label">Not matched</div><div class="kpi-value">{unmatched}</div></div>'
        "</section>"
    )


def category_chart(unmatched: list[dict]) -> str:
    denominator = len(unmatched)
    counts = {
        category: sum(category in result_categories(row) for row in unmatched)
        for category in CATEGORY_LABELS
    }
    bars: List[str] = []
    for category, label in CATEGORY_LABELS.items():
        count = counts[category]
        if not count:
            continue
        pct = count / denominator * 100 if denominator else 0.0
        bars.append(
            f'<button type="button" class="cause-bar" data-category="{esc_attr(category)}" '
            f'data-label="{esc_attr(label)}" aria-pressed="false" style="--pct:{pct:.1f}%">'
            f'<span class="cause-bar-label">{esc(label)}</span>'
            f'<span class="cause-bar-track"><span class="cause-bar-fill"></span></span>'
            f'<span class="cause-bar-value">{count} {"file" if count == 1 else "files"} &middot; '
            f"{pct:.1f}% of unmatched</span></button>"
        )
    content = "".join(bars) if bars else '<div class="okbox">No mismatches to categorize.</div>'
    return (
        '<section class="cause-chart" aria-labelledby="causeChartTitle">'
        '<h2 id="causeChartTitle">Why files do not match</h2>'
        '<p class="cause-chart-note">A file may appear in more than one category. '
        "Select a bar to filter Not matched.</p>"
        + content
        + '<div class="category-filter-status" id="categoryFilterStatus" hidden>'
        '<span></span><button type="button" id="clearCategoryFilter">Clear filter</button></div></section>'
    )


def mismatch_remarks(
    mismatches: list[dict], categories: Optional[Iterable[str]] = None
) -> str:
    cats = sorted(
        set(categories or ())
        or {c for m in mismatches for c in (m.get("categories") or set())},
        key=lambda category: list(CATEGORY_LABELS).index(category)
        if category in CATEGORY_LABELS
        else 999,
    )
    if not mismatches and not cats:
        return '<span class="okmark">All values matched</span>'
    category_html = "".join(
        f'<span class="cause-tag">{esc(CATEGORY_LABELS.get(c, c))}</span>' for c in cats
    )
    n = len(mismatches) if mismatches else len(cats)
    return (
        f'<div class="cause-tags">{category_html}</div>'
        f'<span class="bad-remark">{n} mismatch(es)</span>'
    )


def _row_attrs(r: dict, has_issue: bool) -> str:
    search = f"{r.get('file_id') or r.get('docid', '')} {r.get('docid', '')}".lower()
    categories = " ".join(sorted(result_categories(r)))
    attrs = (
        f' data-row data-s="{esc_attr(search)}" '
        f'data-categories="{esc_attr(categories)}"'
    )
    return attrs + (" data-issue" if has_issue else "")


def _file_result_row(r: dict) -> str:
    fid = esc(r.get("file_id") or r.get("docid", ""))
    did = esc(r.get("docid", ""))
    href = r.get("compare_href")
    label = f'<a href="{esc_attr(href)}">{fid}</a>' if href else fid
    if r.get("error"):
        return (
            f'<tr{_row_attrs(r, True)}><td>{label}<div class="docid">{did}</div></td>'
            '<td class="na">N/A</td>'
            f'<td class="err"><div class="cause-tags"><span class="cause-tag">'
            f'{esc(CATEGORY_LABELS["processing-error"])}</span></div>{esc(r["error"])}</td></tr>'
        )
    issue = float(r.get("pct", 0)) != 100.0
    return (
        f'<tr{_row_attrs(r, issue)}><td>{label}<div class="docid">{did}</div></td>'
        f'<td>{float(r.get("pct", 0)):.1f}%'
        f'<div class="cg-n">{r.get("match", 0)}/{r.get("total", 0)}</div></td>'
        f'<td>{mismatch_remarks(r.get("mismatches") or [], result_categories(r))}</td></tr>'
    )


def _result_table(rows_html: str) -> str:
    return (
        '<table class="regen-table"><tr><th>File ID</th><th>Percentage</th>'
        f"<th>Remarks</th></tr>{rows_html}</table>"
    )


def _tab_section(
    title: str,
    prefix: str,
    tabs: list[tuple[str, str, list, str, int]],
    default: str,
) -> str:
    buttons: List[str] = []
    panes: List[str] = []
    for tab_id, label, rows, rows_html, issues in tabs:
        on = tab_id == default
        buttons.append(
            f'<button type="button" class="{"on" if on else ""}" data-rt-tab="{prefix}-{tab_id}">'
            f'{esc(label)} <span class="rt-count">{len(rows)}</span>'
            + (f'<span class="rt-warn">&#9888;{issues}</span>' if issues else "")
            + "</button>"
        )
        panes.append(
            f'<div class="rt-pane{" on" if on else ""}" data-rt-pane="{prefix}-{tab_id}">'
            + _result_table(rows_html)
            + "</div>"
        )
    return (
        f'<section class="report-section" data-regen-tabs><h2>{esc(title)}</h2>'
        f'<div class="rt-tabs">{"".join(buttons)}</div>{"".join(panes)}</section>'
    )


def _page(title: str, chips: list[tuple[str, Any, str]], body: str) -> str:
    chips_html = "".join(
        f'<span class="chip {style}"><b>{esc(label)}</b> {esc(str(value))}</span>'
        for label, value, style in chips
    )
    return (
        "<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{esc(title)}</title>{REGEN_COMPARE_CSS}</head><body>"
        f'<header><div class="ttl">{esc(title)}</div><div class="chips">{chips_html}</div></header>'
        f"<main>{body}</main></body></html>"
    )


def build_batch_regen_compare_html(
    client: str,
    shortcode: str,
    rows: Sequence[dict],
    *,
    config_name: str = "",
    config_version: str = "",
    note: str = "",
) -> str:
    """Build batch regen-compare HTML with KPI band + interactive cause chart."""
    ok_rows = [r for r in rows if not r.get("error")]
    err_rows = [r for r in rows if r.get("error")]
    ok_rows = sorted(
        ok_rows,
        key=lambda r: (
            float(r.get("pct", 0)),
            (r.get("file_id") or r.get("docid") or "").lower(),
        ),
    )
    total_match = sum(int(r.get("match") or 0) for r in ok_rows)
    total_all = sum(int(r.get("total") or 0) for r in ok_rows)
    overall = 100.0 if total_all == 0 else total_match / total_all * 100.0

    matched = [r for r in ok_rows if float(r.get("pct", 0)) == 100.0]
    unmatched = [r for r in ok_rows if float(r.get("pct", 0)) != 100.0] + err_rows
    file_tabs = [
        (
            "matched",
            "Matched 100%",
            matched,
            "".join(_file_result_row(r) for r in matched),
            0,
        ),
        (
            "unmatched",
            "Not matched",
            unmatched,
            "".join(_file_result_row(r) for r in unmatched),
            len(unmatched),
        ),
    ]
    file_section = _tab_section(
        "File-level results",
        "files",
        file_tabs,
        "unmatched" if unmatched else "matched",
    )
    tools = (
        '<div class="report-tools"><input type="search" id="regenSearch" '
        'placeholder="search file id / docid" aria-label="search files">'
        '<label><input type="checkbox" id="regenOnlyIssues"> Only files with issues</label></div>'
    )
    note_html = (
        f'<p class="note">{esc(note)}</p>'
        if note
        else (
            '<p class="note">Lightweight compare (original_clean vs regen equality). '
            "Category bars filter the Not matched tab.</p>"
        )
    )
    body = (
        note_html
        + summary_kpis(len(rows), overall, len(unmatched))
        + category_chart(unmatched)
        + tools
        + file_section
        + REGEN_COMPARE_JS
    )
    chips = [
        ("Client", client, ""),
        ("Project shortcode", shortcode, ""),
        ("Config", config_name or "-", ""),
        ("Documents", len(rows), ""),
        ("Overall match", f"{overall:.1f}%", "good" if overall == 100 else "warn"),
        ("Config version", config_version or "-", ""),
        ("Report version", f"v{REPORT_VERSION}", ""),
        ("Generated", now(), ""),
    ]
    return _page(f"{client} / {shortcode} - regen compare", chips, body)


def write_batch_regen_compare_report(
    client: str,
    shortcode: str,
    rows: Sequence[dict],
    report_dir: Path,
    *,
    config_name: str = "",
    config_version: str = "",
    note: str = "",
) -> Path:
    """Write batch regen-compare HTML into report_dir; return path."""
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    html_text = build_batch_regen_compare_html(
        client,
        shortcode,
        rows,
        config_name=config_name,
        config_version=config_version,
        note=note,
    )
    out = report_dir / (
        f"{safe_name(client)}_{safe_name(shortcode)}_regen_compare_v{REPORT_VERSION}.html"
    )
    out.write_text(html_text, encoding="utf-8")
    return out


def enrich_compare_stub_html(
    stub_html: str,
    *,
    matched: Optional[bool] = None,
    categories: Optional[Iterable[str]] = None,
) -> str:
    """Inject a one-doc KPI band into an existing Phase0 compare stub page."""
    if matched is None:
        return stub_html
    docs = 1
    overall = 100.0 if matched else 0.0
    unmatched_n = 0 if matched else 1
    kpi = summary_kpis(docs, overall, unmatched_n)
    chart = ""
    if not matched:
        cats = set(categories or {"other-value-difference"})
        row = {
            "docid": "doc",
            "file_id": "doc",
            "pct": 0.0,
            "match": 0,
            "total": 1,
            "categories": cats,
            "mismatches": [{"categories": cats}],
        }
        chart = category_chart([row])
    inject = REGEN_COMPARE_CSS + kpi + chart + REGEN_COMPARE_JS
    marker = "<h1>contrib_group_compare</h1>"
    if marker in stub_html:
        return stub_html.replace(marker, marker + inject, 1)
    return inject + stub_html

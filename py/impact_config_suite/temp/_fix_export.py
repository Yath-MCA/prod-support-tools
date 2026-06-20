import re
from pathlib import Path

SRC = Path(__file__).parent.parent / "compare_tab.py"
content = SRC.read_text(encoding="utf-8")

NEW_METHOD = r'''    def _export_html_report(self, export_folder=None) -> None:
        if not self.result_rows or not self.current_columns:
            messagebox.showwarning("Export Warning", "No compare results available to export.")
            return

        if export_folder is None:
            export_folder = self.last_export_folder
        if isinstance(export_folder, (str, Path)):
            export_folder = Path(export_folder)
        else:
            export_folder = Path.cwd()
        export_folder.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.report_docid:
            save_path = export_folder / f"html_compare_report_{self.report_docid}_{timestamp}.html"
        else:
            save_path = export_folder / f"html_compare_report_{timestamp}.html"

        dcols = ["anchor_id", "data_user", "data_time", "file_0", "file_1", "status", "parent_status", "reason"]
        dheads = {
            "anchor_id": "Anchor ID", "data_user": "data-username", "data_time": "data-time",
            "file_0": self.current_headings.get("file_0", "Source"),
            "file_1": self.current_headings.get("file_1", "Update"),
            "status": "Status", "parent_status": "Parent Status", "reason": "Reason",
        }
        header_cells = "".join(f"<th>{escape(dheads[c])}</th>" for c in dcols)
        body_rows = []
        for row in self.result_rows:
            st = str(row.get("status", "")).strip()
            ps = str(row.get("parent_status", "\u2014")).strip()
            cells = "".join(f"<td>{escape(str(row.get(c, '')))}</td>" for c in dcols)
            body_rows.append(f'<tr data-status="{escape(st)}" data-parent="{escape(ps)}">{cells}</tr>')

        summary_text = escape(self.summary_label.cget("text"))
        generated = escape(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        rows_body = "".join(body_rows)

        CSS = """\
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Segoe UI",Arial,sans-serif;background:#f1f5f9;color:#1e293b;padding:24px}
.container{max-width:1600px;margin:0 auto}
h1{font-size:1.35rem;font-weight:700;color:#0f172a;margin-bottom:4px}
.meta{font-size:.82rem;color:#64748b;margin-bottom:14px}
.filters{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px;align-items:center}
.filters input,.filters select{padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:.84rem;background:#fff}
.filters input{flex:1;min-width:200px}
.filters label{font-size:.82rem;color:#475569;white-space:nowrap}
.count{font-size:.82rem;color:#6366f1;font-weight:600;margin-left:auto}
.find-bar{display:flex;gap:8px;align-items:center;margin-bottom:10px;background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:8px 12px}
.find-bar input{flex:1;padding:5px 8px;border:1px solid #cbd5e1;border-radius:4px;font-size:.84rem}
.find-bar button{padding:5px 12px;border:none;border-radius:4px;cursor:pointer;font-size:.82rem;font-weight:600}
.btn-f{background:#6366f1;color:#fff}.btn-fn{background:#059669;color:#fff}.btn-cl{background:#e2e8f0;color:#475569}
.mb{font-size:.8rem;color:#64748b;white-space:nowrap}
.table-wrap{overflow-x:auto;border-radius:8px;border:1px solid #e2e8f0;box-shadow:0 1px 4px rgba(0,0,0,.06)}
table{border-collapse:collapse;width:100%;font-size:.83rem}
th{background:#0f172a;color:#fff;padding:9px 10px;text-align:left;white-space:nowrap;position:sticky;top:0;z-index:2}
td{border-bottom:1px solid #e2e8f0;padding:7px 10px;vertical-align:top;max-width:320px;word-break:break-word}
tr:hover td{background:#eff6ff!important}
tr[data-status="Same"] td{background:#f0fdf4}
tr[data-status="Changed"] td{background:#fef2f2}
tr[data-status="Missing in update"] td{background:#f8fafc;color:#94a3b8}
tr[data-status="New in update"] td{background:#fffbeb}
tr[data-status="Changed (Div Replace)"] td{background:#fdf4ff}
.ring{outline:2px solid #f59e0b}"""

        JS = """\
var fm=[],fi=-1;
function af(){
  var t=(document.getElementById('tf').value||'').toLowerCase();
  var s=document.getElementById('sf').value;
  var p=document.getElementById('pf').value;
  var v=0;
  document.querySelectorAll('tbody tr').forEach(function(r){
    var ok=((!t||r.textContent.toLowerCase().includes(t))&&(!s||r.dataset.status===s)&&(!p||(r.dataset.parent||'').includes(p)));
    r.style.display=ok?'':'none';if(ok)v++;});
  document.getElementById('rc').textContent=v+' rows shown';}
function bd(){
  var ss=document.getElementById('sf'),ps=document.getElementById('pf');
  var sv=new Set(),pv=new Set();
  document.querySelectorAll('tbody tr').forEach(function(r){if(r.dataset.status)sv.add(r.dataset.status);if(r.dataset.parent&&r.dataset.parent!=='\u2014')pv.add(r.dataset.parent);});
  [...sv].sort().forEach(function(s){var o=document.createElement('option');o.value=s;o.textContent=s;ss.appendChild(o);});
  [...pv].sort().forEach(function(s){var o=document.createElement('option');o.value=s;o.textContent=s;ps.appendChild(o);});
  document.getElementById('rc').textContent=document.querySelectorAll('tbody tr').length+' rows shown';}
function df(){
  var q=(document.getElementById('fi').value||'').toLowerCase();
  if(!q){cf();return;}
  fm=[];fi=-1;
  document.querySelectorAll('tbody tr').forEach(function(r){if(r.style.display!=='none'&&r.textContent.toLowerCase().includes(q))fm.push(r);});
  document.getElementById('fc').textContent=fm.length+' found';
  if(fm.length){fi=0;sm();}}
function sm(){fm.forEach(function(r){r.classList.remove('ring');});if(fi>=0&&fi<fm.length){fm[fi].classList.add('ring');fm[fi].scrollIntoView({block:'center'});}}
function fn(){if(!fm.length)return;fi=(fi+1)%fm.length;sm();}
function fp(){if(!fm.length)return;fi=(fi-1+fm.length)%fm.length;sm();}
function cf(){document.getElementById('fi').value='';fm=[];fi=-1;document.getElementById('fc').textContent='';document.querySelectorAll('tbody tr').forEach(function(r){r.classList.remove('ring');});}
window.onload=bd;"""

        report_html = (
            f"<!DOCTYPE html>\n<html lang=en>\n<head><meta charset=utf-8>"
            f"<title>HTML Compare Report</title>\n"
            f"<style>\n{CSS}\n</style>\n"
            f"<script>\n{JS}\n</script>\n"
            f"</head><body><div class=container>\n"
            f"<h1>&#128202; HTML Compare Report</h1>\n"
            f"<p class=meta>{summary_text} &nbsp;|&nbsp; Generated: {generated}</p>\n"
            f"<div class=filters>"
            f"<input id=tf type=text placeholder='Filter rows by any text...' oninput='af()'>"
            f"<label>Status:</label><select id=sf onchange='af()'><option value=''>\u2014 All \u2014</option></select>"
            f"<label>Parent&nbsp;Status:</label><select id=pf onchange='af()'><option value=''>\u2014 All \u2014</option></select>"
            f"<span class=count id=rc></span></div>\n"
            f"<div class=find-bar>"
            f"<span style='font-size:.82rem;color:#475569'>&#128269; Find:</span>"
            f"<input id=fi type=text placeholder='Find in visible rows...' onkeydown=\"if(event.key==='Enter')df()\">"
            f"<button class=btn-f onclick='df()'>Find</button>"
            f"<button class=btn-fn onclick='fp()'>&#8593; Prev</button>"
            f"<button class=btn-fn onclick='fn()'>Next &#8595;</button>"
            f"<button class=btn-cl onclick='cf()'>Clear</button>"
            f"<span class=mb id=fc></span></div>\n"
            f"<div class=table-wrap><table>"
            f"<thead><tr>{header_cells}</tr></thead>"
            f"<tbody>{rows_body}</tbody>"
            f"</table></div></div></body></html>"
        )

        with open(save_path, "w", encoding="utf-8") as handle:
            handle.write(report_html)
        messagebox.showinfo("Export Complete", f"Report saved to:\n{save_path}")

'''

start = content.index("    def _export_html_report")
end   = content.index("    def _on_method_change")
new_content = content[:start] + NEW_METHOD + "\n" + content[end:]
SRC.write_text(new_content, encoding="utf-8")
print(f"Done. Lines: {new_content.count(chr(10))}")

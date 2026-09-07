"""
Citation Pattern Extractor — Cite Types × Clients matrix report.

Mirrors ID Pattern Extractor structure: scan impact_config folders by type|client,
extract citation display patterns, and build a consolidated matrix HTML/CSV.
"""

from __future__ import annotations

import csv
import html
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.element_extractor import ElementExtractor
from core.id_pattern_extractor import IDPatternExtractor


class CitationPatternExtractor:
    """
    Scan IMPACT document folders, extract citation patterns per cite type,
    and generate a Cite Types × Clients matrix report.
    """

    CONTENT_HTML_GLOBS = ("*_original.html", "*_original.htm")
    CONTENT_XML_GLOB = "*_original.xml"

    def __init__(self):
        self.id_scanner = IDPatternExtractor()
        self.cite_extractor = ElementExtractor()

    def _find_content_file(self, folder: Path) -> Optional[Path]:
        """Prefer *_original.html, then *_original.xml (same folder naming as ID Pattern)."""
        folder = Path(folder)
        for pattern in self.CONTENT_HTML_GLOBS:
            files = list(folder.glob(pattern))
            if files:
                folder_name = folder.name
                for f in files:
                    if folder_name in f.stem:
                        return f
                return files[0]
        xml_files = list(folder.glob(self.CONTENT_XML_GLOB))
        if not xml_files:
            return None
        folder_name = folder.name
        for f in xml_files:
            if folder_name in f.stem:
                return f
        return xml_files[0]

    def scan_documents(
        self,
        root_path: Path,
        recursive: bool = True,
        type_filter: Optional[str] = None,
        client_filter: Optional[str] = None,
        progress_callback=None,
    ) -> Dict[str, List[Dict]]:
        """
        Reuse ID Pattern folder discovery, then attach a citation content file path.
        """
        documents_by_client = self.id_scanner.scan_documents(
            root_path,
            recursive=recursive,
            type_filter=type_filter,
            client_filter=client_filter,
            progress_callback=progress_callback,
        )

        filtered: Dict[str, List[Dict]] = {}
        for key, docs in documents_by_client.items():
            kept = []
            for doc in docs:
                folder = Path(doc["folder"])
                content = self._find_content_file(folder)
                if not content:
                    continue
                enriched = dict(doc)
                enriched["content_file"] = str(content)
                kept.append(enriched)
            if kept:
                filtered[key] = kept
        return filtered

    def build_matrix_data(
        self,
        documents_by_client: Dict[str, List[Dict]],
        cite_type: str = "All",
        progress_callback=None,
    ) -> Tuple[List[Dict], List[str], Dict, List[Dict], List[Dict]]:
        """
        Build matrix: rows = cite types, columns = clients,
        cells = pattern keys with counts (+ sample text).

        Returns (rows, clients, detail_data, cite_details, doc_metadata).
        """
        all_clients = set()
        for key in documents_by_client:
            parts = key.split("|", 1)
            if len(parts) == 2:
                all_clients.add(parts[1])
        client_keys = sorted(all_clients)

        # {cite_type: {client: {pattern_key: count}}}
        patterns_by_type_client: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )
        # {cite_type: {client: {pattern_key: sample_text}}}
        samples_by_type_client: Dict[str, Dict[str, Dict[str, str]]] = defaultdict(
            lambda: defaultdict(dict)
        )

        detail_data: Dict[str, Dict] = {}
        cite_details: List[Dict] = []
        doc_metadata: List[Dict] = []
        seq = 0

        flat_docs = []
        for key, docs in documents_by_client.items():
            parts = key.split("|", 1)
            if len(parts) != 2:
                continue
            _doc_type_val, client = parts
            for doc in docs:
                flat_docs.append((client, doc))

        total = len(flat_docs)
        for idx, (client, doc) in enumerate(flat_docs):
            if progress_callback:
                progress_callback(idx + 1, total, Path(doc.get("content_file", "")).name)

            doc_key = doc["folder"]
            doc_title = doc.get("doc_title", "") or os.path.basename(doc_key)
            content_file = Path(doc["content_file"])

            try:
                matches = self.cite_extractor.extract_bibr_citations(
                    content_file, cite_type=cite_type
                )
            except Exception as exc:
                detail_data[doc_key] = {
                    "doc_info": doc,
                    "matches": [],
                    "error": str(exc),
                }
                continue

            detail_data[doc_key] = {
                "doc_info": doc,
                "matches": matches,
                "error": "",
            }

            doc_metadata.append({
                "type": doc.get("doc_type", ""),
                "client": doc.get("client", ""),
                "identifier": doc.get("identifier", ""),
                "doc_title": doc_title,
                "folder": doc_key,
                "content_file": str(content_file),
            })

            # Matrix counts use all matches; detail rows = one per pattern_key per file
            file_pattern_counts: Dict[str, int] = defaultdict(int)
            file_pattern_first: Dict[str, Dict] = {}
            for match in matches:
                ct = (match.get("cite_type") or "unknown").lower()
                pattern = match.get("pattern_key") or "Bare Link Text"
                text = (match.get("text") or "").strip()
                subcategory = match.get("subcategory") or match.get("classification", "")

                patterns_by_type_client[ct][client][pattern] += 1
                if pattern not in samples_by_type_client[ct][client]:
                    samples_by_type_client[ct][client][pattern] = text[:120]

                detail_key = f"{ct}|{pattern}"
                file_pattern_counts[detail_key] += 1
                if detail_key not in file_pattern_first:
                    file_pattern_first[detail_key] = {
                        "document": doc_title,
                        "doc_type": doc.get("doc_type", "") or "",
                        "client": client,
                        "identifier": doc.get("identifier", "") or "",
                        "cite_type": ct,
                        "classification": subcategory,
                        "text": text,
                        "pattern": pattern,
                        "sample": (match.get("entire_citation") or match.get("html") or "")[:200],
                        "content_file": str(content_file),
                    }

            for detail_key, first in file_pattern_first.items():
                seq += 1
                cite_details.append({
                    "seq": seq,
                    "document": first["document"],
                    "doc_type": first["doc_type"],
                    "client": first["client"],
                    "identifier": first["identifier"],
                    "cite_type": first["cite_type"],
                    "classification": first["classification"],
                    "text": first["text"],
                    "pattern": first["pattern"],
                    "sample": first["sample"],
                    "content_file": first["content_file"],
                    "count": file_pattern_counts[detail_key],
                })

        all_cite_types = sorted(patterns_by_type_client.keys())
        rows = []
        for cite_type_row in all_cite_types:
            row: Dict[str, Any] = {"cite_type": cite_type_row}
            for client in client_keys:
                client_patterns = patterns_by_type_client[cite_type_row].get(client, {})
                if client_patterns:
                    sorted_patterns = sorted(
                        client_patterns.items(), key=lambda x: (-x[1], x[0])
                    )
                    samples = samples_by_type_client[cite_type_row].get(client, {})
                    row[client] = {
                        "patterns": [p[0] for p in sorted_patterns],
                        "counts": [p[1] for p in sorted_patterns],
                        "samples": [samples.get(p[0], "") for p in sorted_patterns],
                        "total_count": sum(client_patterns.values()),
                    }
                else:
                    row[client] = None
            rows.append(row)

        return rows, client_keys, detail_data, cite_details, doc_metadata

    def generate_html_report(
        self,
        root_path: str,
        doc_type: str,
        client_filter: str,
        cite_type: str,
        rows: List[Dict],
        clients: List[str],
        detail_data: Dict,
        cite_details: List[Dict],
        total_docs: int,
        doc_metadata: Optional[List[Dict]] = None,
    ) -> str:
        """Generate Citation Pattern Extraction Report HTML."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        folder_name = os.path.basename(root_path)
        total_cites = len(cite_details)
        cite_type_count = len(rows)

        header_cols = "<th>Cite Type</th>"
        for client in clients:
            header_cols += f"<th>{html.escape(client)}</th>"

        table_rows = ""
        for row in rows:
            cite_type_row = row.get("cite_type", "")
            tr = f'<tr><td class="element-type">{html.escape(cite_type_row)}</td>'
            for client in clients:
                cell_data = row.get(client)
                if cell_data and cell_data.get("patterns"):
                    patterns_html = ""
                    for i, (pattern, count) in enumerate(
                        zip(cell_data["patterns"], cell_data["counts"])
                    ):
                        count_display = (
                            f" <span class='pattern-count'>({count})</span>"
                            if len(cell_data["patterns"]) > 1 or count > 1
                            else f" <span class='pattern-count'>({count})</span>"
                        )
                        patterns_html += (
                            f'<code class="pattern">{html.escape(pattern)}</code>{count_display}'
                        )
                        if i < len(cell_data["patterns"]) - 1:
                            patterns_html += "<br>"
                    tr += f'<td class="multi-pattern">{patterns_html}</td>'
                else:
                    tr += '<td class="empty">—</td>'
            tr += "</tr>"
            table_rows += tr

        if not table_rows:
            table_rows = (
                f'<tr><td colspan="{1 + max(len(clients), 1)}" class="empty">'
                "No citation patterns found.</td></tr>"
            )

        detail_table_rows = ""
        for elem in cite_details:
            text_short = elem["text"][:40] + ("..." if len(elem["text"]) > 40 else "")
            doc_title = elem.get("document") or ""
            title_display = html.escape(
                doc_title[:35] + ("..." if len(doc_title) > 35 else "")
            )
            meta_type = html.escape(elem.get("doc_type") or "Unknown")
            meta_client = html.escape(elem.get("client") or "Unknown")
            meta_id = html.escape(elem.get("identifier") or "N/A")
            detail_table_rows += (
                "<tr>"
                f'<td>{elem["seq"]}</td>'
                f'<td class="doc-name" title="{html.escape(doc_title)}">'
                f'<div class="doc-title">{title_display}</div>'
                f'<div class="doc-meta">'
                f'<span class="meta-type">{meta_type}</span>'
                f'<span class="meta-sep">|</span>'
                f'<span class="meta-client">{meta_client}</span>'
                f'<span class="meta-sep">|</span>'
                f'<span class="meta-identifier">{meta_id}</span>'
                f"</div></td>"
                f'<td><span class="client-badge">{html.escape(elem["client"])}</span></td>'
                f'<td><code class="tag">{html.escape(elem["cite_type"])}</code></td>'
                f'<td><span class="area-badge">{html.escape(elem["classification"])}</span></td>'
                f'<td><code class="id-value">{html.escape(text_short)}</code></td>'
                f'<td><code class="pattern">{html.escape(elem["pattern"])}</code></td>'
                "</tr>"
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Citation Pattern Report - {html.escape(folder_name)}</title>
    <style>
        :root {{
            --bg-main: #0b0f19;
            --bg-card: #111827;
            --bg-code: #030712;
            --border-color: #374151;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --primary: #6366f1;
            --accent: #818cf8;
        }}
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg-main);
            color: var(--text-main);
            margin: 0;
            padding: 32px 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ margin: 0; color: var(--accent); font-size: 1.75rem; }}
        .meta {{ color: var(--text-muted); margin-top: 6px; font-size: 0.9rem; }}
        .timestamp {{
            display: inline-block; margin-top: 10px; padding: 4px 10px;
            background: var(--bg-card); border: 1px solid var(--border-color);
            border-radius: 6px; color: var(--text-muted); font-size: 0.85rem;
        }}
        .stats {{
            display: flex; flex-wrap: wrap; gap: 12px; margin: 20px 0;
        }}
        .stat-card {{
            background: var(--bg-card); border: 1px solid var(--border-color);
            border-radius: 8px; padding: 14px 18px; min-width: 140px;
        }}
        .stat-value {{ font-size: 1.4rem; font-weight: 700; color: var(--accent); }}
        .stat-label {{ font-size: 0.8rem; color: var(--text-muted); margin-top: 2px; }}
        .meta-sep {{ color: var(--text-muted); margin: 0 3px; }}
        .matrix-container, .detail-container {{
            background: var(--bg-card); border: 1px solid var(--border-color);
            border-radius: 10px; padding: 18px; margin-bottom: 24px; overflow-x: auto;
        }}
        .matrix-header h2, .detail-container h2 {{
            margin: 0 0 14px; font-size: 1.15rem; color: var(--accent);
        }}
        table {{
            width: 100%; border-collapse: collapse; font-size: 0.88rem;
        }}
        th, td {{
            padding: 10px 12px; border-bottom: 1px solid var(--border-color);
            text-align: left; vertical-align: top;
        }}
        th {{
            background: rgba(255,255,255,0.03); color: var(--text-muted);
            text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.04em;
            position: sticky; top: 0;
        }}
        .element-type {{ font-weight: 700; color: #a5b4fc; white-space: nowrap; }}
        .multi-pattern {{ line-height: 1.55; }}
        .pattern {{
            background: var(--bg-code); color: #34d399; padding: 2px 6px;
            border-radius: 4px; font-size: 0.8rem;
        }}
        .pattern-count {{ color: var(--text-muted); font-size: 0.78rem; }}
        .empty {{ color: var(--text-muted); text-align: center; }}
        .client-badge {{
            background: #1e3a5f; color: #7dd3fc; padding: 2px 8px;
            border-radius: 10px; font-size: 0.78rem;
        }}
        .area-badge {{
            background: #3b2f1e; color: #fbbf24; padding: 2px 8px;
            border-radius: 10px; font-size: 0.75rem;
        }}
        .tag {{ color: #c4b5fd; }}
        .id-value {{ color: #e2e8f0; }}
        .doc-name {{
            max-width: 260px;
            white-space: normal;
            line-height: 1.35;
        }}
        .doc-title {{
            font-weight: 600;
            color: var(--text-main);
        }}
        .doc-meta {{
            margin-top: 3px;
            font-size: 0.75rem;
            color: var(--text-muted);
            font-family: Consolas, 'Courier New', monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Citation Pattern Extraction Report</h1>
            <div class="meta">
                Root: <code>{html.escape(root_path)}</code> |
                Type: <strong>{html.escape(doc_type)}</strong> |
                Client filter: <strong>{html.escape(client_filter)}</strong> |
                Cite type: <strong>{html.escape(cite_type)}</strong>
            </div>
            <div class="timestamp">Generated: {timestamp}</div>
        </header>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{total_docs}</div>
                <div class="stat-label">Documents Scanned</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(clients)}</div>
                <div class="stat-label">Clients Found</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{cite_type_count}</div>
                <div class="stat-label">Cite Types</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_cites}</div>
                <div class="stat-label">Total Citations</div>
            </div>
        </div>

        <div class="matrix-container">
            <div class="matrix-header">
                <h2>Citation Pattern Matrix (Cite Types × Clients)</h2>
            </div>
            <table>
                <thead><tr>{header_cols}</tr></thead>
                <tbody>{table_rows}</tbody>
            </table>
        </div>

        <div class="detail-container">
            <h2>Cite-wise Consolidated Report</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Document</th>
                        <th>Client</th>
                        <th>Cite Type</th>
                        <th>Classification</th>
                        <th>Text</th>
                        <th>Pattern</th>
                    </tr>
                </thead>
                <tbody>
                    {detail_table_rows if detail_table_rows else '<tr><td colspan="7" class="empty">No citations found.</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

    def export_csv(self, rows: List[Dict], clients: List[str], output_path: Path) -> Path:
        """Export matrix to CSV (most frequent pattern per cell)."""
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Cite Type"] + clients)
            for row in rows:
                data_row = [row.get("cite_type", "")]
                for client in clients:
                    cell = row.get(client)
                    if cell and cell.get("patterns"):
                        pats = cell["patterns"]
                        counts = cell.get("counts") or []
                        parts = []
                        for i, p in enumerate(pats):
                            c = counts[i] if i < len(counts) else ""
                            parts.append(f"{p} ({c})" if c != "" else p)
                        data_row.append(" | ".join(parts))
                    else:
                        data_row.append("—")
                writer.writerow(data_row)
        return output_path

    def export_cite_csv(self, cite_details: List[Dict], output_path: Path) -> Path:
        """Export cite-wise detail CSV."""
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "#", "Document", "Client", "Cite Type", "Classification",
                "Text", "Pattern", "Count", "Sample",
            ])
            for elem in cite_details:
                writer.writerow([
                    elem["seq"],
                    elem["document"],
                    elem["client"],
                    elem["cite_type"],
                    elem["classification"],
                    elem["text"],
                    elem["pattern"],
                    elem.get("count", 1),
                    elem.get("sample", ""),
                ])
        return output_path

    def _write_type_reports(
        self,
        run_folder: Path,
        ts: str,
        root_path: str,
        doc_type: str,
        client_filter: str,
        cite_type: str,
        rows: List[Dict],
        clients: List[str],
        detail_data: Dict,
        cite_details: List[Dict],
        total_docs: int,
        doc_metadata: Optional[List[Dict]],
    ) -> Dict[str, str]:
        """Write HTML + CSVs for a single cite type. Returns paths dict."""
        cite_slug = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in cite_type.lower()
        ) or "all"
        html_report = self.generate_html_report(
            root_path,
            doc_type,
            client_filter,
            cite_type,
            rows,
            clients,
            detail_data,
            cite_details,
            total_docs,
            doc_metadata,
        )
        html_path = run_folder / f"citation_pattern_report_{cite_slug}_{ts}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_report)
        csv_path = run_folder / f"citation_pattern_matrix_{cite_slug}_{ts}.csv"
        self.export_csv(rows, clients, csv_path)
        cite_csv_path = run_folder / f"citation_pattern_cites_{cite_slug}_{ts}.csv"
        self.export_cite_csv(cite_details, cite_csv_path)
        return {
            "html_path": str(html_path),
            "csv_path": str(csv_path),
            "cite_csv_path": str(cite_csv_path),
            "cite_type": cite_type,
        }

    def run_extraction(
        self,
        root_path: str,
        output_dir: str,
        doc_type: str = "Books",
        client_filter: str = "All",
        cite_type: str = "All",
        recursive: bool = True,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """Full pipeline: scan → matrix → HTML + CSV (one report set per cite type)."""
        root_path_obj = Path(root_path)
        output_dir_obj = Path(output_dir)
        output_dir_obj.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_folder = output_dir_obj / f"citation_pattern_{ts}"
        run_folder.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback("scan", 0, 0, "Scanning for documents...")

        documents_by_client = self.scan_documents(
            root_path_obj,
            recursive=recursive,
            type_filter=doc_type,
            client_filter=client_filter,
            progress_callback=lambda cur, tot, name: (
                progress_callback("scan", cur, tot, name) if progress_callback else None
            ),
        )

        total_docs = sum(len(docs) for docs in documents_by_client.values())

        if progress_callback:
            progress_callback("analyze", 0, total_docs, "Analyzing citations...")

        # Always scan all types when filter is All, then split reports per type
        scan_filter = cite_type
        rows, clients, detail_data, cite_details, doc_metadata = self.build_matrix_data(
            documents_by_client,
            cite_type=scan_filter,
            progress_callback=lambda cur, tot, name: (
                progress_callback("analyze", cur, tot, name) if progress_callback else None
            ),
        )

        type_norm = (cite_type or "All").strip().lower()
        if type_norm == "all":
            cite_types = sorted({r.get("cite_type") for r in rows if r.get("cite_type")})
            if not cite_types:
                cite_types = ["all"]
        else:
            cite_types = [cite_type]

        if progress_callback:
            progress_callback("report", 0, max(len(cite_types), 1), "Generating reports...")

        per_type_reports = []
        primary = None
        for i, ct in enumerate(cite_types):
            if type_norm == "all" and ct != "all":
                type_rows = [r for r in rows if r.get("cite_type") == ct]
                type_details = [d for d in cite_details if d.get("cite_type") == ct]
            else:
                type_rows = rows
                type_details = cite_details
            paths = self._write_type_reports(
                run_folder,
                ts,
                root_path,
                doc_type,
                client_filter,
                ct,
                type_rows,
                clients,
                detail_data,
                type_details,
                total_docs,
                doc_metadata,
            )
            per_type_reports.append(paths)
            if primary is None:
                primary = paths
            if progress_callback:
                progress_callback("report", i + 1, len(cite_types), f"Wrote {ct} report")

        if progress_callback:
            progress_callback("complete", len(cite_types), len(cite_types), "Complete")

        primary = primary or {
            "html_path": "",
            "csv_path": "",
            "cite_csv_path": "",
        }
        return {
            "html_path": primary["html_path"],
            "csv_path": primary["csv_path"],
            "cite_csv_path": primary["cite_csv_path"],
            "run_folder": str(run_folder),
            "total_docs": total_docs,
            "clients": clients,
            "rows": rows,
            "cite_count": sum(d.get("count", 1) for d in cite_details),
            "per_type_reports": per_type_reports,
        }

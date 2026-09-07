import csv
import html
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.element_extractor import ElementExtractor


class DOIExtractor:
    """
    Core engine for DOI extraction from local XML/HTML files.

    Reuses ElementExtractor.scan_directory (the existing "extract elements
    from XML/HTML files" engine) with a fixed XPath covering the known
    DOI-bearing tag shapes, then normalizes and validates the DOI values
    and generates an HTML + CSV report.
    """

    DOI_XPATH = "//*[@pub-id-type='doi'] | //ext-link[@ext-link-type='doi']"
    DOI_VALIDATION_PATTERN = re.compile(r'^10\.\d{4,9}/\S+$')
    DOI_PREFIX_STRIP = (
        "https://doi.org/", "http://doi.org/",
        "https://dx.doi.org/", "http://dx.doi.org/", "doi:",
    )

    def __init__(self):
        self.element_extractor = ElementExtractor()

    @staticmethod
    def _extract_href(attributes: dict) -> Optional[str]:
        """Find an href-like attribute regardless of namespace prefix
        (lxml exposes xlink:href as '{http://www.w3.org/1999/xlink}href')."""
        for key, value in attributes.items():
            if key == "href" or key.endswith("}href"):
                return value
        return None

    def normalize_doi(self, raw_text: str, attributes: dict) -> Optional[str]:
        """Normalize a raw match into a bare DOI value, falling back to an
        href attribute (e.g. ext-link's xlink:href) when the text itself
        doesn't look like a DOI."""
        candidate = (raw_text or "").strip()
        if not candidate.lower().startswith("10."):
            href = self._extract_href(attributes)
            if href:
                candidate = href.strip()

        for prefix in self.DOI_PREFIX_STRIP:
            if candidate.lower().startswith(prefix):
                candidate = candidate[len(prefix):]
                break

        candidate = candidate.strip()
        return candidate or None

    def is_valid_doi(self, doi: str) -> bool:
        """Offline syntax check only (10.NNNN(N*)/suffix) -- no live resolution."""
        return bool(doi) and bool(self.DOI_VALIDATION_PATTERN.match(doi))

    def extract_dois_from_matches(self, matches: List[Dict]) -> List[Dict]:
        """Normalize raw parse_and_extract matches into deduped DOI records."""
        results = []
        seen = set()
        for match in matches:
            doi = self.normalize_doi(match.get("text", ""), match.get("attributes", {}))
            if not doi:
                continue
            key = (match.get("tag", ""), doi)
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "tag": match.get("tag", ""),
                "doi": doi,
                "valid": self.is_valid_doi(doi),
                "line": match.get("line", 0),
            })
        return results

    def scan_directory(self, dir_path, recursive: bool = True,
                       filename_filter: Optional[str] = None,
                       progress_callback=None) -> Tuple[Dict[str, Dict], int, int]:
        """
        Scan a directory for DOI-bearing tags, reusing
        ElementExtractor.scan_directory for the actual file walking/parsing.
        Returns (doi_results, total_dois, total_files) where doi_results is
        {abs_file_path: {"ok": bool, "dois": [...], "error": str}}.
        """
        scan_results, _total_matches, total_files = self.element_extractor.scan_directory(
            dir_path=dir_path,
            query_type="XPath",
            query_val=self.DOI_XPATH,
            recursive=recursive,
            filename_filter=filename_filter,
            progress_callback=progress_callback,
        )

        doi_results = {}
        total_dois = 0
        for file_path, data in scan_results.items():
            if not data.get("ok", True):
                doi_results[file_path] = {"ok": False, "error": data.get("error", ""), "dois": []}
                continue
            dois = self.extract_dois_from_matches(data.get("matches", []))
            doi_results[file_path] = {"ok": True, "dois": dois}
            total_dois += len(dois)

        # ElementExtractor.scan_directory only returns entries for files that
        # matched or errored -- zero-match files are silently omitted. Backfill
        # them here (as {"ok": True, "dois": []}) so "files without a DOI" can
        # be computed, reusing the same file-discovery/filter logic rather than
        # modifying ElementExtractor itself.
        for file_path in self._discover_all_files(dir_path, recursive, filename_filter):
            if file_path not in doi_results:
                doi_results[file_path] = {"ok": True, "dois": []}

        return doi_results, total_dois, total_files

    def _discover_all_files(self, dir_path, recursive: bool,
                            filename_filter: Optional[str]) -> List[str]:
        """Mirror ElementExtractor.scan_directory's file discovery so we know
        the full scanned file set, including zero-match files it omits."""
        dir_path = Path(dir_path)
        extensions = ['.xml', '.html', '.htm', '.xhtml']
        normalized_filter = filename_filter.strip() if filename_filter else ""
        if normalized_filter and normalized_filter.lower() != "none" and not any(
            char in normalized_filter for char in "*?[]"
        ):
            normalized_filter = f"*{normalized_filter}"

        pattern = "**/*" if recursive else "*"
        files = []
        for file in dir_path.glob(pattern):
            if not file.is_file() or file.suffix.lower() not in extensions:
                continue
            if normalized_filter and normalized_filter.lower() != "none" and not \
                    self.element_extractor._matches_filename_filter(file.name, normalized_filter):
                continue
            files.append(str(file.absolute()))
        return files

    def _summarize(self, doi_results: Dict[str, Dict]) -> Dict[str, int]:
        files_with_doi = 0
        files_without_doi = 0
        total_dois = 0
        invalid_doi_count = 0
        unique_dois = set()

        for data in doi_results.values():
            if not data.get("ok", True):
                continue
            dois = data.get("dois", [])
            if dois:
                files_with_doi += 1
            else:
                files_without_doi += 1
            for match in dois:
                total_dois += 1
                unique_dois.add(match["doi"])
                if not match["valid"]:
                    invalid_doi_count += 1

        return {
            "files_with_doi": files_with_doi,
            "files_without_doi": files_without_doi,
            "total_dois": total_dois,
            "unique_doi_count": len(unique_dois),
            "invalid_doi_count": invalid_doi_count,
        }

    def generate_html_report(self, target_path: str, doi_results: Dict[str, Dict],
                             total_files: int) -> str:
        """Generate a dark-theme HTML report: stat cards, a DOI match table,
        and a 'Files without a DOI' section."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target_name = os.path.basename(target_path)
        summary = self._summarize(doi_results)

        table_rows = ""
        files_without_doi = []
        for file_path, data in sorted(doi_results.items()):
            file_name = os.path.basename(file_path)
            if not data.get("ok", True):
                continue
            dois = data.get("dois", [])
            if not dois:
                files_without_doi.append(file_path)
                continue
            for match in dois:
                valid_label = "Yes" if match["valid"] else "No"
                valid_class = "valid-yes" if match["valid"] else "valid-no"
                table_rows += f"""
                <tr>
                    <td class="col-file" title="{html.escape(file_path)}">
                        <strong>{html.escape(file_name)}</strong>
                        <div class="file-path-sub">{html.escape(file_path)}</div>
                    </td>
                    <td><code class="tag">{html.escape(match['tag'])}</code></td>
                    <td><code class="doi-value">{html.escape(match['doi'])}</code></td>
                    <td class="{valid_class}">{valid_label}</td>
                    <td>{match['line']}</td>
                </tr>
                """

        if not table_rows:
            table_rows = '<tr><td colspan="5" class="no-data">No DOIs found matching the known tag shapes.</td></tr>'

        missing_rows = ""
        for file_path in sorted(files_without_doi):
            missing_rows += f'<li title="{html.escape(file_path)}">{html.escape(os.path.basename(file_path))}</li>'
        if not missing_rows:
            missing_rows = "<li class=\"no-data\">All scanned files contained at least one DOI.</li>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DOI Extraction Report - {html.escape(target_name)}</title>
    <style>
        :root {{
            --bg-main: #0b0f19;
            --bg-card: #111827;
            --bg-code: #030712;
            --border-color: #374151;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --accent: #818cf8;
            --success: #34d399;
            --error: #f87171;
        }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            margin: 0; padding: 0; line-height: 1.5;
        }}
        .container {{ max-width: 1300px; margin: 0 auto; padding: 40px 20px; }}
        header {{ border-bottom: 1px solid var(--border-color); padding-bottom: 24px; margin-bottom: 32px; }}
        h1 {{
            font-size: 2rem; font-weight: 800; margin: 0;
            background: linear-gradient(135deg, #a5b4fc, #6366f1, #38bdf8);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }}
        .subtitle {{ color: var(--text-muted); margin: 8px 0 0 0; }}
        .timestamp {{
            font-size: 0.9rem; color: var(--text-muted); background: var(--bg-card);
            padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border-color);
            display: inline-block; margin-top: 16px;
        }}
        .summary-stats {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px; margin-bottom: 32px;
        }}
        .stat-card {{
            background: var(--bg-card); border: 1px solid var(--border-color);
            border-radius: 12px; padding: 20px; text-align: center;
        }}
        .stat-label {{
            font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em;
            color: var(--text-muted); margin-bottom: 8px;
        }}
        .stat-value {{ font-size: 1.8rem; font-weight: 700; color: var(--accent); }}
        .matrix-container, .missing-container {{
            background: var(--bg-card); border: 1px solid var(--border-color);
            border-radius: 12px; overflow: hidden; margin-bottom: 32px;
        }}
        .matrix-header, .missing-header {{
            background: rgba(99, 102, 241, 0.1); padding: 16px 20px;
            border-bottom: 1px solid var(--border-color);
        }}
        .matrix-header h2, .missing-header h2 {{ margin: 0; font-size: 1.2rem; color: var(--accent); }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border-color); }}
        th {{
            background: rgba(255, 255, 255, 0.02); font-size: 0.8rem; text-transform: uppercase;
            letter-spacing: 0.05em; color: var(--text-muted); font-weight: 600;
        }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover td {{ background: rgba(255, 255, 255, 0.02); }}
        .col-file {{ max-width: 320px; }}
        .file-path-sub {{ font-size: 0.75rem; color: var(--text-muted); word-break: break-all; }}
        .tag {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; }}
        .doi-value {{ font-family: 'Consolas', monospace; background: var(--bg-code); color: var(--success); padding: 4px 8px; border-radius: 4px; }}
        .valid-yes {{ color: var(--success); font-weight: 600; }}
        .valid-no {{ color: var(--error); font-weight: 600; }}
        .no-data {{ color: var(--text-muted); text-align: center; }}
        .missing-container ul {{ list-style: none; margin: 0; padding: 16px 20px; columns: 3; }}
        .missing-container li {{ padding: 4px 0; color: var(--text-muted); }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>DOI Extraction Report</h1>
            <p class="subtitle">Scan Root: <strong>{html.escape(target_path)}</strong></p>
            <div class="timestamp">Generated: {timestamp}</div>
        </header>

        <div class="summary-stats">
            <div class="stat-card"><div class="stat-label">Files Scanned</div><div class="stat-value">{total_files}</div></div>
            <div class="stat-card"><div class="stat-label">Files With DOI</div><div class="stat-value">{summary['files_with_doi']}</div></div>
            <div class="stat-card"><div class="stat-label">Files Without DOI</div><div class="stat-value">{summary['files_without_doi']}</div></div>
            <div class="stat-card"><div class="stat-label">Total DOI Matches</div><div class="stat-value">{summary['total_dois']}</div></div>
            <div class="stat-card"><div class="stat-label">Unique DOIs</div><div class="stat-value">{summary['unique_doi_count']}</div></div>
            <div class="stat-card"><div class="stat-label">Invalid DOIs</div><div class="stat-value">{summary['invalid_doi_count']}</div></div>
        </div>

        <div class="matrix-container">
            <div class="matrix-header"><h2>DOI Matches</h2></div>
            <table>
                <thead><tr><th>File</th><th>Tag</th><th>DOI</th><th>Valid</th><th>Line</th></tr></thead>
                <tbody>{table_rows}</tbody>
            </table>
        </div>

        <div class="missing-container">
            <div class="missing-header"><h2>Files Without a DOI</h2></div>
            <ul>{missing_rows}</ul>
        </div>
    </div>
</body>
</html>
"""

    def export_csv(self, doi_results: Dict[str, Dict], output_path: Path) -> Path:
        """Export DOI matches to CSV: File, Tag, DOI, Valid, Line."""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["File", "Tag", "DOI", "Valid", "Line"])
            for file_path, data in sorted(doi_results.items()):
                if not data.get("ok", True):
                    continue
                for match in data.get("dois", []):
                    writer.writerow([
                        file_path, match["tag"], match["doi"],
                        "Yes" if match["valid"] else "No", match["line"],
                    ])
        return output_path

    def run_extraction(self, root_path: str, output_dir: str,
                       recursive: bool = True, filename_filter: Optional[str] = None,
                       progress_callback=None) -> Dict:
        """Run the full DOI extraction pipeline: scan, report, export."""
        output_dir_obj = Path(output_dir)
        output_dir_obj.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_folder = output_dir_obj / f"doi_extractor_{ts}"
        run_folder.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback("scan", 0, 0, "Scanning for DOIs...")

        doi_results, total_dois, total_files = self.scan_directory(
            root_path,
            recursive=recursive,
            filename_filter=filename_filter,
            progress_callback=lambda cur, tot, name: progress_callback("scan", cur, tot, name) if progress_callback else None,
        )

        if progress_callback:
            progress_callback("report", 0, 2, "Generating HTML report...")

        html_report = self.generate_html_report(root_path, doi_results, total_files)
        html_path = run_folder / f"doi_report_{ts}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_report)

        if progress_callback:
            progress_callback("report", 1, 2, "Generating CSV export...")

        csv_path = run_folder / f"doi_matches_{ts}.csv"
        self.export_csv(doi_results, csv_path)

        if progress_callback:
            progress_callback("complete", 2, 2, "Complete")

        summary = self._summarize(doi_results)

        return {
            "html_path": str(html_path),
            "csv_path": str(csv_path),
            "run_folder": str(run_folder),
            "total_files": total_files,
            "total_dois": summary["total_dois"],
            "files_with_doi": summary["files_with_doi"],
            "files_without_doi": summary["files_without_doi"],
            "unique_doi_count": summary["unique_doi_count"],
            "invalid_doi_count": summary["invalid_doi_count"],
        }

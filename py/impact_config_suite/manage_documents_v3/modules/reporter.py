"""Report generation module for summary reports."""
from __future__ import annotations

import csv
import html
from datetime import datetime
from pathlib import Path
from typing import Callable

from .. import config
from .database import DocumentDatabase
from .utils import Logger


class ReportManager:
    """Generates summary reports across all documents."""
    
    def __init__(
        self,
        database: DocumentDatabase,
        log_callback: Callable[[str], None] | None = None,
    ):
        self.db = database
        self.logger = Logger(
            database.project_path / config.LOG_FILE,
            console_callback=log_callback,
        )
    
    def generate_html_summary(self, output_path: Path = None) -> Path:
        """Generate HTML summary report.
        
        Args:
            output_path: Output file path (default: project/summary_report.html)
            
        Returns:
            Path to generated report
        """
        project_path = self.db.project_path
        if output_path is None:
            output_path = project_path / "summary_report.html"
        
        self.logger.info("Generating HTML summary report...")
        
        stats = self.db.get_statistics()
        data = self._build_summary_data()
        
        html_content = self._build_html_report(stats, data)
        
        output_path.write_text(html_content, encoding='utf-8')
        
        self.db.update_document("_meta", {"process.report_generated": True})
        self.db.save()
        
        self.logger.info(f"HTML report saved: {output_path}")
        return output_path
    
    def generate_csv(self, output_path: Path = None) -> Path:
        """Generate CSV summary report.
        
        Args:
            output_path: Output file path (default: project/summary_report.csv)
            
        Returns:
            Path to generated report
        """
        project_path = self.db.project_path
        if output_path is None:
            output_path = project_path / "summary_report.csv"
        
        self.logger.info("Generating CSV summary report...")
        
        data = self._build_summary_data()
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "DocID", "Organized", "Config Downloaded", "Compared",
                "Report Generated", "Error", "Last Step", "Retry Count"
            ])
            for row in data:
                writer.writerow([
                    row["docid"],
                    row["organized"],
                    row["config_downloaded"],
                    row["compared"],
                    row["report_generated"],
                    row["error"],
                    row["last_step"],
                    row["retry_count"],
                ])
        
        self.logger.info(f"CSV report saved: {output_path}")
        return output_path
    
    def generate_excel(self, output_path: Path = None) -> Path:
        """Generate Excel summary report.
        
        Note: This generates a CSV file with .xlsx extension for simplicity.
        Full Excel support would require openpyxl.
        
        Args:
            output_path: Output file path (default: project/summary_report.xlsx)
            
        Returns:
            Path to generated report
        """
        project_path = self.db.project_path
        if output_path is None:
            output_path = project_path / "summary_report.xlsx"
        
        self.logger.info("Generating Excel summary report...")
        
        # For now, generate CSV with xlsx extension
        # In production, use openpyxl for proper Excel format
        csv_path = output_path.with_suffix('.csv')
        self.generate_csv(csv_path)
        
        # Copy to xlsx extension
        import shutil
        shutil.copy(str(csv_path), str(output_path))
        
        self.logger.info(f"Excel report saved: {output_path}")
        return output_path
    
    def _build_summary_data(self) -> list[dict]:
        """Build summary data from database."""
        data = []
        for docid, doc in sorted(self.db.get_all().items()):
            if docid.startswith("_"):
                continue  # Skip meta entries
            
            process = doc.get("process", {})
            data.append({
                "docid": docid,
                "organized": process.get("organized", False),
                "config_downloaded": process.get("config_downloaded", False),
                "compared": process.get("compared", False),
                "report_generated": process.get("report_generated", False),
                "error": doc.get("error", ""),
                "last_step": doc.get("last_step", ""),
                "retry_count": doc.get("retry_count", 0),
            })
        return data
    
    def _build_html_report(self, stats: dict, data: list[dict]) -> str:
        """Build HTML report content."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_template = f"""<!DOCTYPE html>
<html>
<head>
    <title>Document Manager Summary Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: #f8fafc; }}
        h1 {{ color: #1e293b; }}
        .summary {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-box {{ background: #e0e7ff; padding: 15px; border-radius: 6px; text-align: center; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #4f46e5; }}
        .stat-label {{ font-size: 12px; color: #64748b; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
        th {{ background: #1e293b; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }}
        tr:hover {{ background: #f1f5f9; }}
        .status-yes {{ color: #10b981; font-weight: bold; }}
        .status-no {{ color: #94a3b8; }}
        .error {{ color: #ef4444; }}
        .timestamp {{ color: #64748b; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <h1>Document Manager Summary Report</h1>
    <div class="summary">
        <h2>Statistics</h2>
        <div class="stats">
            <div class="stat-box">
                <div class="stat-value">{stats['total']}</div>
                <div class="stat-label">Total Documents</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{stats['steps']['organized']}</div>
                <div class="stat-label">Organized</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{stats['steps']['config_downloaded']}</div>
                <div class="stat-label">Config Downloaded</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{stats['steps']['compared']}</div>
                <div class="stat-label">Compared</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{stats['with_errors']}</div>
                <div class="stat-label">With Errors</div>
            </div>
        </div>
    </div>
    
    <h2>Document Details</h2>
    <table>
        <tr>
            <th>DocID</th>
            <th>Organized</th>
            <th>Config</th>
            <th>Compared</th>
            <th>Report</th>
            <th>Status</th>
        </tr>
"""
        
        for row in data:
            organized = "✓" if row["organized"] else "✗"
            config = "✓" if row["config_downloaded"] else "✗"
            compared = "✓" if row["compared"] else "✗"
            report = "✓" if row["report_generated"] else "✗"
            
            organized_class = "status-yes" if row["organized"] else "status-no"
            config_class = "status-yes" if row["config_downloaded"] else "status-no"
            compared_class = "status-yes" if row["compared"] else "status-no"
            report_class = "status-yes" if row["report_generated"] else "status-no"
            
            if row["error"]:
                status = f'<span class="error">Error: {html.escape(str(row["error"])[:50])}</span>'
            else:
                status = '<span class="status-yes">OK</span>'
            
            html_template += f"""        <tr>
            <td><strong>{html.escape(row["docid"])}</strong></td>
            <td class="{organized_class}">{organized}</td>
            <td class="{config_class}">{config}</td>
            <td class="{compared_class}">{compared}</td>
            <td class="{report_class}">{report}</td>
            <td>{status}</td>
        </tr>
"""
        
        html_template += f"""    </table>
    <p class="timestamp">Generated: {timestamp}</p>
</body>
</html>"""
        
        return html_template

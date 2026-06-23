"""
Report builder for XML comparison.

This module provides the ReportBuilder class for orchestrating the report
generation pipeline with streaming write support.
"""

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Optional, TextIO, Callable

from .models import CompareResult, CompareOptions, CompareStatistics
from .statistics import StatisticsBuilder
from .html_renderer import HtmlTemplateRenderer


class ReportBuilder:
    """
    Orchestrates XML comparison report generation.
    
    Provides a pipeline that calculates statistics, renders HTML, and writes
the report to disk using streaming writes to minimize memory usage.
    """
    
    def __init__(self):
        """Initialize the report builder."""
        self._stats_builder = StatisticsBuilder()
        self._renderer = HtmlTemplateRenderer()
    
    def build_report(
        self,
        result: CompareResult,
        output_path: Path,
        use_streaming: bool = True
    ) -> Path:
        """
        Build and write the comparison report.
        
        Args:
            result: The CompareResult containing all diff data
            output_path: Path where the HTML report should be written
            use_streaming: If True, use streaming write to minimize memory
            
        Returns:
            Path: The path to the generated report file
        """
        # Ensure statistics are calculated
        if result.statistics.total_nodes == 0:
            result.statistics = self._stats_builder.build(result)
        
        # Generate output filename
        output_file = self._generate_filename(result, output_path)
        
        # Write report
        if use_streaming:
            self._write_report_streaming(result, output_file)
        else:
            self._write_report_buffered(result, output_file)
        
        return output_file
    
    def _generate_filename(self, result: CompareResult, output_dir: Path) -> Path:
        """
        Generate the report filename based on revised file and timestamp.
        
        Format: {xml_name}_compare_YYYYMMDD_HHMMSS.html
        
        Args:
            result: The CompareResult with file paths
            output_dir: Directory where the report should be saved
            
        Returns:
            Path: Full path to the output file
        """
        xml_name = result.revised_path.stem
        timestamp = result.generated_time.strftime('%Y%m%d_%H%M%S')
        filename = f"{xml_name}_compare_{timestamp}.html"
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        return output_dir / filename
    
    def _write_report_streaming(
        self,
        result: CompareResult,
        output_file: Path
    ) -> None:
        """
        Write the report using streaming output to minimize memory usage.
        
        Writes sections incrementally using Path.open("w") to avoid holding
        the full HTML string in memory.
        
        Args:
            result: The CompareResult containing all diff data
            output_file: Path to the output HTML file
        """
        css = self._renderer._get_css()
        js = self._renderer._get_js()
        
        with output_file.open("w", encoding="utf-8") as f:
            # Write HTML head
            self._write_header(f, result, css)
            
            # Write body start and sidebar
            self._write_sidebar(f, result)
            
            # Write main content start
            f.write('        <main class="main-content">\n')
            
            # Write each tab panel incrementally
            self._write_overview_tab(f, result)
            self._write_text_tab(f, result)
            self._write_formatting_tab(f, result)
            
            # Only write attribute tab if enabled
            if result.options.include_attributes or result.statistics.attribute_changes > 0:
                self._write_attribute_tab(f, result)
            
            self._write_structure_tab(f, result)
            self._write_full_compare_tab(f, result)
            self._write_statistics_tab(f, result)
            
            # Write footer and closing
            self._write_footer(f, result, js)
    
    def _write_report_buffered(
        self,
        result: CompareResult,
        output_file: Path
    ) -> None:
        """
        Write the report using buffered output (non-streaming).
        
        For smaller reports or when streaming is disabled.
        
        Args:
            result: The CompareResult containing all diff data
            output_file: Path to the output HTML file
        """
        html_content = self._renderer.render_report(result)
        
        with output_file.open("w", encoding="utf-8") as f:
            f.write(html_content)
    
    def _write_header(
        self,
        f: TextIO,
        result: CompareResult,
        css: str
    ) -> None:
        """Write the HTML document header."""
        f.write(f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XML Compare Report - {escape(result.revised_path.stem)}</title>
    <style>
{css}
    </style>
</head>
<body>
    <div class="app-container">
''')
    
    def _write_sidebar(
        self,
        f: TextIO,
        result: CompareResult
    ) -> None:
        """Write the sidebar navigation."""
        stats = result.statistics
        filename = result.revised_path.stem
        struct_total = stats.added_nodes + stats.deleted_nodes + stats.moved_nodes
        
        f.write(f'''<aside class="sidebar">
            <div class="sidebar-header">
                <h1>XML Compare Report</h1>
                <div class="subtitle">{escape(filename)}</div>
            </div>
            
            <div class="sidebar-section">
                <h3>Report Info</h3>
                <div class="info-block">
                    <div class="label">Generated</div>
                    <div class="value">{result.generated_time.strftime('%Y-%m-%d %H:%M')}</div>
                </div>
                <div class="info-block">
                    <div class="label">Original</div>
                    <div class="value">{escape(result.original_path.name)}</div>
                </div>
                <div class="info-block">
                    <div class="label">Revised</div>
                    <div class="value">{escape(result.revised_path.name)}</div>
                </div>
            </div>
            
            <div class="sidebar-section">
                <h3>Navigation</h3>
                <ul class="nav-list">
                    <li><a class="nav-link active" data-tab="tab-overview">Overview
                        <span class="count">{stats.total_differences}</span></a></li>
                    <li><a class="nav-link" data-tab="tab-text">Text Corrections
                        <span class="count">{stats.text_changes}</span></a></li>
                    <li><a class="nav-link" data-tab="tab-formatting">Formatting Only
                        <span class="count">{stats.format_changes}</span></a></li>
''')
        
        if result.options.include_attributes or stats.attribute_changes > 0:
            f.write(f'''                    <li><a class="nav-link" data-tab="tab-attributes">Attribute Changes
                        <span class="count">{stats.attribute_changes}</span></a></li>
''')
        
        f.write(f'''                    <li><a class="nav-link" data-tab="tab-structure">Structure Changes
                        <span class="count">{struct_total}</span></a></li>
                    <li><a class="nav-link" data-tab="tab-full">Full Compare
                        <span class="count">{stats.total_differences}</span></a></li>
                    <li><a class="nav-link" data-tab="tab-statistics">Statistics</a></li>
                </ul>
            </div>
        </aside>
''')
    
    def _write_overview_tab(
        self,
        f: TextIO,
        result: CompareResult
    ) -> None:
        """Write the Overview tab."""
        stats = result.statistics
        match_class = 'match-high' if stats.match_percentage >= 90 else ('match-medium' if stats.match_percentage >= 70 else 'match-low')
        
        f.write(f'''<div id="tab-overview" class="tab-panel active">
            <div class="content-header">
                <h2>Comparison Overview</h2>
                <div class="search-box">
                    <input type="text" id="searchInput" placeholder="Search changes...">
                    <div class="filter-buttons">
                        <button class="filter-btn active" data-filter="all">All</button>
                        <button class="filter-btn" data-filter="text">Text</button>
                        <button class="filter-btn" data-filter="format">Format</button>
                        <button class="filter-btn" data-filter="attribute">Attr</button>
                        <button class="filter-btn" data-filter="structure">Struct</button>
                    </div>
                </div>
            </div>
            
            <div class="cards-grid">
                <div class="stat-card {match_class}">
                    <div class="value">{stats.match_percentage:.1f}%</div>
                    <div class="label">Match Percentage</div>
                </div>
                <div class="stat-card text">
                    <div class="value">{stats.total_differences}</div>
                    <div class="label">Total Differences</div>
                </div>
                <div class="stat-card text">
                    <div class="value">{stats.text_changes}</div>
                    <div class="label">Text Changes</div>
                </div>
                <div class="stat-card format">
                    <div class="value">{stats.format_changes}</div>
                    <div class="label">Formatting Changes</div>
                </div>
                <div class="stat-card attribute">
                    <div class="value">{stats.attribute_changes}</div>
                    <div class="label">Attribute Changes</div>
                </div>
                <div class="stat-card structure">
                    <div class="value">{stats.added_nodes + stats.deleted_nodes + stats.moved_nodes}</div>
                    <div class="label">Structure Changes</div>
                </div>
            </div>
            
            <div class="diff-container">
                <div class="diff-header">
                    <h3>Quick Summary</h3>
                </div>
                <div style="padding: 20px;">
                    <p>This report compares two XML files and categorizes the differences into text corrections, 
                    formatting changes, attribute modifications, and structural changes.</p>
                    <p style="margin-top: 15px;">
                        <strong>Original:</strong> {escape(str(result.original_path))}<br>
                        <strong>Revised:</strong> {escape(str(result.revised_path))}<br>
                        <strong>Generated:</strong> {result.generated_time.strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                    <p style="margin-top: 15px;">
                        Use the sidebar navigation to explore specific categories of changes, 
                        or use the search box above to filter by content.
                    </p>
                </div>
            </div>
        </div>
''')
    
    def _write_text_tab(
        self,
        f: TextIO,
        result: CompareResult
    ) -> None:
        """Write the Text Corrections tab."""
        f.write('''<div id="tab-text" class="tab-panel">
            <div class="content-header">
                <h2>Text Corrections</h2>
                <div class="search-box">
                    <input type="text" id="searchInput-text" placeholder="Search text changes..." class="search-input-alt">
                </div>
            </div>
            <p style="margin-bottom: 20px; color: #666;">Side-by-side comparison of text content changes</p>
''')
        
        if not result.text_diffs:
            f.write(self._render_empty_state_html("No text corrections found", "The text content matches between the two files."))
        else:
            f.write(f'''<div class="diff-container">
                <div class="diff-header"><h3>{len(result.text_diffs)} Text Changes</h3></div>
''')
            
            for diff in result.text_diffs:
                inline_html = self._renderer._generate_inline_diff(diff.old_text, diff.new_text)
                f.write(f'''<div class="diff-row" data-category="text">
                    <div class="diff-side old">
                        <div class="diff-side-label">Original</div>
                        <div class="diff-path">{escape(diff.path)}</div>
                        <div class="diff-content">{escape(diff.old_text)}</div>
                    </div>
                    <div class="diff-side new">
                        <div class="diff-side-label">Revised</div>
                        <div class="diff-path">{escape(diff.path)}</div>
                        <div class="diff-content">{inline_html or escape(diff.new_text)}</div>
                    </div>
                </div>
''')
            
            f.write('</div>\n')
        
        f.write('</div>\n')
    
    def _write_formatting_tab(
        self,
        f: TextIO,
        result: CompareResult
    ) -> None:
        """Write the Formatting Changes tab."""
        f.write('''<div id="tab-formatting" class="tab-panel">
            <div class="content-header">
                <h2>Formatting Changes</h2>
                <div class="search-box">
                    <input type="text" id="searchInput-formatting" placeholder="Search formatting changes..." class="search-input-alt">
                </div>
            </div>
            <p style="margin-bottom: 20px; color: #666;">Tag and style changes without text modification</p>
''')
        
        if not result.format_diffs:
            f.write(self._render_empty_state_html("No formatting changes found", "The formatting and styling match between the two files."))
        else:
            f.write(f'''<div class="diff-container">
                <div class="diff-header"><h3>{len(result.format_diffs)} Formatting Changes</h3></div>
''')
            
            for diff in result.format_diffs:
                style_info = ""
                if diff.old_style or diff.new_style:
                    style_info = f"<br>Style: {escape(str(diff.old_style))} → {escape(str(diff.new_style))}"
                
                f.write(f'''<div class="diff-row formatting" data-category="format">
                    <div class="diff-side old">
                        <div class="diff-side-label">Original Tag</div>
                        <div class="diff-path">{escape(diff.path)}</div>
                        <div class="diff-content">
                            <strong>&lt;{escape(diff.old_tag)}&gt;</strong>
                            {style_info}
                            <br><br>
                            {escape(diff.content[:200])}{"..." if len(diff.content) > 200 else ""}
                        </div>
                    </div>
                    <div class="diff-side new">
                        <div class="diff-side-label">New Tag</div>
                        <div class="diff-path">{escape(diff.path)}</div>
                        <div class="diff-content">
                            <strong>&lt;{escape(diff.new_tag)}&gt;</strong>
                            {style_info}
                            <br><br>
                            {escape(diff.content[:200])}{"..." if len(diff.content) > 200 else ""}
                        </div>
                    </div>
                </div>
''')
            
            f.write('</div>\n')
        
        f.write('</div>\n')
    
    def _write_attribute_tab(
        self,
        f: TextIO,
        result: CompareResult
    ) -> None:
        """Write the Attribute Changes tab."""
        f.write('''<div id="tab-attributes" class="tab-panel">
            <div class="content-header">
                <h2>Attribute Changes</h2>
                <div class="search-box">
                    <input type="text" id="searchInput-attributes" placeholder="Search attribute changes..." class="search-input-alt">
                </div>
            </div>
            <p style="margin-bottom: 20px; color: #666;">Differences in element attributes</p>
''')
        
        if not result.attribute_diffs:
            f.write(self._render_empty_state_html("No attribute changes found", "The element attributes match between the two files."))
        else:
            f.write(f'''<div class="diff-container">
                <div class="diff-header"><h3>{len(result.attribute_diffs)} Attribute Changes</h3></div>
                <table class="attr-table">
                    <thead><tr><th>Element</th><th>Path</th><th>Attribute</th><th>Old Value</th><th>New Value</th></tr></thead>
                    <tbody>
''')
            
            for diff in result.attribute_diffs:
                old_val = escape(str(diff.old_value)) if diff.old_value is not None else "<em>(none)</em>"
                new_val = escape(str(diff.new_value)) if diff.new_value is not None else "<em>(none)</em>"
                
                f.write(f'''<tr data-category="attribute">
                            <td><code>{escape(diff.element_tag)}</code></td>
                            <td><code>{escape(diff.path)}</code></td>
                            <td>{escape(diff.attribute_name)}</td>
                            <td class="attr-old">{old_val}</td>
                            <td class="attr-new">{new_val}</td>
                        </tr>
''')
            
            f.write('''</tbody></table>
            </div>
''')
        
        f.write('</div>\n')
    
    def _write_structure_tab(
        self,
        f: TextIO,
        result: CompareResult
    ) -> None:
        """Write the Structure Changes tab."""
        f.write('''<div id="tab-structure" class="tab-panel">
            <div class="content-header">
                <h2>Structure Changes</h2>
                <div class="search-box">
                    <input type="text" id="searchInput-structure" placeholder="Search structure changes..." class="search-input-alt">
                </div>
            </div>
            <p style="margin-bottom: 20px; color: #666;">Added, deleted, and moved elements</p>
''')
        
        if not result.structure_diffs:
            f.write(self._render_empty_state_html("No structure changes found", "The document structure matches between the two files."))
        else:
            f.write(f'''<div class="diff-container">
                <div class="diff-header"><h3>{len(result.structure_diffs)} Structure Changes</h3></div>
''')
            
            for diff in result.structure_diffs:
                move_info = ""
                if diff.change_type == 'moved' and diff.old_path:
                    move_info = f'<div style="font-size: 0.8rem; color: #666; margin-top: 5px;">From: {escape(diff.old_path)}</div>'
                
                f.write(f'''<div class="structure-item" data-category="structure">
                    <span class="structure-badge {diff.change_type}">{diff.change_type}</span>
                    <div class="structure-content">
                        <div class="structure-tag">&lt;{escape(diff.element_tag)}&gt;</div>
                        <div class="diff-path" style="margin-bottom: 5px;">{escape(diff.path)}</div>
                        <div class="structure-preview">{escape(diff.element_preview[:150])}{"..." if len(diff.element_preview) > 150 else ""}</div>
                        {move_info}
                    </div>
                </div>
''')
            
            f.write('</div>\n')
        
        f.write('</div>\n')
    
    def _write_full_compare_tab(
        self,
        f: TextIO,
        result: CompareResult
    ) -> None:
        """Write the Full Compare tab."""
        f.write('''<div id="tab-full" class="tab-panel">
            <div class="content-header">
                <h2>Full Comparison</h2>
                <div class="search-box">
                    <input type="text" id="searchInput-full" placeholder="Search all changes..." class="search-input-alt">
                </div>
            </div>
            <p style="margin-bottom: 20px; color: #666;">Complete list of all differences</p>
''')
        
        all_diffs = result.get_all_diffs()
        
        if not all_diffs:
            f.write(self._render_empty_state_html("No differences found", "The files are identical."))
        else:
            f.write(f'''<div class="diff-container">
                <div class="diff-header"><h3>All Changes ({len(all_diffs)} total)</h3></div>
                <ul class="details-list">
''')
            
            # Combine and categorize all diffs
            for diff in result.text_diffs:
                content = f"Old: {diff.old_text[:100]}...\nNew: {diff.new_text[:100]}..."
                f.write(f'''<li class="details-item" data-category="text">
                    <div class="details-summary" aria-expanded="false">
                        <span>{escape(diff.path)}</span>
                        <span class="details-type text">text</span>
                    </div>
                    <div class="details-content" style="display: none;">
                        <pre>{escape(content)}</pre>
                    </div>
                </li>
''')
            
            for diff in result.format_diffs:
                content = f"Tag: {diff.old_tag} → {diff.new_tag}\nContent: {diff.content[:100]}..."
                f.write(f'''<li class="details-item" data-category="format">
                    <div class="details-summary" aria-expanded="false">
                        <span>{escape(diff.path)}</span>
                        <span class="details-type format">format</span>
                    </div>
                    <div class="details-content" style="display: none;">
                        <pre>{escape(content)}</pre>
                    </div>
                </li>
''')
            
            for diff in result.attribute_diffs:
                content = f"Element: {diff.element_tag}\nAttr: {diff.attribute_name}\n{diff.old_value} → {diff.new_value}"
                f.write(f'''<li class="details-item" data-category="attribute">
                    <div class="details-summary" aria-expanded="false">
                        <span>{escape(diff.path)}</span>
                        <span class="details-type attribute">attribute</span>
                    </div>
                    <div class="details-content" style="display: none;">
                        <pre>{escape(content)}</pre>
                    </div>
                </li>
''')
            
            for diff in result.structure_diffs:
                content = f"Tag: {diff.element_tag}\n{diff.element_preview[:100]}..."
                change_label = diff.change_type.title()
                f.write(f'''<li class="details-item" data-category="structure">
                    <div class="details-summary" aria-expanded="false">
                        <span>{escape(diff.path)}</span>
                        <span class="details-type structure">{change_label}</span>
                    </div>
                    <div class="details-content" style="display: none;">
                        <pre>{escape(content)}</pre>
                    </div>
                </li>
''')
            
            f.write('''</ul>
            </div>
''')
        
        f.write('</div>\n')
    
    def _write_statistics_tab(
        self,
        f: TextIO,
        result: CompareResult
    ) -> None:
        """Write the Statistics tab."""
        stats = result.statistics
        
        total = stats.total_differences or 1
        text_pct = (stats.text_changes / total) * 100 if total else 0
        format_pct = (stats.format_changes / total) * 100 if total else 0
        attr_pct = (stats.attribute_changes / total) * 100 if total else 0
        struct_pct = ((stats.added_nodes + stats.deleted_nodes + stats.moved_nodes) / total) * 100 if total else 0
        
        f.write('''<div id="tab-statistics" class="tab-panel">
            <div class="content-header">
                <h2>Statistics Dashboard</h2>
            </div>
            <p style="margin-bottom: 20px; color: #666;">Detailed breakdown of comparison metrics</p>
            
            <div class="stats-dashboard">
                <div class="stats-section">
                    <h3>Changes Breakdown</h3>
''')
        
        if stats.text_changes > 0:
            f.write(f'''<div class="stats-bar">
                        <div class="stats-bar-label">Text Changes</div>
                        <div class="stats-bar-track"><div class="stats-bar-fill text" style="width: {text_pct}%"></div></div>
                        <div class="stats-bar-value">{stats.text_changes}</div>
                    </div>
''')
        
        if stats.format_changes > 0:
            f.write(f'''<div class="stats-bar">
                        <div class="stats-bar-label">Formatting</div>
                        <div class="stats-bar-track"><div class="stats-bar-fill format" style="width: {format_pct}%"></div></div>
                        <div class="stats-bar-value">{stats.format_changes}</div>
                    </div>
''')
        
        if stats.attribute_changes > 0:
            f.write(f'''<div class="stats-bar">
                        <div class="stats-bar-label">Attributes</div>
                        <div class="stats-bar-track"><div class="stats-bar-fill attribute" style="width: {attr_pct}%"></div></div>
                        <div class="stats-bar-value">{stats.attribute_changes}</div>
                    </div>
''')
        
        struct_total = stats.added_nodes + stats.deleted_nodes + stats.moved_nodes
        if struct_total > 0:
            f.write(f'''<div class="stats-bar">
                        <div class="stats-bar-label">Structure</div>
                        <div class="stats-bar-track"><div class="stats-bar-fill structure" style="width: {struct_pct}%"></div></div>
                        <div class="stats-bar-value">{struct_total}</div>
                    </div>
''')
        
        f.write('''</div>
                
                <div class="stats-section">
                    <h3>Structure Details</h3>
''')
        
        f.write(f'''<div class="stats-bar">
                        <div class="stats-bar-label">Added</div>
                        <div class="stats-bar-track"><div class="stats-bar-fill match" style="width: 100%"></div></div>
                        <div class="stats-bar-value">{stats.added_nodes}</div>
                    </div>
                    <div class="stats-bar">
                        <div class="stats-bar-label">Deleted</div>
                        <div class="stats-bar-track"><div class="stats-bar-fill text" style="width: 100%"></div></div>
                        <div class="stats-bar-value">{stats.deleted_nodes}</div>
                    </div>
                    <div class="stats-bar">
                        <div class="stats-bar-label">Moved</div>
                        <div class="stats-bar-track"><div class="stats-bar-fill format" style="width: 100%"></div></div>
                        <div class="stats-bar-value">{stats.moved_nodes}</div>
                    </div>
                </div>
                
                <div class="stats-section">
                    <h3>Match Analysis</h3>
''')
        
        match_class = 'match-high' if stats.match_percentage >= 90 else ('match-medium' if stats.match_percentage >= 70 else 'match-low')
        f.write(f'''<div class="stat-card {match_class}">
                        <div class="value">{stats.match_percentage:.2f}%</div>
                        <div class="label">Overall Match</div>
                    </div>
                    <p style="margin-top: 15px; color: #666;">
                        Based on approximately {stats.total_nodes} total nodes analyzed.
                    </p>
                </div>
            </div>
        </div>
''')
    
    def _write_footer(
        self,
        f: TextIO,
        result: CompareResult,
        js: str
    ) -> None:
        """Write the report footer and closing tags."""
        f.write(f'''
            <footer class="report-footer">
                <p>Generated by XML Compare on {result.generated_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Match: {result.statistics.match_percentage:.2f}% | Differences: {result.statistics.total_differences}</p>
            </footer>
        </main>
    </div>
    
    <script>
{js}
    </script>
</body>
</html>''')
    
    def _render_empty_state_html(self, title: str, message: str) -> str:
        """Render an empty state as HTML string."""
        return f'''<div class="empty-state">
            <div class="empty-state-icon">✓</div>
            <h3>{title}</h3>
            <p>{message}</p>
        </div>
'''

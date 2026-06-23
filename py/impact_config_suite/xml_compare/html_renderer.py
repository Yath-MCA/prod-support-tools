"""
HTML template renderer for XML comparison reports.

Generates self-contained HTML reports with inline CSS and JavaScript,
no external CDN dependencies required.
"""

from datetime import datetime
from difflib import SequenceMatcher
from html import escape
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import (
    CompareResult,
    CompareOptions,
    CompareStatistics,
    TextDiff,
    FormatDiff,
    AttributeDiff,
    StructureDiff,
    DiffType
)


class HtmlTemplateRenderer:
    """
    Renders XML comparison results as self-contained HTML.
    
    Generates a single HTML file with all CSS and JavaScript embedded,
    featuring sidebar navigation, tab panels, and client-side filtering.
    """
    
    # Color constants per spec
    COLOR_DELETED_BG = "#ffebee"
    COLOR_DELETED_TEXT = "#c62828"
    COLOR_INSERTED_BG = "#e8f5e9"
    COLOR_INSERTED_TEXT = "#2e7d32"
    COLOR_FORMATTING = "#1976d2"
    COLOR_ATTRIBUTE_OLD = "#ff9800"
    COLOR_ATTRIBUTE_NEW = "#4caf50"
    
    def __init__(self):
        """Initialize the HTML template renderer."""
        self._css_cache: Optional[str] = None
        self._js_cache: Optional[str] = None
    
    def _get_css(self) -> str:
        """Generate inline CSS styles."""
        if self._css_cache is None:
            self._css_cache = self._generate_css()
        return self._css_cache
    
    def _get_js(self) -> str:
        """Generate inline JavaScript."""
        if self._js_cache is None:
            self._js_cache = self._generate_js()
        return self._js_cache
    
    def _generate_css(self) -> str:
        """Generate the CSS styles for the report."""
        return """
        :root {
            --color-bg: #fafafa;
            --color-surface: #ffffff;
            --color-text: #212121;
            --color-text-secondary: #757575;
            --color-border: #e0e0e0;
            --color-sidebar-bg: #263238;
            --color-sidebar-text: #eceff1;
            --color-sidebar-hover: #37474f;
            --color-primary: #1976d2;
            --color-primary-light: #bbdefb;
            --color-accent: #ff4081;
            --color-deleted-bg: #ffebee;
            --color-deleted-text: #c62828;
            --color-inserted-bg: #e8f5e9;
            --color-inserted-text: #2e7d32;
            --color-formatting: #1976d2;
            --color-attribute-old: #ff9800;
            --color-attribute-new: #4caf50;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--color-bg);
            color: var(--color-text);
            line-height: 1.6;
        }
        
        /* Layout */
        .app-container {
            display: flex;
            min-height: 100vh;
        }
        
        /* Sidebar */
        .sidebar {
            width: 280px;
            background: var(--color-sidebar-bg);
            color: var(--color-sidebar-text);
            position: fixed;
            height: 100vh;
            overflow-y: auto;
            padding: 20px;
        }
        
        .sidebar-header {
            border-bottom: 1px solid var(--color-sidebar-hover);
            padding-bottom: 15px;
            margin-bottom: 20px;
        }
        
        .sidebar-header h1 {
            font-size: 1.25rem;
            margin-bottom: 5px;
        }
        
        .sidebar-header .subtitle {
            font-size: 0.85rem;
            color: #90a4ae;
        }
        
        .sidebar-section {
            margin-bottom: 25px;
        }
        
        .sidebar-section h3 {
            font-size: 0.75rem;
            text-transform: uppercase;
            color: #90a4ae;
            margin-bottom: 10px;
            letter-spacing: 0.5px;
        }
        
        .info-block {
            background: var(--color-sidebar-hover);
            padding: 10px;
            border-radius: 4px;
            font-size: 0.85rem;
            margin-bottom: 8px;
        }
        
        .info-block .label {
            color: #90a4ae;
            font-size: 0.75rem;
            margin-bottom: 2px;
        }
        
        .info-block .value {
            word-break: break-all;
        }
        
        /* Navigation */
        .nav-list {
            list-style: none;
        }
        
        .nav-list li {
            margin-bottom: 2px;
        }
        
        .nav-link {
            display: flex;
            align-items: center;
            padding: 10px 12px;
            color: var(--color-sidebar-text);
            text-decoration: none;
            border-radius: 4px;
            transition: background 0.2s;
            cursor: pointer;
        }
        
        .nav-link:hover {
            background: var(--color-sidebar-hover);
        }
        
        .nav-link.active {
            background: var(--color-primary);
        }
        
        .nav-link .count {
            margin-left: auto;
            background: var(--color-sidebar-hover);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
        }
        
        .nav-link.active .count {
            background: rgba(255,255,255,0.2);
        }
        
        /* Main Content */
        .main-content {
            margin-left: 280px;
            flex: 1;
            padding: 30px;
        }
        
        /* Tab Panels */
        .tab-panel {
            display: none;
        }
        
        .tab-panel.active {
            display: block;
        }
        
        /* Header & Search */
        .content-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--color-border);
        }
        
        .content-header h2 {
            font-size: 1.5rem;
            font-weight: 500;
        }
        
        .search-box {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .search-box input {
            padding: 8px 12px;
            border: 1px solid var(--color-border);
            border-radius: 4px;
            font-size: 0.9rem;
            width: 250px;
        }
        
        .search-box input:focus {
            outline: none;
            border-color: var(--color-primary);
        }
        
        .filter-buttons {
            display: flex;
            gap: 5px;
        }
        
        .filter-btn {
            padding: 6px 12px;
            border: 1px solid var(--color-border);
            background: var(--color-surface);
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
            transition: all 0.2s;
        }
        
        .filter-btn:hover, .filter-btn.active {
            background: var(--color-primary);
            color: white;
            border-color: var(--color-primary);
        }
        
        /* Cards */
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }
        
        .stat-card {
            background: var(--color-surface);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .stat-card .value {
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .stat-card .label {
            font-size: 0.9rem;
            color: var(--color-text-secondary);
        }
        
        .stat-card.match-high .value { color: var(--color-inserted-text); }
        .stat-card.match-medium .value { color: var(--color-attribute-old); }
        .stat-card.match-low .value { color: var(--color-deleted-text); }
        .stat-card.text .value { color: var(--color-deleted-text); }
        .stat-card.format .value { color: var(--color-formatting); }
        .stat-card.attribute .value { color: var(--color-attribute-old); }
        .stat-card.structure .value { color: #9c27b0; }
        
        /* Diff Tables */
        .diff-container {
            background: var(--color-surface);
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .diff-header {
            padding: 15px 20px;
            border-bottom: 1px solid var(--color-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .diff-header h3 {
            font-size: 1.1rem;
            font-weight: 500;
        }
        
        .diff-row {
            display: flex;
            border-bottom: 1px solid var(--color-border);
        }
        
        .diff-row:last-child {
            border-bottom: none;
        }
        
        .diff-row.hidden {
            display: none;
        }
        
        .diff-side {
            flex: 1;
            padding: 15px;
            overflow-x: auto;
        }
        
        .diff-side.old {
            background: var(--color-deleted-bg);
            border-right: 1px solid var(--color-border);
        }
        
        .diff-side.new {
            background: var(--color-inserted-bg);
        }
        
        .diff-side-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            color: var(--color-text-secondary);
            margin-bottom: 8px;
            font-weight: 600;
        }
        
        .diff-path {
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.8rem;
            color: var(--color-text-secondary);
            margin-bottom: 15px;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 4px;
            word-break: break-all;
        }
        
        .diff-content {
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9rem;
            line-height: 1.5;
            white-space: pre-wrap;
            word-break: break-word;
        }
        
        /* Inline diff highlighting */
        .diff-delete {
            background: var(--color-deleted-bg);
            color: var(--color-deleted-text);
            text-decoration: line-through;
            padding: 1px 2px;
            border-radius: 2px;
        }
        
        .diff-insert {
            background: var(--color-inserted-bg);
            color: var(--color-inserted-text);
            font-weight: bold;
            padding: 1px 2px;
            border-radius: 2px;
        }
        
        /* Formatting diff specific */
        .diff-row.formatting .diff-side.old {
            background: #e3f2fd;
        }
        
        .diff-row.formatting .diff-side.new {
            background: #e3f2fd;
        }
        
        .diff-row.formatting .diff-delete,
        .diff-row.formatting .diff-insert {
            background: #bbdefb;
            color: var(--color-formatting);
        }
        
        /* Attribute diff table */
        .attr-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .attr-table th,
        .attr-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid var(--color-border);
        }
        
        .attr-table th {
            background: #f5f5f5;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            color: var(--color-text-secondary);
        }
        
        .attr-table tr:hover {
            background: #fafafa;
        }
        
        .attr-old {
            color: var(--color-attribute-old);
            font-weight: 500;
        }
        
        .attr-new {
            color: var(--color-attribute-new);
            font-weight: 500;
        }
        
        /* Structure diff */
        .structure-item {
            padding: 15px 20px;
            border-bottom: 1px solid var(--color-border);
            display: flex;
            align-items: flex-start;
            gap: 15px;
        }
        
        .structure-item:last-child {
            border-bottom: none;
        }
        
        .structure-badge {
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .structure-badge.added {
            background: var(--color-inserted-bg);
            color: var(--color-inserted-text);
        }
        
        .structure-badge.deleted {
            background: var(--color-deleted-bg);
            color: var(--color-deleted-text);
        }
        
        .structure-badge.moved {
            background: #fff3e0;
            color: #e65100;
        }
        
        .structure-content {
            flex: 1;
        }
        
        .structure-tag {
            font-family: monospace;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .structure-preview {
            font-size: 0.85rem;
            color: var(--color-text-secondary);
            font-family: monospace;
            max-height: 100px;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        /* Full compare details */
        .details-list {
            list-style: none;
        }
        
        .details-item {
            margin-bottom: 10px;
            border: 1px solid var(--color-border);
            border-radius: 4px;
            overflow: hidden;
        }
        
        .details-summary {
            padding: 12px 15px;
            background: #f5f5f5;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .details-summary:hover {
            background: #eeeeee;
        }
        
        .details-type {
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .details-type.text { background: var(--color-deleted-bg); color: var(--color-deleted-text); }
        .details-type.format { background: #e3f2fd; color: var(--color-formatting); }
        .details-type.attribute { background: #fff3e0; color: #e65100; }
        .details-type.structure { background: #f3e5f5; color: #7b1fa2; }
        
        .details-content {
            padding: 15px;
            background: var(--color-surface);
        }
        
        .details-content pre {
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.85rem;
            background: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            white-space: pre-wrap;
        }
        
        /* Statistics dashboard */
        .stats-dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .stats-section {
            background: var(--color-surface);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .stats-section h3 {
            font-size: 1rem;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--color-border);
        }
        
        .stats-bar {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .stats-bar-label {
            width: 150px;
            font-size: 0.9rem;
        }
        
        .stats-bar-track {
            flex: 1;
            height: 20px;
            background: #f5f5f5;
            border-radius: 10px;
            overflow: hidden;
            margin: 0 10px;
        }
        
        .stats-bar-fill {
            height: 100%;
            border-radius: 10px;
            transition: width 0.3s ease;
        }
        
        .stats-bar-fill.text { background: var(--color-deleted-text); }
        .stats-bar-fill.format { background: var(--color-formatting); }
        .stats-bar-fill.attribute { background: var(--color-attribute-old); }
        .stats-bar-fill.structure { background: #9c27b0; }
        .stats-bar-fill.match { background: var(--color-inserted-text); }
        
        .stats-bar-value {
            width: 50px;
            text-align: right;
            font-weight: 600;
        }
        
        /* Empty state */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: var(--color-text-secondary);
        }
        
        .empty-state-icon {
            font-size: 3rem;
            margin-bottom: 15px;
        }
        
        .empty-state h3 {
            font-size: 1.25rem;
            margin-bottom: 10px;
            color: var(--color-text);
        }
        
        /* Footer */
        .report-footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--color-border);
            text-align: center;
            font-size: 0.85rem;
            color: var(--color-text-secondary);
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .sidebar {
                width: 100%;
                position: relative;
                height: auto;
            }
            
            .main-content {
                margin-left: 0;
            }
            
            .app-container {
                flex-direction: column;
            }
            
            .cards-grid {
                grid-template-columns: 1fr;
            }
            
            .diff-row {
                flex-direction: column;
            }
            
            .diff-side.old {
                border-right: none;
                border-bottom: 1px solid var(--color-border);
            }
        }
        """.strip()
    
    def _generate_js(self) -> str:
        """Generate the JavaScript for the report."""
        return """
        (function() {
            // Tab switching
            function showTab(tabId) {
                // Hide all tabs
                document.querySelectorAll('.tab-panel').forEach(function(panel) {
                    panel.classList.remove('active');
                });
                
                // Show selected tab
                var selectedPanel = document.getElementById(tabId);
                if (selectedPanel) {
                    selectedPanel.classList.add('active');
                }
                
                // Update nav links
                document.querySelectorAll('.nav-link').forEach(function(link) {
                    link.classList.remove('active');
                    if (link.getAttribute('data-tab') === tabId) {
                        link.classList.add('active');
                    }
                });
                
                // Store current tab
                localStorage.setItem('xmlCompareActiveTab', tabId);
            }
            
            // Initialize tab navigation
            document.querySelectorAll('.nav-link').forEach(function(link) {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    var tabId = this.getAttribute('data-tab');
                    if (tabId) {
                        showTab(tabId);
                    }
                });
            });
            
            // Restore last active tab
            var savedTab = localStorage.getItem('xmlCompareActiveTab');
            if (savedTab && document.getElementById(savedTab)) {
                showTab(savedTab);
            }
            
            // Search functionality
            var searchInput = document.getElementById('searchInput');
            if (searchInput) {
                var searchTimeout;
                searchInput.addEventListener('input', function() {
                    clearTimeout(searchTimeout);
                    searchTimeout = setTimeout(function() {
                        performSearch(searchInput.value);
                    }, 150);
                });
            }
            
            function performSearch(query) {
                query = query.toLowerCase().trim();
                
                // Get all diff rows
                var allRows = document.querySelectorAll('[data-category]');
                
                allRows.forEach(function(row) {
                    if (!query) {
                        // Show all if no query
                        row.classList.remove('hidden');
                        return;
                    }
                    
                    // Search in text content
                    var text = row.textContent.toLowerCase();
                    if (text.indexOf(query) !== -1) {
                        row.classList.remove('hidden');
                    } else {
                        row.classList.add('hidden');
                    }
                });
            }
            
            // Category filtering
            var activeFilter = 'all';
            
            document.querySelectorAll('.filter-btn').forEach(function(btn) {
                btn.addEventListener('click', function() {
                    var filter = this.getAttribute('data-filter');
                    
                    // Update button states
                    document.querySelectorAll('.filter-btn').forEach(function(b) {
                        b.classList.remove('active');
                    });
                    this.classList.add('active');
                    
                    activeFilter = filter;
                    applyFilter();
                });
            });
            
            function applyFilter() {
                var allRows = document.querySelectorAll('[data-category]');
                
                allRows.forEach(function(row) {
                    var category = row.getAttribute('data-category');
                    
                    if (activeFilter === 'all' || category === activeFilter) {
                        row.classList.remove('hidden');
                    } else {
                        row.classList.add('hidden');
                    }
                });
                
                // Also apply search if present
                var searchInput = document.getElementById('searchInput');
                if (searchInput && searchInput.value) {
                    performSearch(searchInput.value);
                }
            }
            
            // Smooth scroll for anchor links
            document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
                anchor.addEventListener('click', function(e) {
                    var target = document.querySelector(this.getAttribute('href'));
                    if (target) {
                        e.preventDefault();
                        target.scrollIntoView({ behavior: 'smooth' });
                    }
                });
            });
            
            // Toggle details
            document.querySelectorAll('.details-summary').forEach(function(summary) {
                summary.addEventListener('click', function() {
                    var details = this.nextElementSibling;
                    if (details) {
                        var isHidden = details.style.display === 'none';
                        details.style.display = isHidden ? 'block' : 'none';
                        this.setAttribute('aria-expanded', isHidden);
                    }
                });
            });
            
            // Print button (if added later)
            window.printReport = function() {
                window.print();
            };
            
            // Export function for JSON data (if needed)
            window.exportData = function() {
                var dataElement = document.getElementById('report-data');
                if (dataElement) {
                    var data = dataElement.textContent;
                    var blob = new Blob([data], { type: 'application/json' });
                    var url = URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url;
                    a.download = 'xml-compare-data.json';
                    a.click();
                    URL.revokeObjectURL(url);
                }
            };
        })();
        """.strip()
    
    def _generate_inline_diff(self, old_text: str, new_text: str) -> str:
        """
        Generate inline HTML diff highlighting using SequenceMatcher.
        
        Args:
            old_text: Original text
            new_text: New text
            
        Returns:
            str: HTML with highlighted differences
        """
        if not old_text and not new_text:
            return ""
        
        if not old_text:
            return f'<span class="diff-insert">{escape(new_text)}</span>'
        
        if not new_text:
            return f'<span class="diff-delete">{escape(old_text)}</span>'
        
        sm = SequenceMatcher(None, old_text, new_text)
        result = []
        
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                result.append(escape(old_text[i1:i2]))
            elif tag == 'delete':
                result.append(f'<span class="diff-delete">{escape(old_text[i1:i2])}</span>')
            elif tag == 'insert':
                result.append(f'<span class="diff-insert">{escape(new_text[j1:j2])}</span>')
            elif tag == 'replace':
                result.append(f'<span class="diff-delete">{escape(old_text[i1:i2])}</span>')
                result.append(f'<span class="diff-insert">{escape(new_text[j1:j2])}</span>')
        
        return ''.join(result)
    
    def _render_overview_tab(self, result: CompareResult) -> str:
        """Render the Overview tab content."""
        stats = result.statistics
        match_class = 'match-high' if stats.match_percentage >= 90 else ('match-medium' if stats.match_percentage >= 70 else 'match-low')
        
        html = f'''
        <div id="tab-overview" class="tab-panel active">
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
        '''
        return html
    
    def _render_text_tab(self, result: CompareResult) -> str:
        """Render the Text Corrections tab content."""
        html = '<div id="tab-text" class="tab-panel">\n'
        html += self._render_tab_header("Text Corrections", "Side-by-side comparison of text content changes")
        
        if not result.text_diffs:
            html += self._render_empty_state("No text corrections found", "The text content matches between the two files.")
        else:
            html += '<div class="diff-container">\n'
            html += f'<div class="diff-header"><h3>{len(result.text_diffs)} Text Changes</h3></div>\n'
            
            for diff in result.text_diffs:
                inline_html = self._generate_inline_diff(diff.old_text, diff.new_text)
                html += f'''
                <div class="diff-row" data-category="text">
                    <div class="diff-side old">
                        <div class="diff-side-label">Original</div>
                        <div class="diff-path">{escape(diff.path)}</div>
                        <div class="diff-content">{escape(diff.old_text) if not inline_html else escape(diff.old_text)}</div>
                    </div>
                    <div class="diff-side new">
                        <div class="diff-side-label">Revised</div>
                        <div class="diff-path">{escape(diff.path)}</div>
                        <div class="diff-content">{inline_html or escape(diff.new_text)}</div>
                    </div>
                </div>
                '''
            
            html += '</div>\n'
        
        html += '</div>\n'
        return html
    
    def _render_formatting_tab(self, result: CompareResult) -> str:
        """Render the Formatting Only tab content."""
        html = '<div id="tab-formatting" class="tab-panel">\n'
        html += self._render_tab_header("Formatting Changes", "Tag and style changes without text modification")
        
        if not result.format_diffs:
            html += self._render_empty_state("No formatting changes found", "The formatting and styling match between the two files.")
        else:
            html += '<div class="diff-container">\n'
            html += f'<div class="diff-header"><h3>{len(result.format_diffs)} Formatting Changes</h3></div>\n'
            
            for diff in result.format_diffs:
                style_info = ""
                if diff.old_style or diff.new_style:
                    style_info = f"<br>Style: {escape(str(diff.old_style))} → {escape(str(diff.new_style))}"
                
                html += f'''
                <div class="diff-row formatting" data-category="format">
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
                '''
            
            html += '</div>\n'
        
        html += '</div>\n'
        return html
    
    def _render_attribute_tab(self, result: CompareResult) -> str:
        """Render the Attribute Changes tab content."""
        html = '<div id="tab-attributes" class="tab-panel">\n'
        html += self._render_tab_header("Attribute Changes", "Differences in element attributes")
        
        if not result.attribute_diffs:
            html += self._render_empty_state("No attribute changes found", "The element attributes match between the two files.")
        else:
            html += '<div class="diff-container">\n'
            html += f'<div class="diff-header"><h3>{len(result.attribute_diffs)} Attribute Changes</h3></div>\n'
            html += '<table class="attr-table">\n'
            html += '<thead><tr><th>Element</th><th>Path</th><th>Attribute</th><th>Old Value</th><th>New Value</th></tr></thead>\n'
            html += '<tbody>\n'
            
            for diff in result.attribute_diffs:
                old_val = escape(str(diff.old_value)) if diff.old_value is not None else "<em>(none)</em>"
                new_val = escape(str(diff.new_value)) if diff.new_value is not None else "<em>(none)</em>"
                
                html += f'''
                <tr data-category="attribute">
                    <td><code>{escape(diff.element_tag)}</code></td>
                    <td><code>{escape(diff.path)}</code></td>
                    <td>{escape(diff.attribute_name)}</td>
                    <td class="attr-old">{old_val}</td>
                    <td class="attr-new">{new_val}</td>
                </tr>
                '''
            
            html += '</tbody></table>\n'
            html += '</div>\n'
        
        html += '</div>\n'
        return html
    
    def _render_structure_tab(self, result: CompareResult) -> str:
        """Render the Structure Changes tab content."""
        html = '<div id="tab-structure" class="tab-panel">\n'
        html += self._render_tab_header("Structure Changes", "Added, deleted, and moved elements")
        
        if not result.structure_diffs:
            html += self._render_empty_state("No structure changes found", "The document structure matches between the two files.")
        else:
            html += '<div class="diff-container">\n'
            html += f'<div class="diff-header"><h3>{len(result.structure_diffs)} Structure Changes</h3></div>\n'
            
            for diff in result.structure_diffs:
                move_info = ""
                if diff.change_type == 'moved' and diff.old_path:
                    move_info = f'<div style="font-size: 0.8rem; color: #666; margin-top: 5px;">From: {escape(diff.old_path)}</div>'
                
                html += f'''
                <div class="structure-item" data-category="structure">
                    <span class="structure-badge {diff.change_type}">{diff.change_type}</span>
                    <div class="structure-content">
                        <div class="structure-tag">&lt;{escape(diff.element_tag)}&gt;</div>
                        <div class="diff-path" style="margin-bottom: 5px;">{escape(diff.path)}</div>
                        <div class="structure-preview">{escape(diff.element_preview[:150])}{"..." if len(diff.element_preview) > 150 else ""}</div>
                        {move_info}
                    </div>
                </div>
                '''
            
            html += '</div>\n'
        
        html += '</div>\n'
        return html
    
    def _render_full_compare_tab(self, result: CompareResult) -> str:
        """Render the Full Compare tab content."""
        html = '<div id="tab-full" class="tab-panel">\n'
        html += self._render_tab_header("Full Comparison", "Complete list of all differences")
        
        all_diffs = result.get_all_diffs()
        
        if not all_diffs:
            html += self._render_empty_state("No differences found", "The files are identical.")
        else:
            html += '<div class="diff-container">\n'
            html += f'<div class="diff-header"><h3>All Changes ({len(all_diffs)} total)</h3></div>\n'
            html += '<ul class="details-list">\n'
            
            # Combine and categorize all diffs
            items = []
            for diff in result.text_diffs:
                items.append(('text', diff.path, 'Text Change', f"Old: {diff.old_text[:100]}...\nNew: {diff.new_text[:100]}..."))
            for diff in result.format_diffs:
                items.append(('format', diff.path, 'Format Change', f"Tag: {diff.old_tag} → {diff.new_tag}\nContent: {diff.content[:100]}..."))
            for diff in result.attribute_diffs:
                items.append(('attribute', diff.path, 'Attribute Change', f"Element: {diff.element_tag}\nAttr: {diff.attribute_name}\n{diff.old_value} → {diff.new_value}"))
            for diff in result.structure_diffs:
                items.append(('structure', diff.path, f"Structure: {diff.change_type.title()}", f"Tag: {diff.element_tag}\n{diff.element_preview[:100]}..."))
            
            for category, path, title, content in items:
                html += f'''
                <li class="details-item" data-category="{category}">
                    <div class="details-summary" aria-expanded="false">
                        <span>{escape(path)}</span>
                        <span class="details-type {category}">{category}</span>
                    </div>
                    <div class="details-content" style="display: none;">
                        <pre>{escape(content)}</pre>
                    </div>
                </li>
                '''
            
            html += '</ul>\n'
            html += '</div>\n'
        
        html += '</div>\n'
        return html
    
    def _render_statistics_tab(self, result: CompareResult) -> str:
        """Render the Statistics tab content."""
        stats = result.statistics
        
        # Calculate percentages for bars
        total = stats.total_differences or 1  # Avoid division by zero
        text_pct = (stats.text_changes / total) * 100
        format_pct = (stats.format_changes / total) * 100
        attr_pct = (stats.attribute_changes / total) * 100
        struct_pct = ((stats.added_nodes + stats.deleted_nodes + stats.moved_nodes) / total) * 100
        
        html = '<div id="tab-statistics" class="tab-panel">\n'
        html += self._render_tab_header("Statistics Dashboard", "Detailed breakdown of comparison metrics")
        
        html += '<div class="stats-dashboard">\n'
        
        # Changes breakdown
        html += '''
        <div class="stats-section">
            <h3>Changes Breakdown</h3>
        '''
        
        if stats.text_changes > 0:
            html += f'''
            <div class="stats-bar">
                <div class="stats-bar-label">Text Changes</div>
                <div class="stats-bar-track"><div class="stats-bar-fill text" style="width: {text_pct}%"></div></div>
                <div class="stats-bar-value">{stats.text_changes}</div>
            </div>
            '''
        
        if stats.format_changes > 0:
            html += f'''
            <div class="stats-bar">
                <div class="stats-bar-label">Formatting</div>
                <div class="stats-bar-track"><div class="stats-bar-fill format" style="width: {format_pct}%"></div></div>
                <div class="stats-bar-value">{stats.format_changes}</div>
            </div>
            '''
        
        if stats.attribute_changes > 0:
            html += f'''
            <div class="stats-bar">
                <div class="stats-bar-label">Attributes</div>
                <div class="stats-bar-track"><div class="stats-bar-fill attribute" style="width: {attr_pct}%"></div></div>
                <div class="stats-bar-value">{stats.attribute_changes}</div>
            </div>
            '''
        
        struct_total = stats.added_nodes + stats.deleted_nodes + stats.moved_nodes
        if struct_total > 0:
            html += f'''
            <div class="stats-bar">
                <div class="stats-bar-label">Structure</div>
                <div class="stats-bar-track"><div class="stats-bar-fill structure" style="width: {struct_pct}%"></div></div>
                <div class="stats-bar-value">{struct_total}</div>
            </div>
            '''
        
        html += '</div>\n'
        
        # Structure details
        html += '''
        <div class="stats-section">
            <h3>Structure Details</h3>
        '''
        
        html += f'''
            <div class="stats-bar">
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
        '''
        
        html += '</div>\n'
        
        # Match percentage
        html += f'''
        <div class="stats-section">
            <h3>Match Analysis</h3>
            <div class="stat-card {'match-high' if stats.match_percentage >= 90 else ('match-medium' if stats.match_percentage >= 70 else 'match-low')}">
                <div class="value">{stats.match_percentage:.2f}%</div>
                <div class="label">Overall Match</div>
            </div>
            <p style="margin-top: 15px; color: #666;">
                Based on approximately {stats.total_nodes} total nodes analyzed.
            </p>
        </div>
        '''
        
        html += '</div>\n'  # Close stats-dashboard
        html += '</div>\n'  # Close tab-panel
        
        return html
    
    def _render_tab_header(self, title: str, subtitle: str) -> str:
        """Render the standard tab content header with search."""
        return f'''
        <div class="content-header">
            <h2>{title}</h2>
            <div class="search-box">
                <input type="text" id="searchInput-{title.lower().replace(' ', '-'}" placeholder="Search {title.lower()}..." class="search-input-alt">
            </div>
        </div>
        <p style="margin-bottom: 20px; color: #666;">{subtitle}</p>
        '''
    
    def _render_empty_state(self, title: str, message: str) -> str:
        """Render an empty state message."""
        return f'''
        <div class="empty-state">
            <div class="empty-state-icon">✓</div>
            <h3>{title}</h3>
            <p>{message}</p>
        </div>
        '''
    
    def _render_sidebar(self, result: CompareResult) -> str:
        """Render the sidebar navigation."""
        stats = result.statistics
        filename = result.revised_path.stem
        
        # Calculate structure total
        struct_total = stats.added_nodes + stats.deleted_nodes + stats.moved_nodes
        
        html = f'''
        <aside class="sidebar">
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
        '''
        
        # Only show attribute tab if attributes were compared
        if result.options.include_attributes or stats.attribute_changes > 0:
            html += f'''
                    <li><a class="nav-link" data-tab="tab-attributes">Attribute Changes
                        <span class="count">{stats.attribute_changes}</span></a></li>
            '''
        
        html += f'''
                    <li><a class="nav-link" data-tab="tab-structure">Structure Changes
                        <span class="count">{struct_total}</span></a></li>
                    <li><a class="nav-link" data-tab="tab-full">Full Compare
                        <span class="count">{stats.total_differences}</span></a></li>
                    <li><a class="nav-link" data-tab="tab-statistics">Statistics</a></li>
                </ul>
            </div>
        </aside>
        '''
        
        return html
    
    def render_report(self, result: CompareResult) -> str:
        """
        Render the complete HTML report.
        
        This method generates a full self-contained HTML document with all
        CSS and JavaScript embedded. Suitable for streaming write.
        
        Args:
            result: The CompareResult containing all comparison data
            
        Returns:
            str: Complete HTML document as string
        """
        css = self._get_css()
        js = self._get_js()
        
        # Build all tab content
        tabs_html = ""
        tabs_html += self._render_overview_tab(result)
        tabs_html += self._render_text_tab(result)
        tabs_html += self._render_formatting_tab(result)
        
        # Only include attribute tab if enabled
        if result.options.include_attributes or result.statistics.attribute_changes > 0:
            tabs_html += self._render_attribute_tab(result)
        
        tabs_html += self._render_structure_tab(result)
        tabs_html += self._render_full_compare_tab(result)
        tabs_html += self._render_statistics_tab(result)
        
        # Build complete HTML
        html = f'''<!DOCTYPE html>
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
{self._render_sidebar(result)}
        
        <main class="main-content">
{tabs_html}
            
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
</html>'''
        
        return html
    
    def render_report_chunked(
        self,
        result: CompareResult,
        chunk_callback: callable
    ) -> None:
        """
        Render the HTML report in chunks for streaming output.
        
        Calls chunk_callback with each section of the HTML document.
        
        Args:
            result: The CompareResult containing all comparison data
            chunk_callback: Function to receive each chunk (takes str argument)
        """
        css = self._get_css()
        js = self._get_js()
        
        # HTML header
        chunk_callback(f'''<!DOCTYPE html>
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
        
        # Sidebar
        chunk_callback(self._render_sidebar(result))
        chunk_callback('        <main class="main-content">\n')
        
        # Tab panels
        chunk_callback(self._render_overview_tab(result))
        chunk_callback(self._render_text_tab(result))
        chunk_callback(self._render_formatting_tab(result))
        
        if result.options.include_attributes or result.statistics.attribute_changes > 0:
            chunk_callback(self._render_attribute_tab(result))
        
        chunk_callback(self._render_structure_tab(result))
        chunk_callback(self._render_full_compare_tab(result))
        chunk_callback(self._render_statistics_tab(result))
        
        # Footer and closing
        chunk_callback(f'''
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

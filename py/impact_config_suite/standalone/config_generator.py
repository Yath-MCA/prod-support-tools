"""
Config Generator Module
Generates HTML form for creating journal configuration XMLs.
Uses allowed_values.json to populate dropdowns.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional

# Get current directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ALLOWED_VALUES_FILE = os.path.join(CURRENT_DIR, "allowed_values.json")
OUTPUT_DIR = os.path.join(CURRENT_DIR, "generated")


def load_allowed_values() -> Dict:
    """Load the allowed values from JSON file"""
    if not os.path.exists(ALLOWED_VALUES_FILE):
        print(f"❌ Error: allowed_values.json not found at {ALLOWED_VALUES_FILE}")
        return {}
    
    with open(ALLOWED_VALUES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_form_html(allowed_values: Dict) -> str:
    """Generate the complete HTML form"""
    
    # Get values, excluding _meta
    figure_data = allowed_values.get('Figure', {})
    table_data = allowed_values.get('Table', {})
    reference_data = allowed_values.get('Reference', {})
    heading_data = allowed_values.get('heading', {})
    author_data = allowed_values.get('author', {})
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Journal Config Generator | IMPACT</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --primary-light: #818cf8;
            --secondary: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --bg-input: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --border: #475569;
            --shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: linear-gradient(135deg, var(--bg-dark) 0%, #1a1a2e 50%, #16213e 100%);
            min-height: 100vh;
            color: var(--text-primary);
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(180deg, rgba(99, 102, 241, 0.1) 0%, transparent 100%);
            border-bottom: 1px solid rgba(99, 102, 241, 0.2);
            margin-bottom: 30px;
        }}
        
        header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-light), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }}
        
        header p {{
            color: var(--text-secondary);
            font-size: 1.1rem;
        }}
        
        .layout {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }}
        
        @media (max-width: 1200px) {{
            .layout {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .form-panel {{
            background: var(--bg-card);
            border-radius: 16px;
            padding: 30px;
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
        }}
        
        .preview-panel {{
            position: sticky;
            top: 20px;
            height: fit-content;
            max-height: calc(100vh - 40px);
            overflow: auto;
        }}
        
        .section {{
            margin-bottom: 30px;
            padding: 25px;
            background: rgba(15, 23, 42, 0.5);
            border-radius: 12px;
            border: 1px solid var(--border);
        }}
        
        .section-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid var(--primary);
        }}
        
        .section-icon {{
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
        }}
        
        .section-title {{
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-primary);
        }}
        
        .subsection {{
            margin-top: 20px;
            padding: 15px;
            background: rgba(51, 65, 85, 0.3);
            border-radius: 8px;
        }}
        
        .subsection-title {{
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--primary-light);
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .form-group {{
            margin-bottom: 15px;
        }}
        
        .form-group label {{
            display: block;
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-secondary);
            margin-bottom: 6px;
        }}
        
        .form-group select,
        .form-group input {{
            width: 100%;
            padding: 10px 14px;
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 0.95rem;
            font-family: inherit;
            transition: all 0.2s ease;
        }}
        
        .form-group select:focus,
        .form-group input:focus {{
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
        }}
        
        .form-group select option {{
            background: var(--bg-input);
            color: var(--text-primary);
        }}
        
        .form-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
        }}
        
        .required::after {{
            content: " *";
            color: var(--danger);
        }}
        
        .preview-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .preview-title {{
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-primary);
        }}
        
        .btn-group {{
            display: flex;
            gap: 10px;
        }}
        
        .btn {{
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .btn-primary {{
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
        }}
        
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 20px -5px rgba(99, 102, 241, 0.4);
        }}
        
        .btn-secondary {{
            background: var(--bg-input);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }}
        
        .btn-secondary:hover {{
            background: var(--border);
        }}
        
        .btn-success {{
            background: linear-gradient(135deg, var(--secondary), #059669);
            color: white;
        }}
        
        .xml-preview {{
            background: #0d1117;
            border-radius: 12px;
            padding: 20px;
            overflow-x: auto;
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 0.85rem;
            line-height: 1.8;
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid var(--border);
        }}
        
        .xml-preview code {{
            color: #c9d1d9;
        }}
        
        .xml-tag {{ color: #7ee787; }}
        .xml-attr {{ color: #79c0ff; }}
        .xml-value {{ color: #ffa657; }}
        .xml-comment {{ color: #8b949e; font-style: italic; }}
        
        .toast {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            padding: 15px 25px;
            background: var(--secondary);
            color: white;
            border-radius: 10px;
            font-weight: 500;
            transform: translateX(150%);
            transition: transform 0.3s ease;
            z-index: 1000;
        }}
        
        .toast.show {{
            transform: translateX(0);
        }}
        
        .help-text {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 4px;
        }}
        
        .tabs {{
            display: flex;
            gap: 5px;
            margin-bottom: 20px;
            background: rgba(15, 23, 42, 0.5);
            padding: 5px;
            border-radius: 10px;
        }}
        
        .tab {{
            flex: 1;
            padding: 12px;
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-weight: 500;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.2s;
        }}
        
        .tab.active {{
            background: var(--primary);
            color: white;
        }}
        
        .tab:hover:not(.active) {{
            background: rgba(99, 102, 241, 0.2);
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        footer {{
            text-align: center;
            padding: 30px;
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 40px;
        }}
        
        footer a {{
            color: var(--primary-light);
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <header>
        <h1>📝 Journal Config Generator</h1>
        <p>Generate valid configuration XML for IMPACT journals</p>
    </header>
    
    <div class="container">
        <div class="layout">
            <!-- Form Panel -->
            <div class="form-panel">
                <div class="tabs">
                    <button class="tab active" onclick="showTab('basic')">📋 Basic Info</button>
                    <button class="tab" onclick="showTab('figure')">🖼️ Figure</button>
                    <button class="tab" onclick="showTab('table')">📊 Table</button>
                    <button class="tab" onclick="showTab('reference')">📚 Reference</button>
                </div>
                
                <!-- Basic Info Tab -->
                <div id="tab-basic" class="tab-content active">
                    <div class="section">
                        <div class="section-header">
                            <div class="section-icon">📋</div>
                            <span class="section-title">Basic Information</span>
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label class="required">Journal Short Name</label>
                                <input type="text" id="journal-short" placeholder="e.g., JCIM" oninput="updatePreview()">
                                <div class="help-text">Unique identifier for the journal</div>
                            </div>
                            <div class="form-group">
                                <label>Journal Abbreviation</label>
                                <input type="text" id="journal-abbr" placeholder="e.g., J Chem Inf Model" oninput="updatePreview()">
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label>Journal Full Title</label>
                            <input type="text" id="journal-title" placeholder="e.g., Journal of Chemical Information and Modeling" oninput="updatePreview()">
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label>Client</label>
                                <select id="client" onchange="updatePreview()">
                                    <option value="acs">ACS</option>
                                    <option value="lww">LWW</option>
                                    <option value="oup">OUP</option>
                                    <option value="medknow">Medknow</option>
                                    <option value="plos">PLOS</option>
                                    <option value="brill">Brill</option>
                                    <option value="nihr">NIHR</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Dictionary</label>
                                <select id="dictionary" onchange="updatePreview()">
                                    <option value="US spelling">US Spelling</option>
                                    <option value="UK spelling">UK Spelling</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Figure Tab -->
                <div id="tab-figure" class="tab-content">
                    <div class="section">
                        <div class="section-header">
                            <div class="section-icon">🖼️</div>
                            <span class="section-title">Figure Configuration</span>
                        </div>
                        
                        <div class="subsection">
                            <div class="subsection-title">Caption Settings</div>
                            <div class="form-row">
                                {generate_select_options('fig-caption-label', 'Label', figure_data.get('caption', {}).get('label', ['yes', 'no']))}
                                {generate_select_options('fig-caption-label-end-sep', 'Label End Separator', figure_data.get('caption', {}).get('label_end_sep', ['.', ':', '']))}
                                {generate_select_options('fig-caption-end-sep', 'Caption End Separator', figure_data.get('caption', {}).get('end_sep', ['.', '']))}
                            </div>
                        </div>
                        
                        <div class="subsection">
                            <div class="subsection-title">Direct Citation (dircite)</div>
                            <div class="form-row">
                                {generate_select_options('fig-dircite-single-prefix', 'Single Prefix', figure_data.get('dircite', {}).get('single_prefix', ['Figure ', 'Fig. ']))}
                                {generate_select_options('fig-dircite-double-prefix', 'Double Prefix', figure_data.get('dircite', {}).get('double_prefix', ['Figures ', 'Figs. ']))}
                                {generate_select_options('fig-dircite-multi-prefix', 'Multi Prefix', figure_data.get('dircite', {}).get('multi_prefix', ['Figures ', 'Figs. ']))}
                            </div>
                            <div class="form-row">
                                {generate_select_options('fig-dircite-double-sep', 'Double Separator', figure_data.get('dircite', {}).get('double_sep', [', ', ' and ']))}
                                {generate_select_options('fig-dircite-last-sep', 'Last Separator', figure_data.get('dircite', {}).get('last_sep', [' and ', ', and ']))}
                                {generate_select_options('fig-dircite-range-sep', 'Range Separator', figure_data.get('dircite', {}).get('range_sep', ['–', '-']))}
                            </div>
                            <div class="form-row">
                                {generate_select_options('fig-dircite-part-lab-prefix-num', 'Part Label Prefix Num', figure_data.get('dircite', {}).get('part_lab_prefix_num', ['yes', 'no']))}
                                {generate_select_options('fig-dircite-part-lab-case', 'Part Label Case', figure_data.get('dircite', {}).get('part_lab_case', ['upper', 'lower', 'follow']))}
                            </div>
                        </div>
                        
                        <div class="subsection">
                            <div class="subsection-title">Indirect Citation (indircite)</div>
                            <div class="form-row">
                                {generate_select_options('fig-indircite-single-prefix', 'Single Prefix', figure_data.get('indircite', {}).get('single_prefix', ['Figure ', 'Fig. ']))}
                                {generate_select_options('fig-indircite-double-prefix', 'Double Prefix', figure_data.get('indircite', {}).get('double_prefix', ['Figures ', 'Figs. ']))}
                                {generate_select_options('fig-indircite-openwrap', 'Open Wrap', figure_data.get('indircite', {}).get('openwrap', ['(', '[', '']))}
                                {generate_select_options('fig-indircite-closewrap', 'Close Wrap', figure_data.get('indircite', {}).get('closewrap', [')', ']', '']))}
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Table Tab -->
                <div id="tab-table" class="tab-content">
                    <div class="section">
                        <div class="section-header">
                            <div class="section-icon">📊</div>
                            <span class="section-title">Table Configuration</span>
                        </div>
                        
                        <div class="subsection">
                            <div class="subsection-title">Caption Settings</div>
                            <div class="form-row">
                                {generate_select_options('tab-caption-label', 'Label', table_data.get('caption', {}).get('label', ['yes', 'no']))}
                                {generate_select_options('tab-caption-label-end-sep', 'Label End Separator', table_data.get('caption', {}).get('label_end_sep', ['.', ':', '']))}
                            </div>
                        </div>
                        
                        <div class="subsection">
                            <div class="subsection-title">Direct Citation (dircite)</div>
                            <div class="form-row">
                                {generate_select_options('tab-dircite-single-prefix', 'Single Prefix', table_data.get('dircite', {}).get('single_prefix', ['Table ', 'Tab. ']))}
                                {generate_select_options('tab-dircite-double-prefix', 'Double Prefix', table_data.get('dircite', {}).get('double_prefix', ['Tables ', 'Tabs. ']))}
                                {generate_select_options('tab-dircite-range-sep', 'Range Separator', table_data.get('dircite', {}).get('range_sep', ['–', '-']))}
                            </div>
                        </div>
                        
                        <div class="subsection">
                            <div class="subsection-title">Indirect Citation (indircite)</div>
                            <div class="form-row">
                                {generate_select_options('tab-indircite-single-prefix', 'Single Prefix', table_data.get('indircite', {}).get('single_prefix', ['Table ', 'Tab. ']))}
                                {generate_select_options('tab-indircite-openwrap', 'Open Wrap', table_data.get('indircite', {}).get('openwrap', ['(', '[', '']))}
                                {generate_select_options('tab-indircite-closewrap', 'Close Wrap', table_data.get('indircite', {}).get('closewrap', [')', ']', '']))}
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Reference Tab -->
                <div id="tab-reference" class="tab-content">
                    <div class="section">
                        <div class="section-header">
                            <div class="section-icon">📚</div>
                            <span class="section-title">Reference Configuration</span>
                        </div>
                        
                        <div class="form-row">
                            {generate_select_options('ref-label-format', 'Label Format', reference_data.get('data-label-format', ['numbered', 'numbered_with_squre_bracket']))}
                            {generate_select_options('ref-text-format', 'Text Format', reference_data.get('text-format', ['sup', 'normal']))}
                        </div>
                        
                        <div class="subsection">
                            <div class="subsection-title">Direct Citation (dircite)</div>
                            <div class="form-row">
                                {generate_select_options('ref-dircite-double-sep', 'Double Separator', reference_data.get('dircite', {}).get('double_sep', [',', ', ']))}
                                {generate_select_options('ref-dircite-range-sep', 'Range Separator', reference_data.get('dircite', {}).get('range_sep', ['–', '-']))}
                                {generate_select_options('ref-dircite-openwrap', 'Open Wrap', reference_data.get('dircite', {}).get('openwrap', ['', '(', '[']))}
                                {generate_select_options('ref-dircite-closewrap', 'Close Wrap', reference_data.get('dircite', {}).get('closewrap', ['', ')', ']']))}
                            </div>
                        </div>
                        
                        <div class="subsection">
                            <div class="subsection-title">Indirect Citation (indircite)</div>
                            <div class="form-row">
                                {generate_select_options('ref-indircite-double-sep', 'Double Separator', reference_data.get('indircite', {}).get('double_sep', [',', ', ']))}
                                {generate_select_options('ref-indircite-range-sep', 'Range Separator', reference_data.get('indircite', {}).get('range_sep', ['–', '-']))}
                                {generate_select_options('ref-indircite-openwrap', 'Open Wrap', reference_data.get('indircite', {}).get('openwrap', ['(', '[', '']))}
                                {generate_select_options('ref-indircite-closewrap', 'Close Wrap', reference_data.get('indircite', {}).get('closewrap', [')', ']', '']))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Preview Panel -->
            <div class="form-panel preview-panel">
                <div class="preview-header">
                    <span class="preview-title">📄 XML Preview</span>
                    <div class="btn-group">
                        <button class="btn btn-secondary" onclick="copyXML()">📋 Copy</button>
                        <button class="btn btn-success" onclick="downloadXML()">💾 Download</button>
                    </div>
                </div>
                
                <div class="xml-preview" id="xml-preview">
                    <code id="xml-code"></code>
                </div>
            </div>
        </div>
    </div>
    
    <div class="toast" id="toast">✅ Copied to clipboard!</div>
    
    <footer>
        <p>Generated by <a href="#">IMPACT Config Generator</a> | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </footer>
    
    <script>
        // Tab switching
        function showTab(tabName) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            
            document.querySelector(`[onclick="showTab('${{tabName}}')"]`).classList.add('active');
            document.getElementById('tab-' + tabName).classList.add('active');
        }}
        
        // Escape XML special characters
        function escapeXml(str) {{
            return str.replace(/&/g, '&amp;')
                      .replace(/</g, '&lt;')
                      .replace(/>/g, '&gt;')
                      .replace(/"/g, '&quot;')
                      .replace(/'/g, '&apos;');
        }}
        
        // Get form value
        function getVal(id) {{
            const el = document.getElementById(id);
            return el ? el.value : '';
        }}
        
        // Generate XML
        function generateXML() {{
            const journalShort = getVal('journal-short') || 'NEWJOURNAL';
            const journalAbbr = getVal('journal-abbr') || journalShort;
            const journalTitle = getVal('journal-title') || journalShort;
            const dictionary = getVal('dictionary');
            
            // Figure values
            const figCaptionLabel = getVal('fig-caption-label');
            const figCaptionLabelEndSep = getVal('fig-caption-label-end-sep');
            const figCaptionEndSep = getVal('fig-caption-end-sep');
            const figDirciteSinglePrefix = getVal('fig-dircite-single-prefix');
            const figDirciteDoublePrefix = getVal('fig-dircite-double-prefix');
            const figDirciteMultiPrefix = getVal('fig-dircite-multi-prefix');
            const figDirciteDoubleSep = getVal('fig-dircite-double-sep');
            const figDirciteLastSep = getVal('fig-dircite-last-sep');
            const figDirciteRangeSep = getVal('fig-dircite-range-sep');
            const figDircitePartLabPrefixNum = getVal('fig-dircite-part-lab-prefix-num');
            const figDircitePartLabCase = getVal('fig-dircite-part-lab-case');
            const figIndirciteSinglePrefix = getVal('fig-indircite-single-prefix');
            const figIndirciteDoublePrefix = getVal('fig-indircite-double-prefix');
            const figIndirciteOpenwrap = getVal('fig-indircite-openwrap');
            const figIndirciteClosewrap = getVal('fig-indircite-closewrap');
            
            // Table values
            const tabCaptionLabel = getVal('tab-caption-label');
            const tabCaptionLabelEndSep = getVal('tab-caption-label-end-sep');
            const tabDirciteSinglePrefix = getVal('tab-dircite-single-prefix');
            const tabDirciteDoublePrefix = getVal('tab-dircite-double-prefix');
            const tabDirciteRangeSep = getVal('tab-dircite-range-sep');
            const tabIndirciteSinglePrefix = getVal('tab-indircite-single-prefix');
            const tabIndirciteOpenwrap = getVal('tab-indircite-openwrap');
            const tabIndirciteClosewrap = getVal('tab-indircite-closewrap');
            
            // Reference values
            const refLabelFormat = getVal('ref-label-format');
            const refTextFormat = getVal('ref-text-format');
            const refDirciteDoubleSep = getVal('ref-dircite-double-sep');
            const refDirciteRangeSep = getVal('ref-dircite-range-sep');
            const refDirciteOpenwrap = getVal('ref-dircite-openwrap');
            const refDirciteClosewrap = getVal('ref-dircite-closewrap');
            const refIndirciteDoubleSep = getVal('ref-indircite-double-sep');
            const refIndirciteRangeSep = getVal('ref-indircite-range-sep');
            const refIndirciteOpenwrap = getVal('ref-indircite-openwrap');
            const refIndirciteClosewrap = getVal('ref-indircite-closewrap');
            
            return `<journal short="${{journalShort}}" abbr="${{journalAbbr}}" journal-title="${{journalTitle}}">
    <!-- Author Configuration -->
    <author data-name="contrib" surname="yes" given-names="yes" prefix="no" suffix="yes" orcid="yes" degrees="no" role="yes" collab="yes" crosslink="yes" seperator=", " contribsep=", " pattern="beforecomma"/>
    <affiliation data-name="aff" department="yes" institution="yes" city="yes" state="yes" country="yes" seperator=";" designators="ArabicNumber"/>
    <corresp data-name="corresp" email="yes" address="yes" telephone="yes" fax="yes"/>
    <abstract data-name="abstract" GA="true" laysummery="true"/>
    <keywords data-name="keywords" seperator="" endperiod="false"/>
    <p data-name="p" merge="yes" indent="yes" inscitation="yes" editcitation="yes" delcitation="yes"/>
    <ciation allowedparent="body" allowed="p,tr,td" disallowed="front,ref"/>
    
    <!-- Figure Configuration -->
    <Figure data-name="fig" sentence="Figure " ref-type="fig" findCaption=".caption" findCaptionInner=".caption .p" new-item-key="data-figure" notallowed="no">
        <caption label="${{figCaptionLabel}}" label_end_sep="${{figCaptionLabelEndSep}}" end_sep="${{figCaptionEndSep}}" limit="3"/>
        <dircite single_prefix="${{figDirciteSinglePrefix}}" double_prefix="${{figDirciteDoublePrefix}}" double_sep="${{figDirciteDoubleSep}}" last_sep="${{figDirciteLastSep}}" multi_prefix="${{figDirciteMultiPrefix}}" range_sep="${{figDirciteRangeSep}}" openwrap="" closewrap="" part_lab_prefix_num="${{figDircitePartLabPrefixNum}}" part_lab_case="${{figDircitePartLabCase}}"/>
        <indircite single_prefix="${{figIndirciteSinglePrefix}}" double_prefix="${{figIndirciteDoublePrefix}}" double_sep="${{figDirciteDoubleSep}}" last_sep="${{figDirciteLastSep}}" multi_prefix="${{figDirciteMultiPrefix}}" range_sep="${{figDirciteRangeSep}}" openwrap="${{figIndirciteOpenwrap}}" closewrap="${{figIndirciteClosewrap}}"/>
    </Figure>
    
    <!-- Table Configuration -->
    <Table data-name="table-wrap" sentence="Table " ref-type="Table" findCaption=".caption" findCaptionInner=".caption .p" new-item-key="data-table">
        <caption label="${{tabCaptionLabel}}" label_end_sep="${{tabCaptionLabelEndSep}}" end_sep="" limit="3"/>
        <dircite single_prefix="${{tabDirciteSinglePrefix}}" double_prefix="${{tabDirciteDoublePrefix}}" double_sep=", " last_sep=" and " multi_prefix="${{tabDirciteDoublePrefix}}" range_sep="${{tabDirciteRangeSep}}" openwrap="" closewrap=""/>
        <indircite single_prefix="${{tabIndirciteSinglePrefix}}" double_prefix="${{tabDirciteDoublePrefix}}" double_sep=", " last_sep=" and " multi_prefix="${{tabDirciteDoublePrefix}}" range_sep="${{tabDirciteRangeSep}}" openwrap="${{tabIndirciteOpenwrap}}" closewrap="${{tabIndirciteClosewrap}}"/>
    </Table>
    
    <!-- Notes Configuration -->
    <notes footnote="notallowed" endnote="notallowed" note=""/>
    
    <!-- Heading Configuration -->
    <heading data-name="title" numbered="no" label="no" maximum="4">
        <h1 style="bold" type="All Caps"/>
        <h2 style="italics" type="Title case"/>
        <h3 style="italics" type="Title case"/>
        <h4 style="italics" type="Title case"/>
    </heading>
    
    <!-- Dictionary -->
    <dictionary spelling="${{dictionary}}" name="Merriam Webster"/>
    
    <!-- Back Matter -->
    <BackMatter ack="allowed" act="allowed" coi="allowed" fund="allowed" das="allowed" supp="allowed" app="allowed"/>
    
    <!-- Reference Configuration -->
    <Reference data-name="ref" sentence="Reference" ref-type="bibr" data-label-format="${{refLabelFormat}}" text-format="${{refTextFormat}}">
        <dircite double_sep="${{refDirciteDoubleSep}}" range_sep="${{refDirciteRangeSep}}" openwrap="${{refDirciteOpenwrap}}" closewrap="${{refDirciteClosewrap}}"/>
        <indircite double_sep="${{refIndirciteDoubleSep}}" range_sep="${{refIndirciteRangeSep}}" openwrap="${{refIndirciteOpenwrap}}" closewrap="${{refIndirciteClosewrap}}"/>
    </Reference>
</journal>`;
        }}
        
        // Syntax highlight XML
        function highlightXML(xml) {{
            return xml
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/(&lt;\\/?)([\\w-]+)/g, '$1<span class="xml-tag">$2</span>')
                .replace(/(\\w+)=(")/g, '<span class="xml-attr">$1</span>=<span class="xml-value">"</span>')
                .replace(/"([^"]*)"/g, '<span class="xml-value">"$1"</span>')
                .replace(/(&lt;!--[^>]*--&gt;)/g, '<span class="xml-comment">$1</span>');
        }}
        
        // Update preview
        function updatePreview() {{
            const xml = generateXML();
            document.getElementById('xml-code').innerHTML = highlightXML(xml);
        }}
        
        // Copy XML
        function copyXML() {{
            const xml = generateXML();
            navigator.clipboard.writeText(xml).then(() => {{
                showToast('✅ Copied to clipboard!');
            }});
        }}
        
        // Download XML
        function downloadXML() {{
            const xml = generateXML();
            const journalShort = getVal('journal-short') || 'journal';
            const blob = new Blob([xml], {{ type: 'application/xml' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${{journalShort}}_config.xml`;
            a.click();
            URL.revokeObjectURL(url);
            showToast('💾 Downloaded!');
        }}
        
        // Show toast
        function showToast(message) {{
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2000);
        }}
        
        // Initialize
        document.addEventListener('DOMContentLoaded', updatePreview);
        
        // Add change listeners to all selects
        document.querySelectorAll('select').forEach(select => {{
            select.addEventListener('change', updatePreview);
        }});
    </script>
</body>
</html>'''
    
    return html


def generate_select_options(field_id: str, label: str, options: List[str]) -> str:
    """Generate HTML select element with options"""
    options_html = ""
    for opt in options:
        display = opt if opt else "(empty)"
        options_html += f'<option value="{opt}">{display}</option>'
    
    return f'''
                                <div class="form-group">
                                    <label>{label}</label>
                                    <select id="{field_id}" onchange="updatePreview()">
                                        {options_html}
                                    </select>
                                </div>'''


def generate_html_form(output_path: Optional[str] = None) -> str:
    """
    Generate the HTML form and save it.
    
    Args:
        output_path: Optional custom output path
    
    Returns:
        Path to the generated HTML file
    """
    print("🔧 Loading allowed values...")
    allowed_values = load_allowed_values()
    
    if not allowed_values:
        print("❌ Could not load allowed values")
        return ""
    
    print("📝 Generating HTML form...")
    html = generate_form_html(allowed_values)
    
    # Create output directory if needed
    if output_path is None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, "config_generator.html")
    
    print(f"💾 Saving to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML form generated successfully!")
    print(f"   📂 Location: {output_path}")
    print(f"   🌐 Open in browser to use")
    
    return output_path


# CLI interface
if __name__ == "__main__":
    import sys
    
    print("🎨 CONFIG GENERATOR")
    print("=" * 50)
    
    output_path = None
    if len(sys.argv) > 1:
        output_path = sys.argv[1]
    
    result = generate_html_form(output_path)
    
    if result:
        # Try to open in browser
        try:
            import webbrowser
            open_browser = input("\n🌐 Open in browser? (y/n): ").strip().lower()
            if open_browser == 'y':
                webbrowser.open(f'file://{os.path.abspath(result)}')
        except Exception:
            pass

# --- PREMIUM HTML REPORT TEMPLATE WITH ADVANCED FEATURES ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Impact Unified Analysis Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --card-bg: rgba(30, 41, 59, 0.8);
            --card-hover: rgba(30, 41, 59, 1);
            --primary: #6366f1;
            --primary-light: #818cf8;
            --secondary: #a855f7;
            --accent: #f43f5e;
            --success: #10b981;
            --warning: #f59e0b;
            --text: #f1f5f9;
            --text-secondary: #cbd5e1;
            --text-dim: #94a3b8;
            --border: rgba(148, 163, 184, 0.2);
            --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
            --shadow-lg: 0 20px 25px rgba(0, 0, 0, 0.2);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            background-color: var(--bg-primary);
            background-image:
                radial-gradient(circle at 20% 50%, rgba(99, 102, 241, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(168, 85, 247, 0.05) 0%, transparent 50%);
            color: var(--text);
            font-family: 'Outfit', sans-serif;
            line-height: 1.6;
            padding: 40px 20px;
            min-height: 100vh;
        }}

        /* HEADER */
        header {{
            max-width: 1400px;
            margin: 0 auto 50px;
            padding-bottom: 30px;
            border-bottom: 2px solid var(--primary);
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            gap: 40px;
            flex-wrap: wrap;
        }}

        .header-title h1 {{
            font-size: clamp(2rem, 5vw, 3rem);
            background: linear-gradient(135deg, #818cf8 0%, #c084fc 50%, #f43f5e 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-weight: 700;
            margin-bottom: 8px;
        }}

        .header-title p {{
            color: var(--text-dim);
            font-size: 0.95rem;
            font-weight: 500;
        }}

        .header-meta {{
            text-align: right;
        }}

        .header-meta div {{
            color: var(--text-dim);
            font-size: 0.9rem;
            margin-bottom: 6px;
        }}

        .header-meta strong {{
            color: var(--primary-light);
            font-weight: 600;
        }}

        /* DASHBOARD STATS */
        .dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto 50px;
            padding: 0 0;
        }}

        .stat-card {{
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            box-shadow: var(--shadow-lg);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }}

        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
        }}

        .stat-card:hover {{
            background: var(--card-hover);
            border-color: var(--primary);
            transform: translateY(-4px);
            box-shadow: 0 25px 30px rgba(99, 102, 241, 0.15);
        }}

        .stat-card .label {{
            color: var(--text-dim);
            text-transform: uppercase;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 1px;
            margin-bottom: 12px;
        }}

        .stat-card .value {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-light), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        /* MAIN CONTAINER */
        .main-container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        /* DOCUMENT SECTIONS */
        .doc-section {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            margin-bottom: 30px;
            box-shadow: var(--shadow-lg);
            overflow: hidden;
            transition: all 0.3s;
        }}

        .doc-section:hover {{
            border-color: var(--primary);
        }}

        .doc-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 24px;
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(168, 85, 247, 0.05));
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            user-select: none;
            transition: background 0.3s;
        }}

        .doc-header:hover {{
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.1));
        }}

        .doc-header-left {{
            display: flex;
            align-items: center;
            gap: 16px;
            flex: 1;
            min-width: 0;
        }}

        .toggle-icon {{
            flex-shrink: 0;
            font-size: 1.4rem;
            color: var(--primary);
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .doc-title {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary-light);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .doc-meta {{
            color: var(--text-dim);
            font-size: 0.9rem;
            white-space: nowrap;
            flex-shrink: 0;
        }}

        .doc-meta strong {{
            color: var(--success);
            font-weight: 600;
        }}

        .doc-section.collapsed .doc-content-wrapper {{
            display: none;
        }}

        .doc-section.collapsed .toggle-icon {{
            transform: rotate(-90deg);
        }}

        .doc-content-wrapper {{
            padding: 24px;
        }}

        /* TABS SYSTEM */
        .tabs-header {{
            display: flex;
            gap: 8px;
            margin-bottom: 24px;
            border-bottom: 1px solid var(--border);
            overflow-x: auto;
            padding-bottom: 12px;
            scroll-behavior: smooth;
        }}

        .tabs-header::-webkit-scrollbar {{
            height: 4px;
        }}

        .tabs-header::-webkit-scrollbar-track {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
        }}

        .tabs-header::-webkit-scrollbar-thumb {{
            background: var(--primary);
            border-radius: 4px;
        }}

        .tab-btn {{
            padding: 10px 20px;
            border: none;
            background: transparent;
            color: var(--text-dim);
            font-family: 'Outfit', sans-serif;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            border-radius: 8px;
            position: relative;
            white-space: nowrap;
            flex-shrink: 0;
        }}

        .tab-btn:hover {{
            color: var(--text);
            background: rgba(99, 102, 241, 0.1);
        }}

        .tab-btn.active {{
            color: var(--primary);
            background: rgba(99, 102, 241, 0.15);
        }}

        .tab-btn.active::after {{
            content: '';
            position: absolute;
            bottom: -13px;
            left: 0;
            width: 100%;
            height: 3px;
            background: var(--primary);
            border-radius: 3px;
        }}

        .tab-content {{
            display: none;
            animation: fadeIn 0.3s ease-out;
        }}

        .tab-content.active {{
            display: block;
        }}

        @keyframes fadeIn {{
            from {{
                opacity: 0;
                transform: translateY(8px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        /* CHAPTER BREAKDOWN */
        .chapter-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }}

        .ch-summary-card {{
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 18px;
            transition: all 0.3s;
            cursor: pointer;
        }}

        .ch-summary-card:hover {{
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.05));
            border-color: var(--primary);
            transform: translateY(-2px);
        }}

        .ch-title {{
            font-weight: 700;
            color: var(--text);
            margin-bottom: 14px;
            font-size: 0.95rem;
            line-height: 1.4;
        }}

        .ch-stats {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}

        .ch-stat-item {{
            font-size: 0.8rem;
            color: var(--text-dim);
            padding: 8px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 6px;
            text-align: center;
        }}

        .ch-stat-item b {{
            display: block;
            color: var(--primary);
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 2px;
        }}

        /* TABLES */
        .table-wrapper {{
            overflow-x: auto;
            border-radius: 12px;
            border: 1px solid var(--border);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}

        th {{
            background: rgba(99, 102, 241, 0.1);
            text-align: left;
            padding: 14px 16px;
            color: var(--text-dim);
            font-size: 0.75rem;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
        }}

        td {{
            padding: 14px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            vertical-align: top;
        }}

        tr:hover {{
            background: rgba(99, 102, 241, 0.05);
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        /* BADGES & LABELS */
        .id-code {{
            font-family: 'JetBrains Mono', monospace;
            color: var(--secondary);
            font-weight: 600;
            background: rgba(168, 85, 247, 0.15);
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 0.85rem;
            border: 1px solid rgba(168, 85, 247, 0.3);
            display: inline-block;
        }}

        .label-text {{
            color: var(--success);
            font-weight: 700;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .count-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 36px;
            height: 36px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 700;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }}

        .citation-box {{
            font-family: 'JetBrains Mono', monospace;
            background: rgba(0, 0, 0, 0.5);
            padding: 10px 12px;
            border-radius: 8px;
            color: #d1d5db;
            font-size: 0.8rem;
            max-width: 100%;
            overflow-x: auto;
            border: 1px solid rgba(255, 255, 255, 0.08);
            line-height: 1.4;
        }}

        .citation-box::-webkit-scrollbar {{
            height: 4px;
        }}

        .citation-box::-webkit-scrollbar-thumb {{
            background: var(--primary);
            border-radius: 4px;
        }}

        /* EMPTY STATE */
        .empty-state {{
            text-align: center;
            padding: 40px 20px;
            color: var(--text-dim);
        }}

        .empty-state i {{
            font-size: 3rem;
            margin-bottom: 16px;
            opacity: 0.5;
        }}

        /* FOOTER */
        .footer {{
            text-align: center;
            margin-top: 60px;
            padding: 30px 20px;
            color: var(--text-dim);
            font-size: 0.8rem;
            border-top: 1px solid var(--border);
        }}

        .footer a {{
            color: var(--primary);
            text-decoration: none;
            transition: color 0.3s;
        }}

        .footer a:hover {{
            color: var(--secondary);
        }}

        /* RESPONSIVE */
        @media (max-width: 768px) {{
            body {{
                padding: 20px 10px;
            }}

            header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 20px;
                margin-bottom: 30px;
            }}

            .header-meta {{
                text-align: left;
                width: 100%;
            }}

            .stat-card {{
                padding: 18px;
            }}

            .stat-card .value {{
                font-size: 2rem;
            }}

            .doc-header {{
                flex-wrap: wrap;
                padding: 18px;
            }}

            .doc-title {{
                font-size: 1.3rem;
            }}

            .chapter-grid {{
                grid-template-columns: 1fr;
            }}

            table {{
                font-size: 0.8rem;
            }}

            th, td {{
                padding: 10px 12px;
            }}
        }}
    </style>
</head>
<body>
    <!-- HEADER -->
    <header>
        <div class="header-title">
            <h1>📊 Unified Analysis Report</h1>
            <p>Comprehensive DOM & Citation Analysis</p>
        </div>
        <div class="header-meta">
            <div>📋 <strong>{client}</strong></div>
            <div>⏱️ {timestamp}</div>
        </div>
    </header>

    <!-- DASHBOARD STATS -->
    <div class="dashboard">
        <div class="stat-card">
            <div class="label">📄 Documents</div>
            <div class="value">{total_docs}</div>
        </div>
        <div class="stat-card">
            <div class="label">📖 Chapters</div>
            <div class="value">{total_chapters}</div>
        </div>
        <div class="stat-card">
            <div class="label">🖼️ Figures</div>
            <div class="value">{total_figs}</div>
        </div>
        <div class="stat-card">
            <div class="label">📊 Tables</div>
            <div class="value">{total_tables}</div>
        </div>
        <div class="stat-card">
            <div class="label">✏️ Labels</div>
            <div class="value">{total_labels}</div>
        </div>
    </div>

    <!-- MAIN CONTENT -->
    <div class="main-container">
        {rows}
    </div>

    <!-- FOOTER -->
    <div class="footer">
        <p>Generated by Impact Unified Analyzer v3.0 | &copy; 2025</p>
        <p style="margin-top: 10px; font-size: 0.75rem;">Advanced DOM & Regex Analysis Engine</p>
    </div>

    <script>
        function openTab(evt, docId, tabName) {{
            // Get all tabs within the current doc section
            const section = evt.currentTarget.closest('.doc-content-wrapper');
            if (!section) return;

            const tabContents = section.querySelectorAll('.tab-content');
            const tabBtns = section.querySelectorAll('.tab-btn');

            // Hide all tabs and deactivate buttons
            tabContents.forEach(tab => tab.classList.remove('active'));
            tabBtns.forEach(btn => btn.classList.remove('active'));

            // Show selected tab and activate button
            const targetTab = document.getElementById(docId + '_' + tabName);
            if (targetTab) {{
                targetTab.classList.add('active');
            }}
            evt.currentTarget.classList.add('active');
        }}

        function toggleSection(header) {{
            const section = header.closest('.doc-section');
            section.classList.toggle('collapsed');
        }}

        // Auto-activate first tab in each section
        document.querySelectorAll('.tab-btn').forEach((btn, idx) => {{
            if (idx === 0 && !btn.classList.contains('active')) {{
                btn.classList.add('active');
            }}
        }});
    </script>
</body>
</html>
"""
import os
import re

class WordExtractor:
    """
    Logic for extracting words from TXT/HTML/XML files based on different segments.
    """
    
    def __init__(self):
        self.segments = {
            "Non-Alphabetic": r"[A-Za-z]", 
            "Alphabetic Only": r"^[A-Za-z]+$", 
            "Numeric Only": r"^\d+$"
        }
        # Common English stop words
        self.stop_words = {
            'the', 'of', 'and', 'a', 'to', 'in', 'is', 'you', 'that', 'it', 'he', 'was', 'for', 'on', 'are', 'as', 'with', 
            'his', 'they', 'at', 'be', 'this', 'have', 'from', 'or', 'one', 'had', 'by', 'word', 'but', 'not', 'what', 
            'all', 'were', 'we', 'when', 'your', 'can', 'said', 'there', 'use', 'an', 'each', 'which', 'she', 'do', 'how', 
            'their', 'if', 'will', 'up', 'other', 'about', 'out', 'many', 'then', 'them', 'these', 'so', 'some', 'her', 
            'would', 'make', 'like', 'him', 'into', 'time', 'has', 'look', 'two', 'more', 'write', 'go', 'see', 'number', 
            'no', 'way', 'could', 'people', 'my', 'than', 'first', 'water', 'been', 'called', 'who', 'am', 'its', 'now', 
            'find', 'long', 'down', 'day', 'did', 'get', 'come', 'made', 'may', 'part', 'where'
        }

    def extract_text_from_html(self, file_path):
        """Extracts clean text from HTML/XML file."""
        from bs4 import BeautifulSoup
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            soup = BeautifulSoup(content, "lxml")
            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text(separator=", ") # Use comma as separator for consistency
            return text
        except Exception as e:
            return ""

    def get_unique_words(self, text, filter_stop_words=True):
        """Returns unique alphabetic words, optionally filtering stop words."""
        # Find all words
        words = re.findall(r'[A-Za-z]+', text.lower())
        if filter_stop_words:
            words = [w for w in words if w not in self.stop_words and len(w) > 1]
        
        return sorted(list(set(words)))

    def extract(self, file_path, segment_type="Non-Alphabetic"):
        """Extract from file based on segment."""
        if not os.path.exists(file_path):
            return {"ok": False, "error": "File not found"}

        try:
            if file_path.lower().endswith(('.html', '.xml', '.xhtml', '.htm')):
                text = self.extract_text_from_html(file_path)
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()

            items = [item.strip() for item in text.split(",")]
            
            if segment_type == "Non-Alphabetic":
                result = [item for item in items if item and not re.search(r"[A-Za-z]", item)]
            elif segment_type == "Alphabetic Only":
                result = [item for item in items if item and re.search(r"^[A-Za-z]+$", item)]
            elif segment_type == "Numeric Only":
                result = [item for item in items if item and item.isdigit()]
            else:
                result = [item for item in items if item and not re.search(r"[A-Za-z]", item)]

            return {
                "ok": True,
                "result": sorted(list(set(result))), # Always unique
                "total": len(set(result)),
                "segment": segment_type
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def process_all(self, file_path):
        """Runs all extractions and returns a consolidated dict."""
        results = {}
        for seg in self.segments.keys():
            res = self.extract(file_path, seg)
            if res["ok"]:
                results[seg] = res["result"]
        return results

    def generate_html_report(self, results_dict, input_file):
        """
        Creates a multi-segment HTML report.
        results_dict: { segment_name: [values] }
        """
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_name = os.path.basename(input_file)
        
        sections_html = ""
        for seg_name, vals in results_dict.items():
            rows = "".join([f"<tr><td>{i+1}</td><td>{res}</td></tr>" for i, res in enumerate(vals)])
            sections_html += f"""
            <section class="segment-section" id="section-{seg_name.replace(' ', '')}">
                <div class="segment-header">
                    <h2>{seg_name}</h2>
                    <span class="count-badge">{len(vals)} items</span>
                </div>
                <div class="table-container">
                    <table>
                        <thead><tr><th style="width: 60px;">#</th><th>Value</th></tr></thead>
                        <tbody>{rows if rows else "<tr><td colspan='2' style='text-align:center; color:var(--muted)'>No items found</td></tr>"}</tbody>
                    </table>
                </div>
            </section>
            """

        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Extraction Report - {file_name}</title>
    <style>
        :root {{
            --primary: #38bdf8;
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text: #e2e8f0;
            --muted: #94a3b8;
            --border: #334155;
            --success: #10b981;
            --accent: #818cf8;
        }}
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 40px 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .container {{ width: 100%; max-width: 1000px; }}
        header {{
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid var(--border);
            text-align: center;
        }}
        h1 {{ color: var(--primary); font-size: 2.8rem; margin: 0; }}
        .meta {{ color: var(--muted); margin-top: 10px; font-size: 0.95rem; }}
        
        .nav-tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            justify-content: center;
            position: sticky;
            top: 20px;
            z-index: 10;
            background: rgba(15, 23, 42, 0.8);
            backdrop-filter: blur(8px);
            padding: 10px;
            border-radius: 50px;
        }}
        .tab-btn {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            color: var(--muted);
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 600;
        }}
        .tab-btn.active {{
            background: var(--primary);
            color: var(--bg);
            border-color: var(--primary);
        }}
        
        .segment-section {{ margin-bottom: 50px; display: none; }}
        .segment-section.active {{ display: block; animation: fadeIn 0.4s ease; }}
        
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}

        .segment-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        h2 {{ color: var(--accent); margin: 0; font-size: 1.8rem; }}
        .count-badge {{
            background: rgba(56, 189, 248, 0.2);
            color: var(--primary);
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
        }}
        
        .table-container {{
            background: var(--card-bg);
            border-radius: 15px;
            border: 1px solid var(--border);
            overflow: hidden;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2);
        }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{
            background: rgba(255, 255, 255, 0.03);
            color: var(--muted);
            padding: 15px 20px;
            text-align: left;
            font-size: 0.85rem;
            text-transform: uppercase;
            border-bottom: 1px solid var(--border);
        }}
        td {{
            padding: 12px 20px;
            border-bottom: 1px solid var(--border);
            font-family: 'Consolas', monospace;
        }}
        tr:hover td {{ background: rgba(255, 255, 255, 0.02); }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Master Extraction Report</h1>
            <div class="meta">
                Source: <b>{file_name}</b> &nbsp;|&nbsp; Generated: <b>{timestamp}</b>
            </div>
        </header>

        <div class="nav-tabs">
            {''.join([f'<button class="tab-btn" onclick="showSection(\'section-{n.replace(" ", "")}\', this)">{n}</button>' for n in results_dict.keys()])}
        </div>

        {sections_html}
    </div>

    <script>
        function showSection(id, btn) {{
            document.querySelectorAll('.segment-section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            btn.classList.add('active');
        }}
        // Init first section
        document.querySelector('.tab-btn').click();
    </script>
</body>
</html>
        """
        return html_template

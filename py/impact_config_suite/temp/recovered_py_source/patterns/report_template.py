import json
from . import report_config as cfg

def render_html(data, patterns_data, mapping, sigs, ts):
    # Extract pattern categories
    ref_num_patterns = patterns_data.get('ref_numbered', {})
    ref_unnum_patterns = patterns_data.get('ref_unnumbered', {})
    ref_fn_patterns = patterns_data.get('ref_footnote', {})
    figtab_patterns = patterns_data.get('figtab', {})
    partlab_fig_patterns = patterns_data.get('partlab_figure', {})
    partlab_tab_patterns = patterns_data.get('partlab_table', {})
    ref_num_mapping = patterns_data.get('ref_numbered_mapping', {})
    ref_unnum_mapping = patterns_data.get('ref_unnumbered_mapping', {})
    ref_fn_mapping = patterns_data.get('ref_footnote_mapping', {})
    figtab_mapping = patterns_data.get('figtab_mapping', {})
    partlab_fig_mapping = patterns_data.get('partlab_figure_mapping', {})
    partlab_tab_mapping = patterns_data.get('partlab_table_mapping', {})
    journal_info = patterns_data.get('journal_info', {})

    # Group data by type
    by_type = {'journals': [], 'books': []}
    for item in data:
        t = item.get('type', 'unknown')
        if t in by_type:
            by_type[t].append(item)
    
    # Collect unique Pattern per attribute
    unique_values = {}
    for item in data:
        # Figure/Table sections
        for sec in ['Figure', 'Table']:
            S = item.get(sec, {})
            for k, v in S.items():
                if k in ('dircite', 'indircite'):
                    for ca, arr in v.items():
                        attr_key = f"{sec}.{k}.{ca}"
                        for b in arr:
                            if b['value'] != '⊘ empty':
                                unique_values.setdefault(attr_key, set()).add(b['value'])
                else:
                    attr_key = f"{sec}.{k}"
                    for b in v:
                        if b['value'] != '⊘ empty':
                            unique_values.setdefault(attr_key, set()).add(b['value'])
        
        # Reference section
        S = item.get('Reference', {})
        for k, v in S.items():
            if k in ('dircite', 'indircite'):
                for ca, arr in v.items():
                    attr_key = f"Reference.{k}.{ca}"
                    for b in arr:
                        if b['value'] != '⊘ empty':
                            unique_values.setdefault(attr_key, set()).add(b['value'])
            else:
                attr_key = f"Reference.{k}"
                for b in v:
                    if b['value'] != '⊘ empty':
                        unique_values.setdefault(attr_key, set()).add(b['value'])
        
        # Part Label Figure
        PL = item.get('PartLabel_Figure', {})
        for k, v in PL.items():
            attr_key = f"PartLabel.Figure.{k}"
            for b in v:
                if b['value'] != '⊘ empty':
                    unique_values.setdefault(attr_key, set()).add(b['value'])
        
        # Part Label Table
        PL = item.get('PartLabel_Table', {})
        for k, v in PL.items():
            attr_key = f"PartLabel.Table.{k}"
            for b in v:
                if b['value'] != '⊘ empty':
                    unique_values.setdefault(attr_key, set()).add(b['value'])
    
    # Unify dircite/indircite attributes if they have the same unique Pattern
    def unify_cite_attrs(unique_vals):
        """Merge dircite/indircite into 'cite' if they share identical unique Pattern"""
        unified = {}
        processed = set()
        
        for attr_key, values in unique_vals.items():
            if attr_key in processed:
                continue
            
            # Check if this is a dircite or indircite attribute
            if '.dircite.' in attr_key:
                # Find corresponding indircite
                indircite_key = attr_key.replace('.dircite.', '.indircite.')
                if indircite_key in unique_vals and unique_vals[indircite_key] == values:
                    # Both have same values, unify them
                    unified_key = attr_key.replace('.dircite.', '.cite.')
                    unified[unified_key] = values
                    processed.add(attr_key)
                    processed.add(indircite_key)
                else:
                    # Different values, keep separate
                    unified[attr_key] = values
                    processed.add(attr_key)
            elif '.indircite.' in attr_key:
                # Check if already processed with dircite
                dircite_key = attr_key.replace('.indircite.', '.dircite.')
                if dircite_key in unique_vals and unique_vals[dircite_key] == values:
                    # Already unified via dircite path
                    if attr_key not in processed:
                        unified_key = attr_key.replace('.indircite.', '.cite.')
                        if unified_key not in unified:
                            unified[unified_key] = values
                        processed.add(attr_key)
                else:
                    # Different values or no dircite counterpart, keep separate
                    unified[attr_key] = values
                    processed.add(attr_key)
            else:
                # Not a cite attribute, keep as-is
                unified[attr_key] = values
                processed.add(attr_key)
        
        return unified
    
    unique_values = unify_cite_attrs(unique_values)

    # Calculate total journals for percentage calculations
    all_journals = set()
    for item in data:
        for j in item.get('journals', []):
            all_journals.add(j)
    # Also collect from pattern data
    for cat_patterns in [ref_num_patterns, ref_unnum_patterns, ref_fn_patterns, figtab_patterns, partlab_fig_patterns, partlab_tab_patterns]:
        for journals in cat_patterns.values():
            all_journals.update(journals)
    total_journals = len(all_journals) if all_journals else 1  # Avoid division by zero
    
    # Calculate percentage stats for each category
    def calc_category_stats(patterns):
        if not patterns:
            return {'total': 0, 'max_match': 0, 'max_pct': 0.0, 'patterns': []}
        total_in_cat = sum(len(js) for js in patterns.values())
        pattern_stats = []
        for pname, journals in sorted(patterns.items(), key=lambda x: -len(x[1])):
            count = len(journals)
            pct = (count / total_in_cat * 100) if total_in_cat > 0 else 0
            pattern_stats.append({'name': pname, 'count': count, 'pct': pct, 'journals': journals})
        max_match = pattern_stats[0]['count'] if pattern_stats else 0
        max_pct = pattern_stats[0]['pct'] if pattern_stats else 0
        return {'total': total_in_cat, 'max_match': max_match, 'max_pct': max_pct, 'patterns': pattern_stats}
    
    ref_num_stats = calc_category_stats(ref_num_patterns)
    ref_unnum_stats = calc_category_stats(ref_unnum_patterns)
    ref_fn_stats = calc_category_stats(ref_fn_patterns)
    figtab_stats = calc_category_stats(figtab_patterns)
    partlab_fig_stats = calc_category_stats(partlab_fig_patterns)
    partlab_tab_stats = calc_category_stats(partlab_tab_patterns)
    
    # Calculate consolidated stats
    total_ref = ref_num_stats['total'] + ref_unnum_stats['total'] + ref_fn_stats['total']
    total_figtab = figtab_stats['total']
    total_partlab = partlab_fig_stats['total'] + partlab_tab_stats['total']
    grand_total = total_ref + total_figtab + total_partlab
    
    # Overall best match percentage for each category
    consolidated_stats = {
        'ref_numbered': ref_num_stats,
        'ref_unnumbered': ref_unnum_stats,
        'ref_footnote': ref_fn_stats,
        'figtab': figtab_stats,
        'partlab_figure': partlab_fig_stats,
        'partlab_table': partlab_tab_stats,
        'total_ref': total_ref,
        'total_figtab': total_figtab,
        'total_partlab': total_partlab,
        'grand_total': grand_total
    }

    H = []
    H.append("<!DOCTYPE html><html><head><meta charset=utf-8><title>Pattern Report</title>")
    H.append("""<style>
:root{--primary:#4a90d9;--ref-num:#2196F3;--ref-unnum:#9c27b0;--ref-fn:#ff5722;--figtab:#ff9800;--partlab-fig:#00bcd4;--partlab-tab:#8bc34a;--unique:#607d8b}
body{font-family:'Segoe UI',Arial,sans-serif;margin:0;background:#f5f5f5;display:flex;height:100vh}
.sidebar{width:250px;background:linear-gradient(180deg,#2c3e50,#34495e);color:#fff;padding:0;flex-shrink:0;overflow-y:auto}
.sidebar-header{padding:20px;background:#1a252f;text-align:center;border-bottom:1px solid #3d5166}
.sidebar-header h2{margin:0;font-size:16px}
.sidebar-header .ts{font-size:11px;color:#8899a6;margin-top:5px}
.nav-item{padding:15px 20px;cursor:pointer;border-left:4px solid transparent;transition:all 0.2s}
.nav-item:hover{background:#3d5166;border-left-color:#4a90d9}
.nav-item.active{background:#3d5166;border-left-color:#4a90d9}
.nav-item .icon{margin-right:10px}
.main-content{flex:1;overflow-y:auto;padding:20px}
.tab-content{display:none}
.tab-content.active{display:block}
h1{color:#333;border-bottom:2px solid #4a90d9;padding-bottom:10px;margin-top:0}
h2{color:#4a90d9;margin-top:20px;background:#fff;padding:15px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1)}
h3{color:#2c5282;margin-top:20px;padding:10px 15px;background:#e8f4fd;border-radius:6px}
h4{color:#666;margin-top:15px;border-left:4px solid #4a90d9;padding-left:10px}
table{border-collapse:collapse;width:100%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:20px}
td,th{border:1px solid #ddd;padding:8px 12px;text-align:left;vertical-align:top}
th{background:#4a90d9;color:#fff;font-weight:600}
tr:nth-child(even){background:#f9f9f9}
tr:hover{background:#e8f4fd}
.pattern-section{margin:15px 0;padding:20px;background:#fff;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}
.pattern-name{font-weight:bold;font-size:16px;margin-bottom:10px}
.pattern-name.ref-num{color:var(--ref-num)}
.pattern-name.ref-unnum{color:var(--ref-unnum)}
.pattern-name.ref-fn{color:var(--ref-fn)}
.pattern-name.figtab{color:var(--figtab)}
.pattern-name.partlab-fig{color:var(--partlab-fig)}
.pattern-name.partlab-tab{color:var(--partlab-tab)}
.journal-list{background:#f0f7ff;padding:10px 15px;border-radius:6px;margin:10px 0}
.journal-tag{display:inline-block;background:#4a90d9;color:#fff;padding:3px 8px;margin:2px;border-radius:4px;font-size:12px}
.attr-value{font-family:monospace;background:#f5f5f5;padding:2px 6px;border-radius:3px;display:inline-block}
.category-header{padding:12px 15px;margin:15px 0 10px;border-radius:8px;color:#fff;font-size:16px;font-weight:bold}
.category-header.ref-num{background:linear-gradient(135deg,#2196F3,#1976D2)}
.category-header.ref-unnum{background:linear-gradient(135deg,#9c27b0,#7b1fa2)}
.category-header.ref-fn{background:linear-gradient(135deg,#ff5722,#e64a19)}
.category-header.figtab{background:linear-gradient(135deg,#ff9800,#f57c00)}
.category-header.partlab-fig{background:linear-gradient(135deg,#00bcd4,#0097a7)}
.category-header.partlab-tab{background:linear-gradient(135deg,#8bc34a,#689f38)}
.category-header.unique{background:linear-gradient(135deg,#607d8b,#455a64)}
.warning{background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:15px;margin:15px 0}
.warning-title{color:#856404;font-weight:bold}
.diff-section{background:#ffe6e6;border-left:4px solid #dc3545;padding:15px;margin:10px 0;border-radius:0 8px 8px 0}
.diff-attr{background:#ffcccc;padding:2px 6px;border-radius:3px;font-family:monospace}
.match-attr{background:#ccffcc;padding:2px 6px;border-radius:3px;font-family:monospace}
.compare-table th{background:#6c757d}
.count-badge{display:inline-block;background:#dc3545;color:#fff;padding:2px 8px;border-radius:12px;font-size:12px;margin-left:8px}
.count-badge.ok{background:#28a745}
.count-badge.info{background:#607d8b}
.pct-badge{display:inline-block;background:#17a2b8;color:#fff;padding:3px 10px;border-radius:15px;font-size:13px;font-weight:bold;margin-left:8px}
.pct-badge.high{background:#28a745}
.pct-badge.medium{background:#ffc107;color:#333}
.pct-badge.low{background:#dc3545}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:15px;margin:20px 0}
.stats-card{background:#fff;border-radius:10px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.1);border-left:4px solid var(--primary)}
.stats-card.ref-num{border-left-color:var(--ref-num)}
.stats-card.ref-unnum{border-left-color:var(--ref-unnum)}
.stats-card.ref-fn{border-left-color:var(--ref-fn)}
.stats-card.figtab{border-left-color:var(--figtab)}
.stats-card.partlab-fig{border-left-color:var(--partlab-fig)}
.stats-card.partlab-tab{border-left-color:var(--partlab-tab)}
.stats-card h4{margin:0 0 10px;color:#333}
.stats-value{font-size:28px;font-weight:bold;color:var(--primary)}
.stats-label{font-size:12px;color:#666;margin-top:5px}
.stats-detail{margin-top:10px;padding-top:10px;border-top:1px solid #eee;font-size:13px;color:#555}
.consolidated-box{background:linear-gradient(135deg,#2c3e50,#34495e);color:#fff;border-radius:12px;padding:25px;margin:20px 0}
.consolidated-box h3{margin:0 0 15px;font-size:18px}
.consolidated-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px}
.consolidated-item{text-align:center;padding:15px;background:rgba(255,255,255,0.1);border-radius:8px}
.consolidated-item .value{font-size:24px;font-weight:bold}
.consolidated-item .label{font-size:11px;opacity:0.8;margin-top:5px}
.test-suggestion-box{background:#fff;border-radius:10px;padding:20px;margin:15px 0;box-shadow:0 2px 8px rgba(0,0,0,0.1);border-left:4px solid #28a745}
.test-suggestion-box.overall{border-left-color:#6f42c1;background:linear-gradient(135deg,#f8f9fa,#e9ecef)}
.test-suggestion-box h4{margin:0 0 15px;color:#333;display:flex;align-items:center;gap:10px}
.test-journal{display:inline-flex;align-items:center;background:#28a745;color:#fff;padding:5px 12px;margin:4px;border-radius:20px;font-size:13px;font-weight:500}
.test-journal.primary{background:#6f42c1}
.test-journal .covers{background:rgba(255,255,255,0.3);padding:2px 6px;border-radius:10px;margin-left:6px;font-size:11px}
.coverage-meter{background:#e9ecef;border-radius:10px;height:24px;overflow:hidden;margin:10px 0}
.coverage-fill{height:100%;background:linear-gradient(90deg,#28a745,#20c997);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:bold;font-size:12px;transition:width 0.5s}
.coverage-fill.full{background:linear-gradient(90deg,#28a745,#198754)}
.client-section{background:#f8f9fa;border-radius:10px;padding:20px;margin:15px 0;border:1px solid #dee2e6}
.client-section h5{margin:0 0 15px;color:#495057;border-bottom:2px solid #dee2e6;padding-bottom:10px}
.pattern-coverage-list{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.pattern-tag{background:#e9ecef;color:#495057;padding:4px 10px;border-radius:15px;font-size:12px;display:inline-flex;align-items:center;gap:5px}
.pattern-tag .check{color:#28a745}
.min-set-badge{background:#17a2b8;color:#fff;padding:8px 15px;border-radius:20px;font-weight:bold;display:inline-block;margin:10px 0}
.unique-table{margin-top:10px}
.unique-table td{padding:6px 12px}
.unique-table code{background:#e9ecef;padding:2px 6px;border-radius:4px;font-size:13px}
.type-filter{background:#fff;padding:15px;margin-bottom:20px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1)}
.type-filter label{margin-right:15px;cursor:pointer}
.type-section{margin-bottom:30px;padding:20px;background:#fafafa;border-radius:10px}
.ref-subcategory{margin:15px 0;padding:15px;background:#fff;border-radius:8px;border-left:4px solid var(--primary)}
.compare-grid{overflow-x:auto}
.compare-grid table{min-width:800px}
.compare-grid th.attr-col{background:#34495e;min-width:200px;position:sticky;left:0;z-index:1}
.compare-grid th.val-col{background:#2196F3;min-width:120px}
.compare-grid th.jnl-col{background:#1976D2;min-width:150px}
.compare-grid td.attr-cell{background:#ecf0f1;font-weight:bold;position:sticky;left:0;z-index:1}
.compare-grid td.val-cell{background:#e3f2fd}
.compare-grid td.jnl-cell{background:#fff;font-size:11px}
.unique-value{display:inline-block;background:#e0e0e0;color:#333;padding:4px 10px;margin:3px;border-radius:15px;font-family:monospace;font-size:13px}
.unique-section{margin:15px 0;padding:15px;background:#fff;border-radius:8px;border-left:4px solid #607d8b}
.unique-attr{font-weight:bold;color:#455a64;margin-bottom:8px}
</style>""")
    H.append("""<script>
function showTab(tabId){document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));document.getElementById(tabId).classList.add('active');document.querySelector('[data-tab="'+tabId+'"]').classList.add('active');}
function filterType(t){document.querySelectorAll('.type-section').forEach(s=>{s.style.display=(t=='all'||s.dataset.type==t)?'block':'none';});}
</script>""")
    H.append("</head><body>")
    
    # Sidebar
    H.append("<div class='sidebar'>")
    H.append(f"<div class='sidebar-header'><h2>Pattern Report</h2><div class='ts'>{ts}</div></div>")
    H.append("<div class='nav-item active' data-tab='tab-overall' onclick=\"showTab('tab-overall')\"><span class='icon'>📊</span>Overall Report</div>")
    H.append("<div class='nav-item' data-tab='tab-ref' onclick=\"showTab('tab-ref')\"><span class='icon'>📚</span>Reference Pattern</div>")
    H.append("<div class='nav-item' data-tab='tab-figtab' onclick=\"showTab('tab-figtab')\"><span class='icon'>📈</span>Figure/Table Pattern</div>")
    H.append("<div class='nav-item' data-tab='tab-partlab' onclick=\"showTab('tab-partlab')\"><span class='icon'>🏷️</span>Part Label Pattern</div>")
    H.append("<div class='nav-item' data-tab='tab-unique' onclick=\"showTab('tab-unique')\"><span class='icon'>🎯</span>Unique Pattern</div>")
    H.append("<div class='nav-item' data-tab='tab-compare' onclick=\"showTab('tab-compare')\"><span class='icon'>🔍</span>Pattern Compare</div>")
    H.append("<div class='nav-item' data-tab='tab-test' onclick=\"showTab('tab-test')\"><span class='icon'>🧪</span>Unit Test Suggestion</div>")
    H.append("</div>")
    
    # Main content
    H.append("<div class='main-content'>")
    
    # TAB 1: Overall Report
    H.append("<div id='tab-overall' class='tab-content active'>")
    H.append("<h1>Overall Report</h1>")
    
    # Consolidated percentage summary box
    H.append("<div class='consolidated-box'>")
    H.append("<h3>📊 Consolidated Pattern Match Summary</h3>")
    H.append("<div class='consolidated-grid'>")
    
    # Reference Numbered
    if ref_num_stats['total'] > 0:
        H.append(f"<div class='consolidated-item'><div class='value'>{ref_num_stats['max_pct']:.1f}%</div><div class='label'>Numbered Ref<br>({ref_num_stats['max_match']}/{ref_num_stats['total']} journals)</div></div>")
    
    # Reference Unnumbered
    if ref_unnum_stats['total'] > 0:
        H.append(f"<div class='consolidated-item'><div class='value'>{ref_unnum_stats['max_pct']:.1f}%</div><div class='label'>Unnumbered Ref<br>({ref_unnum_stats['max_match']}/{ref_unnum_stats['total']} journals)</div></div>")
    
    # Reference Footnote
    if ref_fn_stats['total'] > 0:
        H.append(f"<div class='consolidated-item'><div class='value'>{ref_fn_stats['max_pct']:.1f}%</div><div class='label'>Footnote Ref<br>({ref_fn_stats['max_match']}/{ref_fn_stats['total']} journals)</div></div>")
    
    # Figure/Table
    if figtab_stats['total'] > 0:
        H.append(f"<div class='consolidated-item'><div class='value'>{figtab_stats['max_pct']:.1f}%</div><div class='label'>Figure/Table<br>({figtab_stats['max_match']}/{figtab_stats['total']} journals)</div></div>")
    
    # Part Label Figure
    if partlab_fig_stats['total'] > 0:
        H.append(f"<div class='consolidated-item'><div class='value'>{partlab_fig_stats['max_pct']:.1f}%</div><div class='label'>PartLabel Fig<br>({partlab_fig_stats['max_match']}/{partlab_fig_stats['total']} journals)</div></div>")
    
    # Part Label Table
    if partlab_tab_stats['total'] > 0:
        H.append(f"<div class='consolidated-item'><div class='value'>{partlab_tab_stats['max_pct']:.1f}%</div><div class='label'>PartLabel Tab<br>({partlab_tab_stats['max_match']}/{partlab_tab_stats['total']} journals)</div></div>")
    
    H.append("</div></div>")
    
    # Stats cards for each category
    H.append("<div class='stats-grid'>")
    
    def render_stats_card(stats, title, css_class, icon):
        if stats['total'] == 0:
            return ""
        pct_class = 'high' if stats['max_pct'] >= 50 else ('medium' if stats['max_pct'] >= 25 else 'low')
        top_pattern = stats['patterns'][0] if stats['patterns'] else None
        card = f"<div class='stats-card {css_class}'>"
        card += f"<h4>{icon} {title}</h4>"
        card += f"<div class='stats-value'>{stats['max_pct']:.1f}%</div>"
        card += f"<div class='stats-label'>Best Pattern Match</div>"
        card += f"<div class='stats-detail'>"
        card += f"<strong>Total Journals:</strong> {stats['total']}<br>"
        card += f"<strong>Total Patterns:</strong> {len(stats['patterns'])}<br>"
        if top_pattern:
            card += f"<strong>Top Pattern:</strong> {top_pattern['name']} ({top_pattern['count']} journals)"
        card += "</div></div>"
        return card
    
    H.append(render_stats_card(ref_num_stats, 'Numbered References', 'ref-num', '🔢'))
    H.append(render_stats_card(ref_unnum_stats, 'Unnumbered References', 'ref-unnum', '📖'))
    H.append(render_stats_card(ref_fn_stats, 'Footnote References', 'ref-fn', '📝'))
    H.append(render_stats_card(figtab_stats, 'Figure/Table', 'figtab', '📊'))
    H.append(render_stats_card(partlab_fig_stats, 'Part Label (Figure)', 'partlab-fig', '🖼️'))
    H.append(render_stats_card(partlab_tab_stats, 'Part Label (Table)', 'partlab-tab', '📋'))
    H.append("</div>")
    
    H.append("<div class='type-filter'><strong>Filter:</strong> ")
    H.append("<label><input type=radio name=tf value=all checked onclick=\"filterType('all')\">All</label>")
    H.append("<label><input type=radio name=tf value=journals onclick=\"filterType('journals')\">Journals</label>")
    H.append("<label><input type=radio name=tf value=books onclick=\"filterType('books')\">Books</label></div>")
    
    for type_name in ['books', 'journals']:
        items = by_type.get(type_name, [])
        if not items: continue
        H.append(f"<div class='type-section' data-type='{type_name}'>")
        H.append(f"<h2>{type_name.capitalize()}</h2>")
        
        for sec in ['Figure', 'Table']:
            rows = []
            for item in items:
                S = item.get(sec, {})
                if not S: continue
                client = item['client']
                for k, v in S.items():
                    if k in ('dircite', 'indircite'):
                        for ca, arr in v.items():
                            for b in arr:
                                rows.append({'attr': f"{k}.{ca}", 'value': b['value'], 'journals': b['journal'], 'client': client, 'cite_type': k, 'cite_attr': ca})
                    else:
                        for b in v:
                            rows.append({'attr': k, 'value': b['value'], 'journals': b['journal'], 'client': client, 'cite_type': None, 'cite_attr': None})
            
            # Unify dircite/indircite rows if they have identical values and journals
            def unify_cite_rows(rows_list):
                unified = []
                processed_keys = set()
                
                for r in rows_list:
                    row_key = (r['client'], r['attr'], r['value'], tuple(sorted(r['journals'])))
                    if row_key in processed_keys:
                        continue
                    
                    if r['cite_type'] == 'dircite':
                        # Look for matching indircite
                        indircite_attr = f"indircite.{r['cite_attr']}"
                        matching = None
                        for other in rows_list:
                            if (other['client'] == r['client'] and 
                                other['attr'] == indircite_attr and 
                                other['value'] == r['value'] and 
                                tuple(sorted(other['journals'])) == tuple(sorted(r['journals']))):
                                matching = other
                                break
                        
                        if matching:
                            # Unify into 'cite'
                            unified_row = r.copy()
                            unified_row['attr'] = f"cite.{r['cite_attr']}"
                            unified.append(unified_row)
                            processed_keys.add(row_key)
                            processed_keys.add((matching['client'], matching['attr'], matching['value'], tuple(sorted(matching['journals']))))
                        else:
                            unified.append(r)
                            processed_keys.add(row_key)
                    elif r['cite_type'] == 'indircite':
                        # Check if already processed with dircite
                        dircite_attr = f"dircite.{r['cite_attr']}"
                        already_unified = False
                        for other in rows_list:
                            if (other['client'] == r['client'] and 
                                other['attr'] == dircite_attr and 
                                other['value'] == r['value'] and 
                                tuple(sorted(other['journals'])) == tuple(sorted(r['journals']))):
                                # This will be/was unified via dircite
                                already_unified = True
                                break
                        
                        if not already_unified:
                            unified.append(r)
                            processed_keys.add(row_key)
                    else:
                        unified.append(r)
                        processed_keys.add(row_key)
                
                return unified
            
            rows = unify_cite_rows(rows)
            
            if rows:
                H.append(f"<h3>{sec}</h3>")
                H.append("<table><tr><th>Client</th><th>Attribute</th><th>Value</th><th>Journals</th></tr>")
                rows.sort(key=lambda x: (x['client'], x['attr']))
                for r in rows:
                    H.append(f"<tr><td>{r['client']}</td><td>{r['attr']}</td><td><span class=attr-value>{r['value']}</span></td><td>{', '.join(r['journals'])}</td></tr>")
                H.append("</table>")
        
        # Reference summary
        H.append("<h3>Reference</h3>")
        ref_summary = {'numbered': [], 'unnumbered': [], 'footnote': []}
        for item in items:
            S = item.get('Reference', {})
            for b in S.get('ref.data-label-format', []):
                for j in b['journal']:
                    ct = journal_info.get(j, {}).get('citation_type', '')
                    if ct == 'FOOTNOTE':
                        ref_summary['footnote'].append(j)
                    elif 'unnumbered' in b['value']:
                        ref_summary['unnumbered'].append(j)
                    else:
                        ref_summary['numbered'].append(j)
        
        H.append("<div class='ref-subcategory' style='border-left-color:var(--ref-num)'><strong>🔢 Numbered:</strong> " + (', '.join(sorted(set(ref_summary['numbered']))) or 'None') + "</div>")
        H.append("<div class='ref-subcategory' style='border-left-color:var(--ref-unnum)'><strong>📖 Unnumbered:</strong> " + (', '.join(sorted(set(ref_summary['unnumbered']))) or 'None') + "</div>")
        H.append("<div class='ref-subcategory' style='border-left-color:var(--ref-fn)'><strong>📝 Footnote:</strong> " + (', '.join(sorted(set(ref_summary['footnote']))) or 'None') + "</div>")
        H.append("</div>")
    H.append("</div>")
    
    # Helper: render comparison grid with percentages
    def render_comparison_grid(patterns, pat_mapping, title, css_class, stats=None):
        result = []
        if not patterns:
            result.append(f"<p>No {title} patterns found.</p>")
            return result
        
        # Calculate total for percentage
        total_journals_in_cat = sum(len(js) for js in patterns.values())
        
        result.append(f"<div class='category-header {css_class}'>{title}")
        if stats:
            result.append(f" <span class='pct-badge'>Best: {stats['max_pct']:.1f}%</span>")
        result.append("</div>")
        
        sorted_patterns = sorted(patterns.items(), key=lambda x: -len(x[1]))
        
        all_attrs = set()
        pattern_attrs = {}
        for pname, journals in sorted_patterns:
            sig = pat_mapping.get(pname, '')
            attrs = {}
            if sig:
                for part in sig.split(';'):
                    if '=' in part:
                        k, v = part.split('=', 1)
                        attrs[k] = v
                        all_attrs.add(k)
            pattern_attrs[pname] = attrs
        
        all_attrs = sorted(all_attrs)
        
        result.append("<div class='compare-grid'>")
        result.append("<table>")
        
        result.append("<tr><th class='attr-col'>Attribute</th>")
        for i, (pname, journals) in enumerate(sorted_patterns):
            is_max = i == 0
            pct = (len(journals) / total_journals_in_cat * 100) if total_journals_in_cat > 0 else 0
            pct_class = 'high' if pct >= 50 else ('medium' if pct >= 25 else 'low')
            max_style = " style='background:#4CAF50'" if is_max else ""
            result.append(f"<th colspan='2'{max_style}>{pname}<br><span style='font-size:11px'>({len(journals)} journals)</span><br><span class='pct-badge {pct_class}'>{pct:.1f}%</span></th>")
        result.append("</tr>")
        
        result.append("<tr><th class='attr-col'></th>")
        for pname, journals in sorted_patterns:
            result.append("<th class='val-col'>Value</th><th class='jnl-col'>Journals</th>")
        result.append("</tr>")
        
        for attr in all_attrs:
            result.append("<tr>")
            result.append(f"<td class='attr-cell'>{attr}</td>")
            for pname, journals in sorted_patterns:
                val = pattern_attrs[pname].get(attr, '-')
                jnl_str = ', '.join(journals[:5])
                if len(journals) > 5:
                    jnl_str += f" (+{len(journals)-5})"
                result.append(f"<td class='val-cell'><span class='attr-value'>{val}</span></td>")
                result.append(f"<td class='jnl-cell'>{jnl_str}</td>")
            result.append("</tr>")
        
        result.append("</table></div>")
        
        result.append("<h4>Full Journal List with Percentage:</h4>")
        for pname, journals in sorted_patterns:
            pct = (len(journals) / total_journals_in_cat * 100) if total_journals_in_cat > 0 else 0
            pct_class = 'high' if pct >= 50 else ('medium' if pct >= 25 else 'low')
            result.append(f"<div class='pattern-section'>")
            result.append(f"<div class='pattern-name {css_class}'>{pname} <span class='count-badge {'ok' if len(journals)>=3 else ''}'>{len(journals)}</span> <span class='pct-badge {pct_class}'>{pct:.1f}%</span></div>")
            result.append("<div class='journal-list'>")
            for j in sorted(journals):
                result.append(f"<span class='journal-tag'>{j}</span>")
            result.append("</div></div>")
        
        return result
    
    # TAB 2: Reference Pattern
    H.append("<div id='tab-ref' class='tab-content'>")
    H.append("<h1>Reference Patterns</h1>")
    H.append("<p>Patterns sorted by journal count (maximum matched first). Percentage shows match ratio within category.</p>")
    H.extend(render_comparison_grid(ref_num_patterns, ref_num_mapping, "🔢 Numbered References", "ref-num", ref_num_stats))
    H.extend(render_comparison_grid(ref_unnum_patterns, ref_unnum_mapping, "📖 Unnumbered References", "ref-unnum", ref_unnum_stats))
    H.extend(render_comparison_grid(ref_fn_patterns, ref_fn_mapping, "📝 Footnote References", "ref-fn", ref_fn_stats))
    H.append("</div>")
    
    # TAB 3: Figure/Table Pattern
    H.append("<div id='tab-figtab' class='tab-content'>")
    H.append("<h1>Figure/Table Patterns</h1>")
    H.append("<p>Patterns sorted by journal count (maximum matched first). Percentage shows match ratio within category.</p>")
    H.extend(render_comparison_grid(figtab_patterns, figtab_mapping, "📊 Figure/Table Patterns", "figtab", figtab_stats))
    H.append("</div>")
    
    # TAB 4: Part Label Pattern
    H.append("<div id='tab-partlab' class='tab-content'>")
    H.append("<h1>Part Label Patterns</h1>")
    H.append("<p>Patterns for part_lab_* attributes (prefix_num, case, format, double_sep). Percentage shows match ratio within category.</p>")
    H.extend(render_comparison_grid(partlab_fig_patterns, partlab_fig_mapping, "🖼️ Figure Part Labels", "partlab-fig", partlab_fig_stats))
    H.extend(render_comparison_grid(partlab_tab_patterns, partlab_tab_mapping, "📋 Table Part Labels", "partlab-tab", partlab_tab_stats))
    H.append("</div>")
    
    # TAB 5: Unique Pattern (NEW)
    H.append("<div id='tab-unique' class='tab-content'>")
    H.append("<h1>Unique Pattern</h1>")
    H.append("<p>List of all unique patterns found for each attribute across all journals.</p>")
    
    # Group by category
    categories = {
        'Figure': {},
        'Table': {},
        'Reference': {},
        'PartLabel.Figure': {},
        'PartLabel.Table': {}
    }
    
    for attr_key, values in sorted(unique_values.items()):
        for cat in categories:
            if attr_key.startswith(cat):
                categories[cat][attr_key] = values
                break
    
    cat_styles = {
        'Figure': ('figtab', '📊 Figure Attributes'),
        'Table': ('figtab', '📋 Table Attributes'),
        'Reference': ('ref-num', '📚 Reference Attributes'),
        'PartLabel.Figure': ('partlab-fig', '🖼️ Part Label (Figure) Attributes'),
        'PartLabel.Table': ('partlab-tab', '📋 Part Label (Table) Attributes')
    }
    
    for cat, attrs in categories.items():
        if not attrs:
            continue
        style, title = cat_styles[cat]
        H.append(f"<div class='category-header {style}'>{title}</div>")
        
        # Render as compact table
        H.append("<table class='unique-table'>")
        H.append("<tr><th style='width:35%'>Attribute</th><th>Values</th></tr>")
        for attr_key in sorted(attrs.keys()):
            values = sorted(attrs[attr_key])
            values_html = " ".join(f"<span class='attr-value'>{v}</span>" for v in values)
            H.append(f"<tr><td><code>{attr_key}</code> <span class='count-badge info'>{len(values)}</span></td><td>{values_html}</td></tr>")
        H.append("</table>")
    
    H.append("</div>")
    
    # TAB 6: Pattern Compare
    H.append("<div id='tab-compare' class='tab-content'>")
    H.append("<h1>Pattern Compare</h1>")
    H.append("<p>Patterns with less than 3 journals are flagged as anomalies.</p>")
    
    def render_compare(patterns, pat_mapping, title, css_class):
        result = []
        small = {p: js for p, js in patterns.items() if len(js) < 3}
        large = {p: js for p, js in patterns.items() if len(js) >= 3}
        if not small:
            result.append(f"<p>✅ All {title} patterns have 3+ journals.</p>")
            return result
        result.append(f"<div class='warning'><div class='warning-title'>⚠️ {len(small)} {title} pattern(s) with less than 3 journals</div></div>")
        
        def parse_sig(sig):
            return {part.split('=', 1)[0]: part.split('=', 1)[1] for part in sig.split(';') if '=' in part} if sig else {}
        
        common_attrs = {}
        for p, js in large.items():
            for k, v in parse_sig(pat_mapping.get(p, '')).items():
                common_attrs.setdefault(k, {}).setdefault(v, []).append(p)
        most_common = {k: max(vs.items(), key=lambda x: len(x[1]))[0] for k, vs in common_attrs.items()} if common_attrs else {}
        
        for pname in sorted(small.keys(), key=lambda x: int(x.split('_')[-1])):
            journals = small[pname]
            attrs = parse_sig(pat_mapping.get(pname, ''))
            result.append("<div class='diff-section'>")
            result.append(f"<div class='pattern-name {css_class}'>{pname} <span class='count-badge'>{len(journals)}</span></div>")
            result.append("<div class='journal-list'>")
            for j in sorted(journals):
                result.append(f"<span class='journal-tag'>{j}</span>")
            result.append("</div>")
            if most_common:
                result.append("<table class='compare-table'><tr><th>Attribute</th><th>This</th><th>Common</th><th>Status</th></tr>")
                for attr in sorted(set(attrs.keys()) | set(most_common.keys())):
                    this_val = attrs.get(attr, '(missing)')
                    common_val = most_common.get(attr, '(n/a)')
                    match = this_val == common_val
                    result.append(f"<tr><td>{attr}</td><td><span class='{'match' if match else 'diff'}-attr'>{this_val}</span></td><td><span class='attr-value'>{common_val}</span></td><td>{'✅' if match else '❌'}</td></tr>")
                result.append("</table>")
            result.append("</div>")
        return result
    
    H.extend(render_compare(ref_num_patterns, ref_num_mapping, "Numbered Ref", "ref-num"))
    H.extend(render_compare(ref_unnum_patterns, ref_unnum_mapping, "Unnumbered Ref", "ref-unnum"))
    H.extend(render_compare(ref_fn_patterns, ref_fn_mapping, "Footnote Ref", "ref-fn"))
    H.extend(render_compare(figtab_patterns, figtab_mapping, "Figure/Table", "figtab"))
    H.extend(render_compare(partlab_fig_patterns, partlab_fig_mapping, "Figure Part Label", "partlab-fig"))
    H.extend(render_compare(partlab_tab_patterns, partlab_tab_mapping, "Table Part Label", "partlab-tab"))
    H.append("</div>")
    
    # TAB 7: Unit Test Suggestion
    H.append("<div id='tab-test' class='tab-content'>")
    H.append("<h1>🧪 Unit Test Suggestion</h1>")
    H.append("<p>Recommended journals to cover all unique patterns. Select one journal from each pattern to achieve 100% coverage.</p>")
    
    # Helper function to find minimum set of journals covering all patterns
    def find_min_coverage_set(patterns):
        """Find minimum set of journals that covers all patterns (greedy set cover)"""
        if not patterns:
            return [], {}
        
        # Build reverse mapping: journal -> patterns it covers
        journal_patterns = {}
        for pname, journals in patterns.items():
            for j in journals:
                journal_patterns.setdefault(j, set()).add(pname)
        
        uncovered = set(patterns.keys())
        selected = []
        coverage_map = {}  # journal -> patterns it covers
        
        while uncovered and journal_patterns:
            # Find journal that covers most uncovered patterns
            best_journal = max(journal_patterns.keys(), 
                              key=lambda j: len(journal_patterns[j] & uncovered))
            covered_by_best = journal_patterns[best_journal] & uncovered
            
            if not covered_by_best:
                break
            
            selected.append(best_journal)
            coverage_map[best_journal] = list(covered_by_best)
            uncovered -= covered_by_best
        
        return selected, coverage_map
    
    # Calculate minimum coverage sets for each category
    ref_num_min, ref_num_cov = find_min_coverage_set(ref_num_patterns)
    ref_unnum_min, ref_unnum_cov = find_min_coverage_set(ref_unnum_patterns)
    ref_fn_min, ref_fn_cov = find_min_coverage_set(ref_fn_patterns)
    figtab_min, figtab_cov = find_min_coverage_set(figtab_patterns)
    partlab_fig_min, partlab_fig_cov = find_min_coverage_set(partlab_fig_patterns)
    partlab_tab_min, partlab_tab_cov = find_min_coverage_set(partlab_tab_patterns)
    
    # Overall consolidated minimum set (all patterns from all categories)
    all_patterns_combined = {}
    for prefix, patterns_dict in [('RefNum', ref_num_patterns), ('RefUnnum', ref_unnum_patterns), 
                                   ('RefFN', ref_fn_patterns), ('FigTab', figtab_patterns),
                                   ('PartLabFig', partlab_fig_patterns), ('PartLabTab', partlab_tab_patterns)]:
        for pname, journals in patterns_dict.items():
            all_patterns_combined[f"{prefix}:{pname}"] = journals
    
    overall_min, overall_cov = find_min_coverage_set(all_patterns_combined)
    
    # Build client -> journals mapping
    client_journals = {}
    for item in data:
        client = item.get('client', 'Unknown')
        for j in item.get('journals', []):
            client_journals.setdefault(client, set()).add(j)
    # Also collect from pattern data
    for patterns_dict in [ref_num_patterns, ref_unnum_patterns, ref_fn_patterns, 
                          figtab_patterns, partlab_fig_patterns, partlab_tab_patterns]:
        for journals in patterns_dict.values():
            for j in journals:
                # Find client for this journal from data
                for item in data:
                    if j in [jnl for sec in ['Figure', 'Table', 'Reference'] 
                            for vals in item.get(sec, {}).values() 
                            for b in (vals if isinstance(vals, list) else []) 
                            for jnl in b.get('journal', [])]:
                        client_journals.setdefault(item.get('client', 'Unknown'), set()).add(j)
    
    # Overall Consolidated Suggestion Box
    H.append("<div class='test-suggestion-box overall'>")
    H.append("<h4>🎯 Overall Minimum Test Set (All Categories)</h4>")
    total_patterns = len(all_patterns_combined)
    H.append(f"<p>To cover <strong>all {total_patterns} patterns</strong> across all categories, you need minimum <strong>{len(overall_min)} journal(s)</strong>:</p>")
    H.append(f"<div class='min-set-badge'>Minimum: {len(overall_min)} journal(s) for 100% coverage</div>")
    H.append("<div style='margin:15px 0'>")
    for j in overall_min:
        cover_count = len(overall_cov.get(j, []))
        H.append(f"<span class='test-journal primary'>{j}<span class='covers'>covers {cover_count}</span></span>")
    H.append("</div>")
    
    # Coverage meter
    coverage_pct = 100 if overall_min else 0
    H.append(f"<div class='coverage-meter'><div class='coverage-fill full' style='width:{coverage_pct}%'>100% Pattern Coverage</div></div>")
    H.append("</div>")
    
    # Per-category suggestion helper
    def render_category_suggestion(min_set, cov_map, patterns, title, css_class, icon):
        result = []
        if not patterns:
            return result
        
        result.append(f"<div class='test-suggestion-box'>")
        result.append(f"<h4>{icon} {title}</h4>")
        total = len(patterns)
        result.append(f"<p>Total patterns: <strong>{total}</strong> | Minimum journals needed: <strong>{len(min_set)}</strong></p>")
        
        if min_set:
            result.append("<div style='margin:10px 0'>")
            for j in min_set:
                cover_count = len(cov_map.get(j, []))
                pct_of_total = (cover_count / total * 100) if total > 0 else 0
                result.append(f"<span class='test-journal'>{j}<span class='covers'>{cover_count} ({pct_of_total:.0f}%)</span></span>")
            result.append("</div>")
            
            # Show pattern coverage details
            result.append("<details><summary style='cursor:pointer;color:#6c757d;margin:10px 0'>Show pattern coverage details</summary>")
            result.append("<div class='pattern-coverage-list'>")
            for j in min_set:
                for p in sorted(cov_map.get(j, [])):
                    result.append(f"<span class='pattern-tag'><span class='check'>✓</span>{p} → {j}</span>")
            result.append("</div></details>")
        
        result.append("</div>")
        return result
    
    # Render per-category suggestions
    H.extend(render_category_suggestion(ref_num_min, ref_num_cov, ref_num_patterns, "Numbered References", "ref-num", "🔢"))
    H.extend(render_category_suggestion(ref_unnum_min, ref_unnum_cov, ref_unnum_patterns, "Unnumbered References", "ref-unnum", "📖"))
    H.extend(render_category_suggestion(ref_fn_min, ref_fn_cov, ref_fn_patterns, "Footnote References", "ref-fn", "📝"))
    H.extend(render_category_suggestion(figtab_min, figtab_cov, figtab_patterns, "Figure/Table", "figtab", "📊"))
    H.extend(render_category_suggestion(partlab_fig_min, partlab_fig_cov, partlab_fig_patterns, "Part Label (Figure)", "partlab-fig", "🖼️"))
    H.extend(render_category_suggestion(partlab_tab_min, partlab_tab_cov, partlab_tab_patterns, "Part Label (Table)", "partlab-tab", "📋"))
    
    # Client-level suggestions
    H.append("<h2 style='margin-top:30px'>📁 Client-Level Test Suggestions</h2>")
    H.append("<p>Recommended test journals grouped by client. Shows which journals from each client are included in the minimum test set.</p>")
    
    overall_min_set = set(overall_min)
    
    for client in sorted(client_journals.keys()):
        journals = client_journals[client]
        recommended = [j for j in journals if j in overall_min_set]
        other = [j for j in journals if j not in overall_min_set]
        
        H.append(f"<div class='client-section'>")
        H.append(f"<h5>📂 {client}")
        if recommended:
            H.append(f" <span class='count-badge ok'>{len(recommended)} recommended</span>")
        H.append("</h5>")
        
        if recommended:
            H.append("<p><strong>✅ Recommended for testing (covers unique patterns):</strong></p>")
            H.append("<div style='margin:10px 0'>")
            for j in sorted(recommended):
                patterns_covered = overall_cov.get(j, [])
                H.append(f"<span class='test-journal primary'>{j}<span class='covers'>{len(patterns_covered)} patterns</span></span>")
            H.append("</div>")
        
        if other:
            H.append(f"<details><summary style='cursor:pointer;color:#6c757d;margin:10px 0'>Other journals ({len(other)})</summary>")
            H.append("<div style='margin:10px 0'>")
            for j in sorted(other):
                H.append(f"<span class='journal-tag'>{j}</span>")
            H.append("</div></details>")
        
        H.append("</div>")
    
    # Summary table
    H.append("<h2 style='margin-top:30px'>📊 Coverage Summary Table</h2>")
    H.append("<table>")
    H.append("<tr><th>Category</th><th>Total Patterns</th><th>Min Journals Needed</th><th>Coverage Efficiency</th></tr>")
    
    categories_summary = [
        ("Numbered Ref", ref_num_patterns, ref_num_min),
        ("Unnumbered Ref", ref_unnum_patterns, ref_unnum_min),
        ("Footnote Ref", ref_fn_patterns, ref_fn_min),
        ("Figure/Table", figtab_patterns, figtab_min),
        ("Part Label Fig", partlab_fig_patterns, partlab_fig_min),
        ("Part Label Tab", partlab_tab_patterns, partlab_tab_min),
    ]
    
    for name, patterns, min_set in categories_summary:
        if patterns:
            total = len(patterns)
            min_count = len(min_set)
            efficiency = (total / min_count) if min_count > 0 else 0
            eff_class = 'ok' if efficiency >= 2 else ''
            H.append(f"<tr><td>{name}</td><td>{total}</td><td>{min_count}</td><td><span class='count-badge {eff_class}'>{efficiency:.1f}x</span></td></tr>")
    
    # Grand total row
    total_all_patterns = sum(len(p) for _, p, _ in categories_summary if p)
    total_min_journals = len(overall_min)
    overall_efficiency = (total_all_patterns / total_min_journals) if total_min_journals > 0 else 0
    H.append(f"<tr style='background:#f8f9fa;font-weight:bold'><td>TOTAL (All Categories)</td><td>{total_all_patterns}</td><td>{total_min_journals}</td><td><span class='pct-badge high'>{overall_efficiency:.1f}x</span></td></tr>")
    H.append("</table>")
    
    H.append("</div>")
    
    H.append("</div>")  # main-content
    H.append("</body></html>")
    return "\n".join(H)

"""Generate PNG charts from pattern-report JSON output.

Usage:
  python json_to_charts.py /path/to/report.json [--outdir ./charts] [--top N]

This script reads the JSON produced by the report pipeline (it expects
the `percentage_stats` structure added to the JSON) and writes simple
bar/pie charts as PNG files suitable for sharing with stakeholders.
"""
import os
import sys
import json
import argparse
from pathlib import Path
import matplotlib.pyplot as plt


def ensure_outdir(path):
    os.makedirs(path, exist_ok=True)
    return path


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def make_bar_chart(items, title, outpath, top_n=10, horizontal=True):
    if not items:
        return None
    items = sorted(items, key=lambda x: -x.get('pct', x.get('count', 0)))[:top_n]
    labels = [it['name'] for it in items]
    values = [it.get('pct', it.get('count', 0)) for it in items]

    plt.figure(figsize=(10, max(4, 0.4 * len(labels))))
    if horizontal:
        plt.barh(labels, values, color='#4a90d9')
        plt.gca().invert_yaxis()
        plt.xlabel('Percentage (%)')
    else:
        plt.bar(labels, values, color='#4a90d9')
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Percentage (%)')

    plt.title(title)
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()
    return outpath


def make_pie_chart(labels, sizes, title, outpath):
    if not sizes or sum(sizes) == 0:
        return None
    plt.figure(figsize=(6, 6))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=['#2196F3', '#FF9800', '#8BC34A'])
    plt.title(title)
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()
    return outpath


def main():
    parser = argparse.ArgumentParser(description='Generate charts from pattern-report JSON')
    parser.add_argument('json', help='Path to JSON file produced by report')
    parser.add_argument('--outdir', default=None, help='Output directory for charts (defaults to <json_dir>/charts)')
    parser.add_argument('--top', type=int, default=10, help='Top N patterns to include in bar charts')
    args = parser.parse_args()

    jpath = Path(args.json)
    if not jpath.exists():
        print('JSON file not found:', jpath)
        sys.exit(2)

    data = load_json(jpath)

    stats = data.get('percentage_stats') or data.get('percentageStats') or {}

    # If percentage_stats missing, but patterns are present, build them from patterns
    if not stats:
        patterns = data.get('patterns') or data.get('pattern') or {}
        if patterns:
            # Build per-category stats similar to report_writer._calc_category_stats
            def calc_category_stats_from_patterns(pats):
                total_in_cat = sum(len(js) for js in pats.values())
                pattern_stats = []
                for pname, journals in sorted(pats.items(), key=lambda x: -len(x[1])):
                    count = len(journals)
                    pct = (count / total_in_cat * 100) if total_in_cat > 0 else 0
                    pattern_stats.append({'name': pname, 'count': count, 'pct': pct, 'journals': journals})
                max_match = pattern_stats[0]['count'] if pattern_stats else 0
                max_pct = pattern_stats[0]['pct'] if pattern_stats else 0
                return {'total': total_in_cat, 'max_match': max_match, 'max_pct': max_pct, 'patterns': pattern_stats}

            stats = {
                'ref_numbered': calc_category_stats_from_patterns(patterns.get('ref_numbered', {})),
                'ref_unnumbered': calc_category_stats_from_patterns(patterns.get('ref_unnumbered', {})),
                'ref_footnote': calc_category_stats_from_patterns(patterns.get('ref_footnote', {})),
                'figtab': calc_category_stats_from_patterns(patterns.get('figtab', {})),
                'partlab_figure': calc_category_stats_from_patterns(patterns.get('partlab_figure', {})),
                'partlab_table': calc_category_stats_from_patterns(patterns.get('partlab_table', {})),
            }
            total_ref = stats['ref_numbered']['total'] + stats['ref_unnumbered']['total'] + stats['ref_footnote']['total']
            total_figtab = stats['figtab']['total']
            total_partlab = stats['partlab_figure']['total'] + stats['partlab_table']['total']
            stats['summary'] = {
                'total_ref': total_ref,
                'total_figtab': total_figtab,
                'total_partlab': total_partlab,
                'grand_total': total_ref + total_figtab + total_partlab
            }

    outdir = Path(args.outdir) if args.outdir else jpath.parent / 'charts'
    ensure_outdir(outdir)

    generated = []

    # Per-category bar charts
    cat_map = [
        ('ref_numbered', 'Numbered References'),
        ('ref_unnumbered', 'Unnumbered References'),
        ('ref_footnote', 'Footnote References'),
        ('figtab', 'Figure/Table'),
        ('partlab_figure', 'PartLabel Figure'),
        ('partlab_table', 'PartLabel Table')
    ]

    for key, title in cat_map:
        cat = stats.get(key, {})
        patterns = cat.get('patterns', [])
        if patterns:
            outpng = outdir / f"{key}_top{args.top}.png"
            p = make_bar_chart(patterns, f"Top {args.top} Patterns — {title}", str(outpng), top_n=args.top)
            if p:
                generated.append(p)

    # Summary pie chart (total_ref, total_figtab, total_partlab)
    summary = stats.get('summary', {})
    labels = []
    sizes = []
    if summary:
        for k, lab in [('total_ref', 'References'), ('total_figtab', 'Figure/Table'), ('total_partlab', 'PartLabel')]:
            v = summary.get(k, 0)
            labels.append(lab)
            sizes.append(v)

        outpie = outdir / 'summary_distribution.png'
        p = make_pie_chart(labels, sizes, 'Pattern Distribution by Category', str(outpie))
        if p:
            generated.append(p)

    if generated:
        print('Generated charts:')
        for g in generated:
            print(' -', g)
    else:
        print('No charts generated. Check that JSON contains "percentage_stats" with patterns.')


if __name__ == '__main__':
    main()

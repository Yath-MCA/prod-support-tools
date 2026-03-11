import json
from . import report_config as cfg
from .report_log import log


def _journal_signatures_by_category(items):
    """Build separate signatures for Reference categories, Figure/Table, and Part Label"""
    ref_numbered_sigs = {}
    ref_unnumbered_sigs = {}
    ref_footnote_sigs = {}
    figtab_sigs = {}
    partlab_figure_sigs = {}
    partlab_table_sigs = {}
    
    # First pass: determine label format and citation type for each journal
    journal_info = {}
    for item in items:
        s = item.get('Reference', {})
        for k, v in s.items():
            if k == 'ref.data-label-format':
                for b in v:
                    for j in b['journal']:
                        journal_info.setdefault(j, {})['label_format'] = b['value']
            elif k == 'citation.type':
                for b in v:
                    for j in b['journal']:
                        journal_info.setdefault(j, {})['citation_type'] = b['value']
            elif k == 'ref.text-format':
                for b in v:
                    for j in b['journal']:
                        journal_info.setdefault(j, {})['text_format'] = b['value']
    
    # Second pass: build signatures
    for item in items:
        # Part Label Figure section
        pl_fig = item.get('PartLabel_Figure', {})
        for k, v in pl_fig.items():
            for b in v:
                for j in b['journal']:
                    sig_part = f"Figure.{k}={b['value']}"
                    partlab_figure_sigs.setdefault(j, []).append(sig_part)
        
        # Part Label Table section
        pl_tab = item.get('PartLabel_Table', {})
        for k, v in pl_tab.items():
            for b in v:
                for j in b['journal']:
                    sig_part = f"Table.{k}={b['value']}"
                    partlab_table_sigs.setdefault(j, []).append(sig_part)
        
        for sec in cfg.SECTION_TAGS:
            s = item.get(sec, {})
            for k, v in s.items():
                if k in ("dircite", "indircite"):
                    for ca, arr in v.items():
                        for b in arr:
                            for j in b["journal"]:
                                sig_part = f"{sec}.{k}.{ca}={b['value']}"
                                if sec == "Reference":
                                    info = journal_info.get(j, {})
                                    ct = info.get('citation_type', '')
                                    lf = info.get('label_format', 'numbered')
                                    
                                    if ct == 'FOOTNOTE':
                                        ref_footnote_sigs.setdefault(j, []).append(sig_part)
                                    elif 'unnumbered' in lf:
                                        ref_unnumbered_sigs.setdefault(j, []).append(sig_part)
                                    else:
                                        ref_numbered_sigs.setdefault(j, []).append(sig_part)
                                else:
                                    figtab_sigs.setdefault(j, []).append(sig_part)
                elif k.startswith("ref.") or k.startswith("citation."):
                    for b in v:
                        for j in b["journal"]:
                            sig_part = f"{sec}.{k}={b['value']}"
                            info = journal_info.get(j, {})
                            ct = info.get('citation_type', '')
                            lf = info.get('label_format', 'numbered')
                            
                            if ct == 'FOOTNOTE':
                                ref_footnote_sigs.setdefault(j, []).append(sig_part)
                            elif 'unnumbered' in lf:
                                ref_unnumbered_sigs.setdefault(j, []).append(sig_part)
                            else:
                                ref_numbered_sigs.setdefault(j, []).append(sig_part)
                else:
                    for b in v:
                        for j in b["journal"]:
                            sig_part = f"{sec}.{k}={b['value']}"
                            if sec == "Reference":
                                info = journal_info.get(j, {})
                                ct = info.get('citation_type', '')
                                lf = info.get('label_format', 'numbered')
                                
                                if ct == 'FOOTNOTE':
                                    ref_footnote_sigs.setdefault(j, []).append(sig_part)
                                elif 'unnumbered' in lf:
                                    ref_unnumbered_sigs.setdefault(j, []).append(sig_part)
                                else:
                                    ref_numbered_sigs.setdefault(j, []).append(sig_part)
                            else:
                                figtab_sigs.setdefault(j, []).append(sig_part)
    
    # Helper function to unify dircite/indircite signature parts
    def unify_cite_sig_parts(parts):
        """Merge dircite/indircite signature parts into 'cite' if they have identical values"""
        # Group by attribute (without dircite/indircite prefix)
        by_attr = {}
        other_parts = []
        
        for part in parts:
            if '.dircite.' in part:
                # Extract: Section.dircite.attr=value -> Section, attr, value
                eq_idx = part.index('=')
                key = part[:eq_idx]  # Section.dircite.attr
                val = part[eq_idx+1:]  # value
                base_key = key.replace('.dircite.', '.CITE_PLACEHOLDER.')
                by_attr.setdefault(base_key, {})['dircite'] = val
            elif '.indircite.' in part:
                eq_idx = part.index('=')
                key = part[:eq_idx]
                val = part[eq_idx+1:]
                base_key = key.replace('.indircite.', '.CITE_PLACEHOLDER.')
                by_attr.setdefault(base_key, {})['indircite'] = val
            else:
                other_parts.append(part)
        
        unified_parts = other_parts[:]
        for base_key, cite_vals in by_attr.items():
            if 'dircite' in cite_vals and 'indircite' in cite_vals and cite_vals['dircite'] == cite_vals['indircite']:
                # Same value, unify to 'cite'
                unified_key = base_key.replace('.CITE_PLACEHOLDER.', '.cite.')
                unified_parts.append(f"{unified_key}={cite_vals['dircite']}")
            else:
                # Different values or only one exists, keep separate
                if 'dircite' in cite_vals:
                    dircite_key = base_key.replace('.CITE_PLACEHOLDER.', '.dircite.')
                    unified_parts.append(f"{dircite_key}={cite_vals['dircite']}")
                if 'indircite' in cite_vals:
                    indircite_key = base_key.replace('.CITE_PLACEHOLDER.', '.indircite.')
                    unified_parts.append(f"{indircite_key}={cite_vals['indircite']}")
        
        return unified_parts
    
    # Convert to sorted signature strings with unification
    return (
        {j: ";".join(sorted(unify_cite_sig_parts(parts))) for j, parts in ref_numbered_sigs.items()},
        {j: ";".join(sorted(unify_cite_sig_parts(parts))) for j, parts in ref_unnumbered_sigs.items()},
        {j: ";".join(sorted(unify_cite_sig_parts(parts))) for j, parts in ref_footnote_sigs.items()},
        {j: ";".join(sorted(unify_cite_sig_parts(parts))) for j, parts in figtab_sigs.items()},
        {j: ";".join(sorted(unify_cite_sig_parts(parts))) for j, parts in partlab_figure_sigs.items()},
        {j: ";".join(sorted(unify_cite_sig_parts(parts))) for j, parts in partlab_table_sigs.items()},
        journal_info
    )


def _build_category_patterns(sigs, prefix):
    """Build patterns from signatures with given prefix"""
    groups = {}
    for j, s in sigs.items():
        groups.setdefault(s, []).append(j)
    
    patterns = {}
    mapping = {}
    idx = 1
    for sig, js in groups.items():
        pname = f"{prefix}_{idx}"
        patterns[pname] = sorted(js)
        mapping[pname] = sig
        idx += 1
    
    return patterns, mapping


def build_patterns(items):
    log("Building patterns...")
    
    # Build separate signatures
    (ref_num_sigs, ref_unnum_sigs, ref_fn_sigs, figtab_sigs, 
     partlab_fig_sigs, partlab_tab_sigs, journal_info) = _journal_signatures_by_category(items)
    
    # Build patterns for each category
    ref_num_patterns, ref_num_mapping = _build_category_patterns(ref_num_sigs, "ref_numbered_pattern")
    ref_unnum_patterns, ref_unnum_mapping = _build_category_patterns(ref_unnum_sigs, "ref_unnumbered_pattern")
    ref_fn_patterns, ref_fn_mapping = _build_category_patterns(ref_fn_sigs, "ref_footnote_pattern")
    figtab_patterns, figtab_mapping = _build_category_patterns(figtab_sigs, "figtab_pattern")
    partlab_fig_patterns, partlab_fig_mapping = _build_category_patterns(partlab_fig_sigs, "partlab_figure_pattern")
    partlab_tab_patterns, partlab_tab_mapping = _build_category_patterns(partlab_tab_sigs, "partlab_table_pattern")
    
    # Return with category info
    return {
        'ref_numbered': ref_num_patterns,
        'ref_unnumbered': ref_unnum_patterns,
        'ref_footnote': ref_fn_patterns,
        'figtab': figtab_patterns,
        'partlab_figure': partlab_fig_patterns,
        'partlab_table': partlab_tab_patterns,
        'ref_numbered_mapping': ref_num_mapping,
        'ref_unnumbered_mapping': ref_unnum_mapping,
        'ref_footnote_mapping': ref_fn_mapping,
        'figtab_mapping': figtab_mapping,
        'partlab_figure_mapping': partlab_fig_mapping,
        'partlab_table_mapping': partlab_tab_mapping,
        'journal_info': journal_info
    }, {}, {}


def save_patterns_json(patterns, outpath):
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(patterns, f, indent=2)
    log(f"Patterns saved {outpath}")

from lxml import etree
from . import report_config as cfg
from .report_log import log

def normalize(s): return s.strip() if s else ""

def get_client_and_type(path):
    p = path.replace("\\","/").split("/")
    if "journals" in p: return p[p.index("journals")+1].upper(),"journals"
    if "books" in p: return p[p.index("books")+1].upper(),"books"
    return "UNKNOWN","unknown"

def process_config(path):
    log(f"Parsing XML: {path}")
    
    client, type_ = get_client_and_type(path)
    
    # Skip ignored clients
    if client in cfg.IGNORE_CLIENTS:
        log(f"Skipping ignored client: {client}")
        return None
    
    try: root = etree.parse(path).getroot()
    except Exception as e:
        log(f"Parse error {e}"); return None
    
    report = {"file":path,"client":client,"type":type_}
    agg={t:{} for t in cfg.SECTION_TAGS}
    agg["PartLabel_Figure"] = {}  # Figure part label attributes
    agg["PartLabel_Table"] = {}   # Table part label attributes
    
    def get_display_value(raw_v):
        """Convert raw value to display value, showing ⊘ empty for empty/None strings"""
        if raw_v is None:
            return "⊘ empty"
        v = raw_v.strip()
        if v == "":
            return "⊘ empty"
        return v
    
    for j in root.findall(".//journal"):
        short=normalize(j.get("short"))
        if not short: continue
        
        # Format: journal_client (e.g., EJGH_LWW)
        journal_name = f"{short}_{client}"
        
        for sec in cfg.SECTION_TAGS:
            for node in j.findall(".//"+sec):
                # Handle Reference-specific attributes
                if sec == "Reference":
                    for ra in cfg.REF_ATTRS:
                        if ra in node.attrib:
                            v = normalize(node.get(ra))
                            if v:
                                agg[sec].setdefault(f"ref.{ra}",{}).setdefault(v,set()).add(journal_name)
                    
                    for cnode in node.findall(".//citation"):
                        for ca in cfg.REF_CITATION_ATTRS:
                            if ca in cnode.attrib:
                                v = normalize(cnode.get(ca))
                                if v:
                                    agg[sec].setdefault(f"citation.{ca}",{}).setdefault(v,set()).add(journal_name)
                
                # Handle other label attrs
                for la in cfg.LABEL_ATTRS:
                    if la in node.attrib:
                        v=normalize(node.get(la))
                        if v:
                            agg[sec].setdefault(la,{}).setdefault(v,set()).add(journal_name)
                
                # Handle dircite/indircite
                for ct in ("dircite","indircite"):
                    for cnode in node.findall(".//"+ct):
                        # Get cite attributes
                        for ca in cfg.CITE_ATTRS:
                            if ca in cnode.attrib:
                                v = get_display_value(cnode.get(ca))
                                if v:
                                    agg[sec].setdefault(ct,{}).setdefault(ca,{}).setdefault(v,set()).add(journal_name)
                        
                        # Combine openwrap/closewrap into unified 'wrap' attribute
                        ow = cnode.get("openwrap", "")
                        cw = cnode.get("closewrap", "")
                        wrap_val = f"{ow} {cw}".strip() if (ow or cw) else ""
                        if wrap_val:
                            v = get_display_value(wrap_val)
                            agg[sec].setdefault(ct,{}).setdefault("wrap",{}).setdefault(v,set()).add(journal_name)
                        else:
                            agg[sec].setdefault(ct,{}).setdefault("wrap",{}).setdefault("⊘ empty",set()).add(journal_name)
                        
                        # Get part label attributes - split by Figure/Table
                        for pla in cfg.PART_LAB_ATTRS:
                            key = f"{ct}.{pla}"
                            
                            if sec == "Figure":
                                # Figure: always show all attributes, ⊘ empty if missing
                                raw_v = cnode.get(pla)
                                v = get_display_value(raw_v)
                                agg["PartLabel_Figure"].setdefault(key,{}).setdefault(v,set()).add(journal_name)
                            
                            elif sec == "Table":
                                # Table: only show if attribute exists in XML
                                if pla in cnode.attrib:
                                    raw_v = cnode.get(pla)
                                    v = get_display_value(raw_v)
                                    agg["PartLabel_Table"].setdefault(key,{}).setdefault(v,set()).add(journal_name)
    
    # Build report sections
    for sec in cfg.SECTION_TAGS:
        report[sec]={}
        
        if sec == "Reference":
            for ra in cfg.REF_ATTRS:
                key = f"ref.{ra}"
                if key in agg[sec]:
                    report[sec][key]=[{"value":v,"journal":sorted(list(s))} for v,s in agg[sec][key].items()]
            key = "citation.type"
            if key in agg[sec]:
                report[sec][key]=[{"value":v,"journal":sorted(list(s))} for v,s in agg[sec][key].items()]
        
        for la in cfg.LABEL_ATTRS:
            if la in agg[sec]:
                report[sec][la]=[{"value":v,"journal":sorted(list(s))} for v,s in agg[sec][la].items()]
        
        for ct in ("dircite","indircite"):
            if ct in agg[sec]:
                report[sec][ct]={}
                for ca,m in agg[sec][ct].items():
                    report[sec][ct][ca]=[{"value":v,"journal":sorted(list(s))} for v,s in m.items()]
    
    # Build PartLabel sections (Figure and Table separate)
    report["PartLabel_Figure"] = {}
    for key, values in agg["PartLabel_Figure"].items():
        report["PartLabel_Figure"][key] = [{"value":v,"journal":sorted(list(s))} for v,s in values.items()]
    
    report["PartLabel_Table"] = {}
    for key, values in agg["PartLabel_Table"].items():
        report["PartLabel_Table"][key] = [{"value":v,"journal":sorted(list(s))} for v,s in values.items()]
    
    return report

# ============================================================================
# REFACTORED BOOK ANALYZER - DOM/XPATH QUERY SELECTOR ARCHITECTURE
# ============================================================================
# Uses LXML XPath exclusively for all DOM queries instead of regex
# ============================================================================

# ============================================================================
# config.py
# ============================================================================
import os
import json
import time
import logging
import functools
from datetime import datetime
from pathlib import Path

def track_performance(func):
    """Decorator to log function start/end times and save to file."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        log_file = Path(__file__).parent / "function_logs.txt"
        start_time = time.time()
        start_ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        print(f"\n>>> [START] {func.__name__} at {start_ts}")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - START: {func.__name__}\n")
            
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            end_ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            duration = end_time - start_time
            print(f"<<< [END] {func.__name__} at {end_ts} (Duration: {duration:.4f}s)")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - END: {func.__name__} ({duration:.4f}s)\n")
    return wrapper

class Config:
    """Centralized configuration management."""
    
    BASE_DIR = Path(__file__).parent.absolute()
    CACHE_FILE = BASE_DIR / "analyzer_cache.json"
    CONFIG_FILE = BASE_DIR / "analyzer_config.json"
    LOG_DIR = BASE_DIR / "logs"
    
    DEFAULTS = {
        "root_path": r"D:\IMPACT",
        "parameter": "",
        "recursive": False
    }
    
    def __init__(self):
        self._config = {}
        self._ensure_dirs()
        self.load()
    
    def _ensure_dirs(self):
        """Create necessary directories."""
        self.LOG_DIR.mkdir(exist_ok=True)
    
    def load(self):
        """Load configuration from file."""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, "r") as f:
                    self._config = json.load(f)
            except Exception as e:
                print(f"Failed to load config: {e}")
                self._config = {}
    
    def save(self, data):
        """Save configuration to file."""
        try:
            with open(self.CONFIG_FILE, "w") as f:
                json.dump(data, f)
            self._config = data
        except Exception as e:
            print(f"Failed to save config: {e}")
    
    def get(self, key, default=None):
        """Get config value."""
        return self._config.get(key, default or self.DEFAULTS.get(key))
    
    def get_log_path(self):
        """Get today's log file path."""
        return self.LOG_DIR / f"analyzer_{datetime.now().strftime('%Y%m%d')}.log"


# ============================================================================
# logger.py
# ============================================================================
import logging

class Logger:
    """Logging setup and management."""
    
    _instance = None
    
    def __new__(cls, config):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._setup(config)
        return cls._instance
    
    def _setup(self, config):
        """Configure logging."""
        log_file = config.get_log_path()
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            encoding='utf-8'
        )
        self.logger = logging.getLogger(__name__)
    
    def info(self, msg):
        self.logger.info(msg)
    
    def error(self, msg):
        self.logger.error(msg)
    
    def warning(self, msg):
        self.logger.warning(msg)


# ============================================================================
# cache.py
# ============================================================================
import json
from pathlib import Path
from datetime import datetime

class Cache:
    """Cache management with size limits."""
    
    def __init__(self, cache_file, max_items=50):
        self.cache_file = cache_file
        self.max_items = max_items
        self.data = self._load()
    
    def _load(self):
        """Load cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save(self):
        """Save cache to file with size limit."""
        if len(self.data) > self.max_items:
            sorted_keys = sorted(
                self.data.keys(),
                key=lambda k: self.data[k].get('ts', 0)
            )
            for k in sorted_keys[:-self.max_items]:
                del self.data[k]
        
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.data, f)
        except Exception as e:
            print(f"Failed to save cache: {e}")
    
    def get(self, key):
        """Get cached value."""
        return self.data.get(key)
    
    def set(self, key, value, timestamp=None):
        """Set cache value."""
        self.data[key] = {
            'data': value,
            'ts': timestamp or datetime.now().timestamp()
        }
        self.save()
    
    def clear(self):
        """Clear all cache."""
        self.data = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
    
    def __len__(self):
        return len(self.data)


# ============================================================================
# dom_parser.py - DOM/XPATH Query Engine
# ============================================================================
from lxml import etree as lx_etree
from collections import defaultdict
import os
from pathlib import Path

class DOMParser:
    """Parse HTML/XML using LXML DOM and XPath queries."""
    
    @track_performance
    def __init__(self, file_path, logger=None):
        self.file_path = Path(file_path)
        self.logger = logger
        self.tree = None
        self.root = None
        self._parse()
    
    def _parse(self):
        """Parse HTML/XML file into DOM tree."""
        try:
            with open(self.file_path, "rb") as f:
                raw_bytes = f.read()
            
            parser = lx_etree.HTMLParser(recover=True, encoding='utf-8')
            self.tree = lx_etree.fromstring(raw_bytes, parser=parser)
            self.root = self.tree
            
            if self.logger:
                self.logger.info(f"DOM parsed: {self.file_path}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"DOM parse failed: {e}")
            raise
    
    def query(self, xpath_expr):
        """Execute XPath query on document."""
        if self.tree is None:
            return []
        try:
            return self.tree.xpath(xpath_expr)
        except Exception as e:
            if self.logger:
                self.logger.error(f"XPath query failed: {xpath_expr} - {e}")
            return []
    
    def query_one(self, xpath_expr):
        """Execute XPath query and get first result."""
        results = self.query(xpath_expr)
        return results[0] if results else None
    
    def get_text(self, element):
        """Extract all text content from element."""
        if element is None:
            return ""
        if isinstance(element, list):
            element = element[0] if element else None
        if element is None: return ""
        return "".join(element.itertext()).strip()
    
    def get_clean_text(self, element, max_len=500):
        """Extract text but avoid slurping entire content if tags are unclosed."""
        if element is None: return ""
        if isinstance(element, list):
            element = element[0] if element else None
        if element is None: return ""
        
        text_parts = []
        for text in element.itertext():
            text_parts.append(text)
            if sum(len(p) for p in text_parts) > max_len:
                break
        
        result = "".join(text_parts).strip()
        if len(result) > max_len:
            result = result[:max_len-3] + "..."
        return result

    def get_attribute(self, element, attr_name):
        """Get attribute value from element."""
        if element is None: return None
        if isinstance(element, list): element = element[0] if element else None
        if element is None: return None
        return element.get(attr_name)
    
    def element_to_string(self, element):
        """Convert element to string."""
        if element is None: return ""
        if isinstance(element, list): element = element[0] if element else None
        if element is None: return ""
        return lx_etree.tostring(element, encoding="unicode", with_tail=False)


    @track_performance
    def get_title_text(self, element, max_len=200):
        """Specifically extract title text, ignoring nested figures/tables."""
        if element is None: return ""
        if isinstance(element, list):
            element = element[0] if element else None
        if element is None: return ""
        
        print(f"DEBUG: get_title_text processing: {element.tag if hasattr(element, 'tag') else element}")
        
        # Avoid slurping by taking text from the element and small inline children only
        # We skip block-level children that might have been accidentally nested
        text_parts = []
        skip_tags = {"fig", "table", "table-wrap", "disp-formula", "graphic", "notes", "ref-list"}
        
        for node in element.iter():
            if node.tag in skip_tags:
                continue
            if node.text:
                text_parts.append(node.text)
            if node.tail and node != element: # Only take tail if it's not the title element's tail
                text_parts.append(node.tail)
                
            if sum(len(p) for p in text_parts) > max_len:
                break
        
        result = " ".join("".join(text_parts).split()).strip()
        if len(result) > max_len:
            result = result[:max_len-3] + "..."
        return result


class DOMQuerySelector:
    """Standardized DOM query selectors using XPath."""
    
    # XPath expressions for common document elements
    SELECTORS = {
        "figures": r".//fig[@id]",
        "tables": r".//table-wrap[@id]",
        "references": r".//ref[@id]",
        "footnotes": r".//fn[@id]",
        "chapters": r"//book-part[@book-part-type='chapter']",
        "chapter_title": r"./book-part-meta/title-group/title",
        "chapter_label": r"./book-part-meta/title-group/label",
        "citations": r"//xref[@rid]",
    }
    
    def __init__(self, dom_parser):
        self.dom = dom_parser
    
    def find_all(self, selector_name):
        """Find all elements matching selector."""
        if selector_name not in self.SELECTORS:
            raise ValueError(f"Unknown selector: {selector_name}")
        return self.dom.query(self.SELECTORS[selector_name])
    
    def find_in_element(self, element, selector_name):
        """Find elements within a specific element."""
        if selector_name not in self.SELECTORS:
            raise ValueError(f"Unknown selector: {selector_name}")
        
        xpath = self.SELECTORS[selector_name]
        try:
            return element.xpath(xpath)
        except Exception:
            return []
    
    def find_by_id(self, element_id):
        """Find element by ID attribute."""
        return self.dom.query_one(f"//*[@id='{element_id}']")
    
    def find_children_with_attr(self, element, attr_name, attr_value):
        """Find children with specific attribute value."""
        xpath = f".//*[@{attr_name}='{attr_value}']"
        return element.xpath(xpath)
    
    def get_custom(self, xpath_expr):
        """Execute custom XPath expression."""
        return self.dom.query(xpath_expr)


# ============================================================================
# citation_extractor.py
# ============================================================================
class CitationExtractor:
    """Extract citation references using DOM queries."""
    
    def __init__(self, dom_parser, dom_selector, logger=None):
        self.dom = dom_parser
        self.selector = dom_selector
        self.logger = logger
        self.citation_map = defaultdict(list)
    
    @track_performance
    def extract(self):
        """Extract all citations (xref and href links)."""
        # Find all xref elements with rid attribute
        xrefs = self.dom.query(r"//xref[@rid]")
        for xref in xrefs:
            rid = self.dom.get_attribute(xref, "rid")
            if rid:
                xml_str = self.dom.element_to_string(xref)
                self.citation_map[rid].append(xml_str)
        
        # Find all anchor links pointing to IDs
        links = self.dom.query(r"//a[@href[starts-with(., '#')]]")
        for link in links:
            href = self.dom.get_attribute(link, "href")
            if href and href.startswith("#"):
                rid = href[1:]
                if rid not in self.citation_map:  # Only add if not already xref
                    xml_str = self.dom.element_to_string(link)
                    self.citation_map[rid].append(xml_str)
        
        if self.logger:
            self.logger.info(f"Extracted {len(self.citation_map)} citation targets")
        
        return self.citation_map


# ============================================================================
# element_extractor.py
# ============================================================================
class ElementExtractor:
    """Extract labeled elements (figures, tables, references) using DOM."""
    
    ELEMENT_CONFIGS = {
        "fig": {
            "label": "Figures",
            "selector": "figures"
        },
        "tab": {
            "label": "Tables",
            "selector": "tables"
        },
        "ref": {
            "label": "References",
            "selector": "references"
        },
        "fn": {
            "label": "Notes/Footnotes",
            "selector": "footnotes"
        }
    }
    
    def __init__(self, dom_parser, dom_selector, citation_map, logger=None):
        self.dom = dom_parser
        self.selector = dom_selector
        self.citation_map = citation_map
        self.logger = logger
    
    @track_performance
    def extract_all(self):
        """Extract all element categories."""
        results = {}
        for key, config in self.ELEMENT_CONFIGS.items():
            results[key] = {
                "label": config["label"],
                "items": self._extract_category(config["selector"])
            }
        return results
    
    def _extract_category(self, selector_name):
        """Extract items for a specific category."""
        items = []
        found_ids = set()
        
        elements = self.selector.find_all(selector_name)
        
        for element in elements:
            # Try to get ID from various attributes
            elem_id = (
                self.dom.get_attribute(element, "id") or
                self.dom.get_attribute(element, "data-id")
            )
            
            if not elem_id or elem_id in found_ids:
                continue
            
            found_ids.add(elem_id)
            
            # Extract label
            label = self._extract_label(element)
            
            # Get citations for this element
            citations = self.citation_map.get(elem_id, [])
            
            items.append({
                "id": elem_id,
                "label": label,
                "count": len(citations),
                "sample": citations[0] if citations else "No citations found"
            })
        
        return items
    
    def _extract_label(self, element):
        """Extract label text from element using DOM queries."""
        # Try to find label element
        label_elem = element.xpath(r".//label")[0] if element.xpath(r".//label") else None
        if label_elem is not None:
            return self.dom.get_text(label_elem)
        
        # Try caption/title
        caption_elem = element.xpath(r".//caption/title")[0] if element.xpath(r".//caption/title") else None
        if caption_elem is not None:
            return self.dom.get_text(caption_elem)
        
        # Try span with class label
        span_label = element.xpath(r".//span[@class='label']")[0] if element.xpath(r".//span[@class='label']") else None
        if span_label is not None:
            return self.dom.get_text(span_label)
        
        # Get text from first child
        text = self.dom.get_text(element)
        return text[:100] if text else "N/A"


# ============================================================================
# chapter_extractor.py
# ============================================================================
class ChapterExtractor:
    """Extract chapter information using DOM queries."""
    
    def __init__(self, dom_parser, dom_selector, logger=None):
        self.dom = dom_parser
        self.selector = dom_selector
        self.logger = logger
    
    @track_performance
    def extract(self):
        """Extract all chapters."""
        chapters = []
        chapter_elements = self.selector.find_all("chapters")
        
        for i, chapter in enumerate(chapter_elements):
            chapter_data = self._extract_chapter_data(chapter, i)
            chapters.append(chapter_data)
        
        if self.logger:
            self.logger.info(f"Extracted {len(chapters)} chapters")
        
        return chapters
    
    def _extract_chapter_data(self, chapter_elem, index):
        """Extract data from a single chapter element."""
        # 1. Try Chapter Metadata (Title & Label)
        title_node = self.selector.find_in_element(chapter_elem, "chapter_title")
        chap_title = self.dom.get_title_text(title_node) if title_node else None
        
        label_node = self.selector.find_in_element(chapter_elem, "chapter_label")        
        chap_label = self.dom.get_title_text(label_node, max_len=50) if label_node else ""        
        
        # Count internal elements using centralized selectors
        fig_count = len(self.selector.find_in_element(chapter_elem, "figures"))
        tab_count = len(self.selector.find_in_element(chapter_elem, "tables"))
        ref_count = len(self.selector.find_in_element(chapter_elem, "references"))
        fn_count = len(self.selector.find_in_element(chapter_elem, "footnotes"))
        
        return {
            "chap_title": f"{chap_label} {chap_title}".strip(),
            "figs": fig_count,
            "tabs": tab_count,
            "refs": ref_count,
            "fns": fn_count
        }


# ============================================================================
# config_parser.py
# ============================================================================
class ConfigParser:
    """Parse impact_config.xml using DOM queries."""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def parse(self, doc_dir):
        """Extract client and file ID from config file."""
        config_path = Path(doc_dir) / "impact_config.xml"
        result = {"client": "default", "file_id": "N/A"}
        
        if not config_path.exists():
            return result
        
        try:
            dom = DOMParser(config_path, self.logger)
            
            # Query client value
            client_elem = dom.query_one("//client")
            if client_elem is not None:
                result["client"] = dom.get_text(client_elem).strip()
            
            # Query file-id value
            file_id_elem = dom.query_one("//file-id")
            if file_id_elem is not None:
                result["file_id"] = dom.get_text(file_id_elem).strip()
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Config parse error: {e}")
        
        return result


# ============================================================================
# content_analyzer.py
# ============================================================================
class ContentAnalyzer:
    """Main content analysis orchestrator using DOM."""
    
    def __init__(self, cache, logger):
        self.cache = cache
        self.logger = logger
    
    @track_performance
    def analyze(self, doc_dir, doc_id, is_specific=False):
        """Analyze document directory."""
        content_file = self._find_content_file(doc_dir, doc_id, is_specific)
        if not content_file:
            self.logger.warning(f"No content file found in {doc_dir}")
            return None
        
        # Check cache
        mtime = os.path.getmtime(content_file)
        cache_key = f"{content_file}_{mtime}"
        cached = self.cache.get(cache_key)
        if cached:
            self.logger.info(f"Using cache for {content_file}")
            return cached['data']
        
        self.logger.info(f"Analyzing: {content_file}")
        
        try:
            # Parse DOM
            dom = DOMParser(content_file, self.logger)
            selector = DOMQuerySelector(dom)
            
            # Extract citations
            citation_extractor = CitationExtractor(dom, selector, self.logger)
            citation_map = citation_extractor.extract()
            
            # Extract elements
            element_extractor = ElementExtractor(dom, selector, citation_map, self.logger)
            categories = element_extractor.extract_all()
            
            # Extract chapters
            chapter_extractor = ChapterExtractor(dom, selector, self.logger)
            chapters = chapter_extractor.extract()
            
            result = {
                "chapters": len(chapters),
                "categories": categories,
                "chapter_breakdown": chapters
            }
            
            self.cache.set(cache_key, result)
            return result
        
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            return None
    
    def _find_content_file(self, doc_dir, doc_id, is_specific=False):
        """Find content file in directory."""
        doc_path = Path(doc_dir)
        
        # Look for _original.xml if specific
        if is_specific:
            orig = doc_path / f"{doc_id}_original.xml"
            if orig.exists():
                return orig
        
        # Look for _updated.html
        for f in doc_path.glob("*_updated.html"):
            return f
        
        # Look for any .xml except config
        for f in doc_path.glob("*.xml"):
            if f.name != "impact_config.xml":
                return f
        
        return None
    
    def find_doc_dirs(self, root, recursive=False):
        """Find all document directories."""
        docs = []
        root_path = Path(root)
        
        if recursive:
            for item in root_path.rglob("impact_config.xml"):
                docs.append(item.parent)
        else:
            for item in root_path.iterdir():
                if item.is_dir() and (item / "impact_config.xml").exists():
                    docs.append(item)
        
        return sorted(docs)


# ============================================================================
# report.py
# ============================================================================
from datetime import datetime
from pathlib import Path

class ReportGenerator:
    """Generate HTML reports."""
    
    @track_performance
    @staticmethod
    def build_doc_blocks(doc_results):
        """Build HTML blocks for each document."""
        blocks = ""
        for dr in doc_results:
            doc_id = dr["id"].replace("-", "_").replace(".", "_").replace(" ", "_")
            blocks += ReportGenerator._build_doc_section(dr, doc_id)
        return blocks
    
    @staticmethod
    def _build_doc_section(doc, doc_id):
        """Build single document section HTML."""
        # Chapter breakdown
        ch_summary_html = ""
        for ch in doc["data"]["chapter_breakdown"]:
            ch_summary_html += f"""
            <div class='ch-summary-card'>
                <div class='ch-title'>{ch.get('chap_title', "Unknown Chapter")}</div>
                <div class='ch-stats'>
                    <div class='ch-stat-item'>Figs: <b>{ch['figs']}</b></div>
                    <div class='ch-stat-item'>Tabs: <b>{ch['tabs']}</b></div>
                    <div class='ch-stat-item'>Refs: <b>{ch['refs']}</b></div>
                    <div class='ch-stat-item'>Fns: <b>{ch['fns']}</b></div>
                </div>
            </div>
            """
        
        if not ch_summary_html:
            ch_summary_html = "<p style='padding: 20px; color: var(--text-dim)'>No chapter data.</p>"
        
        # Tabs header
        tabs_header = f'<div class="tabs-header"><button class="tab-btn active" onclick="openTab(event, \'{doc_id}\', \'ch_break\')">Chapters ({doc["data"]["chapters"]})</button>'
        content_html = f'<div id="{doc_id}_ch_break" class="tab-content active">{ch_summary_html}</div>'
        
        # Category tabs
        for key, cat in doc["data"]["categories"].items():
            tabs_header += f'<button class="tab-btn" onclick="openTab(event, \'{doc_id}\', \'{key}\')">{cat["label"]} ({len(cat["items"])})</button>'
            
            rows = ""
            for itm in cat["items"]:
                sample_escaped = itm['sample'].replace('<', '&lt;').replace('>', '&gt;')
                rows += f"<tr><td><span class='label-text'>{itm['label']}</span></td><td><span class='id-code'>{itm['id']}</span></td><td><span class='count-badge'>{itm['count']}</span></td><td><div class='citation-box'>{sample_escaped}</div></td></tr>"
            
            content_html += f"<div id='{doc_id}_{key}' class='tab-content'><table><thead><tr><th>Label</th><th>Element ID</th><th>Cites</th><th>Sample Citation XML</th></tr></thead><tbody>{rows if rows else '<tr><td colspan=4>No items.</td></tr>'}</tbody></table></div>"
        
        tabs_header += '</div>'
        
        return f"""
        <div class='doc-section'>
            <div class='doc-header' onclick="toggleSection(this)">
                <div class='doc-title'><span class="toggle-icon">▼</span> {doc['id']}</div>
                <div class='doc-meta'>Client: <b>{doc['cfg']['client']}</b> | File ID: {doc['cfg']['file_id']}</div>
            </div>
            <div class="doc-content-wrapper">
                {tabs_header}
                {content_html}
            </div>
        </div>
        """
    
    @staticmethod
    def save_report(report, filename, additional_paths=None):
        """Save report to file(s)."""
        main_path = Path(filename)
        main_path.write_text(report, encoding='utf-8')
        
        if additional_paths:
            for path in additional_paths:
                Path(path).write_text(report, encoding='utf-8')
        
        return main_path


# ============================================================================
# ui.py
# ============================================================================
import tkinter as tk
from tkinter import filedialog, messagebox
import webbrowser
from .report_template import HTML_TEMPLATE

class BookAnalyzerUI:
    """GUI Application."""
    
    def __init__(self, root, config, cache, analyzer, logger, config_parser):
        self.root = root
        self.config = config
        self.cache = cache
        self.analyzer = analyzer
        self.logger = logger
        self.config_parser = config_parser
        
        self._setup_window()
        self._setup_widgets()
        self._load_last_session()
    
    def _setup_window(self):
        """Setup main window."""
        self.root.title("Impact Unified Analyzer v3.0")
        self.root.geometry("700x620")
        self.root.configure(bg="#1e293b")
    
    def _setup_widgets(self):
        """Create UI widgets."""
        main_frame = tk.Frame(self.root, bg="#1e293b", padx=30, pady=30)
        main_frame.pack(fill="both", expand=True)
        
        tk.Label(main_frame, text="CONTENT ANALYSIS ENGINE", font=("Segoe UI", 18, "bold"), fg="#818cf8", bg="#1e293b").pack(pady=(0, 20))
        
        tk.Label(main_frame, text="Root Path:", bg="#1e293b", fg="#94a3b8").pack(anchor="w")
        self.path_var = tk.StringVar(value=self.config.get("root_path"))
        path_frame = tk.Frame(main_frame, bg="#1e293b")
        path_frame.pack(fill="x", pady=(5, 10))
        tk.Entry(path_frame, textvariable=self.path_var, bg="#334155", fg="white", border=0).pack(side="left", fill="x", expand=True, ipady=5)
        tk.Button(path_frame, text="Browse", command=self._browse_path, bg="#4f46e5", fg="white", border=0).pack(side="right", padx=10)
        
        tk.Label(main_frame, text="Doc ID or Client:", bg="#1e293b", fg="#94a3b8").pack(anchor="w")
        self.param_var = tk.StringVar(value=self.config.get("parameter"))
        tk.Entry(main_frame, textvariable=self.param_var, bg="#334155", fg="white", border=0).pack(fill="x", pady=(5, 10), ipady=5)
        
        self.recursive_var = tk.BooleanVar(value=self.config.get("recursive"))
        tk.Checkbutton(main_frame, text="Recursive Sub-directory Scan", variable=self.recursive_var, bg="#1e293b", fg="#94a3b8").pack(anchor="w")
        
        btn_frame = tk.Frame(main_frame, bg="#1e293b")
        btn_frame.pack(fill="x", pady=20)
        tk.Button(btn_frame, text="GENERATE REPORT", command=self._run_analysis, bg="#10b981", fg="white", font=("Segoe UI", 12, "bold"), border=0, pady=12).pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Button(btn_frame, text="Clear Cache", command=self._clear_cache, bg="#ef4444", fg="white", border=0).pack(side="right")
        
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(main_frame, textvariable=self.status_var, bg="#1e293b", fg="#64748b").pack()
        
        self.cache_info = tk.Label(main_frame, text=f"Cached: {len(self.cache)}", bg="#1e293b", fg="#475569")
        self.cache_info.pack(pady=5)
    
    def _load_last_session(self):
        """Load previous session data."""
        pass
    
    def _browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)
    
    def _clear_cache(self):
        self.cache.clear()
        self.cache_info.config(text="Cached: 0")
        messagebox.showinfo("Cache", "Cache cleared.")
    
    def _run_analysis(self):
        """Execute analysis."""
        root_path = self.path_var.get().strip()
        parameter = self.param_var.get().strip()
        recursive = self.recursive_var.get()
        
        if not Path(root_path).exists():
            messagebox.showerror("Error", "Invalid root path.")
            return
        
        self.config.save({
            "root_path": root_path,
            "parameter": parameter,
            "recursive": recursive
        })
        
        self.status_var.set("Scanning documents...")
        self.root.update()
        
        # Find document directories
        pot_doc = Path(root_path) / parameter
        is_id_mode = pot_doc.is_dir() and parameter != ""
        all_dirs = [pot_doc] if is_id_mode else self.analyzer.find_doc_dirs(root_path, recursive=recursive)
        
        doc_results = []
        global_stats = {"ch": 0, "fig": 0, "tab": 0, "labels": 0}
        target_client = parameter if parameter else "Full Scan"
        
        for doc_dir in all_dirs:
            cfg = self.config_parser.parse(doc_dir)
            if not is_id_mode and parameter and cfg["client"].lower() != parameter.lower():
                continue
            
            self.status_var.set(f"Analyzing {doc_dir.name}...")
            self.root.update()
            
            data = self.analyzer.analyze(str(doc_dir), doc_dir.name, is_specific=is_id_mode)
            if not data:
                continue
            
            global_stats["ch"] += data["chapters"]
            global_stats["fig"] += len(data["categories"]["fig"]["items"])
            global_stats["tab"] += len(data["categories"]["tab"]["items"])
            for cat in data["categories"].values():
                for itm in cat["items"]:
                    if itm["label"] != "N/A":
                        global_stats["labels"] += 1
            
            doc_results.append({
                "id": doc_dir.name,
                "path": doc_dir,
                "cfg": cfg,
                "data": data
            })
        
        if not doc_results:
            messagebox.showinfo("Result", "No documents found.")
            return
        
        # Generate report
        html_blocks = ReportGenerator.build_doc_blocks(doc_results)
        report = HTML_TEMPLATE.format(
            client=target_client,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_docs=len(doc_results),
            total_chapters=global_stats["ch"],
            total_figs=global_stats["fig"],
            total_tables=global_stats["tab"],
            total_labels=global_stats["labels"],
            rows=html_blocks
        )
        
        # Save report
        out_name = f"Unified_Analysis_{target_client}.html"
        report_path = self.config.BASE_DIR / out_name
        
        # Also save JSON data
        json_name = f"Unified_Analysis_{target_client}.json"
        json_path = self.config.BASE_DIR / json_name
        
        # Convert Path objects to strings for JSON serialization
        serializable_results = []
        for dr in doc_results:
            serializable_results.append({
                "id": dr["id"],
                "path": str(dr["path"]),
                "cfg": dr["cfg"],
                "data": dr["data"]
            })
            
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=4, ensure_ascii=False)
        
        # Also save a copy inside each document's folder for traceability
        additional_paths = [
            dr["path"] / f"Analysis_Report_{datetime.now().strftime('%Y%m%d')}.html"
            for dr in doc_results
        ]
        
        ReportGenerator.save_report(report, str(report_path), additional_paths)
        
        # Save individual JSON copies as well
        for dr in doc_results:
            local_json = dr["path"] / f"Analysis_Data_{datetime.now().strftime('%Y%m%d')}.json"
            local_data = {
                "id": dr["id"],
                "path": str(dr["path"]),
                "cfg": dr["cfg"],
                "data": dr["data"]
            }
            with open(local_json, 'w', encoding='utf-8') as f:
                json.dump(local_data, f, indent=4, ensure_ascii=False)
        
        self.status_var.set(f"Report and JSON generated. (Saved to {report_path.name})")
        self.cache_info.config(text=f"Cached: {len(self.cache)}")
        webbrowser.open(f"file:///{report_path.absolute()}")


# ============================================================================
# main.py - Entry Point
# ============================================================================
if __name__ == "__main__":
    config = Config()
    logger = Logger(config)
    cache = Cache(config.CACHE_FILE)
    analyzer = ContentAnalyzer(cache, logger)
    config_parser = ConfigParser(logger)
    
    root = tk.Tk()
    app = BookAnalyzerUI(root, config, cache, analyzer, logger, config_parser)
    
    root.mainloop()

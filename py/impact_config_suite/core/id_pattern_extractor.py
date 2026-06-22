import os
import re
import html
import json
import csv
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any, Set
from lxml import etree


class IDPatternExtractor:
    """
    Core engine for ID Pattern Extraction.
    Scans folders for IMPACT document directories, groups XML by type|client,
    extracts ID patterns by element type, and generates
    a consolidated matrix report with element types as rows and clients as columns.
    """

    def __init__(self, profiles_path: Optional[Path] = None):
        self.profiles = self._load_profiles(profiles_path)
        self._config_cache = {}

    def _load_profiles(self, profiles_path: Optional[Path] = None) -> dict:
        """Load area profiles from JSON configuration."""
        if profiles_path is None:
            profiles_path = Path(__file__).parent.parent / "id_pattern_profiles.json"
        try:
            with open(profiles_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load profiles from {profiles_path}: {e}")
            return self._default_profiles()

    def _default_profiles(self) -> dict:
        """Default profiles if JSON file is not found."""
        return {
            "Books": {
                "areas": [
                    {"key": "front", "label": "Front", "xpath": "//front-matter//*[@id] | //front-matter-part[@id]"},
                    {"key": "body", "label": "Body", "xpath": "//book-body//book-part[@id] | //book-part[@book-part-type='chapter'][@id]"},
                    {"key": "back", "label": "Back", "xpath": "//back-matter//*[@id] | //back-matter-part[@id]"}
                ]
            }
        }

    def _load_impact_config(self, config_path: Path) -> Tuple[str, str, str, str]:
        """Load type, client, doc-title, and identifier from impact_config.xml."""
        config_path = Path(config_path)
        config_str = str(config_path)

        # Check cache first
        try:
            current_mtime = config_path.stat().st_mtime
        except OSError:
            current_mtime = 0

        cached = self._config_cache.get(config_str)
        if cached is not None and cached["mtime"] == current_mtime:
            return (cached["doc_type"], cached["client"], cached["doc_title"], cached["identifier"])

        # Parse the config file
        try:
            root = etree.parse(str(config_path)).getroot()
        except Exception:
            return ("", "", "", "")

        doc_type = ""
        client = ""
        doc_title = ""
        identifier = ""

        type_node = root.find(".//type")
        if type_node is not None:
            doc_type = (type_node.text or "").strip()

        client_node = root.find(".//client")
        if client_node is not None:
            client = (client_node.get("name") or client_node.text or "").strip()

        doc_title_node = root.find(".//doc-title")
        if doc_title_node is not None:
            doc_title = (doc_title_node.text or "").strip()

        identifier_node = root.find(".//identifier[@type]")
        if identifier_node is not None:
            identifier = (identifier_node.text or "").strip()

        # Cache the result
        self._config_cache[config_str] = {
            "mtime": current_mtime,
            "doc_type": doc_type,
            "client": client,
            "doc_title": doc_title,
            "identifier": identifier
        }

        return (doc_type, client, doc_title, identifier)

    def _find_xml_file(self, folder: Path) -> Optional[Path]:
        """Find primary document XML - only *_original.xml files."""
        # Look for *_original.xml files specifically
        xml_files = list(folder.glob("*_original.xml"))
        if not xml_files:
            return None
        folder_name = folder.name
        for xml_file in xml_files:
            if folder_name in xml_file.stem:
                return xml_file
        return xml_files[0]

    def scan_documents(self, root_path: Path, recursive: bool = True,
                       type_filter: Optional[str] = None,
                       client_filter: Optional[str] = None,
                       progress_callback=None) -> Dict[str, List[Dict]]:
        """
        Scan root folder for document directories containing impact_config.xml.
        Returns dict keyed by "type|client" with list of document info dicts.
        """
        root_path = Path(root_path)
        if not root_path.is_dir():
            raise NotADirectoryError(f"'{root_path}' is not a valid directory.")

        documents_by_client = defaultdict(list)

        # Find all folders with impact_config.xml
        pattern = "**/" if recursive else ""
        config_files = list(root_path.glob(f"{pattern}impact_config.xml"))

        total = len(config_files)
        for idx, config_path in enumerate(config_files):
            if progress_callback:
                progress_callback(idx + 1, total, config_path.parent.name)

            doc_folder = config_path.parent

            # Load impact config metadata
            doc_type, client, doc_title, identifier = self._load_impact_config(config_path)

            # Apply filters
            if type_filter and type_filter.lower() != "all" and doc_type.upper() != type_filter.upper():
                continue
            if client_filter and client_filter.lower() != "all" and client.upper() != client_filter.upper():
                continue

            # Skip if missing required metadata
            if not doc_type or not client:
                continue

            # Find XML file to analyze
            xml_file = self._find_xml_file(doc_folder)
            if not xml_file:
                continue

            key = f"{doc_type}|{client}"
            documents_by_client[key].append({
                "folder": str(doc_folder),
                "xml_file": str(xml_file),
                "doc_type": doc_type,
                "client": client,
                "doc_title": doc_title,
                "identifier": identifier
            })

        return dict(documents_by_client)

    def normalize_id_to_pattern(self, id_value: str, element_tag: str = "") -> str:
        """
        Normalize an ID to a pattern template.
        Preserves the element context (front-matter-part, book-part, back-matter-part, etc.)
        Examples:
        - 'front-matter-part-001' -> 'front-matter-part-{nnn}'
        - 'book-part-002' -> 'book-part-{nnn}'
        - 'workid-USAC0048448-book-part-2' -> 'workid-{work}-book-part-{n}'
        - 'workid-USAC0048448-front-matter-part-2' -> 'workid-{work}-front-matter-part-{n}'
        - 'IMP35' -> 'IMP{n}'
        """
        if not id_value:
            return ""

        result = id_value

        # Replace alphanumeric work-id tokens between 'workid-' and next '-'
        # This must be done FIRST before digit replacement
        result = re.sub(r'(workid-)([A-Za-z0-9]+)(-)', r'\1{work}\3', result, flags=re.IGNORECASE)

        # Replace 3+ digit sequences with {nnn}
        result = re.sub(r'\d{3,}', '{nnn}', result)

        # Replace 1-2 digit sequences with {n} (only if not already part of {nnn})
        result = re.sub(r'(?<!\d)\d{1,2}(?!\d)', '{n}', result)

        return result

    def extract_ids_from_xml(self, xml_path: Path, xpath: str) -> List[str]:
        """Extract all id attribute values from XML matching the given XPath."""
        try:
            parser = etree.XMLParser(recover=True, encoding='utf-8', resolve_entities=False)
            tree = etree.parse(str(xml_path), parser=parser)
            elements = tree.xpath(xpath)

            seen_ids = set()
            ids = []
            for elem in elements:
                id_val = None
                if isinstance(elem, etree._Element):
                    id_val = elem.get("id")
                elif isinstance(elem, (str, bytes)):
                    id_val = str(elem)

                if id_val and id_val not in seen_ids:
                    seen_ids.add(id_val)
                    ids.append(id_val)
            return ids
        except Exception:
            return []

    def aggregate_patterns(self, ids: List[str]) -> Tuple[str, int]:
        """
        Aggregate list of IDs to most frequent pattern.
        Returns (pattern, variant_count).
        """
        if not ids:
            return ("—", 0)

        patterns = [self.normalize_id_to_pattern(id_val) for id_val in ids]
        pattern_counts = defaultdict(int)

        for p in patterns:
            pattern_counts[p] += 1

        most_frequent = max(pattern_counts.items(), key=lambda x: (x[1], x[0]))
        pattern = most_frequent[0]
        variants = len(pattern_counts) - 1

        if variants > 0:
            pattern = f"{pattern} (+{variants} variants)"

        return (pattern, variants)

    def _get_element_tag(self, elem: etree._Element) -> str:
        """Get clean tag name without namespace."""
        tag = elem.tag
        if isinstance(tag, str) and '}' in tag:
            return tag.split('}')[-1]
        return str(tag) if tag else "unknown"

    def _determine_area(self, elem: etree._Element, tree, area_keys: List[str]) -> Optional[str]:
        """Determine which area an element belongs to based on ancestors."""
        # Check ancestors by walking up the tree
        ancestor_tags = []
        current = elem
        while current is not None and isinstance(current, etree._Element):
            tag = current.tag.split('}')[-1] if '}' in str(current.tag) else str(current.tag)
            ancestor_tags.append(tag.lower())
            current = current.getparent()

        # Check in order: front, body, back
        for area_key in area_keys:
            area_key_lower = area_key.lower()
            if area_key_lower == "front":
                if any(t in ancestor_tags for t in ["front-matter", "book-front", "front"]):
                    return area_key
            elif area_key_lower == "body":
                if any(t in ancestor_tags for t in ["book-body", "body"]):
                    return area_key
            elif area_key_lower == "back":
                if any(t in ancestor_tags for t in ["back-matter", "book-back", "back"]):
                    return area_key

        return None

    def analyze_document(self, doc_info: Dict, areas: List[Dict]) -> Dict[str, Dict[str, Dict]]:
        """
        Analyze a single document and extract element details by element tag.
        Uses a single XPath `//*[@id]` to get ALL elements with IDs globally,
        then categorizes by element tag (not by area).
        Groups by element tag to avoid repeated element types.
        Deduplicates by (element_tag, pattern) - same pattern appears only once.
        Returns dict mapping element_tag -> {sample_id, pattern, count, area, variants}.
        """
        xml_path = Path(doc_info["xml_file"])
        if not xml_path.exists():
            return {}

        try:
            parser = etree.XMLParser(recover=True, encoding='utf-8', resolve_entities=False)
            tree = etree.parse(str(xml_path), parser=parser)

            # Get ALL elements with id attribute - single global XPath query
            all_elements = tree.xpath("//*[@id]")

            area_keys = [area["key"] for area in areas]

            # Result structure: element_tag -> {sample_id, pattern, count, area, all_ids}
            result = {}

            # Track seen (element_tag, pattern) combinations for deduplication
            seen_patterns = set()

            # Process each element and group by element tag
            for elem in all_elements:
                if not isinstance(elem, etree._Element):
                    continue

                id_val = elem.get("id")
                if not id_val:
                    continue

                tag = self._get_element_tag(elem)
                pattern = self.normalize_id_to_pattern(id_val)
                area_key = self._determine_area(elem, tree, area_keys)

                # Create deduplication key
                pattern_key = (tag, pattern)

                if pattern_key not in seen_patterns:
                    # First occurrence of this element tag + pattern
                    seen_patterns.add(pattern_key)
                    result[tag] = {
                        "sample_id": id_val,
                        "pattern": pattern,
                        "count": 1,
                        "area": area_key or "unknown",
                        "all_ids": [id_val]
                    }
                else:
                    # Already seen this pattern for this element tag, just increment count
                    if tag in result:
                        result[tag]["count"] += 1
                        result[tag]["all_ids"].append(id_val)

            return result

        except Exception:
            return {}

    def build_matrix_data(self, documents_by_client: Dict[str, List[Dict]],
                          doc_type: str) -> Tuple[List[Dict], List[str], Dict, List[Dict], List[Dict]]:
        """
        Build matrix data from analyzed documents.
        Matrix rows = unique element types (book-part, front-matter-part, ref, etc.)
        Matrix columns = clients
        Cells = all patterns for that element type + client combination (line-by-line)
        Deduplication: same (client, element_type, pattern) = 1 row
        Returns (rows, client_keys, detail_data, element_details, doc_metadata).
        """
        # Collect all unique clients
        all_clients = set()
        for key in documents_by_client:
            parts = key.split("|", 1)
            if len(parts) == 2:
                all_clients.add(parts[1])

        client_keys = sorted(all_clients)

        # Get area definitions for this document type (used for area detection in analyze_document)
        type_config = self.profiles.get(doc_type, self.profiles.get("Books", {}))
        areas = type_config.get("areas", [])

        # Data structure for collecting patterns:
        # {element_tag: {client: {pattern: count}}}
        patterns_by_element_client = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        # Detail data for per-document breakdown
        detail_data = {}

        # Element-wise details for consolidated table (ALL elements)
        element_details = []
        element_counter = 0

        # Document metadata for header (TYPE|CLIENT|IDENTIFIER)
        doc_metadata = []

        # First pass: collect all element types and patterns per client
        for key, docs in documents_by_client.items():
            parts = key.split("|", 1)
            if len(parts) != 2:
                continue
            doc_type_val, client = parts

            for doc in docs:
                doc_key = f"{doc['folder']}"
                doc_title = doc.get("doc_title", "") or os.path.basename(doc_key)
                element_data = self.analyze_document(doc, areas)

                # Store detail data (now keyed by element_tag)
                detail_data[doc_key] = {
                    "doc_info": doc,
                    "element_data": element_data
                }

                # Collect document metadata for header
                doc_metadata.append({
                    "type": doc.get("doc_type", ""),
                    "client": doc.get("client", ""),
                    "identifier": doc.get("identifier", ""),
                    "doc_title": doc_title,
                    "folder": doc_key,
                    "xml_file": doc.get("xml_file", "")
                })

                # element_data structure: {element_tag: {sample_id, pattern, count, area, all_ids}}
                for tag, info in element_data.items():
                    element_counter += 1
                    pattern = info["pattern"]
                    count = info["count"]
                    area = info["area"]
                    sample_id = info["sample_id"]

                    # Accumulate pattern count for this element type + client
                    patterns_by_element_client[tag][client][pattern] += count

                    # Build element-wise record (ALL elements for detail table)
                    element_details.append({
                        "seq": element_counter,
                        "document": doc_title,
                        "client": client,
                        "area": area,
                        "element": tag,
                        "sample_id": sample_id,
                        "count": count,
                        "pattern": pattern
                    })

        # Collect all unique element types (rows)
        all_element_tags = sorted(patterns_by_element_client.keys())

        # Build matrix rows with element types as rows
        rows = []
        for element_tag in all_element_tags:
            row = {
                "element_type": element_tag
            }

            for client in client_keys:
                client_patterns = patterns_by_element_client[element_tag].get(client, {})
                if client_patterns:
                    # Sort patterns by frequency (most frequent first)
                    sorted_patterns = sorted(client_patterns.items(), key=lambda x: (-x[1], x[0]))
                    # Store all patterns as list for HTML display
                    row[client] = {
                        "patterns": [p[0] for p in sorted_patterns],
                        "counts": [p[1] for p in sorted_patterns],
                        "total_count": sum(client_patterns.values())
                    }
                else:
                    row[client] = None

            rows.append(row)

        return rows, client_keys, detail_data, element_details, doc_metadata

    def generate_html_report(self, root_path: str, doc_type: str, client_filter: str,
                            rows: List[Dict], clients: List[str],
                            detail_data: Dict, element_details: List[Dict], total_docs: int,
                            doc_metadata: List[Dict] = None) -> str:
        """Generate HTML matrix report with element-wise consolidated table."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        folder_name = os.path.basename(root_path)

        # Build matrix table header - Element Type as first column, then clients
        header_cols = "<th>Element Type</th>"
        for client in clients:
            header_cols += f"<th>{html.escape(client)}</th>"

        # Build matrix table rows - element types as rows with all patterns displayed
        table_rows = ""
        for row in rows:
            element_type = row.get("element_type", "")
            tr = f'<tr><td class="element-type">{html.escape(element_type)}</td>'
            for client in clients:
                cell_data = row.get(client)
                if cell_data and cell_data["patterns"]:
                    # Display all patterns line-by-line with counts
                    patterns_html = ""
                    for i, (pattern, count) in enumerate(zip(cell_data["patterns"], cell_data["counts"])):
                        count_display = f" <span class='pattern-count'>({count})</span>" if len(cell_data["patterns"]) > 1 else ""
                        patterns_html += f'<code class="pattern">{html.escape(pattern)}</code>{count_display}'
                        if i < len(cell_data["patterns"]) - 1:
                            patterns_html += "<br>"
                    tr += f'<td class="multi-pattern">{patterns_html}</td>'
                else:
                    tr += f'<td class="empty">—</td>'
            tr += "</tr>"
            table_rows += tr

        # Build element-wise consolidated table (grouped by element type)
        element_table_rows = ""
        for elem in element_details:
            tr = f'<tr>'
            tr += f'<td>{elem["seq"]}</td>'
            doc_title_escaped = html.escape(elem["document"])
            tr += f'<td class="doc-name" title="{doc_title_escaped}">{html.escape(elem["document"][:35])}{"..." if len(elem["document"]) > 35 else ""}</td>'
            tr += f'<td><span class="client-badge">{html.escape(elem["client"])}</span></td>'
            tr += f'<td><span class="area-badge area-{elem["area"]}">{html.escape(elem["area"])}</span></td>'
            tr += f'<td><code class="tag">{html.escape(elem["element"])}</code></td>'
            tr += f'<td><code class="id-value">{html.escape(elem["sample_id"])}</code></td>'
            tr += f'<td><span class="count">×{elem["count"]}</span></td>'
            tr += f'<td><code class="pattern">{html.escape(elem["pattern"])}</code></td>'
            tr += '</tr>'
            element_table_rows += tr

        # Build document metadata badges for header
        metadata_badges = ""
        if doc_metadata:
            for doc in doc_metadata:
                type_val = html.escape(doc.get("type", "") or "Unknown")
                client_val = html.escape(doc.get("client", "") or "Unknown")
                identifier_val = html.escape(doc.get("identifier", "") or "N/A")
                metadata_badges += f'<div class="metadata-badge"><span class="meta-type">{type_val}</span><span class="meta-sep">|</span><span class="meta-client">{client_val}</span><span class="meta-sep">|</span><span class="meta-identifier">{identifier_val}</span></div>'

        # Build detail section (collapsed by default) - shows grouped element details per document with action buttons
        detail_sections = ""
        for doc_key, doc_detail in detail_data.items():
            doc_info = doc_detail["doc_info"]
            element_data = doc_detail["element_data"]
            xml_file = doc_info.get("xml_file", "")
            xml_file_escaped = html.escape(xml_file.replace("\\", "/"))

            detail_html = f'<div class="doc-detail" data-xml-path="{xml_file_escaped}">'

            # Header row with title and action buttons
            detail_html += f'<div class="doc-detail-header">'
            detail_html += f'<div class="doc-title-section">'
            detail_html += f'<h4>{html.escape(doc_info["doc_title"] or os.path.basename(doc_key))}</h4>'
            detail_html += f'<p class="meta">Client: {html.escape(doc_info["client"])} | Type: {html.escape(doc_info["doc_type"])}</p>'
            detail_html += f'</div>'

            # Action buttons
            if xml_file:
                detail_html += f'<div class="doc-actions">'
                # Open File button - opens XML in new tab
                file_url = f"file:///{xml_file_escaped}"
                detail_html += f'<a href="{file_url}" target="_blank" class="action-btn open-btn">📄 Open File</a>'
                # Copy Path button - uses JavaScript to copy to clipboard
                detail_html += f'<button class="action-btn copy-btn" onclick="copyToClipboard(this, \'{xml_file_escaped}\')" title="Copy full file path to clipboard">📋 Copy Path</button>'
                detail_html += f'</div>'

            detail_html += f'</div>'

            # element_data structure: {element_tag: {sample_id, pattern, count, area, all_ids}}
            if element_data:
                detail_html += f'<div class="elements-detail"><strong>Elements Found:</strong> '
                items = []
                for tag, info in list(element_data.items())[:10]:
                    count_badge = f'<span class="count-badge-small">×{info["count"]}</span>' if info["count"] > 1 else ''
                    area_badge = f'<span class="area-badge-small area-{info["area"]}">{info["area"]}</span>'
                    items.append(f'<code class="tag">{html.escape(tag)}</code>{count_badge}{area_badge}:<code>{html.escape(info["sample_id"])}</code>')
                detail_html += ', '.join(items)
                if len(element_data) > 10:
                    detail_html += f' <em>(+{len(element_data) - 10} more types)</em>'
                detail_html += '</div>'

            detail_html += '</div>'
            detail_sections += detail_html

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ID Pattern Report - {html.escape(folder_name)}</title>
    <style>
        :root {{
            --bg-main: #0b0f19;
            --bg-card: #111827;
            --bg-code: #030712;
            --bg-input: #1f2937;
            --border-color: #374151;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --success: #10b981;
            --error: #ef4444;
            --warning: #f59e0b;
            --accent: #818cf8;
        }}

        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            margin: 0;
            padding: 0;
            line-height: 1.5;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 20px;
        }}

        header {{
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 24px;
            margin-bottom: 32px;
        }}

        h1 {{
            font-size: 2rem;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(135deg, #a5b4fc, #6366f1, #38bdf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .subtitle {{
            color: var(--text-muted);
            margin: 8px 0 0 0;
            font-size: 1rem;
        }}

        .timestamp {{
            font-size: 0.9rem;
            color: var(--text-muted);
            background: var(--bg-card);
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            display: inline-block;
            margin-top: 16px;
        }}

        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }}

        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}

        .stat-label {{
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}

        .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--accent);
        }}

        .matrix-container {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 32px;
        }}

        .matrix-header {{
            background: rgba(99, 102, 241, 0.1);
            padding: 16px 20px;
            border-bottom: 1px solid var(--border-color);
        }}

        .matrix-header h2 {{
            margin: 0;
            font-size: 1.2rem;
            color: var(--accent);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}

        th {{
            background: rgba(255, 255, 255, 0.02);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            font-weight: 600;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}

        .element-type {{
            font-weight: 600;
            color: var(--text-main);
            font-family: 'Consolas', 'Courier New', monospace;
        }}

        .pattern {{
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 0.85rem;
            background: var(--bg-code);
            padding: 4px 8px;
            border-radius: 4px;
            color: #34d399;
        }}

        .empty {{
            color: var(--text-muted);
            text-align: center;
        }}

        .detail-section {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
        }}

        .detail-header {{
            background: rgba(99, 102, 241, 0.1);
            padding: 16px 20px;
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
            user-select: none;
        }}

        .detail-header h2 {{
            margin: 0;
            font-size: 1.2rem;
            color: var(--accent);
        }}

        .detail-content {{
            padding: 20px;
            display: none;
        }}

        .detail-content.expanded {{
            display: block;
        }}

        .doc-detail {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }}

        .doc-detail h4 {{
            margin: 0 0 8px 0;
            color: var(--text-main);
        }}

        .doc-detail .meta {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 12px;
        }}

        /* Multi-pattern cell styles */
        .multi-pattern {{
            line-height: 1.6;
        }}

        .pattern-count {{
            color: var(--text-muted);
            font-size: 0.75rem;
            margin-left: 4px;
        }}

        /* Document metadata badges in header */
        .metadata-section {{
            margin: 20px 0;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .metadata-badge {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 0.85rem;
            font-family: 'Consolas', 'Courier New', monospace;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}

        .meta-type {{
            color: #fbbf24;
            font-weight: 600;
        }}

        .meta-sep {{
            color: var(--text-muted);
        }}

        .meta-client {{
            color: #34d399;
            font-weight: 600;
        }}

        .meta-identifier {{
            color: #a5b4fc;
        }}

        /* Document detail header with action buttons */
        .doc-detail-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 12px;
        }}

        .doc-title-section {{
            flex: 1;
        }}

        .doc-actions {{
            display: flex;
            gap: 8px;
        }}

        .action-btn {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            border: none;
            transition: background-color 0.2s, transform 0.1s;
        }}

        .action-btn:hover {{
            transform: translateY(-1px);
        }}

        .action-btn:active {{
            transform: translateY(0);
        }}

        .open-btn {{
            background: rgba(99, 102, 241, 0.2);
            color: #818cf8;
        }}

        .open-btn:hover {{
            background: rgba(99, 102, 241, 0.3);
        }}

        .copy-btn {{
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
        }}

        .copy-btn:hover {{
            background: rgba(16, 185, 129, 0.3);
        }}

        .copy-btn.copied {{
            background: rgba(16, 185, 129, 0.4);
            color: #10b981;
        }}

        .elements-detail {{
            font-size: 0.9rem;
            margin-bottom: 8px;
        }}

        .toggle-icon {{
            float: right;
            transition: transform 0.2s;
        }}

        .toggle-icon.expanded {{
            transform: rotate(90deg);
        }}

        /* Element-wise table styles */
        .element-section {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 32px;
        }}

        .element-header {{
            background: rgba(16, 185, 129, 0.1);
            padding: 16px 20px;
            border-bottom: 1px solid var(--border-color);
        }}

        .element-header h2 {{
            margin: 0;
            font-size: 1.2rem;
            color: #34d399;
        }}

        .element-table-container {{
            max-height: 600px;
            overflow-y: auto;
        }}

        .element-table th {{
            position: sticky;
            top: 0;
            background: var(--bg-card);
            z-index: 10;
            border-bottom: 2px solid var(--border-color);
        }}

        .element-table td {{
            font-size: 0.9rem;
            padding: 10px 12px;
        }}

        .client-badge {{
            display: inline-block;
            background: rgba(99, 102, 241, 0.2);
            color: var(--accent);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
        }}

        .area-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: capitalize;
        }}

        .area-front {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; }}
        .area-body {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
        .area-back {{ background: rgba(239, 68, 68, 0.2); color: #f87171; }}
        .area-unknown {{ background: rgba(107, 114, 128, 0.2); color: #9ca3af; }}

        .area-badge-small {{
            display: inline-block;
            padding: 1px 4px;
            border-radius: 3px;
            font-size: 0.7rem;
            margin-left: 4px;
            text-transform: capitalize;
        }}

        .tag {{
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.8rem;
        }}

        .count {{
            background: rgba(245, 158, 11, 0.2);
            color: #fbbf24;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 600;
        }}

        .count-badge-small {{
            background: rgba(245, 158, 11, 0.15);
            color: #f59e0b;
            padding: 1px 4px;
            border-radius: 4px;
            font-size: 0.75rem;
            margin-left: 4px;
        }}

        .id-value {{
            background: var(--bg-code);
            color: #a5b4fc;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.8rem;
        }}

        .doc-name {{
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>ID Pattern Extraction Report</h1>
            <p class="subtitle">Scan Root: <strong>{html.escape(root_path)}</strong> | Type Filter: <strong>{html.escape(doc_type)}</strong> | Client Filter: <strong>{html.escape(client_filter)}</strong></p>
            <div class="timestamp">Generated: {timestamp}</div>
        </header>

        <!-- Document Metadata Section (TYPE|CLIENT|IDENTIFIER) -->
        <div class="metadata-section">
            {metadata_badges}
        </div>

        <div class="summary-stats">
            <div class="stat-card">
                <div class="stat-label">Documents Scanned</div>
                <div class="stat-value">{total_docs}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Clients Found</div>
                <div class="stat-value">{len(clients)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Element Types</div>
                <div class="stat-value">{len(rows)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Elements</div>
                <div class="stat-value">{len(element_details)}</div>
            </div>
        </div>

        <div class="matrix-container">
            <div class="matrix-header">
                <h2>ID Pattern Matrix (Element Types × Clients)</h2>
            </div>
            <table>
                <thead>
                    <tr>{header_cols}</tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>

        <div class="element-section">
            <div class="element-header">
                <h2>Element-wise Consolidated Report</h2>
            </div>
            <div class="element-table-container">
                <table class="element-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Document</th>
                            <th>Client</th>
                            <th>Area</th>
                            <th>Element</th>
                            <th>Sample ID</th>
                            <th>Count</th>
                            <th>Pattern</th>
                        </tr>
                    </thead>
                    <tbody>
                        {element_table_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="detail-section">
            <div class="detail-header" onclick="toggleDetails()">
                <h2>Document Details <span class="toggle-icon" id="toggleIcon">▶</span></h2>
            </div>
            <div class="detail-content" id="detailContent">
                {detail_sections}
            </div>
        </div>
    </div>

    <script>
        function toggleDetails() {{
            const content = document.getElementById('detailContent');
            const icon = document.getElementById('toggleIcon');
            content.classList.toggle('expanded');
            icon.classList.toggle('expanded');
        }}

        // Copy file path to clipboard
        async function copyToClipboard(button, text) {{
            try {{
                await navigator.clipboard.writeText(text);
                const originalText = button.innerHTML;
                button.innerHTML = '✅ Copied!';
                button.classList.add('copied');
                setTimeout(() => {{
                    button.innerHTML = originalText;
                    button.classList.remove('copied');
                }}, 2000);
            }} catch (err) {{
                console.error('Failed to copy: ', err);
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.left = '-9999px';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                try {{
                    document.execCommand('copy');
                    const originalText = button.innerHTML;
                    button.innerHTML = '✅ Copied!';
                    button.classList.add('copied');
                    setTimeout(() => {{
                        button.innerHTML = originalText;
                        button.classList.remove('copied');
                    }}, 2000);
                }} catch (err) {{
                    alert('Failed to copy path. Please copy manually: ' + text);
                }}
                document.body.removeChild(textArea);
            }}
        }}
    </script>
</body>
</html>
"""
        return html_template

    def export_csv(self, rows: List[Dict], clients: List[str], output_path: Path) -> Path:
        """Export matrix to CSV file."""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Header
            header = ["Element Type"] + clients
            writer.writerow(header)

            # Data rows
            for row in rows:
                element_type = row.get("element_type", "")
                data_row = [element_type]
                for client in clients:
                    cell_data = row.get(client)
                    if cell_data and cell_data.get("patterns"):
                        # For CSV, use the most frequent pattern only (first in sorted list)
                        value = cell_data["patterns"][0]
                    else:
                        value = "—"
                    data_row.append(value)
                writer.writerow(data_row)

        return output_path

    def export_element_csv(self, element_details: List[Dict], output_path: Path) -> Path:
        """Export element-wise details to CSV file (grouped by element type)."""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Header
            writer.writerow(["#", "Document", "Client", "Area", "Element", "Sample ID", "Count", "Pattern"])

            # Data rows
            for elem in element_details:
                writer.writerow([
                    elem["seq"],
                    elem["document"],
                    elem["client"],
                    elem["area"],
                    elem["element"],
                    elem["sample_id"],
                    elem["count"],
                    elem["pattern"]
                ])

        return output_path

    def run_extraction(self, root_path: str, output_dir: str,
                       doc_type: str = "Books",
                       client_filter: str = "All",
                       recursive: bool = True,
                       progress_callback=None) -> Dict[str, Any]:
        """
        Run the full extraction pipeline.
        Returns dict with report paths and summary data.
        """
        root_path_obj = Path(root_path)
        output_dir_obj = Path(output_dir)
        output_dir_obj.mkdir(parents=True, exist_ok=True)

        # Create timestamped folder
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_folder = output_dir_obj / f"id_pattern_{ts}"
        run_folder.mkdir(parents=True, exist_ok=True)

        # Scan for documents
        if progress_callback:
            progress_callback("scan", 0, 0, "Scanning for documents...")

        documents_by_client = self.scan_documents(
            root_path_obj,
            recursive=recursive,
            type_filter=doc_type,
            client_filter=client_filter,
            progress_callback=lambda cur, tot, name: progress_callback("scan", cur, tot, name) if progress_callback else None
        )

        total_docs = sum(len(docs) for docs in documents_by_client.values())

        if progress_callback:
            progress_callback("analyze", 0, total_docs, "Analyzing documents...")

        # Build matrix data
        rows, clients, detail_data, element_details, doc_metadata = self.build_matrix_data(documents_by_client, doc_type)

        if progress_callback:
            progress_callback("report", 0, 3, "Generating reports...")

        # Generate HTML report
        html_report = self.generate_html_report(
            root_path, doc_type, client_filter,
            rows, clients, detail_data, element_details, total_docs, doc_metadata
        )

        html_path = run_folder / f"id_pattern_report_{ts}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_report)

        if progress_callback:
            progress_callback("report", 1, 3, "Generating matrix CSV export...")

        # Generate matrix CSV export
        csv_path = run_folder / f"id_pattern_matrix_{ts}.csv"
        self.export_csv(rows, clients, csv_path)

        if progress_callback:
            progress_callback("report", 2, 3, "Generating element details CSV...")

        # Generate element details CSV export
        element_csv_path = run_folder / f"id_pattern_elements_{ts}.csv"
        self.export_element_csv(element_details, element_csv_path)

        if progress_callback:
            progress_callback("complete", 3, 3, "Complete")

        return {
            "html_path": str(html_path),
            "csv_path": str(csv_path),
            "element_csv_path": str(element_csv_path),
            "run_folder": str(run_folder),
            "total_docs": total_docs,
            "clients": clients,
            "rows": rows,
            "element_count": len(element_details)
        }

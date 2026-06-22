import os
import re
import html
import json
import hashlib
import fnmatch
import warnings
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from lxml import etree

# Suppress warnings when parsing XML files using HTML parsers
try:
    from bs4 import XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
except ImportError:
    pass

class ElementExtractor:
    """
    Core engine for parsing HTML/XML files, extracting specific elements based on
    Tag Name, CSS Selector, or XPath query, and generating a timestamped HTML report.
    Supports JSON-based caching to skip re-parsing unmodified files.
    """

    def __init__(self):
        # In-memory cache: {cache_key: {"mtime": float, "results": list}}
        self._cache = {}
        # Config cache for doc-title: {config_path: {"mtime": float, "doc_title": str}}
        self._config_cache = {}

    def _cache_key(self, file_path: Path, query_type: str, query_val: str,
                   attr_name: str, attr_val: str) -> str:
        """Build a unique key combining file path + query parameters."""
        raw = f"{file_path.absolute()}|{query_type}|{query_val}|{attr_name}|{attr_val}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _get_cached(self, file_path: Path, query_type: str, query_val: str,
                    attr_name: str, attr_val: str):
        """Return cached results if the file has not been modified since last parse."""
        key = self._cache_key(file_path, query_type, query_val, attr_name, attr_val)
        cached = self._cache.get(key)
        if cached is None:
            return None
        try:
            current_mtime = file_path.stat().st_mtime
        except OSError:
            return None
        if current_mtime == cached["mtime"]:
            return cached["results"]
        return None

    def _set_cache(self, file_path: Path, query_type: str, query_val: str,
                   attr_name: str, attr_val: str, results: list):
        """Store extraction results in the in-memory cache."""
        key = self._cache_key(file_path, query_type, query_val, attr_name, attr_val)
        try:
            mtime = file_path.stat().st_mtime
        except OSError:
            return
        self._cache[key] = {"mtime": mtime, "results": results}

    def save_cache_to_disk(self, cache_path: Path):
        """Persist cache to a JSON file on disk."""
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=2, default=str)
        except Exception:
            pass

    def load_cache_from_disk(self, cache_path: Path):
        """Load cache from a JSON file on disk."""
        try:
            if cache_path.exists():
                with open(cache_path, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
        except Exception:
            self._cache = {}

    @staticmethod
    def _normalize_named_filter(value: str) -> str:
        if not value:
            return ""
        normalized = value.strip()
        if not normalized or normalized.lower() == "none":
            return ""
        return normalized

    @staticmethod
    def _matches_filename_filter(file_name: str, normalized_filter: str) -> bool:
        if not normalized_filter:
            return True

        lowered_name = file_name.lower()
        lowered_filter = normalized_filter.lower()

        # Keep the common folder-scan options strict so *_original.html does not
        # also include *_AU_original.html, and likewise for *_updated.html.
        if lowered_filter == "*_original.html":
            stem = Path(file_name).stem
            return bool(re.fullmatch(r"[^_]+_original", stem, flags=re.IGNORECASE))
        if lowered_filter == "*_updated.html":
            stem = Path(file_name).stem
            return bool(re.fullmatch(r"[^_]+_updated", stem, flags=re.IGNORECASE))

        return fnmatch.fnmatchcase(lowered_name, lowered_filter)

    def _load_impact_config_filters(self, config_path: Path) -> tuple[str, str, str, str, str, str, str]:
        """Load DTD, client, doc-title, project-title, identifier, link-info, and type from impact_config.xml with caching."""
        config_path = Path(config_path)

        # Check cache first
        cached = self._config_cache.get(str(config_path))
        try:
            current_mtime = config_path.stat().st_mtime
        except OSError:
            current_mtime = 0

        if cached is not None and cached["mtime"] == current_mtime:
            return (
                cached["dtd_name"], cached["client_name"], cached["doc_title"],
                cached["project_title"], cached["identifier"], cached["link_info"], cached["doc_type"]
            )

        # Parse the config file
        try:
            root = etree.parse(str(config_path)).getroot()
        except Exception:
            return "", "", "", "", "", "", ""

        dtd_name = ""
        client_name = ""
        doc_title = ""
        project_title = ""
        identifier = ""
        link_info = ""
        doc_type = ""

        dtd_node = root.find(".//dtd")
        if dtd_node is not None:
            dtd_name = (dtd_node.get("name") or "").strip()

        client_node = root.find(".//client")
        if client_node is not None:
            client_name = (client_node.get("name") or client_node.text or "").strip()

        doc_title_node = root.find(".//doc-title")
        if doc_title_node is not None:
            doc_title = (doc_title_node.text or "").strip()

        project_title_node = root.find(".//project-title")
        if project_title_node is not None:
            project_title = (project_title_node.text or "").strip()

        # Read additional metadata fields
        identifier_node = root.find(".//identifier[@type]")
        if identifier_node is not None:
            identifier = (identifier_node.text or "").strip()

        link_info_node = root.find(".//link-info")
        if link_info_node is not None:
            link_info = (link_info_node.text or "").strip()

        type_node = root.find(".//type")
        if type_node is not None:
            doc_type = (type_node.text or "").strip()

        # Cache the result
        self._config_cache[str(config_path)] = {
            "mtime": current_mtime,
            "dtd_name": dtd_name,
            "client_name": client_name,
            "doc_title": doc_title,
            "project_title": project_title,
            "identifier": identifier,
            "link_info": link_info,
            "doc_type": doc_type
        }

        return dtd_name, client_name, doc_title, project_title, identifier, link_info, doc_type

    def _matches_config_filters(self, file_path: Path, dtd_filter: str, client_filter: str) -> bool:
        dtd_filter = self._normalize_named_filter(dtd_filter)
        client_filter = self._normalize_named_filter(client_filter)
        if not dtd_filter and not client_filter:
            return True

        config_path = file_path.parent / "impact_config.xml"
        if not config_path.is_file():
            return False

        # Now returns 7 values: dtd_name, client_name, doc_title, project_title, identifier, link_info, doc_type
        dtd_name, client_name, _, _, _, _, _ = self._load_impact_config_filters(config_path)
        if dtd_filter and dtd_name.upper() != dtd_filter.upper():
            return False
        if client_filter and client_name.upper() != client_filter.upper():
            return False
        return True

    def get_doc_title(self, file_path: Path) -> str:
        """
        Get the doc-title from impact_config.xml in the file's parent directory.
        Uses caching to avoid repeated parsing.

        Args:
            file_path: Path to the HTML/XML file

        Returns:
            The doc-title string, or empty string if not found
        """
        file_path = Path(file_path)
        config_path = file_path.parent / "impact_config.xml"

        if not config_path.is_file():
            return ""

        # _load_impact_config_filters handles caching internally (returns 7 values)
        _, _, doc_title, _, _, _, _ = self._load_impact_config_filters(config_path)
        return doc_title

    def get_file_title(self, file_path: Path) -> tuple[str, str]:
        """
        Get appropriate title for a file based on its DTD.
        BITS DTD: returns project-title
        JATS DTD: returns doc-title

        Returns (title_type, title_value) where title_type is "doc-title", "project-title", or "filename"
        """
        file_path = Path(file_path)
        config_path = file_path.parent / "impact_config.xml"

        if not config_path.is_file():
            return "filename", file_path.name

        # _load_impact_config_filters returns 7 values
        dtd, client, doc_title, project_title, identifier, link_info, doc_type = \
            self._load_impact_config_filters(config_path)

        # Determine title based on DTD
        if dtd.upper() == "BITS" and project_title:
            return "project-title", project_title
        elif dtd.upper() == "JATS" and doc_title:
            return "doc-title", doc_title
        elif doc_title:  # Default fallback
            return "doc-title", doc_title
        elif project_title:
            return "project-title", project_title
        else:
            return "filename", file_path.name

    def clear_config_cache(self) -> None:
        """Clear the impact_config.xml cache."""
        self._config_cache.clear()

    def get_file_metadata(self, file_path: Path) -> dict[str, str]:
        """
        Get all metadata for a file from impact_config.xml.
        Returns dict with keys: dtd, client, doc_title, project_title,
        identifier, link_info, doc_type
        """
        file_path = Path(file_path)
        config_path = file_path.parent / "impact_config.xml"

        if not config_path.is_file():
            return {
                "dtd": "",
                "client": "",
                "doc_title": "",
                "project_title": "",
                "identifier": "",
                "link_info": "",
                "doc_type": ""
            }

        dtd, client, doc_title, project_title, identifier, link_info, doc_type = \
            self._load_impact_config_filters(config_path)

        return {
            "dtd": dtd,
            "client": client,
            "doc_title": doc_title,
            "project_title": project_title,
            "identifier": identifier,
            "link_info": link_info,
            "doc_type": doc_type
        }

    @staticmethod
    def format_metadata_line(metadata: dict[str, str]) -> str:
        """
        Format metadata as TYPE|CLIENT|LINK-INFO|IDENTIFIER
        Only includes non-empty values.
        """
        parts = [
            metadata.get("doc_type", ""),
            metadata.get("client", ""),
            metadata.get("link_info", ""),
            metadata.get("identifier", "")
        ]
        # Only return if at least one part has value
        if any(parts):
            return "|".join(parts)
        return ""

    def parse_and_extract(self, file_path: Path, query_type: str, query_val: str, attr_name: str = "", attr_val: str = ""):
        """
        Parses a single file and extracts elements matching the query.
        Returns a list of dictionaries with extracted element details:
        [
            {
                'line': int,
                'tag': str,
                'attributes': dict,
                'text': str,
                'html': str
            }
        ]
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} does not exist.")

        results = []
        
        try:
            with open(file_path, 'rb') as f:
                content_bytes = f.read()
        except Exception as e:
            raise Exception(f"Failed to read file {file_path.name}: {str(e)}")

        is_xml = file_path.suffix.lower() == '.xml'

        # Decode contents to string safely for BS4 and display
        try:
            content_str = content_bytes.decode('utf-8', errors='ignore')
        except Exception:
            content_str = content_bytes.decode('latin-1', errors='ignore')

        if query_type == "XPath":
            try:
                if is_xml:
                    parser = etree.XMLParser(recover=True, encoding='utf-8', resolve_entities=False)
                else:
                    parser = etree.HTMLParser(recover=True, encoding='utf-8')
                
                tree = etree.fromstring(content_bytes, parser=parser)
                if tree is None:
                    raise Exception("Parsed DOM tree is empty.")

                elements = tree.xpath(query_val)
                if not isinstance(elements, list):
                    # In case xpath returns a scalar, wrap it
                    elements = [elements]

                for index, elem in enumerate(elements):
                    # We only process elements. If XPath matches an attribute or text node, we represent it or skip.
                    if isinstance(elem, etree._Element):
                        line_num = elem.sourceline or (index + 1)
                        tag_name = elem.tag
                        if '}' in tag_name:
                            tag_name = tag_name.split('}', 1)[1] # Strip namespace URI
                        
                        attributes = dict(elem.attrib)
                        
                        text_content = "".join([t for t in elem.itertext()]).strip()
                        
                        try:
                            outer_html = etree.tostring(elem, encoding='unicode', method='xml' if is_xml else 'html').strip()
                        except Exception:
                            outer_html = f"<{elem.tag}>...</{elem.tag}>"

                        results.append({
                            'line': line_num,
                            'tag': tag_name,
                            'attributes': attributes,
                            'text': text_content,
                            'html': outer_html
                        })
                    elif isinstance(elem, (str, bytes)):
                        results.append({
                            'line': 1,
                            'tag': 'text_match',
                            'attributes': {},
                            'text': str(elem).strip(),
                            'html': str(elem).strip()
                        })
                    else:
                        # For other XPath result types (like attributes or numbers)
                        val_str = str(elem).strip()
                        results.append({
                            'line': 1,
                            'tag': 'xpath_result',
                            'attributes': {},
                            'text': val_str,
                            'html': val_str
                        })
            except Exception as e:
                raise Exception(f"XPath Error: {str(e)}")

        else:
            # Use BeautifulSoup for Tag Name and CSS Selector for high flexibility and easy query mapping
            try:
                # Use lxml-xml parser for XML files, and standard lxml for HTML
                parser_backend = 'lxml-xml' if is_xml else 'lxml'
                soup = BeautifulSoup(content_str, parser_backend)
                
                elements = []
                if query_type == "Tag Name":
                    tag_to_find = query_val.strip()
                    if tag_to_find == "*" or not tag_to_find:
                        tag_to_find = True
                        
                    if attr_name.strip():
                        # Match tag name + specific attribute
                        target_val = attr_val.strip()
                        if target_val:
                            # Search for attribute matching exactly or containing the value
                            search_attrs = {attr_name.strip(): re.compile(re.escape(target_val))}
                        else:
                            # Just check for existence of attribute
                            search_attrs = {attr_name.strip(): True}
                        elements = soup.find_all(tag_to_find, attrs=search_attrs)
                    else:
                        elements = soup.find_all(tag_to_find)
                        
                elif query_type == "CSS Selector":
                    elements = soup.select(query_val)

                for index, elem in enumerate(elements):
                    line_num = getattr(elem, 'sourceline', None) or (index + 1)
                    tag_name = elem.name or "element"
                    
                    # Normalize attributes (sometimes list like for classes)
                    attributes = {}
                    for k, v in elem.attrs.items():
                        if isinstance(v, list):
                            attributes[k] = " ".join(v)
                        else:
                            attributes[k] = str(v)
                            
                    text_content = elem.get_text().strip()
                    outer_html = str(elem)
                    
                    results.append({
                        'line': line_num,
                        'tag': tag_name,
                        'attributes': attributes,
                        'text': text_content,
                        'html': outer_html
                    })
            except Exception as e:
                raise Exception(f"Parsing/Selector Error: {str(e)}")

        return results

    def scan_directory(self, dir_path: Path, query_type: str, query_val: str,
                       attr_name: str = "", attr_val: str = "", recursive: bool = False,
                       extensions: list = None, filename_filter: str = None,
                       dtd_filter: str = None, client_filter: str = None,
                       progress_callback=None):
        """
        Scans a directory for matching files and extracts elements.
        Uses cache for files that have not been modified since last scan.
        Returns (scan_results, total_matches, total_files)
        """
        dir_path = Path(dir_path)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"'{dir_path}' is not a valid directory.")

        if not extensions:
            extensions = ['.xml', '.html', '.htm', '.xhtml']

        pattern = "**/*" if recursive else "*"
        all_files = []
        normalized_filter = filename_filter.strip() if filename_filter else ""
        if normalized_filter and normalized_filter.lower() != "none" and not any(
            char in normalized_filter for char in "*?[]"
        ):
            normalized_filter = f"*{normalized_filter}"
        for file in dir_path.glob(pattern):
            if not file.is_file():
                continue
            if normalized_filter and normalized_filter.lower() != "none" and not self._matches_filename_filter(
                file.name, normalized_filter
            ):
                continue
            if file.suffix.lower() in extensions:
                if not self._matches_config_filters(file, dtd_filter, client_filter):
                    continue
                all_files.append(file)

        all_files = sorted(all_files)
        total_files = len(all_files)
        
        scan_results = {}
        total_matches = 0
        
        for i, file_path in enumerate(all_files):
            if progress_callback:
                progress_callback(i + 1, total_files, file_path.name)
            
            try:
                # Check cache first
                cached = self._get_cached(file_path, query_type, query_val, attr_name, attr_val)
                if cached is not None:
                    matches = cached
                else:
                    matches = self.parse_and_extract(file_path, query_type, query_val, attr_name, attr_val)
                    self._set_cache(file_path, query_type, query_val, attr_name, attr_val, matches)
                
                if matches:
                    scan_results[str(file_path.absolute())] = {
                        "ok": True,
                        "matches": matches
                    }
                    total_matches += len(matches)
            except Exception as e:
                scan_results[str(file_path.absolute())] = {
                    "ok": False,
                    "error": str(e),
                    "matches": []
                }
                
        return scan_results, total_matches, total_files

    def generate_html_report(self, target_path: str, query_type: str, query_val: str,
                             attr_name: str, attr_val: str, all_selector_results: list,
                             total_matches: int, total_files: int, is_single_file: bool,
                             show_outer_xml: bool = True, show_inner_text: bool = True) -> str:
        """
        Generates a premium HTML report containing all the extracted elements.
        Supports multi-selector results and conditional display of content sections.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target_name = os.path.basename(target_path)

        # Build query description string
        query_desc = f"{query_type}: <code>{html.escape(query_val)}</code>"
        if query_type == "Tag Name" and attr_name.strip():
            query_desc += f" (Filter: <code>{html.escape(attr_name)}</code>"
            if attr_val.strip():
                query_desc += f" = <code>{html.escape(attr_val)}</code>"
            query_desc += ")"

        # Determine if we have multi-selector results
        is_multi_selector = len(all_selector_results) > 1

        # Generate selector sections for multi-selector mode
        selector_sections = ""
        file_global_index = 0

        for selector_idx, selector_data in enumerate(all_selector_results):
            query_val_single = selector_data.get("query_val", query_val)
            scan_results = selector_data.get("scan_results", {})
            selector_matches = selector_data.get("total_matches", 0)

            if is_multi_selector:
                # Add selector header for multi-selector mode
                selector_sections += f"""
                <div class="selector-section">
                    <div class="selector-header" onclick="toggleSelector('selector-{selector_idx}')">
                        <span class="toggle-icon">{'▼' if selector_idx == 0 else '▶'}</span>
                        <span class="selector-badge">{selector_matches} Match(es)</span>
                        <strong class="selector-name">{html.escape(query_val_single)}</strong>
                    </div>
                    <div id="selector-{selector_idx}" class="selector-content" style="display: {'block' if selector_idx == 0 else 'none'}">
                """

            # Generate file sections for this selector
            file_sections = ""
            for file_path_str, data in scan_results.items():
                file_global_index += 1
                file_name = os.path.basename(file_path_str)
                file_uri = Path(file_path_str).as_uri()
                js_file_path = json.dumps(file_path_str)

                # Get file title info for display
                title_type, title_value = self.get_file_title(Path(file_path_str))
                display_title = html.escape(title_value) if title_value else html.escape(file_name)
                title_badge = f'<span class="title-badge">{html.escape(title_type)}</span>' if title_type != "filename" else ""
                filename_sub = f'<span class="file-name-sub">{html.escape(file_name)}</span>' if title_type != "filename" else ""

                # Get metadata for display
                metadata = self.get_file_metadata(Path(file_path_str))
                metadata_line = self.format_metadata_line(metadata)
                metadata_html = f'<div class="file-metadata">{html.escape(metadata_line)}</div>' if metadata_line else ""

                if not data.get("ok", True):
                    # Error file block
                    err_msg = html.escape(data.get("error", "Unknown parse error"))
                    file_sections += f"""
                    <div class="file-card error-card" data-filename="{html.escape(file_name)}">
                        <div class="file-header" onclick="toggleCard('file-{file_global_index}')">
                            <div class="file-header-main">
                                <div class="file-title">
                                    <span class="toggle-icon">▶</span>
                                    <span class="file-badge badge-error">Error</span>
                                    {title_badge}
                                    <strong>{display_title}</strong>
                                    {filename_sub}
                                </div>
                                <div class="file-actions">
                                    <a class="file-action-btn" href="{html.escape(file_uri)}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()">Open HTML</a>
                                    <button class="file-action-btn" onclick='copyFilePath({js_file_path}, this, event)'>Copy Path</button>
                                </div>
                            </div>
                            <div class="file-path">{html.escape(file_path_str)}</div>
                            {metadata_html}
                        </div>
                        <div id="file-{file_global_index}" class="file-content" style="display: none;">
                            <div class="error-box">
                                <strong>Parsing Failed:</strong> {err_msg}
                            </div>
                        </div>
                    </div>
                    """
                    continue

                matches = data.get("matches", [])
                if not matches:
                    continue

                match_rows = ""
                for m_idx, match in enumerate(matches):
                    line = match["line"]
                    tag = match["tag"]
                    attributes = match["attributes"]
                    text_content = match["text"]
                    outer_html = match["html"]

                    # Attribute table (always shown)
                    attr_html = ""
                    if attributes:
                        attr_rows = ""
                        for k, v in attributes.items():
                            attr_rows += f"""
                            <tr>
                                <td class="attr-name">{html.escape(k)}</td>
                                <td class="attr-val">{html.escape(v)}</td>
                            </tr>
                            """
                        attr_html = f"""
                        <div class="attr-section">
                            <span class="section-lbl">Attributes:</span>
                            <table class="attr-table">
                                <thead>
                                    <tr>
                                        <th>Attribute Name</th>
                                        <th>Value</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {attr_rows}
                                </tbody>
                            </table>
                        </div>
                        """

                    # Text section (conditional based on show_inner_text flag)
                    text_section = ""
                    if show_inner_text and text_content:
                        # Show full text (removed 300 char truncation)
                        text_section = f"""
                        <div class="text-section">
                            <span class="section-lbl">Inner Text Content:</span>
                            <div class="text-box">{html.escape(text_content)}</div>
                        </div>
                        """

                    # Code section (conditional based on show_outer_xml flag)
                    code_section = ""
                    if show_outer_xml:
                        escaped_code = html.escape(outer_html)
                        code_section = f"""
                        <div class="code-section">
                            <span class="section-lbl">Outer HTML/XML Markup:</span>
                            <div class="code-wrapper">
                                <pre><code>{escaped_code}</code></pre>
                            </div>
                        </div>
                        """

                    match_rows += f"""
                    <div class="match-item" data-tag="{html.escape(tag)}" data-text="{html.escape(text_content)}">
                        <div class="match-header">
                            <div class="match-meta">
                                <span class="match-number">#{m_idx + 1}</span>
                                <span class="match-badge">Line {line}</span>
                                <span class="match-tag-badge">&lt;{html.escape(tag)}&gt;</span>
                            </div>
                            <button class="copy-btn" onclick="copySnippet(this)">Copy Markup</button>
                        </div>

                        {attr_html}
                        {text_section}
                        {code_section}
                    </div>
                    """

                file_sections += f"""
                <div class="file-card" data-filename="{html.escape(file_name)}">
                    <div class="file-header" onclick="toggleCard('file-{file_global_index}')">
                        <div class="file-header-main">
                            <div class="file-title">
                                <span class="toggle-icon">▼</span>
                                <span class="file-badge badge-success">{len(matches)} Match(es)</span>
                                {title_badge}
                                <strong>{display_title}</strong>
                                {filename_sub}
                            </div>
                            <div class="file-actions">
                                <a class="file-action-btn" href="{html.escape(file_uri)}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()">Open HTML</a>
                                <button class="file-action-btn" onclick='copyFilePath({js_file_path}, this, event)'>Copy Path</button>
                            </div>
                        </div>
                        <div class="file-path">{html.escape(file_path_str)}</div>
                        {metadata_html}
                    </div>
                    <div id="file-{file_global_index}" class="file-content">
                        <div class="matches-list">
                            {match_rows}
                        </div>
                    </div>
                </div>
                """

            if not file_sections:
                file_sections = f"""
                <div class="no-results">
                    No matching elements found for selector: {html.escape(query_val_single)}
                </div>
                """

            if is_multi_selector:
                selector_sections += file_sections
                selector_sections += "</div></div>"  # Close selector-content and selector-section
            else:
                selector_sections = file_sections

        if not file_sections:
            file_sections = f"""
            <div class="no-results">
                No matching elements found in the scanned files.
            </div>
            """

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Element Extraction Report - {html.escape(target_name)}</title>
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
            --tag-color: #38bdf8;
        }}

        /* Selector Section Styles (for multi-selector mode) */
        .selector-section {{
            margin-bottom: 24px;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            background: var(--bg-card);
        }}

        .selector-header {{
            padding: 16px 20px;
            background: rgba(99, 102, 241, 0.1);
            cursor: pointer;
            user-select: none;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid var(--border-color);
        }}

        .selector-header:hover {{
            background: rgba(99, 102, 241, 0.15);
        }}

        .selector-badge {{
            font-size: 0.75rem;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 4px;
            text-transform: uppercase;
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }}

        .selector-name {{
            font-size: 1.1rem;
            color: var(--primary);
        }}

        .selector-content {{
            padding: 20px;
        }}.
        
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            margin: 0;
            padding: 0;
            line-height: 1.5;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        
        header {{
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 24px;
            margin-bottom: 32px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            flex-wrap: wrap;
            gap: 20px;
        }}
        
        .header-title-section h1 {{
            font-size: 2.25rem;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(135deg, #a5b4fc, #6366f1, #38bdf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .header-title-section p {{
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
        }}
        
        /* Stats Dashboard */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }}
        
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        
        .stat-card .lbl {{
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}
        
        .stat-card .val {{
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--text-main);
        }}
        
        .stat-card .val.highlight-match {{
            color: #818cf8;
            background: linear-gradient(135deg, #c7d2fe, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .stat-card .query-details {{
            font-size: 0.85rem;
            color: var(--text-muted);
            word-break: break-all;
            margin-top: 4px;
        }}
        
        /* Interactive Controls */
        .controls-panel {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }}
        
        .search-container {{
            position: relative;
            flex-grow: 1;
            max-width: 500px;
        }}
        
        .search-input {{
            width: 100%;
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 10px 16px 10px 40px;
            border-radius: 8px;
            font-size: 0.95rem;
            outline: none;
            box-sizing: border-box;
            transition: border-color 0.2s;
        }}
        
        .search-input:focus {{
            border-color: var(--primary);
        }}
        
        .search-icon {{
            position: absolute;
            left: 14px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            pointer-events: none;
        }}
        
        .button-group {{
            display: flex;
            gap: 10px;
        }}
        
        .action-btn {{
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            font-size: 0.9rem;
            transition: all 0.2s;
        }}
        
        .action-btn:hover {{
            background: var(--border-color);
        }}
        
        /* Collapsible File Cards */
        .file-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            margin-bottom: 20px;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        
        .file-card.error-card {{
            border-left: 4px solid var(--error);
        }}
        
        .file-header {{
            padding: 16px 20px;
            background: rgba(255, 255, 255, 0.02);
            cursor: pointer;
            user-select: none;
            transition: background 0.2s;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .file-header:hover {{
            background: rgba(255, 255, 255, 0.04);
        }}

        .file-header-main {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}
        
        .file-title {{
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 1.1rem;
            margin-bottom: 4px;
            color: #f3f4f6; /* Light color for dark background */
        }}

        .file-title strong {{
            color: #f3f4f6; /* Ensure title is light colored */
        }}

        .title-badge {{
            font-size: 0.7rem;
            background: rgba(99, 102, 241, 0.2);
            color: #a5b4fc;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.05em;
        }}

        .file-name-sub {{
            font-size: 0.85rem;
            color: #94a3b8; /* Slightly lighter muted color for visibility */
            font-weight: 400;
            display: block;
            margin-top: 4px;
            margin-left: 28px; /* Align with title content */
        }}

        .file-actions {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .file-action-btn {{
            background: rgba(148, 163, 184, 0.08);
            border: 1px solid rgba(148, 163, 184, 0.2);
            color: var(--text-main);
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.82rem;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s;
        }}

        .file-action-btn:hover {{
            background: rgba(148, 163, 184, 0.18);
            border-color: rgba(148, 163, 184, 0.35);
        }}

        .file-action-btn.copied {{
            background: var(--success);
            color: white;
            border-color: var(--success);
        }}
        
        .toggle-icon {{
            font-size: 0.8rem;
            color: var(--text-muted);
            width: 16px;
            display: inline-block;
            transition: transform 0.2s;
        }}
        
        .file-card.collapsed .toggle-icon {{
            transform: rotate(-90deg);
        }}
        
        .file-badge {{
            font-size: 0.75rem;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
            text-transform: uppercase;
        }}
        
        .badge-success {{
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }}
        
        .badge-error {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--error);
            border: 1px solid rgba(239, 68, 68, 0.2);
        }}
        
        .file-path {{
            font-size: 0.8rem;
            color: var(--text-muted);
            padding-left: 28px;
            word-break: break-all;
        }}

        .file-metadata {{
            font-size: 0.85rem;
            color: #38bdf8;  /* Light blue */
            font-family: 'Consolas', 'Courier New', monospace;
            padding-left: 28px;
            margin-top: 4px;
            letter-spacing: 0.02em;
        }}

        .file-content {{
            padding: 20px;
        }}
        
        .error-box {{
            background: rgba(239, 68, 68, 0.08);
            border: 1px solid rgba(239, 68, 68, 0.2);
            color: #fca5a5;
            padding: 16px;
            border-radius: 8px;
            font-size: 0.95rem;
        }}
        
        /* Extracted Match Items */
        .match-item {{
            background: rgba(255, 255, 255, 0.01);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        
        .match-item:last-child {{
            margin-bottom: 0;
        }}
        
        .match-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 12px;
        }}
        
        .match-meta {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .match-number {{
            font-weight: 800;
            color: var(--primary);
            font-size: 1.1rem;
        }}
        
        .match-badge {{
            font-size: 0.8rem;
            background: var(--bg-input);
            color: var(--text-main);
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid var(--border-color);
        }}
        
        .match-tag-badge {{
            font-family: 'Consolas', monospace;
            font-size: 0.85rem;
            background: rgba(56, 189, 248, 0.1);
            color: var(--tag-color);
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid rgba(56, 189, 248, 0.2);
        }}
        
        .copy-btn {{
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.3);
            color: #a5b4fc;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 500;
            transition: all 0.2s;
        }}
        
        .copy-btn:hover {{
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }}
        
        .copy-btn.copied {{
            background: var(--success);
            color: white;
            border-color: var(--success);
        }}
        
        .section-lbl {{
            display: block;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 8px;
            font-weight: 600;
        }}
        
        .attr-section, .text-section, .code-section {{
            margin-bottom: 16px;
        }}
        
        .code-section {{
            margin-bottom: 0;
        }}
        
        /* Attribute Table */
        .attr-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
            margin-top: 4px;
        }}
        
        .attr-table th, .attr-table td {{
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            text-align: left;
        }}
        
        .attr-table th {{
            background: rgba(255, 255, 255, 0.02);
            color: var(--text-muted);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .attr-name {{
            font-family: 'Consolas', monospace;
            color: #f472b6;
            width: 30%;
            font-weight: 600;
        }}
        
        .attr-val {{
            font-family: 'Consolas', monospace;
            color: #e2e8f0;
            word-break: break-all;
        }}
        
        /* Text Box */
        .text-box {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 0.9rem;
            color: #cbd5e1;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        
        /* Code Box */
        .code-wrapper {{
            background: var(--bg-code);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            overflow-x: auto;
            position: relative;
        }}
        
        .code-wrapper pre {{
            margin: 0;
            padding: 0;
        }}
        
        .code-wrapper code {{
            font-family: 'Consolas', 'Fira Code', monospace;
            font-size: 0.9rem;
            color: #34d399; /* Green text for content code */
            display: block;
            white-space: pre;
        }}
        
        .no-results {{
            text-align: center;
            padding: 60px 20px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            color: var(--text-muted);
            font-size: 1.1rem;
        }}
        
        /* Toast notification */
        .toast {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--bg-card);
            border: 1px solid var(--primary);
            color: var(--text-main);
            padding: 12px 24px;
            border-radius: 8px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
            display: flex;
            align-items: center;
            gap: 10px;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            z-index: 1000;
        }}
        
        .toast.show {{
            transform: translateY(0);
            opacity: 1;
        }}
        
        .toast-icon {{
            color: var(--success);
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-title-section">
                <h1>Element Extraction Report</h1>
                <p>Target: <strong>{html.escape(target_name)}</strong></p>
            </div>
            <div class="timestamp">
                Generated: {timestamp}
            </div>
        </header>
        
        <!-- Stats Dashboard -->
        <div class="stats-grid">
            <div class="stat-card">
                <span class="lbl">Total Matches Found</span>
                <span class="val highlight-match">{total_matches}</span>
            </div>
            <div class="stat-card">
                <span class="lbl">Files Processed</span>
                <span class="val">{total_files}</span>
            </div>
            <div class="stat-card">
                <span class="lbl">Selectors Queried</span>
                <span class="val">{len(all_selector_results)}</span>
            </div>
            <div class="stat-card">
                <span class="lbl">Query Method</span>
                <span class="val" style="font-size: 1.4rem; padding-top: 4px;">{query_type}</span>
            </div>
            <div class="stat-card" style="grid-column: span 2;">
                <span class="lbl">Query Selector(s)</span>
                <div class="query-details">{query_desc}</div>
            </div>
        </div>

        <!-- Interactive Controls -->
        <div class="controls-panel">
            <div class="search-container">
                <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <input type="text" id="searchInput" class="search-input" placeholder="Search matches by tag, text, filename, or markup..." oninput="filterResults()">
            </div>

            <div class="button-group">
                <button class="action-btn" onclick="toggleAll(false)">Collapse All</button>
                <button class="action-btn" onclick="toggleAll(true)">Expand All</button>
            </div>
        </div>

        <!-- Results sections (selector-grouped for multi-selector mode) -->
        <div id="resultsList">
            {selector_sections}
        </div>
    </div>
    
    <!-- Toast Popup -->
    <div id="toast" class="toast">
        <span class="toast-icon">✓</span>
        <span id="toastMsg">Markup copied to clipboard!</span>
    </div>

    <script>
        function toggleCard(id) {{
            const content = document.getElementById(id);
            const card = content.parentElement;
            if (content.style.display === 'none') {{
                content.style.display = 'block';
                card.classList.remove('collapsed');
            }} else {{
                content.style.display = 'none';
                card.classList.add('collapsed');
            }}
        }}
        
        function toggleAll(expand) {{
            const cards = document.querySelectorAll('.file-card');
            cards.forEach(card => {{
                const content = card.querySelector('.file-content');
                if (expand) {{
                    content.style.display = 'block';
                    card.classList.remove('collapsed');
                }} else {{
                    content.style.display = 'none';
                    card.classList.add('collapsed');
                }}
            }});
            // Also toggle selector sections
            const selectors = document.querySelectorAll('.selector-content');
            const selectorHeaders = document.querySelectorAll('.selector-header');
            selectors.forEach((content, idx) => {{
                if (expand) {{
                    content.style.display = 'block';
                    const icon = selectorHeaders[idx].querySelector('.toggle-icon');
                    if (icon) icon.textContent = '▼';
                }} else {{
                    content.style.display = 'none';
                    const icon = selectorHeaders[idx].querySelector('.toggle-icon');
                    if (icon) icon.textContent = '▶';
                }}
            }});
        }}

        function toggleSelector(id) {{
            const content = document.getElementById(id);
            const header = content.previousElementSibling;
            const icon = header.querySelector('.toggle-icon');
            if (content.style.display === 'none') {{
                content.style.display = 'block';
                if (icon) icon.textContent = '▼';
            }} else {{
                content.style.display = 'none';
                if (icon) icon.textContent = '▶';
            }}
        }}
        
        function copySnippet(btn) {{
            const matchItem = btn.closest('.match-item');
            const code = matchItem.querySelector('.code-wrapper code').textContent;
            
            navigator.clipboard.writeText(code).then(() => {{
                btn.textContent = 'Copied!';
                btn.classList.add('copied');
                showToast('Markup copied to clipboard!');
                
                setTimeout(() => {{
                    btn.textContent = 'Copy Markup';
                    btn.classList.remove('copied');
                }}, 2000);
            }}).catch(err => {{
                console.error('Failed to copy text: ', err);
                showToast('Failed to copy markup.');
            }});
        }}

        function copyFilePath(filePath, btn, event) {{
            if (event) {{
                event.stopPropagation();
            }}

            navigator.clipboard.writeText(filePath).then(() => {{
                const originalLabel = btn.textContent;
                btn.textContent = 'Copied!';
                btn.classList.add('copied');
                showToast('File path copied to clipboard!');

                setTimeout(() => {{
                    btn.textContent = originalLabel;
                    btn.classList.remove('copied');
                }}, 2000);
            }}).catch(err => {{
                console.error('Failed to copy path: ', err);
                showToast('Failed to copy file path.');
            }});
        }}
        
        function showToast(msg) {{
            const toast = document.getElementById('toast');
            document.getElementById('toastMsg').textContent = msg;
            toast.classList.add('show');
            setTimeout(() => {{
                toast.classList.remove('show');
            }}, 2500);
        }}
        
        function filterResults() {{
            const searchVal = document.getElementById('searchInput').value.toLowerCase().strip();
            const cards = document.querySelectorAll('.file-card');
            
            cards.forEach(card => {{
                const filename = card.getAttribute('data-filename').toLowerCase();
                const matchItems = card.querySelectorAll('.match-item');
                let fileVisible = false;
                
                // If it's an error card, we filter on filename
                if (card.classList.contains('error-card')) {{
                    if (filename.includes(searchVal) || searchVal === '') {{
                        card.style.display = 'block';
                    }} else {{
                        card.style.display = 'none';
                    }}
                    return;
                }}
                
                matchItems.forEach(item => {{
                    const tag = item.getAttribute('data-tag').toLowerCase();
                    const text = item.getAttribute('data-text').toLowerCase();
                    const code = item.querySelector('.code-wrapper code').textContent.toLowerCase();
                    
                    const isMatch = tag.includes(searchVal) || 
                                    text.includes(searchVal) || 
                                    code.includes(searchVal) ||
                                    filename.includes(searchVal);
                                    
                    if (isMatch || searchVal === '') {{
                        item.style.display = 'block';
                        fileVisible = true;
                    }} else {{
                        item.style.display = 'none';
                    }}
                }});
                
                if (fileVisible || searchVal === '') {{
                    card.style.display = 'block';
                    const content = card.querySelector('.file-content');
                    // Automatically expand matches if search is active
                    if (searchVal !== '') {{
                        content.style.display = 'block';
                        card.classList.remove('collapsed');
                    }}
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}
        
        // Helper string helper
        if (!String.prototype.strip) {{
            String.prototype.strip = function() {{
                return this.replace(/^\\s+|\\s+$/g, '');
            }};
        }}
    </script>
</body>
</html>
"""
        return html_template

    def escape_and_highlight(self, outer_html: str) -> str:
        """
        Escapes the markup code for presentation and highlights year patterns.
        """
        escaped_html = html.escape(outer_html)
        
        # Regex to match year patterns like 1999, 1999b, 1999[2000], 1999,, 2000.
        year_re = re.compile(r'\b((?:18|19|20)\d{2}(?:[a-zA-Z]|\[(?:18|19|20)\d{2}\])?[,.]?)(?=\s|\W|$)')
        
        def replacer(match):
            val = match.group(1)
            return f'<span class="highlight-year">{val}</span>'
            
        return year_re.sub(replacer, escaped_html)

    def generate_simple_report(self, target_path: str, query_type: str, query_val: str,
                               scan_results: dict, total_matches: int, total_files: int) -> str:
        """
        Generates a simple 3-column table HTML report:
        S.NO | Filename | Instance outer html (joined by separator)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target_name = os.path.basename(target_path)
        
        table_rows = ""
        s_no = 0
        
        for file_path_str, data in scan_results.items():
            if not data.get("ok", True):
                continue
                
            matches = data.get("matches", [])
            if not matches:
                continue
                
            s_no += 1
            file_name = os.path.basename(file_path_str)
            
            # Format and highlight each match
            highlighted_matches = []
            for match in matches:
                highlighted_matches.append(self.escape_and_highlight(match["html"]))
                
            # Join elements using a visual separator/divider
            joined_html = '<div class="instance-divider"></div>'.join([
                f'<div class="instance-block">{m}</div>' for m in highlighted_matches
            ])
            
            table_rows += f"""
            <tr>
                <td class="col-sno">{s_no}</td>
                <td class="col-file" title="{html.escape(file_path_str)}">
                    <strong>{html.escape(file_name)}</strong>
                    <div class="file-path-sub">{html.escape(file_path_str)}</div>
                </td>
                <td class="col-instances">
                    {joined_html}
                </td>
            </tr>
            """
            
        if not table_rows:
            table_rows = """
            <tr>
                <td colspan="3" class="no-data">No elements found matching the query criteria.</td>
            </tr>
            """
            
        simple_html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple Element Extraction Report - {html.escape(target_name)}</title>
    <style>
        :root {{
            --bg-main: #0f172a;
            --bg-card: #1e293b;
            --border-color: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #818cf8;
            --highlight-bg: #f59e0b;
            --highlight-fg: #0f172a;
        }}
        
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            margin: 0;
            padding: 40px 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            margin-bottom: 30px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            flex-wrap: wrap;
            gap: 15px;
        }}
        
        h1 {{
            margin: 0;
            font-size: 1.8rem;
            color: var(--primary);
        }}
        
        .meta {{
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-top: 5px;
        }}
        
        .timestamp {{
            font-size: 0.85rem;
            background: var(--bg-card);
            padding: 5px 12px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            color: var(--text-muted);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
        
        th {{
            background-color: rgba(255, 255, 255, 0.03);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            font-weight: 600;
        }}
        
        tr:last-child td {{
            border-bottom: none;
        }}
        
        .col-sno {{
            width: 60px;
            font-weight: bold;
            color: var(--primary);
            text-align: center;
        }}
        th.col-sno-header {{
            text-align: center;
        }}
        
        .col-file {{
            width: 250px;
            vertical-align: top;
        }}
        
        .file-path-sub {{
            font-size: 0.75rem;
            color: var(--text-muted);
            word-break: break-all;
            margin-top: 4px;
        }}
        
        .col-instances {{
            vertical-align: top;
        }}
        
        .instance-block {{
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 0.85rem;
            color: #34d399; /* Emerald green code */
            background: rgba(0, 0, 0, 0.2);
            padding: 8px 12px;
            border-radius: 6px;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        
        .instance-divider {{
            height: 1px;
            background: var(--border-color);
            margin: 8px 0;
            opacity: 0.5;
        }}
        
        .highlight-year {{
            background-color: var(--highlight-bg);
            color: var(--highlight-fg);
            padding: 2px 5px;
            border-radius: 4px;
            font-weight: bold;
            display: inline-block;
        }}
        
        .no-data {{
            text-align: center;
            color: var(--text-muted);
            padding: 40px;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Simple Element Extraction Report</h1>
                <div class="meta">
                    Query: <code>{html.escape(query_type)}</code> - <code>{html.escape(query_val)}</code> | 
                    Total Matches: <strong>{total_matches}</strong> in <strong>{total_files}</strong> file(s)
                </div>
            </div>
            <div class="timestamp">
                Generated: {timestamp}
            </div>
        </header>
        
        <table>
            <thead>
                <tr>
                    <th class="col-sno-header">S.NO</th>
                    <th>Filename</th>
                    <th>Instance outer html</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        return simple_html_template

    # ------------------------------------------------------------------
    # Pattern classification helpers
    # ------------------------------------------------------------------

    def classify_text_pattern(self, text: str) -> str:
        """
        Classify a plain-text string into a human-readable pattern label.

        Categories:
          - Empty
          - Alpha Only        (only letters and spaces)
          - Numeric Only      (only digits)
          - Number+Delimiter  (digits mixed with , . ; : - / etc.)
          - Year Pattern      (contains 4-digit year like 1999, 2000b, 1999[2000])
          - Alphanumeric      (letters + digits, no special delimiters)
          - Mixed             (anything else)
        """
        stripped = text.strip()
        if not stripped:
            return "Empty"

        # Year pattern check first (most specific)
        if re.search(r'\b(?:18|19|20)\d{2}(?:[a-zA-Z]|\[\d{4}\])?[,.]?\b', stripped):
            return "Year Pattern"

        # Pure alphabetic (with spaces)
        if re.fullmatch(r'[A-Za-z\s]+', stripped):
            return "Alpha Only"

        # Pure numeric
        if re.fullmatch(r'\d+', stripped):
            return "Numeric Only"

        # Number + delimiter  (digits with , . ; : - / and spaces)
        if re.fullmatch(r'[\d,.\s;:\-/]+', stripped):
            return "Number+Delimiter"

        # Alphanumeric (letters + digits + spaces, no special chars)
        if re.fullmatch(r'[A-Za-z0-9\s]+', stripped):
            return "Alphanumeric"

        # Everything else
        return "Mixed"

    def generate_pattern_report(self, target_path: str, query_type: str, query_val: str,
                                scan_results: dict, total_matches: int, total_files: int) -> str:
        """
        Generates a pattern-classified HTML report.
        Shows only element text content (no attributes)
        grouped and sorted by detected text pattern.

        Columns:  S.NO | Filename | Text Content | Pattern
        Rows are separated by pattern group headers.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target_name = os.path.basename(target_path)

        # Collect rows: (pattern, file_name, file_path, text, line)
        all_rows = []
        for file_path_str, data in scan_results.items():
            if not data.get("ok", True):
                continue
            for match in data.get("matches", []):
                text = match.get("text", "").strip()
                pattern = self.classify_text_pattern(text)
                outer = match.get("outer", "") or match.get("xml", "") or match.get("html", "")

                all_rows.append({
                    "pattern": pattern,
                    "file_name": os.path.basename(file_path_str),
                    "file_path": file_path_str,
                    "text": text,
                    "line": match.get("line", ""),
                    "outer": outer
                })

        # Sort by pattern, then by filename
        pattern_order = [
            "Year Pattern", "Numeric Only", "Number+Delimiter",
            "Alpha Only", "Alphanumeric", "Mixed", "Empty"
        ]
        order_map = {p: i for i, p in enumerate(pattern_order)}
        all_rows.sort(key=lambda r: (order_map.get(r["pattern"], 99), r["file_name"]))

        # Pattern colour mapping
        pattern_colors = {
            "Year Pattern":      "#f59e0b",
            "Numeric Only":      "#3b82f6",
            "Number+Delimiter":  "#8b5cf6",
            "Alpha Only":        "#10b981",
            "Alphanumeric":      "#06b6d4",
            "Mixed":             "#f43f5e",
            "Empty":             "#64748b",
        }

        # Build pattern summary counts
        pattern_counts = {}
        for row in all_rows:
            pattern_counts[row["pattern"]] = pattern_counts.get(row["pattern"], 0) + 1

        summary_badges = ""
        for pat in pattern_order:
            cnt = pattern_counts.get(pat, 0)
            if cnt > 0:
                clr = pattern_colors.get(pat, "#94a3b8")
                summary_badges += f'<span class="badge" style="background:{clr}">{html.escape(pat)}: {cnt}</span> '

        # Build table rows grouped by pattern
        table_rows = ""
        current_pattern = None
        s_no = 0

        for row in all_rows:
            # Insert pattern group header
            if row["pattern"] != current_pattern:
                current_pattern = row["pattern"]
                clr = pattern_colors.get(current_pattern, "#94a3b8")
                table_rows += f"""
            <tr class="pattern-group-header">
                <td colspan="5" style="border-left:4px solid {clr};">
                    <span class="pattern-label" style="background:{clr};">{html.escape(current_pattern)}</span>
                    <span class="pattern-count">{pattern_counts.get(current_pattern, 0)} instance(s)</span>
                </td>
            </tr>"""

            s_no += 1
            clr = pattern_colors.get(row["pattern"], "#94a3b8")
            display_text = html.escape(row["text"]) if row["text"] else '<em class="empty-text">(empty)</em>'
            outer_html = html.escape(row["outer"]) if row["outer"] else ""

            # Highlight year spans inside the display text
            if row["pattern"] == "Year Pattern":
                display_text = self.escape_and_highlight(row["text"])

            table_rows += f"""
            <tr>
                <td class="col-sno">{s_no}</td>
                <td class="col-file" title="{html.escape(row['file_path'])}">
                    <strong>{html.escape(row['file_name'])}</strong>
                    <div class="file-line">Line {row['line']}</div>
                </td>
                <td class="col-text">{display_text}</td>
                <td class="col-outer"><pre class="outer-preview">{outer_html}</pre></td>
                <td class="col-pattern"><span class="pattern-tag" style="background:{clr};">{html.escape(row['pattern'])}</span></td>
            </tr>"""

        if not table_rows:
            table_rows = """
            <tr>
                <td colspan="4" class="no-data">No elements found matching the query criteria.</td>
            </tr>"""

        pattern_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pattern Analysis Report - {html.escape(target_name)}</title>
    <style>
        :root {{
            --bg-main: #0f172a;
            --bg-card: #1e293b;
            --border-color: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #818cf8;
        }}

        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg-main);
            color: var(--text-main);
            margin: 0;
            padding: 40px 20px;
        }}

        .container {{ max-width: 1300px; margin: 0 auto; }}

        header {{
            margin-bottom: 30px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 20px;
        }}

        h1 {{ margin:0; font-size:1.8rem; color: var(--primary); }}

        .meta {{ color: var(--text-muted); font-size:0.9rem; margin-top:5px; }}

        .timestamp {{
            font-size: 0.85rem;
            background: var(--bg-card);
            padding: 5px 12px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            display: inline-block;
            margin-top: 10px;
        }}

        .badge-bar {{ margin: 15px 0; display: flex; flex-wrap: wrap; gap: 8px; }}

        .badge {{
            display: inline-block;
            padding: 5px 14px;
            border-radius: 20px;
            font-size: 0.82rem;
            font-weight: 600;
            color: #0f172a;
        }}

        /* Filter bar */
        .filter-bar {{
            display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;
        }}
        .filter-bar select, .filter-bar input {{
            background: var(--bg-card);
            color: var(--text-main);
            border: 1px solid var(--border-color);
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 0.9rem;
        }}
        .filter-bar select {{ min-width: 180px; cursor: pointer; }}
        .filter-bar input {{ flex: 1; min-width: 200px; }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }}

        th, td {{
            padding: 10px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}

        th {{
            background: rgba(255,255,255,0.03);
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            font-weight: 600;
            position: sticky; top: 0;
        }}

        tr:last-child td {{ border-bottom: none; }}

        .col-sno {{
            width: 55px; font-weight: bold;
            color: var(--primary); text-align: center;
        }}

        .col-file {{ width: 220px; vertical-align: top; }}

        .file-line {{
            font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;
        }}

        .col-text {{
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 0.88rem;
            color: #34d399;
            white-space: pre-wrap;
            word-break: break-word;
            vertical-align: top;
        }}

        .col-pattern {{ width: 150px; vertical-align: top; text-align: center; }}

        .pattern-tag {{
            display: inline-block;
            padding: 3px 12px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 600;
            color: #0f172a;
        }}

        .pattern-group-header td {{
            background: rgba(255,255,255,0.02);
            padding: 12px 16px;
            font-weight: 600;
        }}

        .pattern-label {{
            display: inline-block;
            padding: 3px 14px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 700;
            color: #0f172a;
            margin-right: 10px;
        }}

        .pattern-count {{
            color: var(--text-muted);
            font-size: 0.85rem;
            font-weight: 400;
        }}

        .highlight-year {{
            background-color: #f59e0b;
            color: #0f172a;
            padding: 2px 5px;
            border-radius: 4px;
            font-weight: bold;
            display: inline-block;
        }}

        .empty-text {{ color: var(--text-muted); }}

        .no-data {{
            text-align: center;
            color: var(--text-muted);
            padding: 40px;
            font-style: italic;
        }}
        .col-outer{{
            max-width: 500px;
        }}

        .outer-preview{{
            margin:0;
            padding:8px;
            max-height:180px;
            overflow:auto;
            white-space:pre-wrap;
            word-break:break-word;
            background:#0f172a;
            color:#e2e8f0;
            border-radius:6px;
            font-size:12px;
            line-height:1.45;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Pattern Analysis Report</h1>
            <div class="meta">
                Query: <code>{html.escape(query_type)}</code> &mdash; <code>{html.escape(query_val)}</code> |
                Total Matches: <strong>{total_matches}</strong> in <strong>{total_files}</strong> file(s)
            </div>
            <div class="badge-bar">{summary_badges}</div>
            <div class="timestamp">Generated: {timestamp}</div>
        </header>

        <div class="filter-bar">
            <select id="patternFilter" onchange="filterTable()">
                <option value="">All Patterns</option>
                {"".join(f'<option value="{html.escape(p)}">{html.escape(p)} ({pattern_counts.get(p, 0)})</option>' for p in pattern_order if pattern_counts.get(p, 0) > 0)}
            </select>
            <input id="textSearch" type="text" placeholder="Search text content..." oninput="filterTable()">
        </div>

        <table id="reportTable">
            <thead>
                <tr>
                    <th style="text-align:center">S.NO</th>
                    <th>Filename</th>
                    <th>Text Content</th>
                    <th>Instance outer html</th>
                    <th style="text-align:center">Pattern</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>

    <script>
        function filterTable() {{
            const patternVal = document.getElementById('patternFilter').value.toLowerCase();
            const searchVal  = document.getElementById('textSearch').value.toLowerCase().trim();
            const rows = document.querySelectorAll('#reportTable tbody tr');

            let currentGroupVisible = true;

            rows.forEach(row => {{
                if (row.classList.contains('pattern-group-header')) {{
                    const label = row.querySelector('.pattern-label');
                    const groupPattern = label ? label.textContent.toLowerCase().trim() : '';
                    currentGroupVisible = (!patternVal || groupPattern === patternVal);
                    row.style.display = currentGroupVisible ? '' : 'none';
                    return;
                }}

                if (!currentGroupVisible) {{
                    row.style.display = 'none';
                    return;
                }}

                const textCell = row.querySelector('.col-text');
                const textContent = textCell ? textCell.textContent.toLowerCase() : '';
                const fileCell = row.querySelector('.col-file');
                const fileName = fileCell ? fileCell.textContent.toLowerCase() : '';

                if (searchVal && !textContent.includes(searchVal) && !fileName.includes(searchVal)) {{
                    row.style.display = 'none';
                }} else {{
                    row.style.display = '';
                }}
            }});
        }}
    </script>
</body>
</html>
"""
        return pattern_html

    def generate_consolidated_summary_report(self, all_selector_results: list, target_path: str,
                                             timestamp_str: str, is_single_file: bool) -> str:
        """
        Generates a consolidated summary HTML report with per-selector stats cards and file tables.
        Inspired by the Patterns tool's consolidated box style.
        """
        from datetime import datetime
        import html

        target_name = os.path.basename(target_path)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Calculate overall stats
        total_selectors = len(all_selector_results)
        total_matches = sum(s.get("total_matches", 0) for s in all_selector_results)
        total_files_scanned = all_selector_results[0].get("total_files", 0) if all_selector_results else 0

        # Generate per-selector stats cards
        selector_stats_html = ""
        for selector_data in all_selector_results:
            query_val = selector_data.get("query_val", "Unknown")
            scan_results = selector_data.get("scan_results", {})
            total_matches_selector = selector_data.get("total_matches", 0)

            # Count files with matches for this selector
            files_with_matches = sum(
                1 for data in scan_results.values()
                if data.get("ok", True) and data.get("matches")
            )

            # Determine card color based on matches
            if total_matches_selector == 0:
                card_class = "stat-card-empty"
            elif total_matches_selector < 10:
                card_class = "stat-card-low"
            else:
                card_class = "stat-card-high"

            selector_stats_html += f"""
            <div class="consolidated-card {card_class}">
                <div class="card-header">
                    <span class="card-icon">🔍</span>
                    <span class="card-title">{html.escape(query_val)}</span>
                </div>
                <div class="card-body">
                    <div class="card-stat">
                        <span class="stat-value">{files_with_matches}</span>
                        <span class="stat-label">/ {total_files_scanned} files</span>
                    </div>
                    <div class="card-stat">
                        <span class="stat-value highlight">{total_matches_selector}</span>
                        <span class="stat-label">instances</span>
                    </div>
                </div>
            </div>
            """

        # Generate per-selector file tables
        selector_tables_html = ""
        for selector_idx, selector_data in enumerate(all_selector_results):
            query_val = selector_data.get("query_val", "Unknown")
            scan_results = selector_data.get("scan_results", {})

            # Build file table rows
            table_rows = ""
            for file_path_str, data in scan_results.items():
                if not data.get("ok", True):
                    continue
                matches = data.get("matches", [])
                if not matches:
                    continue

                file_name = os.path.basename(file_path_str)
                instance_count = len(matches)
                lines = [str(m.get("line", "")) for m in matches]
                lines_str = ", ".join(lines[:10])
                if len(lines) > 10:
                    lines_str += f", ... (+{len(lines) - 10} more)"

                table_rows += f"""
                <tr>
                    <td class="col-path">{html.escape(file_path_str)}</td>
                    <td class="col-filename">{html.escape(file_name)}</td>
                    <td class="col-count">{instance_count}</td>
                    <td class="col-lines">{html.escape(lines_str)}</td>
                </tr>
                """

            if not table_rows:
                table_rows = f"""
                <tr>
                    <td colspan="4" class="no-data">No matches found for this selector.</td>
                </tr>
                """

            selector_tables_html += f"""
            <div class="selector-table-section">
                <h3 class="selector-title">📌 {html.escape(query_val)}</h3>
                <div class="table-wrapper">
                    <table class="file-table">
                        <thead>
                            <tr>
                                <th class="col-path">File Path</th>
                                <th class="col-filename">File Name</th>
                                <th class="col-count">Instances</th>
                                <th class="col-lines">Line(s)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
            </div>
            """

        summary_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Element Extraction Summary - {html.escape(target_name)}</title>
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

        /* Overall Stats */
        .overall-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .overall-stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}

        .overall-stat-card .stat-label {{
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}

        .overall-stat-card .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--accent);
        }}

        /* Consolidated Stats Grid */
        .consolidated-box {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 40px;
        }}

        .consolidated-title {{
            font-size: 1.2rem;
            font-weight: 600;
            margin: 0 0 20px 0;
            color: var(--accent);
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .consolidated-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
        }}

        .consolidated-card {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .consolidated-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }}

        .consolidated-card.stat-card-high {{
            border-left: 4px solid var(--success);
        }}

        .consolidated-card.stat-card-low {{
            border-left: 4px solid var(--warning);
        }}

        .consolidated-card.stat-card-empty {{
            border-left: 4px solid var(--text-muted);
            opacity: 0.7;
        }}

        .card-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
        }}

        .card-icon {{
            font-size: 1.2rem;
        }}

        .card-title {{
            font-weight: 600;
            font-size: 1rem;
            color: var(--text-main);
            word-break: break-word;
        }}

        .card-body {{
            display: flex;
            gap: 24px;
        }}

        .card-stat {{
            display: flex;
            flex-direction: column;
        }}

        .card-stat .stat-value {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-main);
        }}

        .card-stat .stat-value.highlight {{
            color: var(--accent);
        }}

        .card-stat .stat-label {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}

        /* Per-Selector Tables */
        .tables-section {{
            margin-top: 40px;
        }}

        .section-title {{
            font-size: 1.3rem;
            font-weight: 600;
            margin: 0 0 20px 0;
            color: var(--text-main);
        }}

        .selector-table-section {{
            margin-bottom: 32px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
        }}

        .selector-title {{
            background: rgba(99, 102, 241, 0.1);
            margin: 0;
            padding: 16px 20px;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--accent);
            border-bottom: 1px solid var(--border-color);
        }}

        .table-wrapper {{
            overflow-x: auto;
        }}

        .file-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}

        .file-table th {{
            background: rgba(255, 255, 255, 0.02);
            padding: 12px 16px;
            text-align: left;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border-color);
        }}

        .file-table td {{
            padding: 12px 16px;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-main);
        }}

        .file-table tr:last-child td {{
            border-bottom: none;
        }}

        .file-table tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}

        .col-path {{
            font-family: 'Consolas', monospace;
            font-size: 0.85rem;
            color: var(--text-muted);
            max-width: 400px;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .col-filename {{
            font-weight: 500;
        }}

        .col-count {{
            text-align: center;
            font-weight: 600;
            color: var(--accent);
        }}

        .col-lines {{
            font-family: 'Consolas', monospace;
            font-size: 0.85rem;
            color: var(--text-muted);
        }}

        .no-data {{
            text-align: center;
            padding: 40px;
            color: var(--text-muted);
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Element Extraction Summary Report</h1>
            <p class="subtitle">Target: <strong>{html.escape(target_name)}</strong></p>
            <div class="timestamp">Generated: {timestamp}</div>
        </header>

        <!-- Overall Stats -->
        <div class="overall-stats">
            <div class="overall-stat-card">
                <div class="stat-label">Selectors Queried</div>
                <div class="stat-value">{total_selectors}</div>
            </div>
            <div class="overall-stat-card">
                <div class="stat-label">Files Scanned</div>
                <div class="stat-value">{total_files_scanned}</div>
            </div>
            <div class="overall-stat-card">
                <div class="stat-label">Total Matches</div>
                <div class="stat-value">{total_matches}</div>
            </div>
        </div>

        <!-- Consolidated Stats Grid -->
        <div class="consolidated-box">
            <h2 class="consolidated-title">📊 Per-Selector Statistics</h2>
            <div class="consolidated-grid">
                {selector_stats_html}
            </div>
        </div>

        <!-- Per-Selector File Tables -->
        <div class="tables-section">
            <h2 class="section-title">📁 Per-Selector File Details</h2>
            {selector_tables_html}
        </div>
    </div>
</body>
</html>
"""
        return summary_html

    def export_csv(self, all_selector_results: list, output_path: Path) -> Path:
        """
        Exports all match instances to a CSV file.
        Columns: selector, query_type, file_path, file_name, instance_no, line, tag, inner_text, outer_xml
        """
        import csv

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow([
                'selector', 'query_type', 'file_path', 'file_name',
                'instance_no', 'line', 'tag', 'inner_text', 'outer_xml'
            ])

            # Write data rows
            for selector_data in all_selector_results:
                query_val = selector_data.get('query_val', '')
                query_type = selector_data.get('query_type', '')
                scan_results = selector_data.get('scan_results', {})

                for file_path_str, data in scan_results.items():
                    if not data.get('ok', True):
                        continue
                    matches = data.get('matches', [])
                    if not matches:
                        continue

                    file_name = os.path.basename(file_path_str)
                    for idx, match in enumerate(matches, 1):
                        writer.writerow([
                            query_val,
                            query_type,
                            file_path_str,
                            file_name,
                            idx,
                            match.get('line', ''),
                            match.get('tag', ''),
                            match.get('text', ''),
                            match.get('html', '')
                        ])

        return output_path

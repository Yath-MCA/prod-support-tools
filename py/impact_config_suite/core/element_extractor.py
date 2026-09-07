import os
import re
import html
import json
import hashlib
import fnmatch
import warnings
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag
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
    def _matches_month_filter(file_path: Path, month_filter: str, custom_month: str = "") -> bool:
        """
        Check if file modification time matches month filter.

        Args:
            file_path: Path to file
            month_filter: "All Time", "This Month", "Last Month", or "Custom"
            custom_month: Custom month in MM-YYYY format when filter is "Custom"

        Returns:
            True if file matches filter criteria
        """
        if month_filter == "All Time" or not month_filter:
            return True

        try:
            file_mtime = file_path.stat().st_mtime
            file_date = datetime.fromtimestamp(file_mtime)
            now = datetime.now()

            if month_filter == "This Month":
                return file_date.year == now.year and file_date.month == now.month

            elif month_filter == "Last Month":
                # Calculate last month
                if now.month == 1:
                    last_month_year = now.year - 1
                    last_month = 12
                else:
                    last_month_year = now.year
                    last_month = now.month - 1
                return file_date.year == last_month_year and file_date.month == last_month

            elif month_filter == "Custom":
                if not custom_month or not custom_month.strip():
                    # Custom filter selected but no month specified - exclude all files
                    return False
                # Parse MM-YYYY or YYYY-MM format
                custom_month = custom_month.strip()
                try:
                    if "-" in custom_month:
                        parts = custom_month.split("-")
                        if len(parts[0]) == 4:  # YYYY-MM
                            target_year, target_month = int(parts[0]), int(parts[1])
                        else:  # MM-YYYY
                            target_month, target_year = int(parts[0]), int(parts[1])
                    else:
                        return False  # Invalid format, exclude file

                    return file_date.year == target_year and file_date.month == target_month
                except (ValueError, IndexError):
                    return False  # Invalid format, exclude file

            return True
        except (OSError, ValueError):
            return True  # Error checking, include file

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
        # IMPACT originals: DOCID_original.xml (e.g. N20001_original.xml,
        # TNF_Book_001_original.xml). Also accept legacy name._original.xml.
        if lowered_filter in ("*_original.xml", "*._original.xml"):
            stem = Path(file_name).stem
            return bool(
                re.fullmatch(r".+_original", stem, flags=re.IGNORECASE)
                or re.fullmatch(r"[^.]+\._original", stem, flags=re.IGNORECASE)
            )

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
                       month_filter: str = "All Time", custom_month: str = "",
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
                # Apply month filter
                if not self._matches_month_filter(file, month_filter, custom_month):
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

    def scan_directory_batch(self, dir_path: Path, query_type: str, query_val: str,
                               attr_name: str = "", attr_val: str = "",
                               extensions: list = None, filename_filter: str = None,
                               dtd_filter: str = None, client_filter: str = None,
                               month_filter: str = "All Time", custom_month: str = "",
                               batch_size: int = 50, batch_offset: int = 0,
                               progress_callback=None):
        """
        Scan directory in batches - only process batch_size folders starting from offset.

        This method processes files folder-by-folder, limiting the scan to a specific
        batch of folders. This is useful for large directories where scanning all
        folders at once would be time-consuming or memory-intensive.

        Args:
            dir_path: Root directory path to scan
            query_type: Type of query ("Tag Name", "CSS Selector", "XPath")
            query_val: Query value to search for
            attr_name: Attribute name filter (for Tag Name queries)
            attr_val: Attribute value filter (for Tag Name queries)
            extensions: List of file extensions to scan (default: ['.xml', '.html', '.htm', '.xhtml'])
            filename_filter: Filename pattern filter
            dtd_filter: DTD type filter (requires impact_config.xml)
            client_filter: Client name filter (requires impact_config.xml)
            month_filter: Month filter ("All Time", "This Month", "Last Month", "Custom")
            custom_month: Custom month string when month_filter is "Custom"
            batch_size: Number of folders to process in this batch
            batch_offset: Number of folders to skip (for resuming)
            progress_callback: Optional callback(current, total, filename) for progress updates

        Returns:
            Tuple of (scan_results, total_matches, processed_files, has_more, next_offset)
            - scan_results: Dict of file_path -> {"ok": bool, "matches": list, "error": str}
            - total_matches: Total number of matching elements found
            - processed_files: Number of files processed in this batch
            - has_more: True if there are more folders to process after this batch
            - next_offset: Offset to use for the next batch (if has_more is True)
        """
        dir_path = Path(dir_path)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"'{dir_path}' is not a valid directory.")

        if not extensions:
            extensions = ['.xml', '.html', '.htm', '.xhtml']

        # Get immediate subdirectories (not recursive) - sorted for consistent ordering
        all_folders = sorted([d for d in dir_path.iterdir() if d.is_dir()])
        total_folders = len(all_folders)

        # Apply offset and batch size
        folders_to_process = all_folders[batch_offset:batch_offset + batch_size]
        next_offset = batch_offset + batch_size
        has_more = next_offset < total_folders

        # Normalize filename filter
        normalized_filter = filename_filter.strip() if filename_filter else ""
        if normalized_filter and normalized_filter.lower() != "none" and not any(
            char in normalized_filter for char in "*?[]"
        ):
            normalized_filter = f"*{normalized_filter}"

        # Collect all files from the folders to process (recursive within each folder)
        all_files = []
        for folder in folders_to_process:
            for file in folder.rglob("*"):
                if not file.is_file():
                    continue
                if file.suffix.lower() not in extensions:
                    continue
                # Apply filename filter
                if normalized_filter and normalized_filter.lower() != "none":
                    if not self._matches_filename_filter(file.name, normalized_filter):
                        continue
                # Apply DTD and client filters
                if not self._matches_config_filters(file, dtd_filter, client_filter):
                    continue
                # Apply month filter
                if not self._matches_month_filter(file, month_filter, custom_month):
                    continue
                all_files.append(file)

        all_files = sorted(all_files)
        total_files = len(all_files)

        # Process files
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

        return scan_results, total_matches, total_files, has_more, next_offset

    def _process_single_file(self, file_path: Path, query_type: str, query_val: str,
                             attr_name: str, attr_val: str):
        """
        Process a single file - designed to be called by ProcessPoolExecutor.
        Note: Caching is disabled in parallel mode since cache is not shared across processes.
        """
        try:
            matches = self.parse_and_extract(file_path, query_type, query_val, attr_name, attr_val)
            return {"ok": True, "matches": matches}
        except Exception as e:
            return {"ok": False, "error": str(e), "matches": []}

    def scan_directory_parallel(self, dir_path: Path, query_type: str, query_val: str,
                               attr_name: str = "", attr_val: str = "",
                               extensions: list = None, filename_filter: str = None,
                               dtd_filter: str = None, client_filter: str = None,
                               month_filter: str = "All Time", custom_month: str = "",
                               batch_size: int = 0, batch_offset: int = 0,
                               max_workers: int = None, progress_callback=None,
                               recursive: bool = True):
        """
        Parallel directory scanning using ProcessPoolExecutor for 3-4x speedup on multi-core machines.

        Args:
            dir_path: Root directory path to scan
            query_type: Type of query ("Tag Name", "CSS Selector", "XPath")
            query_val: Query value to search for
            attr_name: Attribute name filter (for Tag Name queries)
            attr_val: Attribute value filter (for Tag Name queries)
            extensions: List of file extensions to scan (default: ['.xml', '.html', '.htm', '.xhtml'])
            filename_filter: Filename pattern filter
            dtd_filter: DTD type filter (requires impact_config.xml)
            client_filter: Client name filter (requires impact_config.xml)
            month_filter: Month filter ("All Time", "This Month", "Last Month", "Custom")
            custom_month: Custom month string when month_filter is "Custom"
            batch_size: Number of folders to process (0 means no batch limit)
            batch_offset: Number of folders to skip (for resuming)
            max_workers: Number of parallel processes (default: min(CPU count, 8))
            progress_callback: Optional callback(current, total, filename) for progress updates
            recursive: Whether to scan subdirectories recursively (default: True)

        Returns:
            Tuple of (scan_results, total_matches, total_files, has_more, next_offset)
            - scan_results: Dict of file_path -> {"ok": bool, "matches": list, "error": str}
            - total_matches: Total number of matching elements found
            - total_files: Number of files processed
            - has_more: True if there are more folders to process after this batch
            - next_offset: Offset to use for the next batch (if has_more is True)
        """
        dir_path = Path(dir_path)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"'{dir_path}' is not a valid directory.")

        if not extensions:
            extensions = ['.xml', '.html', '.htm', '.xhtml']

        # Determine max_workers (cap at 8 to avoid overwhelming I/O)
        if max_workers is None:
            max_workers = min(multiprocessing.cpu_count(), 8)

        # Get folders (respect batch settings)
        if batch_size > 0:
            all_folders = sorted([d for d in dir_path.iterdir() if d.is_dir()])
            total_folders = len(all_folders)
            folders_to_process = all_folders[batch_offset:batch_offset + batch_size]
            next_offset = batch_offset + batch_size
            has_more = next_offset < total_folders
        else:
            folders_to_process = [dir_path]
            has_more = False
            next_offset = 0

        # Normalize filename filter
        normalized_filter = filename_filter.strip() if filename_filter else ""
        if normalized_filter and normalized_filter.lower() != "none" and not any(
            char in normalized_filter for char in "*?[]"
        ):
            normalized_filter = f"*{normalized_filter}"

        # Collect all files matching filters
        all_files = []
        for folder in folders_to_process:
            # Use rglob for recursive, glob for non-recursive
            file_iterator = folder.rglob("*") if recursive else folder.glob("*")
            for file in file_iterator:
                if not file.is_file():
                    continue
                if file.suffix.lower() not in extensions:
                    continue
                # Apply filename filter
                if normalized_filter and normalized_filter.lower() != "none":
                    if not self._matches_filename_filter(file.name, normalized_filter):
                        continue
                # Apply DTD and client filters
                if not self._matches_config_filters(file, dtd_filter, client_filter):
                    continue
                # Apply month filter
                if not self._matches_month_filter(file, month_filter, custom_month):
                    continue
                all_files.append(file)

        all_files = sorted(all_files)
        total_files = len(all_files)

        # Process files in parallel
        scan_results = {}
        total_matches = 0
        processed_count = 0

        # Use ProcessPoolExecutor for parallel processing
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self._process_single_file,
                              file_path, query_type, query_val,
                              attr_name, attr_val): file_path
                for file_path in all_files
            }

            # Collect results as they complete
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                processed_count += 1

                try:
                    result = future.result()  # No timeout - allow slow files to complete
                    if result:
                        scan_results[str(file_path.absolute())] = result
                        if result.get("ok") and result.get("matches"):
                            total_matches += len(result["matches"])
                except Exception as e:
                    scan_results[str(file_path.absolute())] = {
                        "ok": False,
                        "error": str(e),
                        "matches": []
                    }

                # Report progress every 5 files
                if progress_callback and processed_count % 5 == 0:
                    progress_callback(processed_count, total_files, file_path.name)

        # Final progress callback if not already reported
        if progress_callback and total_files > 0 and processed_count % 5 != 0:
            progress_callback(processed_count, total_files, all_files[-1].name if all_files else "")

        return scan_results, total_matches, total_files, has_more, next_offset

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

    # ------------------------------------------------------------------
    # Bibliographic citation type (direct / indirect) helpers
    # ------------------------------------------------------------------

    CITE_TYPE_PRESETS = [
        "All",
        "bibr",
        "fig",
        "table",
        "table-wrap",
        "chapter",
        "equation",
        "endnote",
        "fn",
        "sec",
        "boxed-text",
    ]
    BIBR_SELECTOR = '[data-role="bibr"]'  # legacy alias; prefer cite_type APIs
    _PAGE_PP_RE = re.compile(r",\s*pp\.\s*[\d]+", re.IGNORECASE)
    _PAGE_P_RE = re.compile(r",\s*p\.\s*[\d]+", re.IGNORECASE)
    _YEAR_IN_PARENS_RE = re.compile(r"\(\s*(?:18|19|20)\d{2}")
    _AUTHOR_YEAR_COMMA_RE = re.compile(r",\s*(?:18|19|20)\d{2}")
    _YEAR_BARE_RE = re.compile(r"(?:18|19|20)\d{2}")
    _ND_RE = re.compile(r"\bn\.?\s*d\.?\b", re.IGNORECASE)
    _ET_AL_RE = re.compile(r"\bet\s+al\.?\b", re.IGNORECASE)
    _DUAL_AND_RE = re.compile(r"\band\b", re.IGNORECASE)
    _POSSESSIVE_RE = re.compile(r"[\u2019']s\b")
    _DIRECT_AUTHOR_YEAR_RE = re.compile(
        r"^(.*?)\s*\(\s*([^)]+?)\s*\)\s*$", re.DOTALL
    )
    _COMMA_AUTHOR_YEAR_RE = re.compile(
        r"^(.*?),\s*([^,]+)$", re.DOTALL
    )
    _BARE_AUTHOR_YEAR_RE = re.compile(
        r"^(.*?)\s+((?:18|19|20)\d{2}[a-z]?|n\.?\s*d\.?)\s*$",
        re.IGNORECASE | re.DOTALL,
    )
    _NUMBER_RANGE_RE = re.compile(
        r"\d+\s*[-–—]\s*\d+"
        r"|\d+\s*,\s*\d+"
        r"|\d+\s+and\s+\d+",
        re.IGNORECASE,
    )

    def resolve_cite_type(self, elem):
        """
        Resolve cite type from object-type, then ref-type, then data-role.
        Returns (value_lower, source) or None.
        """
        attrs = getattr(elem, "attrs", None) or {}
        for source in ("object-type", "ref-type", "data-role"):
            val = attrs.get(source)
            if isinstance(val, list):
                val = " ".join(str(v) for v in val)
            if val is None:
                continue
            text = str(val).strip()
            if text:
                return text.lower(), source
        return None

    def _normalize_cite_type_filter(self, cite_type: str) -> str:
        """Return lowercase filter, or 'all' when empty/All."""
        t = (cite_type or "bibr").strip()
        if not t or t.lower() == "all":
            return "all"
        return t.lower()

    def _iter_cite_candidates(self, soup):
        """Yield unique xref / related-object / typed cite elements."""
        seen = set()
        selectors = [
            "xref",
            "a.xref",
            '[data-name="related-object"]',
            "[ref-type]",
            "[object-type]",
            "[data-role]",
        ]
        for sel in selectors:
            try:
                found = soup.select(sel)
            except Exception:
                continue
            for elem in found:
                eid = id(elem)
                if eid in seen:
                    continue
                seen.add(eid)
                yield elem

    def cite_type_selector_label(self, cite_type: str) -> str:
        """Human-readable selector description for reports."""
        filtered = self._normalize_cite_type_filter(cite_type)
        if filtered == "all":
            return "ref-type | object-type | data-role (All)"
        return f'ref-type|object-type|data-role = "{filtered}"'

    def _sibling_text_left(self, elem, max_chars: int = 300) -> str:
        """Collect text from previous siblings within the same parent."""
        parts = []
        total = 0
        node = elem.previous_sibling
        while node is not None and total < max_chars:
            if isinstance(node, NavigableString):
                t = str(node)
            elif isinstance(node, Tag):
                t = node.get_text()
            else:
                t = ""
            parts.insert(0, t)
            total += len(t)
            node = node.previous_sibling
        text = "".join(parts)
        if len(text) > max_chars:
            text = text[-max_chars:]
        return text

    def _sibling_text_right(self, elem, max_chars: int = 300) -> str:
        """Collect text from following siblings within the same parent."""
        parts = []
        total = 0
        node = elem.next_sibling
        while node is not None and total < max_chars:
            if isinstance(node, NavigableString):
                t = str(node)
            elif isinstance(node, Tag):
                t = node.get_text()
            else:
                t = ""
            parts.append(t)
            total += len(t)
            node = node.next_sibling
        text = "".join(parts)
        if len(text) > max_chars:
            text = text[:max_chars]
        return text

    def _sibling_html_left(self, elem, max_chars: int = 500) -> str:
        """Collect raw HTML/string from previous siblings."""
        parts = []
        total = 0
        node = elem.previous_sibling
        while node is not None and total < max_chars:
            t = str(node)
            parts.insert(0, t)
            total += len(t)
            node = node.previous_sibling
        text = "".join(parts)
        if len(text) > max_chars:
            text = text[-max_chars:]
        return text

    def _sibling_html_right(self, elem, max_chars: int = 500) -> str:
        """Collect raw HTML/string from following siblings."""
        parts = []
        total = 0
        node = elem.next_sibling
        while node is not None and total < max_chars:
            t = str(node)
            parts.append(t)
            total += len(t)
            node = node.next_sibling
        text = "".join(parts)
        if len(text) > max_chars:
            text = text[:max_chars]
        return text

    def _is_inside_outer_parens(self, left: str, right: str) -> bool:
        """True when an unmatched '(' to the left is closed somewhere to the right."""
        last_open = left.rfind("(")
        last_close = left.rfind(")")
        if last_open > last_close:
            return ")" in right
        return False

    def classify_bibr_citation(self, elem) -> str:
        """
        Classify a [data-role="bibr"] element as Direct, Indirect, or Unclassified.

        Indirect: parentheses wrap the <a> outside the tag (parenthetical cite).
        Direct: parentheses appear inside the <a> text (e.g. Author (Year)).
        Unclassified: neither pattern.
        """
        left = self._sibling_text_left(elem)
        right = self._sibling_text_right(elem)
        if self._is_inside_outer_parens(left, right):
            return "Indirect"
        inner = elem.get_text() if hasattr(elem, "get_text") else str(elem)
        if "(" in inner and ")" in inner:
            return "Direct"
        return "Unclassified"

    def _indirect_subcategory(self, right_text: str) -> str:
        """
        Subclassify an Indirect citation by page suffix inside the wrap.
        Returns: 'Indirect + pp.' | 'Indirect + p.' | 'Indirect'
        """
        close = right_text.find(")")
        segment = right_text[:close] if close >= 0 else right_text
        if self._PAGE_PP_RE.search(segment):
            return "Indirect + pp."
        if self._PAGE_P_RE.search(segment):
            return "Indirect + p."
        return "Indirect"

    def _extract_entire_citation(self, elem) -> str:
        """
        Full parenthetical HTML unit from unmatched '(' through matching ')'.
        For Direct/Unclassified (no outer wrap), returns the <a> outer HTML.
        """
        left_text = self._sibling_text_left(elem)
        right_text = self._sibling_text_right(elem)
        outer = str(elem)

        if not self._is_inside_outer_parens(left_text, right_text):
            return outer

        left_html = self._sibling_html_left(elem)
        right_html = self._sibling_html_right(elem)
        open_idx = left_html.rfind("(")
        if open_idx < 0:
            return outer

        prefix = left_html[open_idx:]
        depth = prefix.count("(") - prefix.count(")")
        pos = 0
        while pos < len(right_html) and depth > 0:
            ch = right_html[pos]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            pos += 1
        suffix = right_html[:pos] if depth == 0 else right_html
        return f"{prefix}{outer}{suffix}"

    def _year_kind_from_token(self, token: str) -> str:
        """Return 'Year', 'n.d.', or 'other' for a year-like token."""
        t = (token or "").strip()
        if not t:
            return "other"
        if re.match(r"^n\.?\s*d\.?$", t, re.IGNORECASE) or self._ND_RE.fullmatch(t):
            return "n.d."
        if re.match(r"^(?:18|19|20)\d{2}[a-z]?$", t, re.IGNORECASE):
            return "Year"
        if self._ND_RE.search(t):
            return "n.d."
        if self._YEAR_BARE_RE.search(t):
            return "Year"
        return "other"

    def _split_author_year(self, text: str):
        """
        Split citation display text into (author_part, year_kind, form).
        form: 'direct_parens' | 'comma' | 'bare' | 'none'
        year_kind: 'Year' | 'n.d.' | 'other'
        """
        text = (text or "").strip()
        if not text:
            return "", "other", "none"

        m = self._DIRECT_AUTHOR_YEAR_RE.match(text)
        if m:
            return m.group(1).strip(), self._year_kind_from_token(m.group(2)), "direct_parens"

        m = self._COMMA_AUTHOR_YEAR_RE.match(text)
        if m:
            author = m.group(1).strip()
            year_raw = m.group(2).strip()
            # Drop trailing page-like noise if somehow present in link text
            year_raw = re.split(r"\s*;\s*", year_raw)[0].strip()
            return author, self._year_kind_from_token(year_raw), "comma"

        m = self._BARE_AUTHOR_YEAR_RE.match(text)
        if m:
            return m.group(1).strip(), self._year_kind_from_token(m.group(2)), "bare"

        return text, "other", "none"

    def _detect_author_structure(self, author_part: str, left_text: str = "") -> str:
        """
        Detect author shape:
          Possessive Author | Author et al. | Dual Author (&) |
          Dual Author (and) | Single Author (multi-word) | Single Author
        """
        author = (author_part or "").strip()
        left_tail = (left_text or "")[-40:]

        if self._POSSESSIVE_RE.search(author) or self._POSSESSIVE_RE.search(left_tail):
            return "Possessive Author"
        if self._ET_AL_RE.search(author):
            return "Author et al."
        if "&" in author:
            return "Dual Author (&)"
        if self._DUAL_AND_RE.search(author):
            return "Dual Author (and)"

        tokens = [t for t in re.split(r"\s+", author) if t and t not in {",", ";"}]
        if len(tokens) >= 2:
            return "Single Author (multi-word)"
        return "Single Author"

    def citation_pattern_key(self, classification: str, subcategory: str,
                             text: str, right_text: str = "",
                             left_text: str = "") -> str:
        """
        Normalize a citation into a context-based pattern template for dedupe.

        Examples:
          Single Author (Year)
          Single Author (multi-word), Year
          Dual Author (&), Year
          Dual Author (and) (Year)
          Author et al., Year
          Possessive Author (Year)
          Dual Author (&), n.d.
          Single Author, Year + p.
        """
        author, year_kind, form = self._split_author_year(text or "")
        structure = self._detect_author_structure(author, left_text)

        is_direct_form = (
            classification == "Direct"
            or (classification != "Indirect" and form == "direct_parens")
        )

        if year_kind == "n.d.":
            year_label = "(n.d.)" if is_direct_form and classification == "Direct" else "n.d."
        elif year_kind == "Year":
            year_label = "(Year)" if classification == "Direct" else "Year"
        else:
            year_label = None

        if classification == "Unclassified" and form == "bare":
            if year_kind == "Year":
                key = f"{structure} Year"
            elif year_kind == "n.d.":
                key = f"{structure} n.d."
            else:
                key = "Bare Link Text"
        elif classification == "Direct":
            if year_label is None:
                key = "Bare Link Text"
            elif year_label.startswith("("):
                key = f"{structure} {year_label}"
            else:
                key = f"{structure} ({year_label})"
        else:
            # Indirect or Unclassified comma / other
            if year_label is None:
                key = "Bare Link Text"
            else:
                if year_label.startswith("("):
                    year_label = year_label.strip("()")
                key = f"{structure}, {year_label}"

        if subcategory == "Indirect + p.":
            key = f"{key} + p."
        elif subcategory == "Indirect + pp.":
            key = f"{key} + pp."

        return key

    def _is_number_range(self, text: str) -> bool:
        """True when display text looks like a number range or multi-number list."""
        t = (text or "").strip()
        if not t:
            return False
        if self._NUMBER_RANGE_RE.search(t):
            return True
        return len(re.findall(r"\d+", t)) >= 2

    def _with_range_suffix(self, base_key: str, text: str) -> str:
        """Append _range when numbered display is a range/multi."""
        key = (base_key or "number").strip() or "number"
        if self._is_number_range(text) and not key.endswith("_range"):
            return f"{key}_range"
        return key

    def _elem_inside_tag(self, elem, tag_name: str) -> bool:
        parent = getattr(elem, "parent", None)
        while parent is not None:
            if getattr(parent, "name", None) == tag_name:
                return True
            parent = getattr(parent, "parent", None)
        return False

    def _has_bracket_neighbors(self, elem) -> bool:
        left = self._sibling_text_left(elem, 40).rstrip()
        right = self._sibling_text_right(elem, 40).lstrip()
        return left.endswith("[") and right.startswith("]")

    def _fn_endnote_pattern_key(self, elem, text: str) -> str:
        """Structural pattern for fn / endnote cites."""
        in_sup = self._elem_inside_tag(elem, "sup")
        has_brackets = self._has_bracket_neighbors(elem)
        # xref/a wrapping a lone <sup>N</sup>
        contains_sup_only = False
        if not in_sup and hasattr(elem, "find_all"):
            children = [c for c in elem.children if not (
                isinstance(c, NavigableString) and not str(c).strip()
            )]
            if (
                len(children) == 1
                and isinstance(children[0], Tag)
                and children[0].name == "sup"
            ):
                contains_sup_only = True

        if in_sup and has_brackets:
            base = "sup_bracket_number"
        elif in_sup:
            base = "sup_number"
        elif has_brackets:
            base = "bracket_number"
        elif contains_sup_only:
            base = "sup_number"
        else:
            base = "number"
        return self._with_range_suffix(base, text)

    def _equation_pattern_key(self, left: str, right: str, text: str) -> str:
        """Phrase patterns for equation cites."""
        ctx = f"{(left or '')[-80:]}{text or ''}{(right or '')[:80]}"
        ctx_norm = re.sub(r"\s+", " ", ctx)

        if re.search(r"\(\s*Equations?\b[^)]*\band\b[^)]*\)", ctx_norm, re.IGNORECASE):
            return "paren_equations_and"

        m = re.search(r"\(\s*Equations?\s+([^)]+)\)", ctx_norm, re.IGNORECASE)
        if m:
            return self._with_range_suffix("paren_equation", m.group(1))

        m = re.search(r"\bEquations?\s*\(\s*([^)]+)\)", ctx_norm, re.IGNORECASE)
        if m:
            return self._with_range_suffix("equation_paren_number", m.group(1))

        m = re.search(r"\bEq\.?\s*\(\s*([^)]+)\)", ctx_norm, re.IGNORECASE)
        if m:
            return self._with_range_suffix("eq_paren_number", m.group(1))

        return self._with_range_suffix("equation_number", text or "")

    def _typed_cite_pattern_key(self, cite_type: str, left: str, right: str, text: str) -> str:
        """Type-aware display patterns for fig/table/chapter/sec/etc."""
        slug = re.sub(r"[^a-z0-9]+", "_", (cite_type or "cite").lower()).strip("_") or "cite"
        if self._is_inside_outer_parens(left or "", right or ""):
            base = f"paren_{slug}"
        else:
            base = f"{slug}_number"
        return self._with_range_suffix(base, text or "")

    def _pattern_key_for_cite(
        self,
        cite_type: str,
        elem,
        classification: str,
        subcategory: str,
        text: str,
        left: str,
        right: str,
    ) -> str:
        """Route pattern key by cite type; bibr keeps author-year names."""
        ct = (cite_type or "").strip().lower()
        if ct == "bibr":
            return self.citation_pattern_key(
                classification, subcategory, text, right, left
            )
        if ct in ("fn", "endnote"):
            return self._fn_endnote_pattern_key(elem, text)
        if ct == "equation":
            return self._equation_pattern_key(left, right, text)
        return self._typed_cite_pattern_key(ct, left, right, text)

    def _build_bibr_snippet(self, elem, left_max: int = 80, right_max: int = 80) -> str:
        """Raw HTML context: surrounding text + element outer HTML."""
        left = self._sibling_text_left(elem, left_max)
        right = self._sibling_text_right(elem, right_max)
        return f"{left}{str(elem)}{right}"

    def extract_bibr_citations(self, file_path: Path, cite_type: str = "bibr") -> list:
        """
        Extract and classify cite elements matching cite_type.

        cite_type: specific value (bibr, fig, endnote, …) or 'all' / 'All'.
        Match uses object-type, then ref-type, then data-role.

        Returns list of dicts including cite_type, cite_type_source, classification, etc.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} does not exist.")

        type_filter = self._normalize_cite_type_filter(cite_type)

        try:
            with open(file_path, "rb") as f:
                content_bytes = f.read()
        except Exception as e:
            raise Exception(f"Failed to read file {file_path.name}: {str(e)}")

        try:
            content_str = content_bytes.decode("utf-8", errors="ignore")
        except Exception:
            content_str = content_bytes.decode("latin-1", errors="ignore")

        is_xml = file_path.suffix.lower() == ".xml"
        parser_backend = "lxml-xml" if is_xml else "lxml"
        soup = BeautifulSoup(content_str, parser_backend)

        results = []
        for index, elem in enumerate(self._iter_cite_candidates(soup)):
            resolved = self.resolve_cite_type(elem)
            if resolved is None:
                continue
            resolved_type, resolved_source = resolved
            if type_filter != "all" and resolved_type != type_filter:
                continue

            line_num = getattr(elem, "sourceline", None) or (index + 1)
            tag_name = elem.name or "element"
            attributes = {}
            for k, v in elem.attrs.items():
                if isinstance(v, list):
                    attributes[k] = " ".join(v)
                else:
                    attributes[k] = str(v)

            text_content = elem.get_text().strip()
            outer_html = str(elem)
            left = self._sibling_text_left(elem)
            right = self._sibling_text_right(elem)

            if resolved_type == "bibr":
                classification = self.classify_bibr_citation(elem)
                if classification == "Indirect":
                    subcategory = self._indirect_subcategory(right)
                else:
                    subcategory = classification
            else:
                classification = resolved_type
                subcategory = resolved_type

            snippet = self._build_bibr_snippet(elem)
            entire_citation = self._extract_entire_citation(elem)
            pattern_key = self._pattern_key_for_cite(
                resolved_type,
                elem,
                classification,
                subcategory,
                text_content,
                left,
                right,
            )
            if resolved_type != "bibr":
                classification = pattern_key
                subcategory = pattern_key

            results.append({
                "line": line_num,
                "tag": tag_name,
                "attributes": attributes,
                "text": text_content,
                "html": outer_html,
                "classification": classification,
                "subcategory": subcategory,
                "snippet": snippet,
                "entire_citation": entire_citation,
                "pattern_key": pattern_key,
                "cite_type": resolved_type,
                "cite_type_source": resolved_source,
                "left_text": left,
                "right_text": right,
            })
        return results

    def scan_bibr_citations(self, path: Path, recursive: bool = False,
                            extensions: list = None, filename_filter: str = None,
                            dtd_filter: str = None, client_filter: str = None,
                            month_filter: str = "All Time", custom_month: str = "",
                            progress_callback=None, cite_type: str = "bibr"):
        """
        Scan a file or directory for citations matching cite_type and classify each.
        Returns (scan_results, total_matches, total_files) in the same shape
        as scan_directory.
        """
        path = Path(path)
        if path.is_file():
            try:
                matches = self.extract_bibr_citations(path, cite_type=cite_type)
                scan_results = {
                    str(path.absolute()): {"ok": True, "matches": matches}
                }
                return scan_results, len(matches), 1
            except Exception as e:
                scan_results = {
                    str(path.absolute()): {
                        "ok": False,
                        "error": str(e),
                        "matches": [],
                    }
                }
                return scan_results, 0, 1

        if not path.is_dir():
            raise NotADirectoryError(f"'{path}' is not a valid file or directory.")

        if not extensions:
            extensions = [".xml", ".html", ".htm", ".xhtml"]

        glob_pattern = "**/*" if recursive else "*"
        all_files = []
        normalized_filter = filename_filter.strip() if filename_filter else ""
        if normalized_filter and normalized_filter.lower() != "none" and not any(
            char in normalized_filter for char in "*?[]"
        ):
            normalized_filter = f"*{normalized_filter}"

        for file in path.glob(glob_pattern):
            if not file.is_file():
                continue
            if normalized_filter and normalized_filter.lower() != "none" and not self._matches_filename_filter(
                file.name, normalized_filter
            ):
                continue
            if file.suffix.lower() in extensions:
                if not self._matches_config_filters(file, dtd_filter, client_filter):
                    continue
                if not self._matches_month_filter(file, month_filter, custom_month):
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
                matches = self.extract_bibr_citations(file_path, cite_type=cite_type)
                if matches:
                    scan_results[str(file_path.absolute())] = {
                        "ok": True,
                        "matches": matches,
                    }
                    total_matches += len(matches)
            except Exception as e:
                scan_results[str(file_path.absolute())] = {
                    "ok": False,
                    "error": str(e),
                    "matches": [],
                }

        return scan_results, total_matches, total_files


    def extract_mixed_citation_direct_hits(self, file_path: Path) -> list:
        """Extract direct-child comment / alpha-text hits under mixed-citation."""
        from core.mixed_citation_direct_hits import extract_direct_hits_from_file

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} does not exist.")
        return extract_direct_hits_from_file(file_path)

    def scan_mixed_citation_direct_hits(
        self,
        path: Path,
        recursive: bool = False,
        extensions: list = None,
        filename_filter: str = None,
        dtd_filter: str = None,
        client_filter: str = None,
        progress_callback=None,
        cancel_check=None,
    ) -> dict:
        """Scan a file or directory for mixed-citation direct comment/alpha hits.

        Returns ``{file_path_str: {ok, hits, client, error?}, ...}``.
        Includes files with zero hits so callers can roll up files searched.
        """
        path = Path(path)

        def _client_for(file_path: Path) -> str:
            try:
                return self.get_file_metadata(file_path).get("client", "") or ""
            except Exception:
                return ""

        def _result_for(file_path: Path) -> dict:
            client = _client_for(file_path)
            try:
                hits = self.extract_mixed_citation_direct_hits(file_path)
                return {"ok": True, "hits": hits, "client": client}
            except Exception as e:
                return {"ok": False, "error": str(e), "hits": [], "client": client}

        if path.is_file():
            return {str(path.absolute()): _result_for(path)}

        if not path.is_dir():
            raise NotADirectoryError(f"'{path}' is not a valid file or directory.")

        if not extensions:
            extensions = [".xml", ".html", ".htm", ".xhtml"]

        glob_pattern = "**/*" if recursive else "*"
        all_files = []
        normalized_filter = filename_filter.strip() if filename_filter else ""
        if normalized_filter and normalized_filter.lower() != "none" and not any(
            char in normalized_filter for char in "*?[]"
        ):
            normalized_filter = f"*{normalized_filter}"

        for file in path.glob(glob_pattern):
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

        for i, file_path in enumerate(all_files):
            if cancel_check is not None and cancel_check():
                break
            if progress_callback:
                progress_callback(i + 1, total_files, file_path.name)
            scan_results[str(file_path.absolute())] = _result_for(file_path)

        return scan_results

    def filter_scan_results_by_cite_type(self, scan_results: dict, cite_type: str):
        """
        Keep only matches for cite_type.
        Returns (filtered_scan_results, total_matches, total_files_with_matches).
        """
        type_filter = self._normalize_cite_type_filter(cite_type)
        filtered = {}
        total_matches = 0
        total_files = 0
        for file_path_str, data in (scan_results or {}).items():
            if not data.get("ok", True):
                filtered[file_path_str] = data
                continue
            matches = list(data.get("matches") or [])
            if type_filter != "all":
                matches = [
                    m for m in matches
                    if (m.get("cite_type") or "").strip().lower() == type_filter
                ]
            if matches:
                total_files += 1
            total_matches += len(matches)
            filtered[file_path_str] = {
                **data,
                "matches": matches,
            }
        return filtered, total_matches, total_files

    def discover_cite_types(self, scan_results: dict) -> list:
        """Sorted cite types present in scan_results (presets first)."""
        preset_types = [
            p.lower() for p in self.CITE_TYPE_PRESETS if str(p).lower() != "all"
        ]
        order_map = {t: i for i, t in enumerate(preset_types)}
        found = set()
        for data in (scan_results or {}).values():
            if not data.get("ok", True):
                continue
            for match in data.get("matches") or []:
                ct = (match.get("cite_type") or "").strip().lower()
                if ct:
                    found.add(ct)
        return sorted(found, key=lambda t: (order_map.get(t, 99), t))

    def dedupe_matches_per_file_pattern(self, matches: list) -> list:
        """
        Keep one match per pattern_key (first sample); attach pattern_count.
        """
        seen = {}
        order = []
        for match in matches or []:
            key = match.get("pattern_key") or "Bare Link Text"
            if key not in seen:
                kept = dict(match)
                kept["pattern_count"] = 1
                seen[key] = kept
                order.append(key)
            else:
                seen[key]["pattern_count"] = seen[key].get("pattern_count", 1) + 1
        return [seen[k] for k in order]

    def dedupe_scan_results_per_file_pattern(self, scan_results: dict) -> dict:
        """Dedupe each file's matches to one row per pattern_key (with counts)."""
        out = {}
        for file_path_str, data in (scan_results or {}).items():
            if not data.get("ok", True):
                out[file_path_str] = data
                continue
            deduped = self.dedupe_matches_per_file_pattern(data.get("matches") or [])
            out[file_path_str] = {**data, "matches": deduped}
        return out

    def generate_citation_type_report(self, target_path: str, scan_results: dict,
                                      total_matches: int, total_files: int,
                                      cite_type: str = "bibr") -> str:
        """
        Generate a Direct/Indirect citation classification HTML report
        with Indirect page-reference subcategories and cite-type grouping.
        Returns a self-contained HTML string suitable for GUI rendering.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target_name = os.path.basename(target_path)
        type_filter = self._normalize_cite_type_filter(cite_type)
        selector_label = self.cite_type_selector_label(cite_type)

        class_order = [
            "Direct",
            "Indirect + p.",
            "Indirect + pp.",
            "Indirect",
            "Unclassified",
        ]
        class_colors = {
            "Direct": "#10b981",
            "Indirect + p.": "#f59e0b",
            "Indirect + pp.": "#fb923c",
            "Indirect": "#fbbf24",
            "Unclassified": "#64748b",
        }
        cite_type_colors = {
            "bibr": "#818cf8",
            "fig": "#38bdf8",
            "table": "#34d399",
            "table-wrap": "#2dd4bf",
            "chapter": "#a78bfa",
            "equation": "#f472b6",
            "endnote": "#fb923c",
            "fn": "#fbbf24",
            "sec": "#94a3b8",
            "boxed-text": "#c084fc",
        }
        preset_types = [
            p.lower() for p in self.CITE_TYPE_PRESETS if str(p).lower() != "all"
        ]
        cite_type_order_map = {t: i for i, t in enumerate(preset_types)}

        # One report row per (file, pattern_key); counts stay on pattern_count
        deduped_scan = self.dedupe_scan_results_per_file_pattern(scan_results)
        all_rows = []
        for file_path_str, data in deduped_scan.items():
            if not data.get("ok", True):
                continue
            for match in data.get("matches", []):
                subcategory = match.get("subcategory") or match.get("classification", "") or (
                    match.get("pattern_key") or "Bare Link Text"
                )
                row_cite = (match.get("cite_type") or "").strip().lower()
                if not row_cite:
                    row_cite = type_filter if type_filter != "all" else "unknown"
                pattern_key = match.get("pattern_key") or "Bare Link Text"
                all_rows.append({
                    "classification": match.get("classification") or pattern_key,
                    "subcategory": subcategory,
                    "pattern_key": pattern_key,
                    "pattern_count": match.get("pattern_count", 1),
                    "cite_type": row_cite,
                    "file_name": os.path.basename(file_path_str),
                    "file_path": file_path_str,
                    "text": (match.get("text") or "").strip(),
                    "line": match.get("line", ""),
                    "html": match.get("html", "") or "",
                    "snippet": match.get("snippet", "") or match.get("html", "") or "",
                    "entire_citation": match.get("entire_citation", "") or "",
                })

        present_types = sorted(
            {r["cite_type"] for r in all_rows},
            key=lambda t: (cite_type_order_map.get(t, 99), t),
        )
        multi_type = len(present_types) > 1

        order_map = {c: i for i, c in enumerate(class_order)}
        if multi_type:
            all_rows.sort(key=lambda r: (
                cite_type_order_map.get(r["cite_type"], 99),
                r["cite_type"],
                order_map.get(r["subcategory"], 99),
                r["file_name"],
            ))
        else:
            all_rows.sort(key=lambda r: (order_map.get(r["subcategory"], 99), r["file_name"]))

        class_counts = {}
        type_counts = {}
        for row in all_rows:
            class_counts[row["subcategory"]] = class_counts.get(row["subcategory"], 0) + 1
            type_counts[row["cite_type"]] = type_counts.get(row["cite_type"], 0) + 1

        summary_badges = ""
        for ct in present_types:
            cnt = type_counts.get(ct, 0)
            if cnt > 0:
                clr = cite_type_colors.get(ct, "#94a3b8")
                summary_badges += (
                    f'<span class="badge" style="background:{clr}">'
                    f"type:{html.escape(ct)}: {cnt}</span> "
                )
        for cls in class_order:
            cnt = class_counts.get(cls, 0)
            if cnt > 0:
                clr = class_colors.get(cls, "#94a3b8")
                summary_badges += (
                    f'<span class="badge" style="background:{clr}">'
                    f"{html.escape(cls)}: {cnt}</span> "
                )

        table_rows = ""
        current_class = None
        current_cite = None
        s_no = 0
        group_counts = {}
        for row in all_rows:
            if multi_type:
                gkey = (row["cite_type"], row["subcategory"])
            else:
                gkey = (row["subcategory"],)
            group_counts[gkey] = group_counts.get(gkey, 0) + 1

        for row in all_rows:
            group_changed = False
            if multi_type:
                if row["cite_type"] != current_cite or row["subcategory"] != current_class:
                    group_changed = True
                    current_cite = row["cite_type"]
                    current_class = row["subcategory"]
            else:
                if row["subcategory"] != current_class:
                    group_changed = True
                    current_class = row["subcategory"]

            if group_changed:
                clr = class_colors.get(current_class, "#94a3b8")
                if multi_type:
                    tclr = cite_type_colors.get(current_cite, "#94a3b8")
                    gkey = (current_cite, current_class)
                    label = (
                        f'<span class="pattern-label" style="background:{tclr};">'
                        f'{html.escape(current_cite)}</span>'
                        f'<span class="pattern-label" style="background:{clr};">'
                        f'{html.escape(current_class)}</span>'
                    )
                    data_attrs = (
                        f'data-cite-type="{html.escape(current_cite)}" '
                        f'data-classification="{html.escape(current_class)}"'
                    )
                else:
                    gkey = (current_class,)
                    label = (
                        f'<span class="pattern-label" style="background:{clr};">'
                        f'{html.escape(current_class)}</span>'
                    )
                    data_attrs = (
                        f'data-cite-type="{html.escape(row["cite_type"])}" '
                        f'data-classification="{html.escape(current_class)}"'
                    )
                table_rows += f"""
            <tr class="pattern-group-header" {data_attrs}>
                <td colspan="6" style="border-left:4px solid {clr};">
                    {label}
                    <span class="pattern-count">{group_counts.get(gkey, 0)} instance(s)</span>
                </td>
            </tr>"""

            s_no += 1
            clr = class_colors.get(row["subcategory"], "#94a3b8")
            tclr = cite_type_colors.get(row["cite_type"], "#94a3b8")
            display_text = html.escape(row["text"]) if row["text"] else '<em class="empty-text">(empty)</em>'
            snippet_src = row["entire_citation"] or row["snippet"]
            snippet_html = html.escape(snippet_src) if snippet_src else ""

            table_rows += f"""
            <tr data-cite-type="{html.escape(row['cite_type'])}" data-classification="{html.escape(row['subcategory'])}">
                <td class="col-sno">{s_no}</td>
                <td class="col-file" title="{html.escape(row['file_path'])}">
                    <strong>{html.escape(row['file_name'])}</strong>
                    <div class="file-line">Line {row['line']}</div>
                </td>
                <td class="col-cite-type">
                    <span class="pattern-tag" style="background:{tclr};">{html.escape(row['cite_type'])}</span>
                </td>
                <td class="col-text">{display_text}</td>
                <td class="col-pattern">
                    <span class="pattern-tag" style="background:{clr};">{html.escape(row['subcategory'])}</span>
                </td>
                <td class="col-outer"><pre class="outer-preview">{snippet_html}</pre></td>
            </tr>"""

        if not table_rows:
            table_rows = f"""
            <tr>
                <td colspan="6" class="no-data">No citations found for {html.escape(selector_label)}.</td>
            </tr>"""

        type_filter_options = "".join(
            f'<option value="{html.escape(t)}">{html.escape(t)} ({type_counts.get(t, 0)})</option>'
            for t in present_types if type_counts.get(t, 0) > 0
        )
        filter_options = "".join(
            f'<option value="{html.escape(c)}">{html.escape(c)} ({class_counts.get(c, 0)})</option>'
            for c in class_order if class_counts.get(c, 0) > 0
        )

        report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Citation Type Report - {html.escape(target_name)}</title>
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

        .container {{ max-width: 1400px; margin: 0 auto; }}

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

        .legend {{
            display: flex; gap: 16px; flex-wrap: wrap;
            margin: 10px 0 0; font-size: 0.85rem; color: var(--text-muted);
        }}
        .legend-item {{ display: flex; align-items: center; gap: 6px; }}
        .legend-swatch {{
            width: 12px; height: 12px; border-radius: 3px; display: inline-block;
        }}

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

        .col-file {{ width: 180px; vertical-align: top; }}

        .file-line {{
            font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;
        }}

        .col-cite-type {{ width: 110px; vertical-align: top; text-align: center; }}

        .col-text {{
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 0.88rem;
            color: #34d399;
            white-space: pre-wrap;
            word-break: break-word;
            vertical-align: top;
            max-width: 240px;
        }}

        .col-pattern {{ width: 140px; vertical-align: top; text-align: center; }}

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

        .empty-text {{ color: var(--text-muted); }}

        .no-data {{
            text-align: center;
            color: var(--text-muted);
            padding: 40px;
            font-style: italic;
        }}

        .col-outer {{ max-width: 480px; }}

        .outer-preview {{
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
            <h1>Citation Type Report</h1>
            <div class="meta">
                Selector: <code>{html.escape(selector_label)}</code> |
                Total Citations: <strong>{total_matches}</strong> in <strong>{total_files}</strong> file(s)
            </div>
            <div class="badge-bar">{summary_badges}</div>
            <div class="legend">
                <span class="legend-item"><span class="legend-swatch" style="background:#10b981"></span> Direct — parentheses inside &lt;a&gt;</span>
                <span class="legend-item"><span class="legend-swatch" style="background:#f59e0b"></span> Indirect + p. — with page</span>
                <span class="legend-item"><span class="legend-swatch" style="background:#fb923c"></span> Indirect + pp. — with page range</span>
                <span class="legend-item"><span class="legend-swatch" style="background:#fbbf24"></span> Indirect — no page suffix</span>
                <span class="legend-item"><span class="legend-swatch" style="background:#64748b"></span> Unclassified — neither pattern</span>
            </div>
            <div class="timestamp">Generated: {timestamp}</div>
        </header>

        <div class="filter-bar">
            <select id="typeFilter" onchange="filterTable()">
                <option value="">All Cite Types</option>
                {type_filter_options}
            </select>
            <select id="classFilter" onchange="filterTable()">
                <option value="">All Classifications</option>
                {filter_options}
            </select>
            <input id="textSearch" type="text" placeholder="Search text or filename..." oninput="filterTable()">
        </div>

        <table id="reportTable">
            <thead>
                <tr>
                    <th style="text-align:center">S.NO</th>
                    <th>Filename</th>
                    <th style="text-align:center">Cite Type</th>
                    <th>Text</th>
                    <th style="text-align:center">Classification</th>
                    <th>Snippet</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>

    <script>
        function filterTable() {{
            const typeVal = document.getElementById('typeFilter').value.toLowerCase();
            const classVal = document.getElementById('classFilter').value.toLowerCase();
            const searchVal  = document.getElementById('textSearch').value.toLowerCase().trim();
            const rows = document.querySelectorAll('#reportTable tbody tr');

            let currentGroupVisible = true;

            rows.forEach(row => {{
                if (row.classList.contains('pattern-group-header')) {{
                    const rowType = (row.getAttribute('data-cite-type') || '').toLowerCase();
                    const rowClass = (row.getAttribute('data-classification') || '').toLowerCase();
                    currentGroupVisible = true;
                    if (typeVal && rowType !== typeVal) currentGroupVisible = false;
                    if (classVal && rowClass !== classVal) currentGroupVisible = false;
                    row.style.display = currentGroupVisible ? '' : 'none';
                    return;
                }}

                if (!currentGroupVisible) {{
                    row.style.display = 'none';
                    return;
                }}

                const rowType = (row.getAttribute('data-cite-type') || '').toLowerCase();
                const rowClass = (row.getAttribute('data-classification') || '').toLowerCase();
                if (typeVal && rowType !== typeVal) {{
                    row.style.display = 'none';
                    return;
                }}
                if (classVal && rowClass !== classVal) {{
                    row.style.display = 'none';
                    return;
                }}

                const textCell = row.querySelector('.col-text');
                const textContent = textCell ? textCell.textContent.toLowerCase() : '';
                const fileCell = row.querySelector('.col-file');
                const fileName = fileCell ? fileCell.textContent.toLowerCase() : '';
                const snippetCell = row.querySelector('.col-outer');
                const snippetText = snippetCell ? snippetCell.textContent.toLowerCase() : '';

                if (searchVal && !textContent.includes(searchVal) && !fileName.includes(searchVal) && !snippetText.includes(searchVal)) {{
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
        return report_html

    def generate_entire_citation_report(self, target_path: str, scan_results: dict,
                                        total_matches: int, total_files: int,
                                        cite_type: str = "bibr") -> str:
        """
        Generate a deduplicated Entire Citation report.
        One row per (cite_type, pattern_key) with count and an example full citation HTML.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target_name = os.path.basename(target_path)
        type_filter = self._normalize_cite_type_filter(cite_type)
        selector_label = self.cite_type_selector_label(cite_type)

        pattern_order = [
            # Direct forms
            "Possessive Author (Year)",
            "Possessive Author (n.d.)",
            "Dual Author (and) (Year)",
            "Dual Author (and) (n.d.)",
            "Dual Author (&) (Year)",
            "Author et al. (Year)",
            "Single Author (multi-word) (Year)",
            "Single Author (Year)",
            # Indirect / comma forms — et al.
            "Author et al., Year",
            "Author et al., Year + p.",
            "Author et al., Year + pp.",
            "Author et al., n.d.",
            # Dual &
            "Dual Author (&), Year",
            "Dual Author (&), Year + p.",
            "Dual Author (&), Year + pp.",
            "Dual Author (&), n.d.",
            "Dual Author (&), n.d. + p.",
            # Dual and (indirect)
            "Dual Author (and), Year",
            "Dual Author (and), Year + p.",
            "Dual Author (and), Year + pp.",
            "Dual Author (and), n.d.",
            # Single multi-word
            "Single Author (multi-word), Year",
            "Single Author (multi-word), Year + p.",
            "Single Author (multi-word), Year + pp.",
            "Single Author (multi-word), n.d.",
            "Single Author (multi-word) Year",
            # Single one-word
            "Single Author, Year",
            "Single Author, Year + p.",
            "Single Author, Year + pp.",
            "Single Author, n.d.",
            "Single Author Year",
            "Single Author n.d.",
            # Possessive indirect
            "Possessive Author, Year",
            "Possessive Author, n.d.",
            "Bare Link Text",
            "bracket_number",
            "bracket_number_range",
            "sup_bracket_number",
            "sup_bracket_number_range",
            "sup_number",
            "sup_number_range",
            "paren_equation",
            "paren_equation_range",
            "paren_equations_and",
            "equation_paren_number",
            "equation_paren_number_range",
            "eq_paren_number",
            "eq_paren_number_range",
            "equation_number",
            "equation_number_range",
        ]
        pattern_colors = {
            "Possessive Author (Year)": "#a78bfa",
            "Possessive Author (n.d.)": "#c4b5fd",
            "Dual Author (and) (Year)": "#34d399",
            "Dual Author (and) (n.d.)": "#6ee7b7",
            "Dual Author (&) (Year)": "#2dd4bf",
            "Author et al. (Year)": "#38bdf8",
            "Single Author (multi-word) (Year)": "#4ade80",
            "Single Author (Year)": "#10b981",
            "Author et al., Year": "#0ea5e9",
            "Author et al., Year + p.": "#f59e0b",
            "Author et al., Year + pp.": "#fb923c",
            "Author et al., n.d.": "#7dd3fc",
            "Dual Author (&), Year": "#14b8a6",
            "Dual Author (&), Year + p.": "#f59e0b",
            "Dual Author (&), Year + pp.": "#fb923c",
            "Dual Author (&), n.d.": "#5eead4",
            "Dual Author (&), n.d. + p.": "#fbbf24",
            "Dual Author (and), Year": "#22c55e",
            "Dual Author (and), Year + p.": "#f59e0b",
            "Dual Author (and), Year + pp.": "#fb923c",
            "Dual Author (and), n.d.": "#86efac",
            "Single Author (multi-word), Year": "#84cc16",
            "Single Author (multi-word), Year + p.": "#f59e0b",
            "Single Author (multi-word), Year + pp.": "#fb923c",
            "Single Author (multi-word), n.d.": "#bef264",
            "Single Author (multi-word) Year": "#a3e635",
            "Single Author, Year": "#fbbf24",
            "Single Author, Year + p.": "#f59e0b",
            "Single Author, Year + pp.": "#fb923c",
            "Single Author, n.d.": "#fde68a",
            "Single Author Year": "#94a3b8",
            "Single Author n.d.": "#cbd5e1",
            "Possessive Author, Year": "#c084fc",
            "Possessive Author, n.d.": "#e9d5ff",
            "Bare Link Text": "#94a3b8",
            "bracket_number": "#fbbf24",
            "bracket_number_range": "#f59e0b",
            "sup_bracket_number": "#fb923c",
            "sup_bracket_number_range": "#ea580c",
            "sup_number": "#fde68a",
            "sup_number_range": "#fcd34d",
            "paren_equation": "#f472b6",
            "paren_equation_range": "#ec4899",
            "paren_equations_and": "#db2777",
            "equation_paren_number": "#e879f9",
            "equation_paren_number_range": "#d946ef",
            "eq_paren_number": "#c084fc",
            "eq_paren_number_range": "#a855f7",
            "equation_number": "#f9a8d4",
            "equation_number_range": "#f472b6",
        }
        subcategory_colors = {
            "Direct": "#10b981",
            "Indirect + p.": "#f59e0b",
            "Indirect + pp.": "#fb923c",
            "Indirect": "#fbbf24",
            "Unclassified": "#64748b",
            "Bare Link Text": "#94a3b8",
        }
        cite_type_colors = {
            "bibr": "#818cf8",
            "fig": "#38bdf8",
            "table": "#34d399",
            "table-wrap": "#2dd4bf",
            "chapter": "#a78bfa",
            "equation": "#f472b6",
            "endnote": "#fb923c",
            "fn": "#fbbf24",
            "sec": "#94a3b8",
            "boxed-text": "#c084fc",
        }
        preset_types = [
            p.lower() for p in self.CITE_TYPE_PRESETS if str(p).lower() != "all"
        ]
        cite_type_order_map = {t: i for i, t in enumerate(preset_types)}

        # One row per (file, cite_type, pattern_key); count = instances in that file
        patterns = {}
        instance_total = 0
        type_counts = {}
        for file_path_str, data in scan_results.items():
            if not data.get("ok", True):
                continue
            for match in data.get("matches", []):
                instance_total += 1
                key = match.get("pattern_key") or "Bare Link Text"
                subcategory = match.get("subcategory") or match.get("classification") or key
                row_cite = (match.get("cite_type") or "").strip().lower()
                if not row_cite:
                    row_cite = type_filter if type_filter != "all" else "unknown"
                type_counts[row_cite] = type_counts.get(row_cite, 0) + 1
                example = match.get("entire_citation") or match.get("html") or match.get("snippet") or ""
                agg_key = (file_path_str, row_cite, key)
                if agg_key not in patterns:
                    patterns[agg_key] = {
                        "cite_type": row_cite,
                        "pattern_key": key,
                        "subcategory": subcategory,
                        "classification": match.get("classification") or key,
                        "count": 0,
                        "example": example,
                        "example_text": (match.get("text") or "").strip(),
                        "file_name": os.path.basename(file_path_str),
                        "file_path": file_path_str,
                    }
                patterns[agg_key]["count"] += 1
                # Prefer an Indirect entire-wrap example when available
                if example.startswith("(") and not patterns[agg_key]["example"].startswith("("):
                    patterns[agg_key]["example"] = example
                    patterns[agg_key]["example_text"] = (match.get("text") or "").strip()

        order_map = {p: i for i, p in enumerate(pattern_order)}
        rows = sorted(
            patterns.values(),
            key=lambda r: (
                cite_type_order_map.get(r["cite_type"], 99),
                r["cite_type"],
                r.get("file_name", ""),
                order_map.get(r["pattern_key"], 99),
                -r["count"],
            )
        )
        unique_patterns = len(rows)
        present_types = sorted(
            type_counts.keys(),
            key=lambda t: (cite_type_order_map.get(t, 99), t),
        )

        summary_badges = (
            f'<span class="badge" style="background:#818cf8">Unique Patterns: {unique_patterns}</span> '
            f'<span class="badge" style="background:#38bdf8">Total Instances: {instance_total}</span> '
        )
        for ct in present_types:
            clr = cite_type_colors.get(ct, "#94a3b8")
            summary_badges += (
                f'<span class="badge" style="background:{clr}">'
                f"type:{html.escape(ct)}: {type_counts[ct]}</span> "
            )
        # Pattern badges (summed across cite types for display)
        pattern_totals = {}
        for row in rows:
            pattern_totals[row["pattern_key"]] = (
                pattern_totals.get(row["pattern_key"], 0) + row["count"]
            )
        badge_keys = [p for p in pattern_order if p in pattern_totals]
        badge_keys.extend(sorted(k for k in pattern_totals if k not in order_map))
        for pkey in badge_keys:
            clr = pattern_colors.get(pkey, "#94a3b8")
            summary_badges += (
                f'<span class="badge" style="background:{clr}">'
                f"{html.escape(pkey)}: {pattern_totals[pkey]}</span> "
            )

        table_rows = ""
        s_no = 0
        for row in rows:
            s_no += 1
            pclr = pattern_colors.get(row["pattern_key"], "#94a3b8")
            sclr = subcategory_colors.get(row["subcategory"], "#94a3b8")
            tclr = cite_type_colors.get(row["cite_type"], "#94a3b8")
            example_html = html.escape(row["example"]) if row["example"] else ""
            file_name = html.escape(row.get("file_name") or "")
            table_rows += f"""
            <tr data-pattern="{html.escape(row['pattern_key'])}" data-cite-type="{html.escape(row['cite_type'])}" data-classification="{html.escape(row['subcategory'])}">
                <td class="col-sno">{s_no}</td>
                <td class="col-file" title="{html.escape(row.get('file_path') or '')}">{file_name}</td>
                <td class="col-cite-type">
                    <span class="pattern-tag" style="background:{tclr};">{html.escape(row['cite_type'])}</span>
                </td>
                <td class="col-pattern-key">
                    <span class="pattern-tag" style="background:{pclr};">{html.escape(row['pattern_key'])}</span>
                </td>
                <td class="col-pattern">
                    <span class="pattern-tag" style="background:{sclr};">{html.escape(row['subcategory'])}</span>
                </td>
                <td class="col-count"><strong>{row['count']}</strong></td>
                <td class="col-outer"><pre class="outer-preview">{example_html}</pre></td>
            </tr>"""

        if not table_rows:
            table_rows = f"""
            <tr>
                <td colspan="6" class="no-data">No citations found for {html.escape(selector_label)}.</td>
            </tr>"""

        type_filter_options = "".join(
            f'<option value="{html.escape(t)}">{html.escape(t)} ({type_counts[t]})</option>'
            for t in present_types
        )
        filter_keys = [p for p in pattern_order if p in pattern_totals]
        filter_keys.extend(sorted(k for k in pattern_totals if k not in order_map))
        filter_options = "".join(
            f'<option value="{html.escape(p)}">{html.escape(p)} ({pattern_totals[p]})</option>'
            for p in filter_keys
        )

        report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Entire Citation Report - {html.escape(target_name)}</title>
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

        .container {{ max-width: 1400px; margin: 0 auto; }}

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

        .legend {{
            display: flex; gap: 16px; flex-wrap: wrap;
            margin: 10px 0 0; font-size: 0.85rem; color: var(--text-muted);
        }}
        .legend-item {{ display: flex; align-items: center; gap: 6px; }}
        .legend-swatch {{
            width: 12px; height: 12px; border-radius: 3px; display: inline-block;
        }}

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

        .col-cite-type {{ width: 110px; vertical-align: top; text-align: center; }}
        .col-pattern-key {{ width: 180px; vertical-align: top; }}
        .col-pattern {{ width: 140px; vertical-align: top; text-align: center; }}
        .col-count {{ width: 80px; text-align: center; vertical-align: top; color: #38bdf8; }}

        .pattern-tag {{
            display: inline-block;
            padding: 3px 12px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 600;
            color: #0f172a;
        }}

        .no-data {{
            text-align: center;
            color: var(--text-muted);
            padding: 40px;
            font-style: italic;
        }}

        .col-outer {{ max-width: 580px; }}

        .outer-preview {{
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
            <h1>Entire Citation Report</h1>
            <div class="meta">
                Selector: <code>{html.escape(selector_label)}</code> |
                Deduplicated patterns from <strong>{total_matches}</strong> citation(s)
                in <strong>{total_files}</strong> file(s)
            </div>
            <div class="badge-bar">{summary_badges}</div>
            <div class="legend">
                <span class="legend-item">Repeated shapes are collapsed per cite type + pattern, with a count.</span>
                <span class="legend-item">Example column shows the full parenthetical citation HTML when available.</span>
            </div>
            <div class="timestamp">Generated: {timestamp}</div>
        </header>

        <div class="filter-bar">
            <select id="typeFilter" onchange="filterTable()">
                <option value="">All Cite Types</option>
                {type_filter_options}
            </select>
            <select id="patternFilter" onchange="filterTable()">
                <option value="">All Patterns</option>
                {filter_options}
            </select>
            <input id="textSearch" type="text" placeholder="Search pattern or example HTML..." oninput="filterTable()">
        </div>

        <table id="reportTable">
            <thead>
                <tr>
                    <th style="text-align:center">S.NO</th>
                    <th>File</th>
                    <th style="text-align:center">Cite Type</th>
                    <th>Pattern</th>
                    <th style="text-align:center">Subcategory</th>
                    <th style="text-align:center">Count</th>
                    <th>Example Entire Citation</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>

    <script>
        function filterTable() {{
            const typeVal = document.getElementById('typeFilter').value.toLowerCase();
            const patternVal = document.getElementById('patternFilter').value.toLowerCase();
            const searchVal  = document.getElementById('textSearch').value.toLowerCase().trim();
            const rows = document.querySelectorAll('#reportTable tbody tr');

            rows.forEach(row => {{
                const rowPattern = (row.getAttribute('data-pattern') || '').toLowerCase();
                const rowType = (row.getAttribute('data-cite-type') || '').toLowerCase();
                const exampleCell = row.querySelector('.col-outer');
                const exampleText = exampleCell ? exampleCell.textContent.toLowerCase() : '';
                const patternCell = row.querySelector('.col-pattern-key');
                const patternText = patternCell ? patternCell.textContent.toLowerCase() : '';

                let visible = true;
                if (typeVal && rowType !== typeVal) {{
                    visible = false;
                }}
                if (visible && patternVal && rowPattern !== patternVal) {{
                    visible = false;
                }}
                if (visible && searchVal && !exampleText.includes(searchVal) && !patternText.includes(searchVal) && !rowPattern.includes(searchVal) && !rowType.includes(searchVal)) {{
                    visible = false;
                }}
                row.style.display = visible ? '' : 'none';
            }});
        }}
    </script>
</body>
</html>
"""
        return report_html

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

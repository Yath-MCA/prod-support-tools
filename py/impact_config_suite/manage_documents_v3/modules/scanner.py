"""Document scanning module."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from .. import config
from .database import DocumentDatabase
from .utils import Logger, PathHelper


class DocumentScanner:
    """Scans project folders and builds documents.json database."""
    
    def __init__(
        self,
        database: DocumentDatabase,
        log_callback: Callable[[str], None] | None = None,
    ):
        self.db = database
        self.logger = Logger(
            database.project_path / config.LOG_FILE,
            console_callback=log_callback,
        )
    
    def scan(
        self,
        original_html_dir: str = None,
        original_xml_dir: str = None,
        updated_html_dir: str = None,
        batch_size: int = None,
        skip_existing: bool = True,
    ) -> tuple[int, int]:
        """Scan source folders with batch limit.
        
        Args:
            original_html_dir: Source folder for original HTML (default from config)
            original_xml_dir: Source folder for original XML (default from config)
            updated_html_dir: Source folder for updated HTML (default from config)
            batch_size: Max new files to process (default from config.SCAN_BATCH_SIZE)
            skip_existing: Skip files already in database
            
        Returns:
            Tuple of (processed_count, remaining_count)
        """
        # Use config defaults if not provided
        if original_html_dir is None:
            original_html_dir = config.SOURCE_FOLDERS["original_html"]
        if original_xml_dir is None:
            original_xml_dir = config.SOURCE_FOLDERS["original_xml"]
        if updated_html_dir is None:
            updated_html_dir = config.SOURCE_FOLDERS["updated_html"]
        if batch_size is None:
            batch_size = config.SCAN_BATCH_SIZE
        
        project_path = self.db.project_path
        self.logger.info(f"Scanning project: {project_path}")
        
        # Get source folder paths
        folders = PathHelper.get_source_folders(
            project_path,
            {
                "original_html": original_html_dir,
                "original_xml": original_xml_dir,
                "updated_html": updated_html_dir,
            }
        )
        
        # Get existing docids for skip logic
        existing_docids = set(self.db.get_all().keys()) if skip_existing else set()
        
        processed = 0
        remaining = 0
        found_docids = set()
        
        # Scan original HTML folder (primary source)
        html_folder = folders["original_html"]
        if html_folder.exists():
            self.logger.info(f"Scanning {html_folder}")
            for file_path in html_folder.iterdir():
                if not (file_path.is_file() and file_path.suffix.lower() == ".html"):
                    continue
                
                docid = PathHelper.extract_docid(file_path.name)
                if not docid:
                    continue
                
                # Skip if already in database
                if skip_existing and docid in existing_docids:
                    continue
                
                # Check if we already processed this docid (duplicate check)
                if docid in found_docids:
                    continue
                
                # Batch limit check
                if processed >= batch_size:
                    remaining += 1
                    continue
                
                # Process this document
                found_docids.add(docid)
                self._process_document(docid, folders)
                processed += 1
        else:
            self.logger.warning(f"Folder not found: {html_folder}")
        
        # Save database
        success, error = self.db.save()
        if not success:
            self.logger.error(f"Failed to save database: {error}")
        
        self.logger.info(f"Batch complete. Processed: {processed}, Remaining: {remaining}")
        return processed, remaining
    
    def _process_document(self, docid: str, folders: dict[str, Path]) -> None:
        """Process a single document - find all matching files."""
        # Check if already exists (for resume support)
        existing = self.db.get_document(docid)
        
        # Find files
        files = self._find_matching_files(docid, folders)
        
        if existing:
            # Merge files, keep existing process status
            merged_files = existing["files"].copy()
            merged_files.update(files)
            self.db._data[docid]["files"] = merged_files
            self.logger.info(f"Updated {docid}")
        else:
            # New document
            self.db.add_document(docid, files)
            self.logger.info(f"Added new document: {docid}")
    
    def _find_matching_files(
        self,
        docid: str,
        folders: dict[str, Path],
    ) -> dict[str, str | None]:
        """Find all matching files for a document ID."""
        files = {
            "original_html": None,
            "original_xml": None,
            "updated_html": None,
            "config_xml": None,
            "compare_report": None,
        }
        
        # Pattern matching for files - use startswith to avoid substring matches
        # e.g., N12345 should NOT match N123456_original.xml
        pattern_lower = docid.lower()
        
        # Original HTML: N12345.html (case insensitive)
        html_folder = folders["original_html"]
        if html_folder.exists():
            for f in html_folder.iterdir():
                if f.is_file() and f.name.lower().startswith(pattern_lower):
                    files["original_html"] = f.name
                    break
        
        # Original XML: N12345_original.xml or similar
        xml_folder = folders["original_xml"]
        if xml_folder.exists():
            for f in xml_folder.iterdir():
                if f.is_file() and f.name.lower().startswith(pattern_lower):
                    files["original_xml"] = f.name
                    break
        
        # Updated HTML: Look in updated folder
        updated_folder = folders["updated_html"]
        if updated_folder.exists():
            for f in updated_folder.iterdir():
                if f.is_file() and f.suffix.lower() == ".html":
                    if f.name.lower().startswith(pattern_lower):
                        files["updated_html"] = f.name
                        break
        
        return files

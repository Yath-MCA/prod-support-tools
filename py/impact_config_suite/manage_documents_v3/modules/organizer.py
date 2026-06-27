"""Folder organization module."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from .. import config
from .database import DocumentDatabase
from .utils import Logger, FileOperation


class FolderOrganizer:
    """Organizes files into per-document folders."""
    
    def __init__(
        self,
        database: DocumentDatabase,
        log_callback: Callable[[str], None] | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ):
        self.db = database
        self.logger = Logger(
            database.project_path / config.LOG_FILE,
            console_callback=log_callback,
        )
        self.progress_callback = progress_callback
    
    def organize(self, skip_existing: bool = True) -> tuple[int, int]:
        """Move files into per-document folders.
        
        Args:
            skip_existing: Skip documents already organized
            
        Returns:
            Tuple of (successful, failed) counts
        """
        project_path = self.db.project_path
        self.logger.info("Starting file organization...")
        
        # Get pending documents
        pending = self.db.get_pending("organized")
        if skip_existing:
            # Filter to only unorganized
            pending = [
                docid for docid in pending
                if not self.db.get_document(docid).get("process", {}).get("organized", False)
            ]
        
        total = len(pending)
        if total == 0:
            self.logger.info("No documents to organize.")
            return 0, 0
        
        self.logger.info(f"Organizing {total} documents...")
        
        successful = 0
        failed = 0
        
        for i, docid in enumerate(pending, 1):
            if self.progress_callback:
                self.progress_callback(i, total)
            
            doc = self.db.get_document(docid)
            if not doc:
                continue
            
            # Create document folder
            doc_folder = project_path / docid
            doc_folder.mkdir(exist_ok=True)
            
            # Move files
            moved_count = 0
            errors = []
            
            # Original HTML
            orig_html = doc["files"].get("original_html")
            if orig_html:
                src = project_path / config.SOURCE_FOLDERS["original_html"] / orig_html
                dest = doc_folder / config.TARGET_NAMES["original_html"].format(docid=docid)
                success, error = FileOperation.safe_move(src, dest)
                if success:
                    moved_count += 1
                    self.db._data[docid]["files"]["original_html"] = str(dest.relative_to(project_path))
                else:
                    errors.append(f"HTML: {error}")
            
            # Original XML
            orig_xml = doc["files"].get("original_xml")
            if orig_xml:
                src = project_path / config.SOURCE_FOLDERS["original_xml"] / orig_xml
                dest = doc_folder / config.TARGET_NAMES["original_xml"].format(docid=docid)
                success, error = FileOperation.safe_move(src, dest)
                if success:
                    moved_count += 1
                    self.db._data[docid]["files"]["original_xml"] = str(dest.relative_to(project_path))
                else:
                    errors.append(f"XML: {error}")
            
            # Updated HTML
            upd_html = doc["files"].get("updated_html")
            if upd_html:
                src = project_path / config.SOURCE_FOLDERS["updated_html"] / upd_html
                dest = doc_folder / config.TARGET_NAMES["updated_html"].format(docid=docid)
                success, error = FileOperation.safe_move(src, dest)
                if success:
                    moved_count += 1
                    self.db._data[docid]["files"]["updated_html"] = str(dest.relative_to(project_path))
                else:
                    errors.append(f"Updated HTML: {error}")
            
            # Update status - only mark as organized if ALL files moved successfully
            if errors:
                # Partial or complete failure - mark as error
                self.db.mark_error(docid, "organize", "; ".join(errors))
                failed += 1
                self.logger.error(f"Failed to organize {docid}: {'; '.join(errors)}")
            else:
                # All files moved successfully
                self.db.update_document(docid, {"process.organized": True})
                self.db.clear_error(docid)
                successful += 1
                self.logger.info(f"Organized {docid} ({moved_count} files)")
        
        # Save database
        self.db.save()
        
        self.logger.info(f"Organization complete. Successful: {successful}, Failed: {failed}")
        return successful, failed

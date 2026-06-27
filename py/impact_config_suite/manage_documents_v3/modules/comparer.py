"""XML comparison module using existing pipeline."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from .. import config
from .database import DocumentDatabase
from .utils import Logger

# Import XML compare pipeline
try:
    from xml_compare.pipeline import run_xml_compare
    from xml_compare.models import CompareOptions
except ImportError:
    # Fallback for when not in full package context
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from xml_compare.pipeline import run_xml_compare
    from xml_compare.models import CompareOptions


class CompareManager:
    """Manages XML comparison for all documents."""
    
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
    
    def compare_all(
        self,
        options: CompareOptions = None,
        skip_existing: bool = True,
    ) -> tuple[int, int, int]:
        """Run XML comparison for all documents.
        
        Args:
            options: Comparison options (default if None)
            skip_existing: Skip if report already exists
            
        Returns:
            Tuple of (successful, skipped, failed) counts
        """
        if options is None:
            options = CompareOptions()
        
        project_path = self.db.project_path
        self.logger.info("Starting XML comparisons...")
        
        # Get pending documents
        pending = self.db.get_pending("compared")
        
        total = len(pending)
        if total == 0:
            self.logger.info("No documents need comparison.")
            return 0, 0, 0
        
        self.logger.info(f"Comparing {total} documents...")
        
        successful = 0
        skipped = 0
        failed = 0
        
        for i, docid in enumerate(pending, 1):
            if self.progress_callback:
                self.progress_callback(i, total)
            
            doc = self.db.get_document(docid)
            if not doc:
                continue
            
            # Get file paths
            doc_folder = project_path / docid
            
            # Check if already has report
            report_path = doc_folder / config.TARGET_NAMES["compare_report"]
            if report_path.exists() and skip_existing:
                self.db.update_document(docid, {
                    "process.compared": True,
                    "files.compare_report": str(report_path.relative_to(project_path)),
                })
                skipped += 1
                self.logger.info(f"Skipped {docid} (report exists)")
                continue
            
            # Get input files
            original_xml = doc["files"].get("original_xml")
            updated_html = doc["files"].get("updated_html")
            config_xml = doc["files"].get("config_xml")
            
            if not original_xml or not updated_html:
                self.db.mark_error(docid, "compare", "Missing required files for comparison")
                failed += 1
                self.logger.error(f"Missing files for {docid}")
                continue
            
            # Build paths
            orig_path = project_path / original_xml
            upd_path = project_path / updated_html
            
            # For comparison, we use original XML vs updated HTML
            # The comparison logic handles the conversion
            success, report_path, error = self._compare_single(
                docid, orig_path, upd_path, report_path, options
            )
            
            if success:
                self.db.update_document(docid, {
                    "process.compared": True,
                    "files.compare_report": str(report_path.relative_to(project_path)),
                })
                self.db.clear_error(docid)
                successful += 1
                self.logger.info(f"Compared {docid}")
            else:
                self.db.mark_error(docid, "compare", error)
                failed += 1
                self.logger.error(f"Failed to compare {docid}: {error}")
        
        # Save database
        self.db.save()
        
        self.logger.info(
            f"Comparisons complete. Successful: {successful}, Skipped: {skipped}, Failed: {failed}"
        )
        return successful, skipped, failed
    
    def _compare_single(
        self,
        docid: str,
        original_path: Path,
        updated_path: Path,
        report_path: Path,
        options: CompareOptions,
    ) -> tuple[bool, Path | None, str | None]:
        """Compare a single document."""
        try:
            # Run comparison using existing pipeline
            result_path = run_xml_compare(
                original=original_path,
                revised=updated_path,
                options=options,
                output_dir=report_path.parent,
                log_callback=lambda msg: self.logger.info(f"[{docid}] {msg}"),
            )
            
            return True, result_path, None
        except Exception as e:
            return False, None, str(e)

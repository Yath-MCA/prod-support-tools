"""Config XML download module with retry and rate limiting."""
from __future__ import annotations

import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError

from .. import config
from .database import DocumentDatabase
from .utils import Logger, RetryHelper


class ConfigDownloader:
    """Downloads impact_config.xml files from backend."""
    
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
        self._lock = threading.Lock()
    
    def download_all(
        self,
        base_url: str = None,
        force: bool = False,
        delay: float = None,
        max_retries: int = None,
    ) -> tuple[int, int, int]:
        """Download config XML for all documents.
        
        Args:
            base_url: Base URL for downloads (default from config)
            force: Download even if file already exists
            delay: Seconds between downloads (default from config)
            max_retries: Max retry attempts (default from config)
            
        Returns:
            Tuple of (successful, skipped, failed) counts
        """
        if base_url is None:
            base_url = config.BASE_URL
        if delay is None:
            delay = config.DOWNLOAD_DELAY
        if max_retries is None:
            max_retries = config.MAX_RETRIES
        
        project_path = self.db.project_path
        self.logger.info(f"Starting config downloads from {base_url}...")
        
        # Get documents needing download
        pending = self.db.get_pending("config_downloaded")
        
        total = len(pending)
        if total == 0:
            self.logger.info("No documents need config download.")
            return 0, 0, 0
        
        self.logger.info(f"Downloading configs for {total} documents...")
        
        successful = 0
        skipped = 0
        failed = 0
        
        for i, docid in enumerate(pending, 1):
            if self.progress_callback:
                self.progress_callback(i, total)
            
            doc = self.db.get_document(docid)
            if not doc:
                continue
            
            # Check if already downloaded
            doc_folder = self.db.resolve_document_folder(docid, doc)
            config_path = doc_folder / config.TARGET_NAMES["config_xml"]
            
            if config_path.exists() and not force:
                # Already exists, mark as done
                self.db.update_document(docid, {"process.config_downloaded": True})
                skipped += 1
                self.logger.info(f"Skipped {docid} (already exists)")
                continue
            
            # Download
            url = f"{base_url}/{docid}/impact_config.xml"
            
            success, error = self._download_with_retry(
                docid,
                config_path,
                url,
                max_retries,
            )
            
            if success:
                self.db.update_document(docid, {
                    "process.config_downloaded": True,
                    "files.config_xml": str(config_path.relative_to(project_path)),
                })
                self.db.clear_error(docid)
                successful += 1
                self.logger.info(f"Downloaded config for {docid}")
            else:
                self.db.mark_error(docid, "download", error)
                failed += 1
                self.logger.error(f"Failed to download config for {docid}: {error}")
            
            # Rate limiting delay (skip after last)
            if i < total and delay > 0:
                time.sleep(delay)
        
        # Save database
        self.db.save()
        
        self.logger.info(
            f"Downloads complete. Successful: {successful}, Skipped: {skipped}, Failed: {failed}"
        )
        return successful, skipped, failed
    
    def download_all_threaded(
        self,
        base_url: str = None,
        force: bool = False,
        max_retries: int = None,
        workers: int = None,
        batch_size: int = None,
        batch_callback: Callable[[int, int, int, int], None] | None = None,
    ) -> tuple[int, int, int]:
        """Download config XML for all documents using thread pool.
        
        Args:
            base_url: Base URL for downloads (default from config)
            force: Download even if file already exists
            max_retries: Max retry attempts (default from config)
            workers: Number of worker threads (default from config)
            batch_size: Files to process per batch (default from config)
            batch_callback: Called with (completed, total, successful, failed)
        
        Returns:
            Tuple of (successful, skipped, failed) counts
        """
        if base_url is None:
            base_url = config.BASE_URL
        if max_retries is None:
            max_retries = config.MAX_RETRIES
        if workers is None:
            workers = config.THREADED_DOWNLOAD_WORKERS
        if batch_size is None:
            batch_size = config.THREADED_DOWNLOAD_BATCH

        project_path = self.db.project_path
        self.logger.info(
            f"Starting threaded config downloads from {base_url} "
            f"(workers={workers}, batch_size={batch_size})..."
        )

        # Get documents needing download
        pending = self.db.get_pending("config_downloaded")

        total = len(pending)
        if total == 0:
            self.logger.info("No documents need config download.")
            return 0, 0, 0

        self.logger.info(f"Downloading configs for {total} documents...")

        # Thread-safe counters
        completed = 0
        successful = 0
        skipped = 0
        failed = 0
        lock = threading.Lock()

        def _download_single(docid: str) -> tuple[str, bool, str | None]:
            """Download a single file (for thread worker).
            
            Returns:
                Tuple of (docid, success, error_message)
            """
            doc = self.db.get_document(docid)
            if not doc:
                return docid, False, "Document not found"

            # Check if already downloaded
            doc_folder = self.db.resolve_document_folder(docid, doc)
            config_path = doc_folder / config.TARGET_NAMES["config_xml"]

            if config_path.exists() and not force:
                # Already exists, mark as done (thread-safe)
                with lock:
                    self.db.update_document(docid, {"process.config_downloaded": True})
                self.logger.info(f"Skipped {docid} (already exists)")
                return docid, True, "skipped"

            # Download
            url = f"{base_url}/{docid}/impact_config.xml"
            success, error = self._download_with_retry(
                docid,
                config_path,
                url,
                max_retries,
            )

            if success:
                with lock:
                    self.db.update_document(docid, {
                        "process.config_downloaded": True,
                        "files.config_xml": str(config_path.relative_to(project_path)),
                    })
                    self.db.clear_error(docid)
                self.logger.info(f"Downloaded config for {docid}")
                return docid, True, None
            else:
                with lock:
                    self.db.mark_error(docid, "download", error)
                self.logger.error(f"Failed to download config for {docid}: {error}")
                return docid, False, error

        # Process in batches
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch = pending[batch_start:batch_end]
            batch_len = len(batch)

            self.logger.info(f"Processing batch {batch_start // batch_size + 1}: {batch_len} files")

            # Execute batch with thread pool
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(_download_single, docid): docid for docid in batch}

                for future in as_completed(futures):
                    docid, success, error = future.result()

                    with lock:
                        completed += 1
                        if error == "skipped":
                            skipped += 1
                            successful += 1  # Count skipped as successful
                        elif success:
                            successful += 1
                        else:
                            failed += 1

                    # Report progress via callback
                    if batch_callback:
                        batch_callback(completed, total, successful, failed)

        # Save database after all threads complete
        self.db.save()

        self.logger.info(
            f"Downloads complete. Successful: {successful}, Skipped: {skipped}, Failed: {failed}"
        )
        return successful, skipped, failed

    def _download_with_retry(
        self,
        docid: str,
        dest_path: Path,
        url: str,
        max_retries: int,
    ) -> tuple[bool, str | None]:
        """Download a single file with retry logic."""
        def download_operation():
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "DocumentManager/3.0"},
            )
            
            with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as response:
                with open(dest_path, 'wb') as f:
                    f.write(response.read())
            
            return True
        
        result, error = RetryHelper.with_retry(
            download_operation,
            max_retries=max_retries,
            backoff_factor=config.RETRY_CONFIG["backoff_factor"],
            max_delay=config.RETRY_CONFIG["max_delay"],
            on_retry=lambda attempt, err: self.logger.warning(
                f"Retry {attempt}/{max_retries} for {docid}: {err}"
            ),
        )
        
        return result is not None, error

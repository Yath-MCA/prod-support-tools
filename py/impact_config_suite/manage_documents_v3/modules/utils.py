"""Utilities for Document Manager v3."""
from __future__ import annotations

import json
import logging
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar, Any

T = TypeVar('T')


class Logger:
    """Dual logging to console and file with progress callback support."""
    
    def __init__(self, log_file: Path | str, console_callback: Callable[[str], None] | None = None):
        self.log_file = Path(log_file)
        self.console_callback = console_callback
        self._setup_file_logging()
    
    def _setup_file_logging(self):
        """Setup file logger."""
        self.logger = logging.getLogger("docmanager")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        handler = logging.FileHandler(self.log_file, mode='a')
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
        if self.console_callback:
            self.console_callback(message)
    
    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)
        if self.console_callback:
            self.console_callback(f"ERROR: {message}")
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
        if self.console_callback:
            self.console_callback(f"WARNING: {message}")


@dataclass
class FileOperation:
    """Safe file operations with error handling."""
    
    @staticmethod
    def safe_move(src: Path, dest: Path, overwrite: bool = False) -> tuple[bool, str | None]:
        """Move file with error handling. Returns (success, error_message)."""
        try:
            if not src.exists():
                return False, f"Source file not found: {src}"
            
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            if dest.exists() and not overwrite:
                return False, f"Destination exists (use overwrite=True): {dest}"
            
            shutil.move(str(src), str(dest))
            return True, None
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def safe_copy(src: Path, dest: Path, overwrite: bool = False) -> tuple[bool, str | None]:
        """Copy file with error handling. Returns (success, error_message)."""
        try:
            if not src.exists():
                return False, f"Source file not found: {src}"
            
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            if dest.exists() and not overwrite:
                return False, f"Destination exists (use overwrite=True): {dest}"
            
            shutil.copy2(str(src), str(dest))
            return True, None
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def safe_delete(path: Path) -> tuple[bool, str | None]:
        """Delete file with error handling. Returns (success, error_message)."""
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            return True, None
        except Exception as e:
            return False, str(e)


class PathHelper:
    """Path construction and validation utilities."""
    
    @staticmethod
    def validate_project_path(project_path: Path | str) -> Path:
        """Validate and return absolute project path. Creates if needed."""
        path = Path(project_path).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def extract_docid(filename: str, pattern: str = None) -> str | None:
        """Extract document ID from filename. Returns Nxxxxx or None.
        
        Handles both simple (N12345.html) and UUID-style (N00013009-f0f8-...html) filenames.
        """
        if pattern is None:
            # Match N followed by digits, optionally followed by dash and UUID
            pattern = r"[Nn][0-9a-f]+(?:-[0-9a-f-]+)?"
        
        match = re.search(pattern, filename)
        if match:
            # Get the full match (N + identifier)
            full_match = match.group(0)
            # Normalize to uppercase N
            docid = full_match[0].upper() + full_match[1:]
            return docid
        return None
    
    @staticmethod
    def get_source_folders(project_path: Path, folder_names: dict) -> dict[str, Path]:
        """Get paths to source folders, validating they exist."""
        folders = {}
        for key, name in folder_names.items():
            folder_path = project_path / name
            folders[key] = folder_path
        return folders


class RetryHelper:
    """Retry logic with exponential backoff."""
    
    @staticmethod
    def with_retry(
        operation: Callable[[], T],
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        on_retry: Callable[[int, str], None] | None = None,
    ) -> tuple[T | None, str | None]:
        """Execute operation with retry logic.
        
        Args:
            operation: Callable to execute
            max_retries: Maximum number of retry attempts
            backoff_factor: Multiply delay by this factor each retry
            max_delay: Maximum delay between retries
            on_retry: Callback(retry_count, error_message) called on each retry
            
        Returns:
            Tuple of (result, error_message). If successful, error_message is None.
        """
        delay = 1.0
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = operation()
                return result, None
            except Exception as e:
                last_error = str(e)
                
                if attempt < max_retries:
                    if on_retry:
                        on_retry(attempt + 1, last_error)
                    time.sleep(min(delay, max_delay))
                    delay *= backoff_factor
                
        return None, last_error


def load_json(path: Path) -> dict:
    """Load JSON file, returning empty dict if not found or invalid."""
    if not path.exists():
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_json(path: Path, data: dict, indent: int = 2) -> tuple[bool, str | None]:
    """Save data to JSON file atomically."""
    try:
        temp_path = path.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        temp_path.replace(path)
        return True, None
    except Exception as e:
        return False, str(e)

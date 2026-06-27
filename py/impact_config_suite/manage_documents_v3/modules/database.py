"""Document database management for JSON persistence."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from .. import config
from .utils import load_json, save_json


class DocumentDatabase:
    """Manages the documents.json database with resume support."""
    
    def __init__(self, project_path: Path | str):
        self.project_path = Path(project_path).resolve()
        self.json_path = self.project_path / config.JSON_FILE
        self._data: dict[str, dict] = {}
        self.load()
    
    def load(self) -> dict[str, dict]:
        """Load database from JSON file."""
        self._data = load_json(self.json_path)
        return self._data
    
    def save(self) -> tuple[bool, str | None]:
        """Save database to JSON file."""
        return save_json(self.json_path, self._data)
    
    def get_all(self) -> dict[str, dict]:
        """Get all documents."""
        return self._data.copy()
    
    def get_document(self, docid: str) -> dict | None:
        """Get single document by ID."""
        return self._data.get(docid)
    
    def add_document(
        self,
        docid: str,
        files: dict[str, str | None],
        process: dict[str, bool] | None = None,
    ) -> None:
        """Add or update a document entry."""
        if process is None:
            process = {step: False for step in config.PROCESS_STEPS}
        
        self._data[docid] = {
            "docid": docid,
            "folder": docid,
            "files": files,
            "process": process,
            "error": None,
            "last_step": None,
            "retry_count": 0,
        }
    
    def update_document(self, docid: str, updates: dict[str, Any]) -> bool:
        """Update specific fields of a document."""
        if docid not in self._data:
            return False
        
        # Handle nested updates (e.g., "process.organized" -> True)
        for key, value in updates.items():
            if "." in key:
                parts = key.split(".")
                target = self._data[docid]
                for part in parts[:-1]:
                    if part not in target:
                        target[part] = {}
                    target = target[part]
                target[parts[-1]] = value
            else:
                self._data[docid][key] = value
        
        return True
    
    def get_pending(self, step: str) -> list[str]:
        """Get list of docids that haven't completed the given step.
        
        Also excludes documents with errors on that step (unless retry_count > 0).
        """
        pending = []
        for docid, doc in self._data.items():
            # Skip if already done this step
            if doc.get("process", {}).get(step, False):
                continue
            
            # Skip if has error on this step and no retries left
            error = doc.get("error")
            last_step = doc.get("last_step")
            retry_count = doc.get("retry_count", 0)
            
            if error and last_step == step and retry_count == 0:
                continue
            
            pending.append(docid)
        
        return pending
    
    def mark_error(self, docid: str, step: str, error: str) -> bool:
        """Mark a document with an error on a specific step."""
        if docid not in self._data:
            return False
        
        self._data[docid]["error"] = error
        self._data[docid]["last_step"] = step
        # Increment retry count on error
        self._data[docid]["retry_count"] = self._data[docid].get("retry_count", 0) + 1
        return True
    
    def clear_error(self, docid: str) -> bool:
        """Clear error status for a document."""
        if docid not in self._data:
            return False
        
        self._data[docid]["error"] = None
        self._data[docid]["last_step"] = None
        self._data[docid]["retry_count"] = 0
        return True
    
    def get_statistics(self) -> dict[str, Any]:
        """Get processing statistics."""
        total = len(self._data)
        
        stats = {
            "total": total,
            "with_errors": 0,
            "steps": {step: 0 for step in config.PROCESS_STEPS},
        }
        
        for doc in self._data.values():
            if doc.get("error"):
                stats["with_errors"] += 1
            
            for step in config.PROCESS_STEPS:
                if doc.get("process", {}).get(step, False):
                    stats["steps"][step] += 1
        
        return stats
    
    def document_exists(self, docid: str) -> bool:
        """Check if document exists in database."""
        return docid in self._data

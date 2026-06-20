from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path


class RunHistoryStore:
    DEFAULT_FOLDER_NAME = "impact-support-log"
    DEFAULT_FILE_NAME = "suite_run_history.json"
    HISTORY_LIMIT = 200

    @classmethod
    def base_dir(cls) -> Path:
        return Path.home() / "Documents" / cls.DEFAULT_FOLDER_NAME

    @classmethod
    def history_file_path(cls) -> Path:
        return cls.base_dir() / cls.DEFAULT_FILE_NAME

    @classmethod
    def load_entries(cls) -> list[dict]:
        history_path = cls.history_file_path()
        if not history_path.exists():
            return []
        try:
            raw = json.loads(history_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if not isinstance(raw, list):
            return []
        return [item for item in raw if isinstance(item, dict)][: cls.HISTORY_LIMIT]

    @classmethod
    def save_entries(cls, entries: list[dict]) -> None:
        history_path = cls.history_file_path()
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(
            json.dumps(entries[: cls.HISTORY_LIMIT], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def add_entry(cls, entry: dict) -> dict:
        payload = dict(entry)
        payload.setdefault("id", str(uuid.uuid4()))
        payload.setdefault("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        payload.setdefault("tool_id", "")
        payload.setdefault("tool_label", "")
        payload.setdefault("summary", "")
        payload.setdefault("params", {})

        entries = cls.load_entries()
        entry_key = (
            str(payload.get("tool_id", "")),
            str(payload.get("action", "")),
            str(payload.get("source_path", "")),
            str(payload.get("output_dir", "")),
            str(payload.get("report_path", "")),
            json.dumps(payload.get("params", {}), sort_keys=True, ensure_ascii=False),
        )
        entries = [
            existing for existing in entries
            if (
                str(existing.get("tool_id", "")),
                str(existing.get("action", "")),
                str(existing.get("source_path", "")),
                str(existing.get("output_dir", "")),
                str(existing.get("report_path", "")),
                json.dumps(existing.get("params", {}), sort_keys=True, ensure_ascii=False),
            ) != entry_key
        ]
        entries.insert(0, payload)
        cls.save_entries(entries)
        return payload

    @classmethod
    def recent_for_tool(cls, tool_id: str) -> list[dict]:
        return [entry for entry in cls.load_entries() if str(entry.get("tool_id", "")) == tool_id]

    @classmethod
    def search_entries(cls, text: str) -> list[dict]:
        entries = cls.load_entries()
        needle = text.strip().lower()
        if not needle:
            return entries
        matched = []
        for entry in entries:
            try:
                haystack = json.dumps(entry, ensure_ascii=False).lower()
            except Exception:
                haystack = str(entry).lower()
            if needle in haystack:
                matched.append(entry)
        return matched

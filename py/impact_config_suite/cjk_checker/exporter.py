from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict
from pathlib import Path

from .diff_engine import DiffRow


def _safe_file_token(doc_id: str) -> str:
    safe = re.sub(r"[\\/:*?\"<>|]+", "_", doc_id.strip())
    return safe or "document"


def export_json(rows: list[DiffRow], summary: dict, output_dir: Path, doc_id: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"report_{_safe_file_token(doc_id)}.json"
    payload = {
        "doc_id": doc_id,
        "summary": summary,
        "rows": [asdict(row) for row in rows],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def export_csv(rows: list[DiffRow], output_dir: Path, doc_id: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"report_{_safe_file_token(doc_id)}.csv"
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "element_path",
                "char_index",
                "original",
                "revised",
                "status",
                "original_snippet",
                "revised_snippet",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.element_path,
                    row.char_index,
                    row.original,
                    row.revised,
                    row.status,
                    row.original_snippet,
                    row.revised_snippet,
                ]
            )
    return output_path

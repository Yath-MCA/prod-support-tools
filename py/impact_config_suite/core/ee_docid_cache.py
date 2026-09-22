"""Optional beside-docid cache for DOI/pub-id by-ref bucket results."""
from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA_VERSION = 1
DOI_QUERY_TYPE = "doi_pubid_by_ref"


def query_slug(query_type: str, schema_version: int = SCHEMA_VERSION) -> str:
    raw = f"{query_type}_v{schema_version}"
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", raw)[:80]
    return s or "query"


def cache_path(source_file: Path, query_type: str = DOI_QUERY_TYPE) -> Path:
    source_file = Path(source_file)
    return source_file.parent / "ee_cache" / f"{query_slug(query_type)}.json"


def _stat_key(source_file: Path) -> tuple[float, int]:
    st = Path(source_file).stat()
    return (st.st_mtime, st.st_size)


def build_cache_payload(
    source_file: Path, *, buckets: list, query_type: str = DOI_QUERY_TYPE
) -> dict:
    mtime, size = _stat_key(source_file)
    return {
        "schema_version": SCHEMA_VERSION,
        "query_type": query_type,
        "query_value": "",
        "mtime": mtime,
        "size": size,
        "buckets": buckets,
    }


def try_load_cache(source_file: Path, *, query_type: str = DOI_QUERY_TYPE) -> dict | None:
    path = cache_path(source_file, query_type=query_type)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema_version") != SCHEMA_VERSION:
        return None
    if data.get("query_type") != query_type:
        return None
    try:
        mtime, size = _stat_key(source_file)
    except OSError:
        return None
    if data.get("mtime") != mtime or data.get("size") != size:
        return None
    if not isinstance(data.get("buckets"), list):
        return None
    return data


def write_cache(source_file: Path, payload: dict) -> Path | None:
    path = cache_path(source_file)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path
    except OSError:
        return None

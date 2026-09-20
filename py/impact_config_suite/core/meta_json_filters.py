"""Load and resolve IMPACT meta.json maps for client/DTD scan filters."""
from __future__ import annotations

import json
from pathlib import Path


def load_meta_map(meta_path: Path, cache: dict) -> dict | None:
    """Return parsed docid->meta dict, or None if missing/invalid. Cache by path+mtime."""
    meta_path = Path(meta_path)
    try:
        mtime = meta_path.stat().st_mtime
    except OSError:
        return None

    try:
        key = str(meta_path.resolve())
    except OSError:
        key = str(meta_path)

    cached = cache.get(key)
    if cached is not None and cached.get("mtime") == mtime:
        return cached.get("data")

    try:
        raw = meta_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
        cache[key] = {"mtime": mtime, "data": None}
        return None

    if not isinstance(data, dict):
        cache[key] = {"mtime": mtime, "data": None}
        return None

    cache[key] = {"mtime": mtime, "data": data}
    return data


def lookup_meta_entry(file_path: Path, cache: dict) -> dict | None:
    """
    Find meta entry for file_path.parent.name.
    Prefer {parent.parent}/meta.json (BITS|JATS), then walk ancestors for meta.json.
    """
    file_path = Path(file_path)
    doc_dir = file_path.parent
    docid = doc_dir.name
    if not docid:
        return None

    tried: set[str] = set()
    candidates: list[Path] = []

    nearest = doc_dir.parent / "meta.json"
    candidates.append(nearest)

    for ancestor in doc_dir.parents:
        candidates.append(ancestor / "meta.json")

    for meta_path in candidates:
        try:
            resolved = str(meta_path.resolve())
        except OSError:
            resolved = str(meta_path)
        if resolved in tried:
            continue
        tried.add(resolved)
        if not meta_path.is_file():
            continue
        data = load_meta_map(meta_path, cache)
        if not data:
            continue
        entry = data.get(docid)
        if isinstance(entry, dict):
            return entry
    return None

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


def load_meta_for_scan_root(dir_path: Path, cache: dict) -> dict | None:
    """
    Load meta map for a folder-scan root.
    Prefer {dir_path}/meta.json, then {dir_path.parent}/meta.json.
    """
    dir_path = Path(dir_path)
    for meta_path in (dir_path / "meta.json", dir_path.parent / "meta.json"):
        if not meta_path.is_file():
            continue
        data = load_meta_map(meta_path, cache)
        if data:
            return data
    return None


def matching_docids(meta_map: dict, dtd_filter: str = "", client_filter: str = "") -> list[str]:
    """Return docids whose meta client/dtd match the filters (case-insensitive)."""
    dtd_filter = (dtd_filter or "").strip()
    client_filter = (client_filter or "").strip()
    if not isinstance(meta_map, dict):
        return []
    out: list[str] = []
    for docid, entry in meta_map.items():
        if not isinstance(entry, dict):
            continue
        dtd = (entry.get("dtd") or "").strip()
        client = (entry.get("client") or "").strip()
        if dtd_filter and dtd.upper() != dtd_filter.upper():
            continue
        if client_filter and client.upper() != client_filter.upper():
            continue
        out.append(str(docid))
    return out


def resolve_doc_dir(scan_root: Path, docid: str, entry: dict | None = None) -> Path | None:
    """
    Locate the document folder for docid under scan_root.
    Tries scan_root/docid, then scan_root/{dtd}/docid, then BITS/JATS children.
    """
    scan_root = Path(scan_root)
    direct = scan_root / docid
    if direct.is_dir():
        return direct

    dtd = ""
    if isinstance(entry, dict):
        dtd = (entry.get("dtd") or "").strip()
    if dtd:
        under_dtd = scan_root / dtd / docid
        if under_dtd.is_dir():
            return under_dtd

    for name in ("BITS", "JATS", "bits", "jats"):
        candidate = scan_root / name / docid
        if candidate.is_dir():
            return candidate
    return None

"""Durable Folder Scan JSON index for Element Extractor.

Index location (chosen deliberately):
  ~/Documents/impact-support-log/indexes/<sha256(abs_source_root)>.json

Why not beside the source folder (e.g. {source}/.impact_folder_scan_index.json)?
  - Production / network source trees are often read-only.
  - Avoids writing tooling artifacts into content folders.
  - Matches the existing impact-support-log home for Element Extractor reports.

The hash is of the resolved absolute source path (normalized case on Windows) so
re-scans of the same root always resolve to the same index file.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

INDEX_VERSION = 1
INDEX_FOLDER_NAME = "impact-support-log"
INDEXES_SUBDIR = "indexes"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_source_root(source_root):
    root = Path(source_root)
    try:
        root = root.resolve()
    except OSError:
        root = root.absolute()
    return root


def source_root_key(source_root):
    root = normalize_source_root(source_root)
    key_str = str(root).replace("\\", "/").lower()
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()


def indexes_dir():
    return Path.home() / "Documents" / INDEX_FOLDER_NAME / INDEXES_SUBDIR


def index_path_for(source_root):
    return indexes_dir() / ("%s.json" % source_root_key(source_root))


def empty_index(source_root):
    root = normalize_source_root(source_root)
    now = _utc_now_iso()
    return {
        "version": INDEX_VERSION,
        "source_root": str(root),
        "created_at": now,
        "updated_at": now,
        "files": [],
    }


def load_index(index_path=None, source_root=None):
    path = Path(index_path) if index_path else None
    if path is None:
        if source_root is None:
            return None
        path = index_path_for(source_root)
    try:
        if not path.is_file():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None
    if data.get("version") != INDEX_VERSION:
        return None
    if not isinstance(data.get("files"), list):
        return None
    if source_root is not None:
        expected = str(normalize_source_root(source_root))
        stored = str(data.get("source_root") or "")
        try:
            if normalize_source_root(stored) != normalize_source_root(expected):
                if source_root_key(stored) != source_root_key(expected):
                    return None
        except Exception:
            if stored.replace("\\", "/").lower() != expected.replace("\\", "/").lower():
                return None
    return data


def save_index(data, index_path=None):
    try:
        root = data.get("source_root") or ""
        path = Path(index_path) if index_path else index_path_for(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = dict(data)
        data["version"] = INDEX_VERSION
        data["updated_at"] = _utc_now_iso()
        if not data.get("created_at"):
            data["created_at"] = data["updated_at"]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path
    except Exception:
        return None


def make_file_entry(file_path, source_root, mtime=None, size=None, client="", dtd="", config_path=""):
    fp = Path(file_path)
    try:
        st = fp.stat()
        if mtime is None:
            mtime = st.st_mtime
        if size is None:
            size = st.st_size
    except OSError:
        mtime = float(mtime or 0.0)
        size = int(size or 0)

    if not config_path:
        cfg = fp.parent / "impact_config.xml"
        config_path = str(cfg) if cfg.is_file() else ""

    try:
        abs_path = str(fp.resolve())
    except OSError:
        abs_path = str(fp.absolute())

    return {
        "path": abs_path,
        "mtime": float(mtime),
        "size": int(size),
        "client": client or "",
        "dtd": dtd or "",
        "config_path": config_path or "",
    }


def entry_map(index_data):
    out = {}
    for entry in index_data.get("files") or []:
        if not isinstance(entry, dict):
            continue
        raw = entry.get("path") or ""
        if not raw:
            continue
        key = str(Path(raw)).replace("\\", "/").lower()
        out[key] = entry
    return out


def path_key(file_path):
    try:
        p = Path(file_path).resolve()
    except OSError:
        p = Path(file_path).absolute()
    return str(p).replace("\\", "/").lower()


def merge_entries(existing, updates):
    merged = entry_map({"files": list(existing)})
    for entry in updates:
        if not isinstance(entry, dict) or not entry.get("path"):
            continue
        merged[path_key(entry["path"])] = entry
    return sorted(merged.values(), key=lambda e: str(e.get("path") or "").lower())


def refresh_entry(entry, metadata_fn=None, force=False):
    fp = Path(entry.get("path") or "")
    if not fp.is_file():
        return None
    try:
        st = fp.stat()
    except OSError:
        return None

    changed = force or (
        float(entry.get("mtime") or 0) != float(st.st_mtime)
        or int(entry.get("size") or 0) != int(st.st_size)
    )
    new_entry = dict(entry)
    new_entry["mtime"] = float(st.st_mtime)
    new_entry["size"] = int(st.st_size)
    cfg = fp.parent / "impact_config.xml"
    new_entry["config_path"] = str(cfg) if cfg.is_file() else ""

    if changed and metadata_fn is not None:
        try:
            meta = metadata_fn(fp) or {}
        except Exception:
            meta = {}
        new_entry["client"] = meta.get("client", "") or ""
        new_entry["dtd"] = meta.get("dtd", "") or ""
    return new_entry


def collect_matching_files(extractor, dir_path, *, recursive=False, extensions=None,
    filename_filter=None, dtd_filter=None, client_filter=None, month_filter="All Time",
    custom_month="", use_index=True, discover_new=True, log_callback=None, cancel_check=None):
    dir_path = normalize_source_root(dir_path)
    if not dir_path.is_dir():
        raise NotADirectoryError("not a directory: %s" % dir_path)
    def _log(msg):
        if log_callback:
            try: log_callback(msg)
            except Exception: pass
    def _cancelled():
        return bool(cancel_check and cancel_check())
    if not extensions:
        extensions = [".xml", ".html", ".htm", ".xhtml"]
    extensions = [e.lower() if str(e).startswith(".") else "." + str(e).lower() for e in extensions]
    normalized_filter = filename_filter.strip() if filename_filter else ""
    if normalized_filter and normalized_filter.lower() != "none" and not any(c in normalized_filter for c in "*?[]"):
        normalized_filter = "*" + normalized_filter
    apply_name = bool(normalized_filter and normalized_filter.lower() != "none")
    dtd_norm = extractor._normalize_named_filter(dtd_filter or "")
    client_norm = extractor._normalize_named_filter(client_filter or "")
    index_data = None; indexed = {}
    if use_index:
        index_data = load_index(source_root=dir_path)
        if index_data is not None:
            indexed = entry_map(index_data); _log("Loaded folder index (%d files)" % len(indexed))
        else:
            index_data = empty_index(dir_path)
    updated_entries = []; matched_files = []; seen_keys = set()
    def _accept(file_path, client, dtd):
        if apply_name and not extractor._matches_filename_filter(file_path.name, normalized_filter): return False
        if file_path.suffix.lower() not in extensions: return False
        if dtd_norm and (dtd or "").upper() != dtd_norm.upper(): return False
        if client_norm and (client or "").upper() != client_norm.upper(): return False
        if not extractor._matches_month_filter(file_path, month_filter, custom_month): return False
        return True
    def _under_root(fp):
        try:
            fp.resolve().relative_to(dir_path); return True
        except Exception: pass
        fp_l = str(fp).lower(); root_l = str(dir_path).lower().rstrip("\\/")
        return fp_l == root_l or fp_l.startswith(root_l + "\\") or fp_l.startswith(root_l + "/")
    def _process_path(file_path, prior=None):
        if _cancelled(): return
        key = path_key(file_path)
        if key in seen_keys or not file_path.is_file(): return
        if file_path.suffix.lower() not in extensions: return
        if prior is not None:
            entry = refresh_entry(prior, metadata_fn=extractor.get_file_metadata, force=False)
            if entry is None: return
        else:
            try: meta = extractor.get_file_metadata(file_path)
            except Exception: meta = {}
            entry = make_file_entry(file_path, dir_path, client=meta.get("client", "") or "", dtd=meta.get("dtd", "") or "")
        updated_entries.append(entry); seen_keys.add(key)
        if _accept(file_path, entry.get("client", ""), entry.get("dtd", "")):
            matched_files.append(Path(entry["path"]))
    if use_index and indexed:
        for _k, entry in indexed.items():
            if _cancelled(): break
            fp = Path(entry.get("path") or "")
            if _under_root(fp): _process_path(fp, prior=entry)
    need_walk = discover_new or (not indexed) or (not use_index)
    if need_walk and not _cancelled():
        pattern = "**/*" if recursive else "*"
        for file in dir_path.glob(pattern):
            if _cancelled(): break
            if not file.is_file() or file.suffix.lower() not in extensions: continue
            key = path_key(file)
            if key in seen_keys: continue
            _process_path(file, prior=(indexed.get(key) if indexed else None))
    matched_files = sorted(set(matched_files), key=lambda p: str(p).lower())
    if use_index:
        base_files = list((index_data or empty_index(dir_path)).get("files") or [])
        if need_walk:
            retained = []
            for e in base_files:
                k = path_key(e.get("path") or "")
                if k in seen_keys: continue
                fp = Path(e.get("path") or "")
                if fp.suffix.lower() in extensions: continue
                if fp.is_file(): retained.append(e)
            base_files = retained
        else:
            base_files = [e for e in base_files if path_key(e.get("path") or "") in seen_keys or Path(e.get("path") or "").suffix.lower() not in extensions]
        merged = merge_entries(base_files, updated_entries)
        payload = index_data or empty_index(dir_path)
        payload["source_root"] = str(dir_path); payload["files"] = merged
        written = save_index(payload)
        if written is not None: _log("Wrote folder index (%d files)" % len(merged))
    return matched_files


import json
from pathlib import Path
import re
from urllib.parse import urlparse

import requests


def load_config(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _original_file_name_from_revised(file_name: str) -> str:
    lower_name = file_name.lower()

    if lower_name.endswith("_updated.html"):
        return file_name[:-13] + ".html"
    if lower_name.endswith("_updated.htm"):
        return file_name[:-12] + ".htm"
    if lower_name.endswith("_updated"):
        return file_name[:-8] + ".html"

    if lower_name.startswith("updated_"):
        trimmed = file_name[8:]
        if "." not in trimmed:
            return trimmed + ".html"
        return trimmed

    return file_name


def _doc_format_values(doc_id: str) -> dict[str, str]:
    raw_doc_id = (doc_id or "").strip()
    normalized = raw_doc_id.replace("\\", "/").lstrip("/")

    parsed = urlparse(raw_doc_id)
    if parsed.scheme and parsed.netloc:
        normalized = parsed.path.lstrip("/")

    segments = [part for part in normalized.split("/") if part]

    # When users provide only the UUID, build the new HTML path convention.
    # Example:
    #   original -> IMPACT/<id>/<id>.html
    #   revised  -> IMPACT/<id>/<id>_updated.html
    if "/" not in normalized and "." not in normalized:
        return {
            "doc_id": normalized,
            "input_doc_id": raw_doc_id,
            "doc_path": f"IMPACT/{normalized}/{normalized}_updated.html",
            "original_doc_path": f"IMPACT/{normalized}/{normalized}.html",
            "revised_doc_path": f"IMPACT/{normalized}/{normalized}_updated.html",
        }

    revised_doc_path = normalized
    original_doc_path = normalized

    if segments:
        revised_name = segments[-1]
        original_name = _original_file_name_from_revised(revised_name)
        original_segments = [*segments[:-1], original_name]
        original_doc_path = "/".join(original_segments)

    base_name = segments[-1] if segments else normalized
    stem = base_name.rsplit(".", 1)[0] if "." in base_name else base_name
    stem = stem.removeprefix("updated_")
    if stem.endswith("_updated"):
        stem = stem[:-8]

    canonical_doc_id = stem or raw_doc_id

    return {
        "doc_id": canonical_doc_id,
        "input_doc_id": raw_doc_id,
        "doc_path": normalized,
        "original_doc_path": original_doc_path,
        "revised_doc_path": revised_doc_path,
    }


def build_urls(config: dict, doc_id: str, domain: str) -> tuple[str, str]:
    domain_key = (domain or "").upper().strip()
    domains = config.get("domains", {})
    format_values = _doc_format_values(doc_id)

    if domains and domain_key in domains:
        domain_cfg = domains[domain_key]
        original_url = domain_cfg["original_url"].format(**format_values)
        revised_url = domain_cfg["revised_url"].format(**format_values)
        return original_url, revised_url

    # Backward compatibility: fall back to old flat config shape.
    original_url = config["original_url"].format(**format_values)
    revised_url = config["revised_url"].format(**format_values)
    return original_url, revised_url


def fetch_html(url: str, timeout: int) -> str:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def _safe_file_token(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return safe or "document"


def get_cache_file_path(base_dir: Path, domain: str, doc_id: str, variant: str) -> Path:
    cache_dir = base_dir / "cache" / _safe_file_token(domain.upper()) / _safe_file_token(doc_id)
    return cache_dir / f"{variant}.html"


def fetch_html_cached(
    *,
    url: str,
    timeout: int,
    cache_file: Path,
    force_fetch: bool,
) -> tuple[str, bool]:
    if not force_fetch and cache_file.exists():
        return cache_file.read_text(encoding="utf-8", errors="replace"), True

    html = fetch_html(url, timeout)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(html, encoding="utf-8")
    return html, False

"""Shared naming helpers for Element Extractor run output folders."""


def format_extraction_run_folder_name(ts: str, safe_target: str, query_slug: str) -> str:
    """Return ``{ts}_extraction_{safe_target}_{query_slug}``."""
    return f"{ts}_extraction_{safe_target}_{query_slug}"

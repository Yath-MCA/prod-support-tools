from __future__ import annotations

from pathlib import Path
import re
from typing import Callable
from urllib.parse import urlparse

from .diff_engine import compare_cjk_chars
from .exporter import export_csv, export_json
from .fetcher import build_urls, fetch_html_cached, load_config
from .parser import extract_cjk_chars
from .report_generator import generate_report


def _safe_dir_token(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return safe or "document"


def _resolve_output_dir(doc_id: str, output_dir: Path | None) -> Path:
    safe_doc_id = _safe_dir_token(doc_id)

    if output_dir:
        has_cjk_compare = any(part.lower() == "cjk_compare" for part in output_dir.parts)
        base_dir = output_dir if has_cjk_compare else output_dir / "CJK_COMPARE"

        if base_dir.name.lower() == safe_doc_id.lower():
            return base_dir
        return base_dir / safe_doc_id

    return Path.home() / "Documents" / "CJK_COMPARE" / safe_doc_id


def _name_from_source(source: str, fallback: str) -> str:
    parsed = urlparse(source)
    candidate = Path(parsed.path).name if parsed.scheme and parsed.netloc else Path(source).name
    if not candidate:
        return fallback
    if "." not in candidate:
        return f"{candidate}.html"
    return candidate


def _store_source_html_files(
    *,
    output_dir: Path,
    original_html: str,
    revised_html: str,
    original_url: str,
    revised_url: str,
    log: Callable[[str], None] | None,
) -> tuple[Path, Path]:
    html_dir = output_dir / "html_files"
    html_dir.mkdir(parents=True, exist_ok=True)

    original_name = _name_from_source(original_url, "original.html")
    revised_name = _name_from_source(revised_url, "revised.html")

    original_path = html_dir / original_name
    revised_path = html_dir / revised_name

    original_path.write_text(original_html, encoding="utf-8")
    revised_path.write_text(revised_html, encoding="utf-8")

    if log:
        log(f"Original HTML saved: {original_path}")
        log(f"Revised HTML saved: {revised_path}")

    return original_path, revised_path


def _run_compare_core(
    doc_id: str,
    original_html: str,
    revised_html: str,
    original_url: str,
    revised_url: str,
    output_dir: Path | None = None,
    log: Callable[[str], None] | None = None,
) -> tuple[Path, dict]:
    def write_log(message: str) -> None:
        if log:
            log(message)

    reports_dir = _resolve_output_dir(doc_id, output_dir)
    write_log(f"Output directory: {reports_dir}")

    _store_source_html_files(
        output_dir=reports_dir,
        original_html=original_html,
        revised_html=revised_html,
        original_url=original_url,
        revised_url=revised_url,
        log=write_log,
    )

    write_log("Extracting CJK characters from original HTML...")
    original_chars = extract_cjk_chars(original_html)

    write_log("Extracting CJK characters from revised HTML...")
    revised_chars = extract_cjk_chars(revised_html)

    write_log("Comparing characters...")
    rows, summary = compare_cjk_chars(original_chars, revised_chars)

    write_log("Generating report...")
    report_path = generate_report(
        doc_id=doc_id,
        original_url=original_url,
        revised_url=revised_url,
        rows=rows,
        summary=summary,
        output_dir=reports_dir,
    )

    json_path = export_json(rows, summary, reports_dir, doc_id)
    csv_path = export_csv(rows, reports_dir, doc_id)

    write_log(f"Report generated: {report_path}")
    write_log(f"JSON exported: {json_path}")
    write_log(f"CSV exported: {csv_path}")
    return report_path, summary


def run_cjk_compare(
    doc_id: str,
    domain: str,
    force_fetch: bool = False,
    output_dir: Path | None = None,
    log: Callable[[str], None] | None = None,
) -> tuple[Path, dict]:
    def write_log(message: str) -> None:
        if log:
            log(message)

    base_dir = Path(__file__).resolve().parent
    config_path = base_dir / "config.json"

    write_log("Loading config...")
    config = load_config(config_path)
    timeout = int(config.get("timeout", 30))
    reports_dir = _resolve_output_dir(doc_id, output_dir)

    original_url, revised_url = build_urls(config, doc_id, domain)
    html_cache_dir = reports_dir / "html_files"
    original_cache_file = html_cache_dir / _name_from_source(original_url, "original.html")
    revised_cache_file = html_cache_dir / _name_from_source(revised_url, "revised.html")

    if force_fetch:
        write_log("Force fetch enabled. Refreshing local backup from server.")

    write_log(f"Loading original HTML (cache/server): {original_url}")
    original_html, original_from_cache = fetch_html_cached(
        url=original_url,
        timeout=timeout,
        cache_file=original_cache_file,
        force_fetch=force_fetch,
    )
    write_log(f"Original source: {'local backup' if original_from_cache else 'server'} ({original_cache_file})")

    write_log(f"Loading revised HTML (cache/server): {revised_url}")
    revised_html, revised_from_cache = fetch_html_cached(
        url=revised_url,
        timeout=timeout,
        cache_file=revised_cache_file,
        force_fetch=force_fetch,
    )
    write_log(f"Revised source: {'local backup' if revised_from_cache else 'server'} ({revised_cache_file})")

    return _run_compare_core(
        doc_id=doc_id,
        original_html=original_html,
        revised_html=revised_html,
        original_url=original_url,
        revised_url=revised_url,
        output_dir=output_dir,
        log=log,
    )


def run_cjk_compare_from_files(
    doc_id: str,
    original_file: Path,
    revised_file: Path,
    output_dir: Path | None = None,
    log: Callable[[str], None] | None = None,
) -> tuple[Path, dict]:
    def write_log(message: str) -> None:
        if log:
            log(message)

    write_log(f"Loading original HTML file: {original_file}")
    original_html = original_file.read_text(encoding="utf-8", errors="replace")

    write_log(f"Loading revised HTML file: {revised_file}")
    revised_html = revised_file.read_text(encoding="utf-8", errors="replace")

    return _run_compare_core(
        doc_id=doc_id,
        original_html=original_html,
        revised_html=revised_html,
        original_url=str(original_file),
        revised_url=str(revised_file),
        output_dir=output_dir,
        log=log,
    )

import datetime
import math
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT_FOLDER = r"D:\IMPACT"
OUTPUT_BASE = r"D:\SEARCH_API"
BATCH_SIZE = 250


def _existing_directory(path_value, label):
    path = Path(path_value).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"{label} is not a directory: {path}")
    return path


def fetch_doc_ids(
    from_date: datetime.datetime,
    output_folder_suffix: str = None,
    root_folder: str = None,
    output_folder: str = None,
):
    """Create batch lists for source directories modified on or after from_date."""
    scan_folder = _existing_directory(root_folder or ROOT_FOLDER, "Root folder")
    output_base = Path(output_folder or OUTPUT_BASE).expanduser()

    try:
        output_base.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OSError(f"Cannot create output folder {output_base}: {exc}") from exc
    if not output_base.is_dir():
        raise ValueError(f"Output folder is not a directory: {output_base}")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = output_folder_suffix or timestamp
    batch_output = output_base / f"BATCH_LISTS_{suffix}"
    batch_output.mkdir(parents=True, exist_ok=True)

    print(f"Fetching documents from: {scan_folder}")
    print(f"Modified on or after: {from_date}")

    doc_ids = []
    for candidate in sorted(scan_folder.iterdir(), key=lambda item: item.name.lower()):
        if not candidate.is_dir():
            continue
        try:
            modified = datetime.datetime.fromtimestamp(candidate.stat().st_mtime)
        except OSError as exc:
            print(f"Skipping unreadable directory {candidate.name}: {exc}")
            continue
        if modified >= from_date:
            doc_ids.append(candidate.name)

    batch_files = []
    for index in range(math.ceil(len(doc_ids) / BATCH_SIZE)):
        start_index = index * BATCH_SIZE
        subset = doc_ids[start_index : start_index + BATCH_SIZE]
        filename = f"{start_index + 1}_{start_index + len(subset)}.txt"
        batch_file = batch_output / filename
        batch_file.write_text("\n".join(subset), encoding="utf-8")
        batch_files.append(str(batch_file))

    print(f"Generated {len(batch_files)} batch file(s) in {batch_output}")
    return batch_files, str(batch_output)


def copy_files_for_batch(
    batch_file_path: str, root_folder: str = None, dest_root: str = None
):
    """Copy each batch document's updated HTML and IMPACT configuration XML."""
    batch_file = Path(batch_file_path).expanduser()
    if not batch_file.exists():
        raise FileNotFoundError(f"Batch file does not exist: {batch_file}")
    if not batch_file.is_file():
        raise ValueError(f"Batch file path is not a file: {batch_file}")

    source_root = _existing_directory(root_folder or ROOT_FOLDER, "Root folder")
    doc_ids = [line.strip() for line in batch_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not doc_ids:
        return 0, 0, 0, None

    destination = Path(dest_root).expanduser() if dest_root else (
        batch_file.parent / "BK_FILES" / batch_file.stem
    )
    destination.mkdir(parents=True, exist_ok=True)

    copied_count = 0
    skipped_count = 0
    for doc_id in doc_ids:
        source = source_root / doc_id
        if not source.is_dir():
            skipped_count += 1
            continue

        copied_any = False
        try:
            for html_file in source.glob("*_updated.html"):
                shutil.copy2(html_file, destination / f"{doc_id}_updated.html")
                copied_any = True

            xml_file = source / "impact_config.xml"
            if xml_file.is_file():
                shutil.copy2(xml_file, destination / f"{doc_id}_config.xml")
                copied_any = True
        except OSError as exc:
            print(f"Unable to copy files for {doc_id}: {exc}")

        if copied_any:
            copied_count += 1
        else:
            skipped_count += 1

    print(
        f"Copy completed: {copied_count} copied, {skipped_count} skipped, "
        f"{len(doc_ids)} total"
    )
    return copied_count, skipped_count, len(doc_ids), str(destination)


def parse_config(xml_path):
    """Extract result metadata; malformed XML is represented as unavailable."""
    try:
        root = ET.parse(xml_path).getroot()

        def get_tag(tag):
            element = root.find(tag)
            return element.text.strip() if element is not None and element.text else ""

        return get_tag("client"), get_tag("file-id"), []
    except (ET.ParseError, OSError):
        return "NA", "NA", []


def _normalize_search_terms(search_terms):
    search_map = {}
    for index, item in enumerate(search_terms or [], start=1):
        if isinstance(item, dict):
            for key, value in item.items():
                if str(value).strip():
                    search_map[str(key)] = str(value).strip()
        elif str(item).strip():
            search_map[f"term_{index}"] = str(item).strip()
    if not search_map:
        raise ValueError("At least one non-empty search term is required")
    return search_map


def search_in_batch(batch_folder: str, search_terms: list):
    """Return files containing any search term, using literal case-insensitive matching."""
    folder = _existing_directory(batch_folder, "Batch folder")
    search_map = _normalize_search_terms(search_terms)
    results = []

    for html_path in sorted(folder.glob("*_updated.html"), key=lambda item: item.name.lower()):
        doc_id = html_path.name[: -len("_updated.html")]
        xml_path = folder / f"{doc_id}_config.xml"
        if not xml_path.is_file():
            continue

        try:
            content = html_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            print(f"Unable to read {html_path.name}: {exc}")
            continue

        found_keys = [
            key
            for key, value in search_map.items()
            if re.search(re.escape(value), content, re.IGNORECASE)
        ]
        if not found_keys:
            continue

        client, file_id, emails = parse_config(xml_path)
        results.append(
            {
                "client": client,
                "file_id": file_id,
                "emails": emails,
                "found_keys": found_keys,
                "doc_id": doc_id,
            }
        )

    print(f"Search completed: {len(results)} matching document(s)")
    return results

"""Internal DTD-based folder organization subprocess."""
from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable

from .. import config
from .database import DocumentDatabase
from .utils import Logger


class DTDOrganizer:
    """Moves organized document folders into JATS or BITS subfolders."""

    SUPPORTED_DTDS = {"JATS", "BITS"}

    def __init__(
        self,
        database: DocumentDatabase,
        log_callback: Callable[[str], None] | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ):
        self.db = database
        self.project_path = database.project_path
        self.logger = Logger(
            database.project_path / config.LOG_FILE,
            console_callback=log_callback,
        )
        self.progress_callback = progress_callback

    def organize_by_dtd(self) -> tuple[int, int, int, int]:
        """Move document folders under JATS or BITS based on impact_config.xml.

        Returns:
            Tuple of (moved, skipped, failed, unknown_dtd).
        """
        documents = [
            (docid, doc)
            for docid, doc in sorted(self.db.get_all().items())
            if not docid.startswith("_")
        ]
        total = len(documents)
        moved = 0
        skipped = 0
        failed = 0
        unknown = 0

        self.logger.info("Starting internal DTD organization...")
        if total == 0:
            self.logger.info("No documents found in database.")
            return moved, skipped, failed, unknown

        for index, (docid, doc) in enumerate(documents, 1):
            if self.progress_callback:
                self.progress_callback(index, total)

            try:
                result = self._organize_document(docid, doc)
            except Exception as exc:
                self.db.mark_error(docid, "dtd_organize", str(exc))
                failed += 1
                self.logger.error(f"Failed DTD organization for {docid}: {exc}")
                continue

            if result == "moved":
                moved += 1
            elif result == "skipped":
                skipped += 1
            elif result == "unknown":
                unknown += 1
            else:
                failed += 1

        self.db.save()
        self.logger.info(
            "DTD organization complete. "
            f"Moved: {moved}, Skipped: {skipped}, Failed: {failed}, Unknown DTD: {unknown}"
        )
        return moved, skipped, failed, unknown

    def _organize_document(self, docid: str, doc: dict) -> str:
        doc_folder = self._resolve_document_folder(docid, doc)
        if not doc_folder:
            self.db.mark_error(docid, "dtd_organize", "Document folder not found")
            self.logger.error(f"Document folder not found for {docid}")
            return "failed"

        config_path = self._resolve_config_path(docid, doc, doc_folder)
        if not config_path:
            self.db.mark_error(docid, "dtd_organize", "impact_config.xml not found")
            self.logger.error(f"impact_config.xml not found for {docid}")
            return "failed"

        dtd = self._read_dtd(config_path)
        if dtd not in self.SUPPORTED_DTDS:
            self.db.mark_error(docid, "dtd_organize", f"Unsupported or missing DTD: {dtd or 'UNKNOWN'}")
            self.logger.warning(f"Unsupported or missing DTD for {docid}: {dtd or 'UNKNOWN'}")
            return "unknown"

        target_root = self.project_path / dtd
        target_folder = target_root / docid
        target_root.mkdir(exist_ok=True)

        if doc_folder.resolve() == target_folder.resolve():
            self._update_document_paths(docid, doc_folder, target_folder)
            self.db.clear_error(docid)
            self.logger.info(f"Skipped {docid} (already in {dtd})")
            return "skipped"

        if target_folder.exists():
            self.db.mark_error(docid, "dtd_organize", f"Destination already exists: {target_folder}")
            self.logger.error(f"Destination already exists for {docid}: {target_folder}")
            return "failed"

        shutil.move(str(doc_folder), str(target_folder))
        self._update_document_paths(docid, doc_folder, target_folder)
        self.db.clear_error(docid)
        self.logger.info(f"Moved {docid} to {dtd}/{docid}")
        return "moved"

    def _resolve_document_folder(self, docid: str, doc: dict) -> Path | None:
        candidates = []
        candidates.append(self.db.resolve_document_folder(docid, doc))
        candidates.extend([
            self.project_path / docid,
            self.project_path / "JATS" / docid,
            self.project_path / "BITS" / docid,
        ])

        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate.resolve()
        return None

    def _resolve_config_path(self, docid: str, doc: dict, doc_folder: Path) -> Path | None:
        candidates = []
        resolved_config = self.db.resolve_file_path(docid, "config_xml", doc)
        if resolved_config:
            candidates.append(resolved_config)
        candidates.extend([
            doc_folder / config.TARGET_NAMES["config_xml"],
            self.project_path / docid / config.TARGET_NAMES["config_xml"],
            self.project_path / "JATS" / docid / config.TARGET_NAMES["config_xml"],
            self.project_path / "BITS" / docid / config.TARGET_NAMES["config_xml"],
        ])

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate.resolve()
        return None

    @staticmethod
    def _read_dtd(config_path: Path) -> str:
        root = ET.parse(config_path).getroot()
        dtd_node = root.find(".//dtd")
        if dtd_node is None:
            return ""
        dtd = (dtd_node.get("name") or dtd_node.text or "").strip().upper()
        return dtd

    def _update_document_paths(self, docid: str, old_folder: Path, new_folder: Path) -> None:
        doc = self.db.get_document(docid)
        if not doc:
            return

        old_rel = old_folder.relative_to(self.project_path).as_posix()
        new_rel = new_folder.relative_to(self.project_path).as_posix()
        self.db.update_document(docid, {"folder": new_rel})

        files = doc.get("files", {})
        for key, value in list(files.items()):
            if not value:
                continue
            path = Path(value)
            if path.is_absolute():
                try:
                    relative_value = path.relative_to(old_folder).as_posix()
                except ValueError:
                    continue
                files[key] = f"{new_rel}/{relative_value}"
                continue

            normalized = Path(value).as_posix()
            if normalized == old_rel:
                files[key] = new_rel
            elif normalized.startswith(old_rel + "/"):
                files[key] = new_rel + normalized[len(old_rel):]
            elif (new_folder / Path(value).name).exists():
                files[key] = f"{new_rel}/{Path(value).name}"

        self.db.update_document(docid, {"files": files})

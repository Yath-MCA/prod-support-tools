"""Workflow preflight analysis for Document Manager v3."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import config
from .database import DocumentDatabase


class WorkflowAnalyzer:
    """Analyzes document readiness without changing workflow state."""

    REQUIRED_FILES = ("original_html", "original_xml", "updated_html")

    def __init__(self, database: DocumentDatabase):
        self.db = database
        self.project_path = database.project_path

    def analyze(self) -> dict[str, Any]:
        """Return project-level and per-document preflight details."""
        documents = []
        counts = {
            "total": 0,
            "complete": 0,
            "errored": 0,
            "blocked": 0,
            "ready_to_organize": 0,
            "ready_to_download": 0,
            "ready_to_compare": 0,
            "ready_to_report": 0,
            "missing_files": 0,
            "html_compare_blocked": 0,
        }

        for docid, doc in sorted(self.db.get_all().items()):
            if docid.startswith("_"):
                continue

            detail = self.analyze_document(docid, doc)
            documents.append(detail)
            counts["total"] += 1

            if detail["analysis_status"] == "complete":
                counts["complete"] += 1
            if detail["has_error"]:
                counts["errored"] += 1
            if detail["is_blocked"]:
                counts["blocked"] += 1
            if detail["ready_to_organize"]:
                counts["ready_to_organize"] += 1
            if detail["ready_to_download"]:
                counts["ready_to_download"] += 1
            if detail["ready_to_compare"]:
                counts["ready_to_compare"] += 1
            if detail["ready_to_report"]:
                counts["ready_to_report"] += 1
            if detail["missing_files"]:
                counts["missing_files"] += 1
            if detail["html_compare_blocked"]:
                counts["html_compare_blocked"] += 1

        return {
            "counts": counts,
            "documents": documents,
            "next_action": self._recommend_next_action(counts),
            "issues": [doc for doc in documents if doc["issue"]],
        }

    def analyze_document(self, docid: str, doc: dict[str, Any]) -> dict[str, Any]:
        """Analyze one document entry from documents.json."""
        files = doc.get("files", {})
        process = doc.get("process", {})

        file_status = {
            key: {
                "value": files.get(key),
                "exists": self._file_exists(docid, key, files.get(key)),
            }
            for key in ("original_html", "original_xml", "updated_html", "config_xml", "compare_report")
        }

        missing_files = [
            key for key in self.REQUIRED_FILES
            if not file_status[key]["exists"]
        ]

        organized = bool(process.get("organized", False))
        config_downloaded = bool(process.get("config_downloaded", False))
        compared = bool(process.get("compared", False))
        report_generated = bool(process.get("report_generated", False))
        has_error = bool(doc.get("error"))
        updated_value = files.get("updated_html") or ""
        html_compare_blocked = (
            organized
            and config_downloaded
            and file_status["original_xml"]["exists"]
            and file_status["updated_html"]["exists"]
            and Path(updated_value).suffix.lower() == ".html"
            and not compared
        )

        ready_to_organize = not has_error and not organized and not missing_files
        ready_to_download = not has_error and organized and not config_downloaded and not missing_files
        ready_to_compare = (
            not has_error
            and organized
            and config_downloaded
            and not missing_files
            and file_status["original_xml"]["exists"]
            and file_status["updated_html"]["exists"]
            and not compared
            and not html_compare_blocked
        )
        ready_to_report = not has_error and compared and not report_generated
        complete = organized and config_downloaded and compared and report_generated

        issue = self._build_issue(
            has_error=has_error,
            error=doc.get("error"),
            missing_files=missing_files,
            html_compare_blocked=html_compare_blocked,
            ready_to_organize=ready_to_organize,
            ready_to_download=ready_to_download,
            ready_to_compare=ready_to_compare,
            ready_to_report=ready_to_report,
            complete=complete,
        )
        is_blocked = bool(missing_files or html_compare_blocked)
        if has_error:
            status = "error"
        elif complete:
            status = "complete"
        elif is_blocked:
            status = "blocked"
        elif any((ready_to_organize, ready_to_download, ready_to_compare, ready_to_report)):
            status = "ready"
        else:
            status = "pending"

        return {
            "docid": docid,
            "analysis_status": status,
            "issue": issue,
            "is_blocked": is_blocked,
            "has_error": has_error,
            "missing_files": missing_files,
            "html_compare_blocked": html_compare_blocked,
            "ready_to_organize": ready_to_organize,
            "ready_to_download": ready_to_download,
            "ready_to_compare": ready_to_compare,
            "ready_to_report": ready_to_report,
            "file_status": file_status,
            "process": {
                "organized": organized,
                "config_downloaded": config_downloaded,
                "compared": compared,
                "report_generated": report_generated,
            },
            "error": doc.get("error") or "",
            "last_step": doc.get("last_step") or "",
            "retry_count": doc.get("retry_count", 0),
        }

    def _file_exists(self, docid: str, file_key: str, value: str | None) -> bool:
        if value:
            resolved_path = self.db.resolve_file_path(docid, file_key)
            if resolved_path and resolved_path.exists():
                return True

            source_key = {
                "original_html": "original_html",
                "original_xml": "original_xml",
                "updated_html": "updated_html",
            }.get(file_key)
            if source_key:
                source_path = self.project_path / config.SOURCE_FOLDERS[source_key] / value
                if source_path.exists():
                    return True

        if file_key == "config_xml":
            return (
                self.db.resolve_document_folder(docid) / config.TARGET_NAMES["config_xml"]
            ).exists()
        if file_key == "compare_report":
            doc_folder = self.db.resolve_document_folder(docid)
            if not doc_folder.exists():
                return False
            return any(doc_folder.glob("*_compare_*.html")) or any(doc_folder.glob("*report*.html"))

        return False

    @staticmethod
    def _build_issue(
        *,
        has_error: bool,
        error: str | None,
        missing_files: list[str],
        html_compare_blocked: bool,
        ready_to_organize: bool,
        ready_to_download: bool,
        ready_to_compare: bool,
        ready_to_report: bool,
        complete: bool,
    ) -> str:
        if has_error:
            return str(error)
        if missing_files:
            return "Missing " + ", ".join(missing_files)
        if html_compare_blocked:
            return "Compare blocked: updated HTML requires XML conversion support"
        if ready_to_organize:
            return "Ready to organize"
        if ready_to_download:
            return "Ready to download config"
        if ready_to_compare:
            return "Ready to compare"
        if ready_to_report:
            return "Ready to generate report"
        if complete:
            return ""
        return "Waiting for previous workflow step"

    @staticmethod
    def _recommend_next_action(counts: dict[str, int]) -> str:
        if counts["total"] == 0:
            return "Run Scan"
        if counts["missing_files"] > 0:
            return "Review missing source files"
        if counts["ready_to_organize"] > 0:
            return "Run Organize"
        if counts["ready_to_download"] > 0:
            return "Download Config"
        if counts["html_compare_blocked"] > 0:
            return "Review HTML compare blockers"
        if counts["ready_to_compare"] > 0:
            return "Run Compare"
        if counts["ready_to_report"] > 0:
            return "Generate Report"
        if counts["errored"] > 0:
            return "Review failed documents"
        if counts["complete"] == counts["total"]:
            return "Workflow complete"
        return "Analyze document status"

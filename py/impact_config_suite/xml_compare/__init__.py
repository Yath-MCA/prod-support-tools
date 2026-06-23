"""XML Compare package for comparing XML files with detailed diff reports.

This package provides comprehensive XML comparison functionality including:
- Text content comparison with inline diff highlighting
- Formatting change detection (tag/style changes without text changes)
- Attribute-level comparison for important XML attributes
- Structural change detection (node insertions, deletions, moves)
- Self-contained HTML reports with dark theme UI

Example:
    from xml_compare import CompareOptions, run_xml_compare
    from pathlib import Path

    options = CompareOptions(
        text_corrections=True,
        formatting_only=True,
        include_attributes=False,  # Expensive operation
    )

    report_path = run_xml_compare(
        original_path=Path("original.xml"),
        revised_path=Path("revised.xml"),
        options=options,
        output_dir=Path("./reports"),
    )
    print(f"Report saved to: {report_path}")
"""

from __future__ import annotations

from .models import (
    CompareOptions,
    CompareResult,
    CompareStatistics,
    TextDiff,
    FormatDiff,
    AttributeDiff,
    StructureDiff,
    DiffType,
)
from .pipeline import run_xml_compare, run_xml_compare_with_result
from .statistics import StatisticsBuilder
from .html_renderer import HtmlTemplateRenderer
from .report_builder import ReportBuilder

__version__ = "1.0.0"

__all__ = [
    # Main entry points
    "run_xml_compare",
    "run_xml_compare_with_result",
    # Data models
    "CompareOptions",
    "CompareResult",
    "CompareStatistics",
    "TextDiff",
    "FormatDiff",
    "AttributeDiff",
    "StructureDiff",
    "DiffType",
    # Report generation
    "StatisticsBuilder",
    "HtmlTemplateRenderer",
    "ReportBuilder",
]

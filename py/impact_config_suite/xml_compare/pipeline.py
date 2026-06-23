"""Pipeline module for orchestrating XML comparison.

This module provides the main entry point for running XML comparisons
with progress reporting and report generation.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

from .attribute_comparator import AttributeComparator
from .diff_engine import DiffEngine
from .models import CompareOptions, CompareResult
from .parser_service import XMLParserService
from .report_builder import ReportBuilder
from .statistics import StatisticsBuilder

if TYPE_CHECKING:
    pass


def run_xml_compare(
    original: Path,
    revised: Path,
    options: CompareOptions | None = None,
    output_dir: Path | None = None,
    log_callback: Callable[[str], None] | None = None,
) -> Path:
    """Run XML comparison and generate HTML report.

    This is the main entry point for the comparison pipeline. It parses
    both XML files, runs the diff engine, optionally compares attributes,
    generates statistics, and produces a self-contained HTML report.

    Args:
        original: Path to the original XML file
        revised: Path to the revised XML file
        options: Comparison options (uses defaults if None)
        output_dir: Directory for output report (defaults to revised file's parent)
        log_callback: Optional callback for progress messages

    Returns:
        Path to the generated HTML report

    Raises:
        FileNotFoundError: If original or revised file does not exist
        ValueError: If files cannot be parsed as valid XML
        RuntimeError: If comparison fails
    """
    if options is None:
        options = CompareOptions()

    if output_dir is None:
        output_dir = revised.parent

    if log_callback:
        log_callback("Initializing comparison pipeline...")

    # Initialize services (no constructor arguments needed)
    parser = XMLParserService()
    diff_engine = DiffEngine()
    attr_comparator = AttributeComparator()
    stats_builder = StatisticsBuilder()
    report_builder = ReportBuilder()

    if log_callback:
        log_callback("Parsing XML files...")

    # Parse both XML files
    original_tree = parser.parse_xml_with_entity_handling(original)
    revised_tree = parser.parse_xml_with_entity_handling(revised)

    if log_callback:
        log_callback("Computing differences...")

    # Run diff engine
    result = diff_engine.diff(original, revised, options)

    # Run attribute comparison if enabled
    if options.include_attributes:
        if log_callback:
            log_callback("Comparing attributes...")
        result.attribute_diffs = attr_comparator.compare(
            original_tree, revised_tree, options
        )
        # Recalculate statistics with attributes
        stats_builder.update_result_statistics(result)

    # Determine output path
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = f"{revised.stem}_compare_{timestamp}.html"
    output_path = output_dir / output_name

    if log_callback:
        log_callback("Generating HTML report...")

    # Build the report
    report_builder.build_report(result, output_path, use_streaming=True)

    result.output_path = output_path
    result.success = True

    if log_callback:
        log_callback(f"Report saved: {output_path}")

    return output_path


def run_xml_compare_simple(
    original: Path,
    revised: Path,
    options: CompareOptions | None = None,
) -> CompareResult:
    """Run XML comparison and return result without generating report.

    This is a lighter-weight entry point useful for programmatic
    comparisons where you only need the result data.

    Args:
        original: Path to the original XML file
        revised: Path to the revised XML file
        options: Comparison options (uses defaults if None)

    Returns:
        CompareResult with all differences and statistics

    Raises:
        FileNotFoundError: If files don't exist
        ValueError: If files are invalid XML
    """
    if options is None:
        options = CompareOptions()

    parser = XMLParserService()
    diff_engine = DiffEngine()
    attr_comparator = AttributeComparator()
    stats_builder = StatisticsBuilder()

    # Parse both XML files
    original_tree = parser.parse_xml_with_entity_handling(original)
    revised_tree = parser.parse_xml_with_entity_handling(revised)

    # Run diff
    result = diff_engine.diff(original, revised, options)

    # Add attribute comparison if enabled
    if options.include_attributes:
        result.attribute_diffs = attr_comparator.compare(
            original_tree, revised_tree, options
        )
        stats_builder.update_result_statistics(result)

    result.success = True
    return result


def run_xml_compare_with_result(
    original: Path,
    revised: Path,
    options: CompareOptions | None = None,
    output_dir: Path | None = None,
    log_callback: Callable[[str], None] | None = None,
) -> tuple[CompareResult, Path]:
    """Run XML comparison and return both result data and report path.

    This is the most complete entry point, returning both the full
    comparison result data and the path to the generated HTML report.

    Args:
        original: Path to the original XML file
        revised: Path to the revised XML file
        options: Comparison options (uses defaults if None)
        output_dir: Directory for output report (defaults to revised file's parent)
        log_callback: Optional callback for progress messages

    Returns:
        Tuple of (CompareResult, Path) containing the comparison data
        and the generated HTML report path

    Raises:
        FileNotFoundError: If original or revised file does not exist
        ValueError: If files cannot be parsed as valid XML
        RuntimeError: If comparison fails
    """
    report_path = run_xml_compare(original, revised, options, output_dir, log_callback)
    result = run_xml_compare_simple(original, revised, options)
    return result, report_path

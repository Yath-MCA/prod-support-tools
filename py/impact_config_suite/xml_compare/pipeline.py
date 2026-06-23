"""Pipeline module for orchestrating XML comparison.

This module provides the main entry point for running XML comparisons,
orchestrating parser_service, diff_engine, attribute_comparator,
statistics, and html_renderer to produce comprehensive HTML reports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional
from datetime import datetime

from .models import CompareOptions, CompareResult
from .parser_service import XMLParserService
from .diff_engine import DiffEngine
from .attribute_comparator import AttributeComparator
from .statistics import StatisticsBuilder
from .html_renderer import HtmlTemplateRenderer


def run_xml_compare(
    original_path: Path,
    revised_path: Path,
    options: CompareOptions,
    output_dir: Path,
    log_callback: Optional[Callable[[str], None]] = None,
) -> Path:
    """Run full comparison pipeline and return report path.

    Orchestrates the complete XML comparison workflow:
    1. Parse both XML files with entity handling
    2. Run diff_engine to classify changes (text, formatting, structure)
    3. Run attribute_comparator if include_attributes is enabled
    4. Generate statistics
    5. Build HTML report using html_renderer

    This function is thread-safe and makes no tk calls internally.
    All UI updates should be done via the log_callback.

    Args:
        original_path: Path to the original XML file
        revised_path: Path to the revised XML file
        options: Comparison options controlling what to compare
        output_dir: Directory where the HTML report will be saved
        log_callback: Optional callback for progress messages (thread-safe)

    Returns:
        Path to the generated HTML report file

    Raises:
        FileNotFoundError: If original or revised file does not exist
        ValueError: If files are not valid XML
        Exception: For other processing errors (message passed to log_callback)
    """

    def log(message: str) -> None:
        """Helper to log messages via callback if provided."""
        if log_callback:
            log_callback(message)

    log(f"Starting XML comparison pipeline")
    log(f"Original file: {original_path}")
    log(f"Revised file: {revised_path}")
    log(f"Output directory: {output_dir}")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{revised_path.stem}_compare_{timestamp}.html"
    output_path = output_dir / output_filename

    log(f"Report will be saved to: {output_filename}")

    # Step 1: Parse both XML files
    log("Parsing XML files...")
    parser_service = XMLParserService()
    left_tree, right_tree = parser_service.parse_both_files(
        original_path, revised_path
    )
    log("XML parsing complete")

    # Step 2: Run diff engine
    log("Running diff engine to detect changes...")
    diff_engine = DiffEngine()
    result = diff_engine.diff(original_path, revised_path, options)
    log(f"Diff engine found {result.statistics.total_differences} differences")

    # Step 3: Run attribute comparator if enabled
    if options.include_attributes:
        log("Running attribute comparison (this may take longer)...")
        attr_comparator = AttributeComparator()
        attr_comparator.compare_and_update_result(left_tree, right_tree, result)
        log(f"Attribute comparison found {len(result.attribute_diffs)} attribute changes")
    else:
        log("Attribute comparison skipped (disabled in options)")

    # Step 4: Update statistics with final counts
    log("Calculating final statistics...")
    stats_builder = StatisticsBuilder()
    stats_builder.update_result_statistics(result)
    stats = result.statistics
    log(f"Match percentage: {stats.match_percentage:.1f}%")
    log(f"Total differences: {stats.total_differences}")
    log(f"  - Text changes: {stats.text_changes}")
    log(f"  - Formatting changes: {stats.formatting_changes}")
    log(f"  - Attribute changes: {stats.attribute_changes}")
    log(f"  - Structure changes: {stats.structure_changes}")

    # Step 5: Generate HTML report
    log("Generating HTML report...")
    renderer = HtmlTemplateRenderer()
    renderer.render_to_file(result, options, output_path)
    log(f"Report generated successfully: {output_path}")

    return output_path


def run_xml_compare_with_result(
    original_path: Path,
    revised_path: Path,
    options: Optional[CompareOptions] = None,
    output_dir: Optional[Path] = None,
    log_callback: Optional[Callable[[str], None]] = None,
) -> CompareResult:
    """Run comparison and return full result object with report path.

    Similar to run_xml_compare but returns the full CompareResult
    for programmatic access to the comparison data.

    Args:
        original_path: Path to the original XML file
        revised_path: Path to the revised XML file
        options: Comparison options (uses defaults if None)
        output_dir: Directory for output report (defaults to revised file's directory)
        log_callback: Optional callback for progress messages

    Returns:
        CompareResult with all diff data and output_path set to the HTML report
    """
    if options is None:
        options = CompareOptions()

    if output_dir is None:
        output_dir = revised_path.parent

    try:
        output_path = run_xml_compare(
            original_path=original_path,
            revised_path=revised_path,
            options=options,
            output_dir=output_dir,
            log_callback=log_callback,
        )

        # Parse both files to get the result
        parser_service = XMLParserService()
        left_tree, right_tree = parser_service.parse_both_files(
            original_path, revised_path
        )

        # Run full pipeline to get result
        diff_engine = DiffEngine()
        result = diff_engine.diff(original_path, revised_path, options)

        # Run attribute comparator if enabled
        if options.include_attributes:
            attr_comparator = AttributeComparator()
            attr_comparator.compare_and_update_result(left_tree, right_tree, result)

        # Update statistics
        stats_builder = StatisticsBuilder()
        stats_builder.update_result_statistics(result)

        # Set output path and success
        result.output_path = output_path
        result.success = True

        return result

    except Exception as exc:
        # Return failed result
        return CompareResult(
            original_path=original_path,
            revised_path=revised_path,
            output_path=None,
            success=False,
            error_message=str(exc),
        )

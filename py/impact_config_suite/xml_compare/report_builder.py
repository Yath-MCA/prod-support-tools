"""ReportBuilder for orchestrating the XML comparison pipeline."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .attribute_comparator import AttributeComparator
from .diff_engine import DiffEngine
from .html_renderer import HtmlTemplateRenderer
from .parser_service import XMLParserService
from .statistics import StatisticsBuilder

if TYPE_CHECKING:
    from .models import CompareOptions, CompareResult


class ReportBuilder:
    """Builder for orchestrating XML comparison and report generation.

    This class coordinates the full pipeline: parsing, diffing, attribute
    comparison, statistics calculation, and HTML report generation.
    """

    def __init__(
        self,
        parser_service: XMLParserService | None = None,
        diff_engine: DiffEngine | None = None,
        attr_comparator: AttributeComparator | None = None,
        stats_builder: StatisticsBuilder | None = None,
        html_renderer: HtmlTemplateRenderer | None = None,
    ):
        """Initialize the report builder with optional component overrides."""
        self.parser = parser_service or XMLParserService()
        self.diff_engine = diff_engine or DiffEngine(self.parser)
        self.attr_comparator = attr_comparator or AttributeComparator()
        self.stats_builder = stats_builder or StatisticsBuilder()
        self.html_renderer = html_renderer or HtmlTemplateRenderer()

    def build_report(
        self,
        original_path: Path,
        revised_path: Path,
        options: CompareOptions | None = None,
        output_dir: Path | None = None,
    ) -> Path:
        """Build full comparison report.

        Args:
            original_path: Path to original XML file
            revised_path: Path to revised XML file
            options: Comparison options (defaults if None)
            output_dir: Output directory (defaults to revised file's directory)

        Returns:
            Path to generated HTML report
        """
        if options is None:
            from .models import CompareOptions

            options = CompareOptions()

        if output_dir is None:
            output_dir = revised_path.parent

        # Parse both files
        original_tree = self.parser.parse_xml_with_entity_handling(original_path)
        revised_tree = self.parser.parse_xml_with_entity_handling(revised_path)

        # Run diff classification
        result = self.diff_engine.diff(original_path, revised_path, options)

        # Run attribute comparison if enabled
        if options.include_attributes:
            result.attribute_diffs = self.attr_comparator.compare(
                original_tree, revised_tree, options
            )
            # Recalculate statistics with attribute diffs
            self.stats_builder.update_result_statistics(result)

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"{revised_path.stem}_compare_{timestamp}.html"
        output_path = output_dir / output_name

        # Write report (streaming to avoid memory issues)
        result.output_path = output_path
        self.html_renderer.render_to_file(result, options, output_path)

        return output_path

    def build_report_streaming(
        self,
        original_path: Path,
        revised_path: Path,
        options: CompareOptions,
        output_path: Path,
        progress_callback: callable | None = None,
    ) -> CompareResult:
        """Build report with progress callback for large files.

        Args:
            original_path: Path to original XML file
            revised_path: Path to revised XML file
            options: Comparison options
            output_path: Path for output HTML
            progress_callback: Optional callback(text) for progress updates

        Returns:
            CompareResult with all comparison data
        """
        if progress_callback:
            progress_callback("Parsing original XML...")

        original_tree = self.parser.parse_xml_with_entity_handling(original_path)

        if progress_callback:
            progress_callback("Parsing revised XML...")

        revised_tree = self.parser.parse_xml_with_entity_handling(revised_path)

        if progress_callback:
            progress_callback("Running diff comparison...")

        result = self.diff_engine.diff(original_path, revised_path, options)

        if options.include_attributes:
            if progress_callback:
                progress_callback("Comparing attributes...")
            result.attribute_diffs = self.attr_comparator.compare(
                original_tree, revised_tree, options
            )
            self.stats_builder.update_result_statistics(result)

        if progress_callback:
            progress_callback("Generating HTML report...")

        result.output_path = output_path
        self.html_renderer.render_to_file(result, options, output_path)

        if progress_callback:
            progress_callback(f"Report saved: {output_path}")

        return result

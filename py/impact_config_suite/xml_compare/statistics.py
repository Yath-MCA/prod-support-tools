"""StatisticsBuilder for calculating comparison statistics."""

from __future__ import annotations

from lxml import etree

from .models import CompareResult, CompareStatistics


class StatisticsBuilder:
    """Builder for calculating XML comparison statistics.

    This class computes summary statistics from a comparison result,
    including match percentages, change counts, and node totals.
    """

    def build(
        self,
        result: CompareResult,
        original_tree: etree.ElementTree | None = None,
        revised_tree: etree.ElementTree | None = None,
    ) -> CompareStatistics:
        """Build statistics from comparison result.

        Args:
            result: The comparison result containing diffs
            original_tree: Optional original tree for node counting
            revised_tree: Optional revised tree for node counting

        Returns:
            CompareStatistics with all computed values
        """
        stats = CompareStatistics()

        # Calculate total nodes if trees are provided, otherwise use result's value
        if original_tree is not None and revised_tree is not None:
            total_original = len(original_tree.xpath("//*"))
            total_revised = len(revised_tree.xpath("//*"))
            stats.total_nodes = (total_original + total_revised) // 2
        elif result.statistics and result.statistics.total_nodes > 0:
            stats.total_nodes = result.statistics.total_nodes

        stats.text_changes = len(result.text_diffs)
        stats.format_changes = len(result.format_diffs)
        stats.attribute_changes = len(result.attribute_diffs)
        stats.structure_changes = len(result.structure_diffs)

        for sd in result.structure_diffs:
            if sd.change_type == "added":
                stats.added_nodes += 1
            elif sd.change_type == "deleted":
                stats.deleted_nodes += 1
            elif sd.change_type == "moved":
                stats.moved_nodes += 1

        total_diffs = (
            stats.text_changes
            + stats.format_changes
            + stats.structure_changes
            + stats.attribute_changes
        )
        stats.total_differences = total_diffs

        # Calculate match percentage
        if stats.total_nodes > 0:
            unchanged = max(0, stats.total_nodes - total_diffs)
            stats.match_percentage = (unchanged / stats.total_nodes) * 100
        else:
            stats.match_percentage = 100.0

        return stats

    def update_result_statistics(self, result: CompareResult) -> None:
        """Recalculate and update statistics in a CompareResult in place."""
        stats = CompareStatistics()

        stats.text_changes = len(result.text_diffs)
        stats.format_changes = len(result.format_diffs)
        stats.attribute_changes = len(result.attribute_diffs)
        stats.structure_changes = len(result.structure_diffs)

        for sd in result.structure_diffs:
            if sd.change_type == "added":
                stats.added_nodes += 1
            elif sd.change_type == "deleted":
                stats.deleted_nodes += 1
            elif sd.change_type == "moved":
                stats.moved_nodes += 1

        stats.total_differences = (
            stats.text_changes
            + stats.format_changes
            + stats.structure_changes
            + stats.attribute_changes
        )

        # Preserve total_nodes from existing statistics if available
        if result.statistics and result.statistics.total_nodes > 0:
            stats.total_nodes = result.statistics.total_nodes
            
            # Calculate match percentage
            unchanged = max(0, stats.total_nodes - stats.total_differences)
            stats.match_percentage = (unchanged / stats.total_nodes) * 100
        else:
            stats.match_percentage = 100.0

        result.statistics = stats

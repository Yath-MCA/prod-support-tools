"""Service layer for element extraction operations."""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure core module can be imported
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.element_extractor import ElementExtractor


class ExtractionService:
    """Service layer for element extraction operations."""

    def __init__(self):
        self.extractor = ElementExtractor()

    def extract_from_folder(
        self,
        source_path: str,
        query_type: str,
        queries: List[str],
        recursive: bool = True,
        extensions: List[str] = None,
        filename_filter: Optional[str] = None,
        dtd_filter: Optional[str] = None,
        client_filter: Optional[str] = None,
        month_filter: str = "All Time",
        custom_month: str = "",
        batch_size: int = 0,
        batch_offset: int = 0,
        use_parallel: bool = True,
        max_workers: Optional[int] = None,
        output_dir: Optional[str] = None,
        attr_name: str = "",
        attr_val: str = ""
    ) -> Dict[str, Any]:
        """
        Extract elements from files in a folder.

        Args:
            source_path: Path to folder containing files to scan
            query_type: Query type ("Tag Name", "CSS Selector", "XPath")
            queries: List of queries to execute
            recursive: Scan subdirectories recursively
            extensions: File extensions to scan (default: ['.xml', '.html', '.htm', '.xhtml'])
            filename_filter: Filename pattern filter
            dtd_filter: DTD type filter
            client_filter: Client filter
            month_filter: Modified date filter ("All Time", "This Month", "Last Month", "Custom")
            custom_month: Custom month string when month_filter is "Custom"
            batch_size: Batch size (0 = no limit)
            batch_offset: Batch offset for resuming
            use_parallel: Use parallel processing
            max_workers: Number of parallel workers
            output_dir: Directory for report output
            attr_name: Attribute name filter (for Tag Name queries)
            attr_val: Attribute value filter (for Tag Name queries)

        Returns:
            Dict with extraction results, report paths, and metadata
        """
        if extensions is None:
            extensions = ['.xml', '.html', '.htm', '.xhtml']

        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source path not found: {source_path}")
        if not source_path.is_dir():
            raise ValueError(f"Source path is not a directory: {source_path}")

        # Build extraction config
        extraction_config = {
            "source_path": str(source_path),
            "query_type": query_type,
            "queries": queries,
            "recursive": recursive,
            "extensions": extensions,
            "filename_filter": filename_filter,
            "dtd_filter": dtd_filter,
            "client_filter": client_filter,
            "month_filter": month_filter,
            "custom_month": custom_month,
            "batch_size": batch_size,
            "batch_offset": batch_offset,
            "use_parallel": use_parallel,
            "max_workers": max_workers,
        }

        # Collect all_selector_results for report generation
        all_selector_results = []

        # Process each query
        total_matches = 0
        total_files = 0
        has_more = False
        next_offset = batch_offset

        for query in queries:
            query = query.strip()
            if not query:
                continue

            # Determine extraction method
            if use_parallel and batch_size > 0:
                # Parallel batch processing
                scan_results, matches, files, query_has_more, query_next_offset = \
                    self.extractor.scan_directory_parallel(
                        source_path,
                        query_type,
                        query,
                        attr_name=attr_name,
                        attr_val=attr_val,
                        extensions=extensions,
                        filename_filter=filename_filter,
                        dtd_filter=dtd_filter,
                        client_filter=client_filter,
                        month_filter=month_filter,
                        custom_month=custom_month,
                        batch_size=batch_size,
                        batch_offset=batch_offset,
                        max_workers=max_workers,
                        recursive=recursive
                    )
                has_more = query_has_more
                next_offset = query_next_offset
            elif use_parallel:
                # Parallel full scan
                scan_results, matches, files, query_has_more, query_next_offset = \
                    self.extractor.scan_directory_parallel(
                        source_path,
                        query_type,
                        query,
                        attr_name=attr_name,
                        attr_val=attr_val,
                        extensions=extensions,
                        filename_filter=filename_filter,
                        dtd_filter=dtd_filter,
                        client_filter=client_filter,
                        month_filter=month_filter,
                        custom_month=custom_month,
                        batch_size=batch_size,
                        batch_offset=batch_offset,
                        max_workers=max_workers,
                        recursive=recursive
                    )
                has_more = query_has_more
                next_offset = query_next_offset
            elif batch_size > 0:
                # Sequential batch processing
                scan_results, matches, files, query_has_more, query_next_offset = \
                    self.extractor.scan_directory_batch(
                        source_path,
                        query_type,
                        query,
                        attr_name=attr_name,
                        attr_val=attr_val,
                        extensions=extensions,
                        filename_filter=filename_filter,
                        dtd_filter=dtd_filter,
                        client_filter=client_filter,
                        month_filter=month_filter,
                        custom_month=custom_month,
                        batch_size=batch_size,
                        batch_offset=batch_offset
                    )
                has_more = query_has_more
                next_offset = query_next_offset
            else:
                # Sequential full scan
                scan_results, matches, files = self.extractor.scan_directory(
                    source_path,
                    query_type,
                    query,
                    attr_name=attr_name,
                    attr_val=attr_val,
                    recursive=recursive,
                    extensions=extensions,
                    filename_filter=filename_filter,
                    dtd_filter=dtd_filter,
                    client_filter=client_filter,
                    month_filter=month_filter,
                    custom_month=custom_month
                )

            all_selector_results.append({
                "query_val": query,
                "query_type": query_type,
                "scan_results": scan_results,
                "total_matches": matches,
                "total_files": files
            })

            total_matches += matches
            total_files += files

        # Generate reports if output_dir provided
        report_paths = []
        if output_dir:
            output_dir_path = Path(output_dir)
            try:
                output_dir_path.mkdir(parents=True, exist_ok=True)
                report_paths = self._generate_reports(
                    all_selector_results,
                    output_dir_path,
                    source_path,
                    query_type,
                    queries
                )
            except OSError as e:
                # Don't fail extraction if report generation fails
                report_paths = [f"Error generating reports: {e}"]

        # Build results dict
        results = {
            "config": extraction_config,
            "all_selector_results": all_selector_results,
            "total_files": total_files,
            "total_matches": total_matches,
            "has_more": has_more,
            "next_offset": next_offset,
            "report_paths": report_paths if report_paths else None
        }

        return results

    def extract_from_file(
        self,
        file_path: str,
        query_type: str,
        queries: List[str],
        attr_name: str = "",
        attr_val: str = ""
    ) -> Dict[str, Any]:
        """
        Extract elements from a single file.

        Args:
            file_path: Path to single file to extract from
            query_type: Query type ("Tag Name", "CSS Selector", "XPath")
            queries: List of queries to execute
            attr_name: Attribute name filter (for Tag Name queries)
            attr_val: Attribute value filter (for Tag Name queries)

        Returns:
            Dict with extraction results
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        all_results = []
        for query in queries:
            query = query.strip()
            if not query:
                continue

            matches = self.extractor.parse_and_extract(
                file_path, query_type, query, attr_name, attr_val
            )
            all_results.append({
                "query": query,
                "query_type": query_type,
                "matches": matches,
                "count": len(matches)
            })

        return {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "queries": all_results,
            "total_matches": sum(r["count"] for r in all_results)
        }

    def _generate_reports(
        self,
        all_selector_results: List[Dict],
        output_dir: Path,
        source_path: Path,
        query_type: str,
        queries: List[str]
    ) -> List[str]:
        """Generate HTML and CSV reports."""
        from datetime import datetime
        import csv

        report_paths = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_name = source_path.name or str(source_path)

        # Calculate total matches and files
        total_matches = sum(
            r.get("total_matches", 0) for r in all_selector_results
        )
        total_files = max(
            (r.get("total_files", 0) for r in all_selector_results),
            default=0
        )

        # Generate HTML report
        try:
            html_report = self.extractor.generate_html_report(
                str(source_path),
                query_type,
                queries[0] if queries else "",
                "",  # attr_name
                "",  # attr_val
                all_selector_results,
                total_matches,
                total_files,
                is_single_file=False
            )

            html_path = output_dir / f"Extraction_Report_{timestamp}.html"
            html_path.write_text(html_report, encoding="utf-8")
            report_paths.append(str(html_path))
        except Exception as e:
            report_paths.append(f"Error generating HTML report: {e}")

        # Generate CSV report
        try:
            csv_path = output_dir / f"Extraction_Report_{timestamp}.csv"
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'selector', 'query_type', 'file_path', 'file_name',
                    'instance_no', 'line', 'tag', 'inner_text', 'outer_xml'
                ])

                for selector_data in all_selector_results:
                    query_val = selector_data.get('query_val', '')
                    query_type = selector_data.get('query_type', '')
                    scan_results = selector_data.get('scan_results', {})

                    for file_path_str, data in scan_results.items():
                        if not data.get('ok', True):
                            continue
                        matches = data.get('matches', [])
                        if not matches:
                            continue

                        file_name = os.path.basename(file_path_str)
                        for idx, match in enumerate(matches, 1):
                            writer.writerow([
                                query_val,
                                query_type,
                                file_path_str,
                                file_name,
                                idx,
                                match.get('line', ''),
                                match.get('tag', ''),
                                match.get('text', ''),
                                match.get('html', '')
                            ])

            report_paths.append(str(csv_path))
        except Exception as e:
            report_paths.append(f"Error generating CSV report: {e}")

        return report_paths


# Singleton instance
extraction_service = ExtractionService()

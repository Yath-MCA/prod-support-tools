"""
Document Manager v3 - CLI Entry Point

Modes:
    scan        - Scan source folders and build documents.json
    folder      - Organize files into per-document folders
    download    - Download config XML files from backend
    compare     - Run XML comparison for all documents
    report      - Generate summary reports (HTML, CSV)
    complete    - Run complete workflow (all steps)

Usage:
    python manage_documents.py <project_path> <mode>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Import modules
from manage_documents_v3.modules.database import DocumentDatabase
from manage_documents_v3.modules.scanner import DocumentScanner
from manage_documents_v3.modules.organizer import FolderOrganizer
from manage_documents_v3.modules.downloader import ConfigDownloader
from manage_documents_v3.modules.comparer import CompareManager
from manage_documents_v3.modules.reporter import ReportManager

# Import CompareOptions for comparison mode
try:
    from xml_compare.models import CompareOptions
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from xml_compare.models import CompareOptions


def banner():
    """Print application banner."""
    print("=" * 60)
    print("Document Manager v3")
    print("=" * 60)


def scan_command(project_path: Path) -> int:
    """Execute scan command."""
    print(f"\nScanning project: {project_path}")
    
    db = DocumentDatabase(project_path)
    scanner = DocumentScanner(db, log_callback=print)
    count = scanner.scan()
    
    print(f"\nScan complete. Found {count} documents.")
    return 0 if count > 0 else 1


def folder_command(project_path: Path) -> int:
    """Execute folder/organize command."""
    print(f"\nOrganizing project: {project_path}")
    
    db = DocumentDatabase(project_path)
    organizer = FolderOrganizer(db, log_callback=print)
    success, failed = organizer.organize()
    
    print(f"\nOrganization complete.")
    print(f"  Successful: {success}")
    print(f"  Failed: {failed}")
    
    return 0 if failed == 0 else 1


def download_command(project_path: Path) -> int:
    """Execute download command."""
    print(f"\nDownloading configs for: {project_path}")
    
    db = DocumentDatabase(project_path)
    downloader = ConfigDownloader(db, log_callback=print)
    success, skipped, failed = downloader.download_all()
    
    print(f"\nDownloads complete.")
    print(f"  Successful: {success}")
    print(f"  Skipped (already exist): {skipped}")
    print(f"  Failed: {failed}")
    
    return 0 if failed == 0 else 1


def compare_command(project_path: Path) -> int:
    """Execute compare command."""
    print(f"\nComparing documents in: {project_path}")
    
    db = DocumentDatabase(project_path)
    comparer = CompareManager(db, log_callback=print)
    options = CompareOptions()
    success, skipped, failed = comparer.compare_all(options=options)
    
    print(f"\nComparisons complete.")
    print(f"  Successful: {success}")
    print(f"  Skipped (already done): {skipped}")
    print(f"  Failed: {failed}")
    
    return 0 if failed == 0 else 1


def report_command(project_path: Path) -> int:
    """Execute report command."""
    print(f"\nGenerating reports for: {project_path}")
    
    db = DocumentDatabase(project_path)
    reporter = ReportManager(db, log_callback=print)
    
    html_path = reporter.generate_html_summary()
    csv_path = reporter.generate_csv()
    
    print(f"\nReports generated:")
    print(f"  HTML: {html_path}")
    print(f"  CSV: {csv_path}")
    
    return 0


def complete_command(project_path: Path) -> int:
    """Execute complete workflow command."""
    print(f"\nRunning complete workflow for: {project_path}")
    print("=" * 60)
    
    db = DocumentDatabase(project_path)
    
    # Step 1: Scan
    print("\n[1/5] Scanning...")
    scanner = DocumentScanner(db, log_callback=print)
    scan_count = scanner.scan()
    print(f"Found {scan_count} documents")
    
    # Step 2: Organize
    print("\n[2/5] Organizing...")
    organizer = FolderOrganizer(db, log_callback=print)
    org_success, org_failed = organizer.organize()
    print(f"Organized: {org_success} success, {org_failed} failed")
    
    # Step 3: Download
    print("\n[3/5] Downloading configs...")
    downloader = ConfigDownloader(db, log_callback=print)
    dl_success, dl_skipped, dl_failed = downloader.download_all()
    print(f"Downloads: {dl_success} success, {dl_skipped} skipped, {dl_failed} failed")
    
    # Step 4: Compare
    print("\n[4/5] Comparing...")
    comparer = CompareManager(db, log_callback=print)
    options = CompareOptions()
    comp_success, comp_skipped, comp_failed = comparer.compare_all(options=options)
    print(f"Comparisons: {comp_success} success, {comp_skipped} skipped, {comp_failed} failed")
    
    # Step 5: Report
    print("\n[5/5] Generating reports...")
    reporter = ReportManager(db, log_callback=print)
    html_path = reporter.generate_html_summary()
    csv_path = reporter.generate_csv()
    print(f"Reports: {html_path}, {csv_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print("WORKFLOW COMPLETE")
    print("=" * 60)
    stats = db.get_statistics()
    print(f"Total documents: {stats['total']}")
    print(f"Organized: {stats['steps']['organized']}")
    print(f"Downloaded: {stats['steps']['config_downloaded']}")
    print(f"Compared: {stats['steps']['compared']}")
    print(f"With errors: {stats['with_errors']}")
    
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Document Manager v3 - Manage and process document workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  scan      - Scan source folders and build documents.json database
  folder    - Organize files into per-document folders
  download  - Download config XML files from backend
  compare   - Run XML comparison for all documents
  report    - Generate HTML and CSV summary reports
  complete  - Run complete workflow (all steps above)

Examples:
  python manage_documents.py C:/Projects/MyProject scan
  python manage_documents.py C:/Projects/MyProject complete
        """
    )
    
    parser.add_argument(
        "project",
        type=str,
        help="Path to project folder",
    )
    parser.add_argument(
        "mode",
        choices=["scan", "folder", "download", "compare", "report", "complete"],
        help="Operation mode",
    )
    
    args = parser.parse_args()
    
    # Resolve project path
    project_path = Path(args.project).resolve()
    if not project_path.exists():
        print(f"Error: Project folder not found: {project_path}")
        sys.exit(1)
    
    banner()
    print(f"Project: {project_path}")
    print(f"Mode: {args.mode}")
    
    # Execute command
    commands = {
        "scan": scan_command,
        "folder": folder_command,
        "download": download_command,
        "compare": compare_command,
        "report": report_command,
        "complete": complete_command,
    }
    
    try:
        exit_code = commands[args.mode](project_path)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user.")
        print("Resume support: Run the same command again to continue.")
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Config File Downloader - Command Line Script

Download config XML files in batches using multi-threaded processing.
Supports up to 100 files per batch with parallel workers.

Usage:
    python scripts/download_configs.py <project_path> [options]

Options:
    --workers N       Number of parallel download threads (default: 4)
    --batch-size N    Files per batch (default: 25, max: 100)
    --force           Download even if files already exist
    --sequential      Use sequential mode instead of threaded
    --url URL         Custom base URL for downloads

Examples:
    # Download with defaults (25 files/batch, 4 workers)
    python scripts/download_configs.py C:/path/to/project

    # Download 100 files per batch with 8 workers
    python scripts/download_configs.py C:/path/to/project --batch-size 100 --workers 8

    # Force re-download all configs
    python scripts/download_configs.py C:/path/to/project --force
"""
from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path
from typing import Callable

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from manage_documents_v3.modules.database import DocumentDatabase
from manage_documents_v3.modules.downloader import ConfigDownloader
from manage_documents_v3 import config


def print_progress(completed: int, total: int, successful: int, failed: int) -> None:
    """Print batch progress to console."""
    percent = (completed / total * 100) if total > 0 else 0
    bar_length = 40
    filled = int(bar_length * percent / 100)
    bar = "=" * filled + "-" * (bar_length - filled)
    print(f"\r[{bar}] {percent:5.1f}% | {completed}/{total} | OK:{successful} Failed:{failed}", end="", flush=True)


def download_configs(
    project_path: Path,
    workers: int = 4,
    batch_size: int = 25,
    force: bool = False,
    sequential: bool = False,
    base_url: str | None = None,
) -> int:
    """Download config files for all pending documents.
    
    Args:
        project_path: Path to project directory with documents.json
        workers: Number of parallel download threads
        batch_size: Files to process per batch (max 100)
        force: Download even if files already exist
        sequential: Use sequential mode instead of threaded
        base_url: Custom base URL for downloads
        
    Returns:
        Exit code (0 = success, 1 = failure)
    """
    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}", file=sys.stderr)
        return 1
    
    if not project_path.is_dir():
        print(f"Error: Project path is not a directory: {project_path}", file=sys.stderr)
        return 1
    
    # Cap batch size at 100
    batch_size = min(batch_size, 100)
    
    print("=" * 60)
    print("Config File Downloader")
    print("=" * 60)
    print(f"Project: {project_path}")
    print(f"Mode: {'Sequential' if sequential else 'Threaded (workers=' + str(workers) + ')'}")
    print(f"Batch size: {batch_size}")
    print(f"Force re-download: {'Yes' if force else 'No'}")
    if base_url:
        print(f"Base URL: {base_url}")
    print("-" * 60)
    
    # Initialize database
    db = DocumentDatabase(project_path)
    pending = db.get_pending("config_downloaded")
    total_pending = len(pending)
    
    if total_pending == 0:
        print("\nNo documents need config download.")
        return 0
    
    print(f"\nFound {total_pending} documents needing config download.")
    
    # Create downloader
    downloader = ConfigDownloader(db, log_callback=print)
    
    # Track results
    lock = threading.Lock()
    final_results = {"successful": 0, "skipped": 0, "failed": 0}
    
    def batch_callback(completed: int, total: int, successful: int, failed: int) -> None:
        """Callback for batch progress updates."""
        print_progress(completed, total, successful, failed)
        with lock:
            final_results["successful"] = successful
            final_results["skipped"] = 0  # Threaded mode doesn't track skipped
            final_results["failed"] = failed
    
    print("\nStarting download...")
    
    if sequential:
        # Sequential mode
        success, skipped, failed = downloader.download_all(
            base_url=base_url,
            force=force,
        )
        with lock:
            final_results["successful"] = success
            final_results["skipped"] = skipped
            final_results["failed"] = failed
        # Print final progress
        total = success + skipped + failed
        print_progress(total, total, success, failed)
    else:
        # Threaded mode
        downloader.download_all_threaded(
            base_url=base_url,
            force=force,
            workers=workers,
            batch_size=batch_size,
            batch_callback=batch_callback,
        )
    
    print()  # New line after progress bar
    print("-" * 60)
    print("Download complete!")
    print(f"  Successful: {final_results['successful']}")
    if sequential:
        print(f"  Skipped: {final_results['skipped']}")
    print(f"  Failed: {final_results['failed']}")
    print("=" * 60)
    
    return 0 if final_results["failed"] == 0 else 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download config XML files in batches using multi-threaded processing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s C:/path/to/project
  %(prog)s C:/path/to/project --batch-size 100 --workers 8
  %(prog)s C:/path/to/project --force --workers 6
        """
    )
    
    parser.add_argument(
        "project_path",
        help="Path to project directory containing documents.json"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="Number of parallel download threads (default: 4)"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=25,
        help="Files per batch, max 100 (default: 25)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Download even if files already exist"
    )
    parser.add_argument(
        "--sequential", "-s",
        action="store_true",
        help="Use sequential mode instead of threaded"
    )
    parser.add_argument(
        "--url", "-u",
        help="Custom base URL for downloads"
    )
    
    args = parser.parse_args()
    
    project_path = Path(args.project_path).resolve()
    
    return download_configs(
        project_path=project_path,
        workers=args.workers,
        batch_size=args.batch_size,
        force=args.force,
        sequential=args.sequential,
        base_url=args.url,
    )


if __name__ == "__main__":
    sys.exit(main())

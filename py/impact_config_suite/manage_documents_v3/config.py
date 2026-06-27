"""Configuration for Document Manager v3."""
from pathlib import Path

# API Configuration
BASE_URL = "https://backend.company.co/IMPACT"
HTTP_TIMEOUT = 30
DOWNLOAD_DELAY = 2.0  # seconds between downloads
MAX_RETRIES = 3

# Threading
THREAD_COUNT = 4

# File paths and naming
JSON_FILE = "documents.json"
LOG_FILE = "process.log"
OUTPUT_FOLDER = "reports"

# Source folder names (as they exist before organizing)
SOURCE_FOLDERS = {
    "original_html": "originalhtml",
    "original_xml": "originalxml",
    "updated_html": "updatedhtmlfiles",
}

# File patterns
FILE_PATTERNS = {
    "docid_regex": r"[Nn]\d+",  # N followed by digits (case insensitive)
    "html_ext": ".html",
    "xml_ext": ".xml",
}

# Target file names (after organizing)
TARGET_NAMES = {
    "original_html": "{docid}.html",
    "original_xml": "{docid}_original.xml",
    "updated_html": "{docid}_updated.html",
    "config_xml": "impact_config.xml",
    "compare_report": "report.html",
}

# Process steps for resume tracking
PROCESS_STEPS = [
    "organized",
    "config_downloaded",
    "compared",
    "report_generated",
]

# Retry configuration
RETRY_CONFIG = {
    "backoff_factor": 2.0,
    "max_delay": 60.0,
}

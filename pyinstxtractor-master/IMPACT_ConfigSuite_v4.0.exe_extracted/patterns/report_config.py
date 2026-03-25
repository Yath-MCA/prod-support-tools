# report_config.py
import os
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))

CLIENTCONFIG_DIR = os.path.join(PROJECT_ROOT, "src", "clientconfig")
SEARCH_PATTERN = os.path.join(CLIENTCONFIG_DIR, "**", "config.xml")

LOG_DIR = os.path.join(CURRENT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

RUN_TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

LOG_FILE = os.path.join(LOG_DIR, f"impact_report_{RUN_TIMESTAMP}.log")
OUT_JSON = os.path.join(LOG_DIR, f"impact_report_{RUN_TIMESTAMP}.json")
OUT_HTML = os.path.join(LOG_DIR, f"impact_report_{RUN_TIMESTAMP}.html")
OUT_XLSX = os.path.join(LOG_DIR, f"impact_report_{RUN_TIMESTAMP}.xlsx")
OUT_PATTERNS = os.path.join(LOG_DIR, f"patterns_{RUN_TIMESTAMP}.json")

# Clients to ignore
IGNORE_CLIENTS = ["OUP"]

# Cite attributes (for dircite/indircite)
# Note: openwrap/closewrap are combined into 'wrap' in extraction
CITE_ATTRS = ["double_sep", "range_sep"]

# Part Label attributes (separate section)
PART_LAB_ATTRS = ["part_lab_prefix_num", "part_lab_case", "part_lab_format", "part_lab_double_sep"]

# Other Figure/Table attributes
LABEL_ATTRS = ["text-format"]

# Reference specific attributes  
REF_ATTRS = ["data-label-format", "text-format"]
REF_CITATION_ATTRS = ["type"]  # citation type attribute

SECTION_TAGS = ["Figure", "Table", "Reference"]

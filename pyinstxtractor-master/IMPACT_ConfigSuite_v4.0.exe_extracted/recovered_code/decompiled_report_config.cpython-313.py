# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'c:\\_IMPACT\\tomcat\\webapps\\impactweb_live\\untils_automation\\py\\impact_config_suite\\patterns\\report_config.py'
# Bytecode version: 3.13.0rc3 (3571)
# Source timestamp: 2026-01-03 06:42:56 UTC (1767422576)

import os
from datetime import datetime
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..', '..'))
CLIENTCONFIG_DIR = os.path.join(PROJECT_ROOT, 'src', 'clientconfig')
SEARCH_PATTERN = os.path.join(CLIENTCONFIG_DIR, '**', 'config.xml')
LOG_DIR = os.path.join(CURRENT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
RUN_TIMESTAMP = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE = os.path.join(LOG_DIR, f'impact_report_{RUN_TIMESTAMP}.log')
OUT_JSON = os.path.join(LOG_DIR, f'impact_report_{RUN_TIMESTAMP}.json')
OUT_HTML = os.path.join(LOG_DIR, f'impact_report_{RUN_TIMESTAMP}.html')
OUT_XLSX = os.path.join(LOG_DIR, f'impact_report_{RUN_TIMESTAMP}.xlsx')
OUT_PATTERNS = os.path.join(LOG_DIR, f'patterns_{RUN_TIMESTAMP}.json')
IGNORE_CLIENTS = ['OUP']
CITE_ATTRS = ['double_sep', 'range_sep']
PART_LAB_ATTRS = ['part_lab_prefix_num', 'part_lab_case', 'part_lab_format', 'part_lab_double_sep']
LABEL_ATTRS = ['text-format']
REF_ATTRS = ['data-label-format', 'text-format']
REF_CITATION_ATTRS = ['type']
SECTION_TAGS = ['Figure', 'Table', 'Reference']
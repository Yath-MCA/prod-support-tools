# Source Generated with Decompyle++
# File: PYZ.pyz_extracted/config_generator.pyc (Python 3.13)

__doc__ = '\nConfig Generator Module\nGenerates HTML form for creating journal configuration XMLs.\nUses allowed_values.json to populate dropdowns.\n'
import os
import json
from datetime import datetime
from typing import Dict, List, Optional
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ALLOWED_VALUES_FILE = os.path.join(CURRENT_DIR, 'allowed_values.json')
OUTPUT_DIR = os.path.join(CURRENT_DIR, 'generated')
# WARNING: Decompyle incomplete

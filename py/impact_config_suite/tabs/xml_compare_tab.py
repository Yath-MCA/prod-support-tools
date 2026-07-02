"""XML Compare Tab for the Common Tools application.

Provides a standalone tab for comparing two XML files with detailed diff reports.
Uses the xml_compare package for the backend comparison logic.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path

from xml_compare.gui_panel import XmlComparePanel
from xml_compare.models import CompareOptions
from xml_compare.pipeline import run_xml_compare


class XMLCompareTab(ttk.Frame):
    """Standalone tab for XML to XML comparison.

    Provides a complete UI for selecting two XML files, configuring comparison
    options, running the comparison, and viewing the generated HTML report.
    """

    def __init__(self, parent: ttk.Notebook):
        """Initialize the XML Compare tab.

        Args:
            parent: Parent notebook widget
        """
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the complete tab UI."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Use the existing XmlComparePanel which has its own title
        self.xml_panel = XmlComparePanel(self)
        self.xml_panel.grid(row=0, column=0, sticky="nsew", padx=12, pady=8)

    def get_tab_name(self) -> str:
        """Return the display name for this tab."""
        return "Compare XML"

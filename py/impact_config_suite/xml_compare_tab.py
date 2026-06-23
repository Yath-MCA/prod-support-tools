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
        self.rowconfigure(1, weight=1)

        # Title section
        title_frame = tk.Frame(self, bg="#1e293b", padx=20, pady=16)
        title_frame.grid(row=0, column=0, sticky="ew")
        tk.Label(
            title_frame,
            text="XML TO XML COMPARISON",
            font=("Segoe UI", 16, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
        ).pack(anchor="w")
        tk.Label(
            title_frame,
            text="Compare two XML files and generate a detailed HTML report with categorized differences (text, formatting, attributes, structure).",
            font=("Segoe UI", 10),
            fg="#94a3b8",
            bg="#1e293b",
            wraplength=800,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        # Main content frame
        content_frame = tk.Frame(self, bg="#0f172a", padx=16, pady=12)
        content_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)

        # Use the existing XmlComparePanel
        self.xml_panel = XmlComparePanel(content_frame)
        self.xml_panel.grid(row=0, column=0, sticky="nsew")

    def get_tab_name(self) -> str:
        """Return the display name for this tab."""
        return "Compare XML"

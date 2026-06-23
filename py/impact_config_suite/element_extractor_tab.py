import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path
import webbrowser

from bs4 import BeautifulSoup

from core.element_extractor import ElementExtractor
from core.run_history import RunHistoryStore

class ElementExtractorTab(ttk.Frame):
    """
    Tkinter Tab for HTML/XML Element Extraction and reporting.
    """
    DEFAULT_REPORT_FOLDER_NAME = "impact-support-log"
    HISTORY_LIMIT = 25
    history_tool_id = "element_extractor"
    history_tool_label = "Element Extractor"

    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent)
        self.extractor = ElementExtractor()
        self.scan_thread = None
        self.cancelled = False
        self.last_report_path = None
        self.last_summary_report_path = None
        self.last_csv_path = None
        self.history_entries = self._load_history_entries()
        self.filtered_history_entries = list(self.history_entries)
        self._build_ui()
        self._restore_last_history_state()
        self._refresh_history_list()

    @classmethod
    def _default_output_dir(cls) -> Path:
        return Path.home() / "Documents" / cls.DEFAULT_REPORT_FOLDER_NAME

    @classmethod
    def _history_file_path(cls) -> Path:
        return RunHistoryStore.history_file_path()

    @classmethod
    def _load_history_entries(cls) -> list[dict]:
        valid_entries = []
        for item in RunHistoryStore.recent_for_tool(cls.history_tool_id):
            if str(item.get("source_path", "")).strip():
                valid_entries.append(item)
        return valid_entries[:cls.HISTORY_LIMIT]

    @classmethod
    def _save_history_entries(cls, entries: list[dict]) -> None:
        all_entries = [entry for entry in RunHistoryStore.load_entries() if entry.get("tool_id") != cls.history_tool_id]
        all_entries.extend(entries[:cls.HISTORY_LIMIT])
        RunHistoryStore.save_entries(all_entries)

    def _build_ui(self):
        # Main container with dark background (blends with existing suite styling)
        main_container = tk.Frame(self, bg="#1e293b", padx=30, pady=25)
        main_container.pack(fill="both", expand=True)

        # Header Section
        header_frame = tk.Frame(main_container, bg="#1e293b")
        header_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(
            header_frame,
            text="🎯 ELEMENT EXTRACTOR",
            font=("Segoe UI", 18, "bold"),
            fg="#818cf8",
            bg="#1e293b",
        ).pack(anchor="w")

        tk.Label(
            header_frame,
            text="Analyze HTML or XML files, extract specific elements using tags, CSS selectors, or XPath, and generate an interactive report.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b",
        ).pack(anchor="w", pady=(2, 5))

        # --- Settings Frame ---
        settings_frame = tk.LabelFrame(
            main_container,
            text="Extraction Configuration",
            bg="#1e293b",
            fg="#cbd5e1",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=15,
            bd=1,
            relief="flat"
        )
        settings_frame.pack(fill="x", pady=(0, 20))
        settings_frame.columnconfigure(1, weight=1)

        # 1. Mode Selector
        tk.Label(
            settings_frame,
            text="Scan Mode:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=5)
        
        self.mode_var = tk.StringVar(value="Single File")
        mode_frame = tk.Frame(settings_frame, bg="#1e293b")
        mode_frame.grid(row=0, column=1, sticky="w", pady=5)
        
        tk.Radiobutton(
            mode_frame,
            text="Single File",
            variable=self.mode_var,
            value="Single File",
            command=self._on_mode_change,
            bg="#1e293b", fg="#e2e8f0", activebackground="#1e293b", activeforeground="white",
            selectcolor="#334155"
        ).pack(side="left", padx=(0, 15))
        
        tk.Radiobutton(
            mode_frame,
            text="Folder Scan",
            variable=self.mode_var,
            value="Folder Scan",
            command=self._on_mode_change,
            bg="#1e293b", fg="#e2e8f0", activebackground="#1e293b", activeforeground="white",
            selectcolor="#334155"
        ).pack(side="left")

        # 2. Path Selection
        self.path_label = tk.Label(
            settings_frame,
            text="Source XML/HTML File:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
        )
        self.path_label.grid(row=1, column=0, sticky="w", pady=5)

        path_input_frame = tk.Frame(settings_frame, bg="#1e293b")
        path_input_frame.grid(row=1, column=1, columnspan=2, sticky="ew", pady=5)
        path_input_frame.columnconfigure(0, weight=1)

        self.path_var = tk.StringVar()
        self.path_entry = tk.Entry(
            path_input_frame,
            textvariable=self.path_var,
            bg="#334155",
            fg="white",
            border=0,
            font=("Segoe UI", 10),
            insertbackground="white"
        )
        self.path_entry.grid(row=0, column=0, sticky="ew", ipady=6, padx=(0, 10))

        self.browse_btn = tk.Button(
            path_input_frame,
            text="Browse",
            command=self._browse_path,
            bg="#4f46e5",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            border=0,
            padx=15,
            pady=5,
            cursor="hand2"
        )
        self.browse_btn.grid(row=0, column=1)

        # 3. Selector Method
        tk.Label(
            settings_frame,
            text="Extraction Method:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
        ).grid(row=2, column=0, sticky="w", pady=5)

        selector_frame = tk.Frame(settings_frame, bg="#1e293b")
        selector_frame.grid(row=2, column=1, columnspan=2, sticky="ew", pady=5)
        selector_frame.columnconfigure(1, weight=1)

        self.selector_type_var = tk.StringVar(value="Tag Name")
        self.selector_combo = ttk.Combobox(
            selector_frame,
            textvariable=self.selector_type_var,
            values=["Tag Name", "XPath Query", "CSS Selector"],
            state="readonly",
            width=15,
            font=("Segoe UI", 9)
        )
        self.selector_combo.grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.selector_combo.bind("<<ComboboxSelected>>", self._on_selector_type_change)

        self.query_var = tk.StringVar(value="span")
        self.query_entry = tk.Entry(
            selector_frame,
            textvariable=self.query_var,
            bg="#334155",
            fg="white",
            border=0,
            font=("Segoe UI", 10),
            insertbackground="white"
        )
        self.query_entry.grid(row=0, column=1, sticky="ew", ipady=6)

        # 4. Attribute Filter (Only active/visible for Tag Name)
        self.attr_filter_lbl = tk.Label(
            settings_frame,
            text="Attribute Filter:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
        )
        self.attr_filter_lbl.grid(row=3, column=0, sticky="w", pady=5)

        attr_frame = tk.Frame(settings_frame, bg="#1e293b")
        attr_frame.grid(row=3, column=1, columnspan=2, sticky="ew", pady=5)
        attr_frame.columnconfigure(1, weight=1)
        attr_frame.columnconfigure(3, weight=1)

        tk.Label(attr_frame, text="Name:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9)).grid(row=0, column=0, padx=(0, 5))
        
        self.attr_name_var = tk.StringVar()
        self.attr_name_entry = tk.Entry(
            attr_frame,
            textvariable=self.attr_name_var,
            bg="#334155",
            fg="white",
            border=0,
            font=("Segoe UI", 10),
            insertbackground="white",
            width=15
        )
        self.attr_name_entry.grid(row=0, column=1, sticky="ew", ipady=6, padx=(0, 15))

        tk.Label(attr_frame, text="Value (Optional):", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9)).grid(row=0, column=2, padx=(0, 5))
        
        self.attr_val_var = tk.StringVar()
        self.attr_val_entry = tk.Entry(
            attr_frame,
            textvariable=self.attr_val_var,
            bg="#334155",
            fg="white",
            border=0,
            font=("Segoe UI", 10),
            insertbackground="white"
        )
        self.attr_val_entry.grid(row=0, column=3, sticky="ew", ipady=6)

        # 5. Scan Options (Recursive, Extensions)
        self.options_lbl = tk.Label(
            settings_frame,
            text="Folder Scan Options:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
        )
        self.options_lbl.grid(row=4, column=0, sticky="w", pady=5)

        options_frame = tk.Frame(settings_frame, bg="#1e293b")
        options_frame.grid(row=4, column=1, columnspan=2, sticky="ew", pady=5)
        options_frame.columnconfigure(1, weight=1)
        options_frame.columnconfigure(2, weight=1)

        self.recursive_var = tk.BooleanVar(value=False)
        self.recursive_chk = tk.Checkbutton(
            options_frame,
            text="Recursive Search",
            variable=self.recursive_var,
            bg="#1e293b", fg="#94a3b8", activebackground="#1e293b", activeforeground="#818cf8",
            selectcolor="#334155",
            font=("Segoe UI", 9),
            state="disabled" # Disabled by default since default mode is Single File
        )
        self.recursive_chk.grid(row=0, column=0, padx=(0, 20), sticky="w")

        tk.Label(options_frame, text="Extensions:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9)).grid(row=0, column=1, sticky="e", padx=(0, 5))
        self.extensions_var = tk.StringVar(value=".xml, .html, .htm, .xhtml")
        self.ext_entry = tk.Entry(
            options_frame,
            textvariable=self.extensions_var,
            bg="#1e293b", # Disabled style initially
            fg="#94a3b8",
            border=0,
            font=("Segoe UI", 10),
            insertbackground="white",
            state="disabled",
            width=25
        )
        self.ext_entry.grid(row=0, column=2, sticky="ew", ipady=6)

        tk.Label(
            options_frame,
            text="Filename Filter:",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 9),
        ).grid(row=1, column=0, sticky="w", pady=(10, 0))

        self.filename_filter_var = tk.StringVar(value="None")
        self.filename_filter_combo = ttk.Combobox(
            options_frame,
            textvariable=self.filename_filter_var,
            values=["*_original.html", "*_updated.html", "*._original.xml", "None"],
            state="readonly",
            width=18,
            font=("Segoe UI", 9),
        )
        self.filename_filter_combo.grid(row=1, column=1, columnspan=2, sticky="w", pady=(10, 0))

        tk.Label(
            options_frame,
            text="DTD Filter:",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 9),
        ).grid(row=2, column=0, sticky="w", pady=(10, 0))

        self.dtd_filter_var = tk.StringVar(value="None")
        self.dtd_filter_combo = ttk.Combobox(
            options_frame,
            textvariable=self.dtd_filter_var,
            values=["None", "JATS", "BITS"],
            state="readonly",
            width=18,
            font=("Segoe UI", 9),
        )
        self.dtd_filter_combo.grid(row=2, column=1, columnspan=2, sticky="w", pady=(10, 0))

        tk.Label(
            options_frame,
            text="Client Filter:",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 9),
        ).grid(row=3, column=0, sticky="w", pady=(10, 0))

        self.client_filter_var = tk.StringVar(value="None")
        self.client_filter_combo = ttk.Combobox(
            options_frame,
            textvariable=self.client_filter_var,
            values=["None", "OUP", "TNF", "PLOS", "BRILL", "ACS", "LWW", "MEDKNOW"],
            state="readonly",
            width=18,
            font=("Segoe UI", 9),
        )
        self.client_filter_combo.grid(row=3, column=1, columnspan=2, sticky="w", pady=(10, 0))

        # 6. Output report path
        tk.Label(
            settings_frame,
            text="Report Output Folder:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
        ).grid(row=5, column=0, sticky="w", pady=5)

        output_frame = tk.Frame(settings_frame, bg="#1e293b")
        output_frame.grid(row=5, column=1, columnspan=2, sticky="ew", pady=5)
        output_frame.columnconfigure(0, weight=1)

        self.output_dir_var = tk.StringVar(value=str(self._default_output_dir()))
        self.output_dir_entry = tk.Entry(
            output_frame,
            textvariable=self.output_dir_var,
            bg="#334155",
            fg="white",
            border=0,
            font=("Segoe UI", 10),
            insertbackground="white"
        )
        self.output_dir_entry.grid(row=0, column=0, sticky="ew", ipady=6, padx=(0, 10))

        self.out_browse_btn = tk.Button(
            output_frame,
            text="Browse",
            command=self._browse_output_dir,
            bg="#475569",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            border=0,
            padx=15,
            pady=5,
            cursor="hand2"
        )
        self.out_browse_btn.grid(row=0, column=1)

        # 7. Post action option
        self.open_report_var = tk.BooleanVar(value=True)
        self.open_report_chk = tk.Checkbutton(
            settings_frame,
            text="Open HTML report automatically in web browser after completion",
            variable=self.open_report_var,
            bg="#1e293b", fg="#e2e8f0", activebackground="#1e293b", activeforeground="white",
            selectcolor="#334155",
            font=("Segoe UI", 9)
        )
        self.open_report_chk.grid(row=6, column=1, columnspan=2, sticky="w", pady=5)

        # 8. Report Content Options
        tk.Label(
            settings_frame,
            text="Report Content:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
        ).grid(row=7, column=0, sticky="w", pady=5)

        report_options_frame = tk.Frame(settings_frame, bg="#1e293b")
        report_options_frame.grid(row=7, column=1, columnspan=2, sticky="ew", pady=5)

        self.show_outer_xml_var = tk.BooleanVar(value=True)
        self.show_outer_xml_chk = tk.Checkbutton(
            report_options_frame,
            text="Include Outer XML/HTML",
            variable=self.show_outer_xml_var,
            bg="#1e293b", fg="#e2e8f0", activebackground="#1e293b", activeforeground="white",
            selectcolor="#334155",
            font=("Segoe UI", 9)
        )
        self.show_outer_xml_chk.pack(side="left", padx=(0, 15))

        self.show_inner_text_var = tk.BooleanVar(value=True)
        self.show_inner_text_chk = tk.Checkbutton(
            report_options_frame,
            text="Include Inner Text Content",
            variable=self.show_inner_text_var,
            bg="#1e293b", fg="#e2e8f0", activebackground="#1e293b", activeforeground="white",
            selectcolor="#334155",
            font=("Segoe UI", 9)
        )
        self.show_inner_text_chk.pack(side="left", padx=(0, 15))

        self.generate_csv_var = tk.BooleanVar(value=True)
        self.generate_csv_chk = tk.Checkbutton(
            report_options_frame,
            text="Export CSV Summary",
            variable=self.generate_csv_var,
            bg="#1e293b", fg="#e2e8f0", activebackground="#1e293b", activeforeground="white",
            selectcolor="#334155",
            font=("Segoe UI", 9)
        )
        self.generate_csv_chk.pack(side="left", padx=(0, 15))

        self.copy_matched_files_var = tk.BooleanVar(value=False)
        self.copy_matched_files_chk = tk.Checkbutton(
            report_options_frame,
            text="Copy matched source files",
            variable=self.copy_matched_files_var,
            bg="#1e293b", fg="#e2e8f0", activebackground="#1e293b", activeforeground="white",
            selectcolor="#334155",
            font=("Segoe UI", 9)
        )
        self.copy_matched_files_chk.pack(side="left")

        history_frame = tk.LabelFrame(
            main_container,
            text="Run History",
            bg="#1e293b",
            fg="#cbd5e1",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=15,
            bd=1,
            relief="flat"
        )
        history_frame.pack(fill="x", pady=(0, 15))
        history_frame.columnconfigure(1, weight=1)
        history_frame.columnconfigure(3, weight=1)

        tk.Label(
            history_frame,
            text="Search History:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=5)

        self.history_search_var = tk.StringVar()
        self.history_search_entry = tk.Entry(
            history_frame,
            textvariable=self.history_search_var,
            bg="#334155",
            fg="white",
            border=0,
            font=("Segoe UI", 10),
            insertbackground="white"
        )
        self.history_search_entry.grid(row=0, column=1, sticky="ew", ipady=6, padx=(0, 10), pady=5)
        self.history_search_entry.bind("<KeyRelease>", self._on_history_search_change)

        tk.Label(
            history_frame,
            text="Saved Runs:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
        ).grid(row=1, column=0, sticky="w", pady=5)

        self.history_choice_var = tk.StringVar()
        self.history_combo = ttk.Combobox(
            history_frame,
            textvariable=self.history_choice_var,
            state="readonly",
            font=("Segoe UI", 9),
        )
        self.history_combo.grid(row=1, column=1, columnspan=3, sticky="ew", ipady=4, pady=5)

        self.apply_history_btn = tk.Button(
            history_frame,
            text="Apply Selected",
            command=self._apply_selected_history,
            bg="#2563eb",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            border=0,
            padx=14,
            pady=6,
            cursor="hand2"
        )
        self.apply_history_btn.grid(row=2, column=0, pady=(10, 0), sticky="w")

        self.rerun_last_btn = tk.Button(
            history_frame,
            text="Rerun Last",
            command=self._rerun_last_history,
            bg="#0f766e",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            border=0,
            padx=14,
            pady=6,
            cursor="hand2"
        )
        self.rerun_last_btn.grid(row=2, column=1, pady=(10, 0), sticky="w")

        self.open_history_report_btn = tk.Button(
            history_frame,
            text="Open Saved Report",
            command=self._open_selected_history_report,
            bg="#7c3aed",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            border=0,
            padx=14,
            pady=6,
            cursor="hand2"
        )
        self.open_history_report_btn.grid(row=2, column=2, pady=(10, 0), sticky="w")

        self.clear_history_search_btn = tk.Button(
            history_frame,
            text="Clear Search",
            command=self._clear_history_search,
            bg="#475569",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            border=0,
            padx=14,
            pady=6,
            cursor="hand2"
        )
        self.clear_history_search_btn.grid(row=2, column=3, pady=(10, 0), sticky="e")

        # --- Progress Bar & Status Line (before action buttons) ---
        self.progress_frame = tk.Frame(main_container, bg="#1e293b")
        self.progress_frame.pack(fill="x", pady=(10, 0))
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", side="top", pady=(0, 5))
        
        self.status_var = tk.StringVar(value="System Ready. Configure options above and click Run.")
        self.status_label = tk.Label(
            self.progress_frame,
            textvariable=self.status_var,
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 9, "italic"),
        )
        self.status_label.pack(side="left")

        # --- Action Buttons Frame ---
        btn_frame = tk.Frame(main_container, bg="#1e293b")
        btn_frame.pack(fill="x", pady=(10, 15))

        self.run_btn = tk.Button(
            btn_frame,
            text="🚀  RUN ELEMENT EXTRACTION",
            command=self._start_extraction,
            bg="#10b981",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            border=0,
            padx=20,
            pady=12,
            cursor="hand2"
        )
        self.run_btn.pack(side="left", fill="x", expand=True)

        self.cancel_btn = tk.Button(
            btn_frame,
            text="❌ Cancel",
            command=self._cancel_extraction,
            bg="#ef4444",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=20,
            pady=12,
            state="disabled",
            cursor="hand2"
        )
        self.cancel_btn.pack(side="left", padx=(10, 0))

        self.open_last_btn = tk.Button(
            btn_frame,
            text="📂 Open Last Report",
            command=self._open_last_report,
            bg="#4f46e5",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=20,
            pady=12,
            state="disabled",
            cursor="hand2"
        )
        self.open_last_btn.pack(side="right", padx=(10, 0))

        # --- Console Log Frame ---
        tk.Label(
            main_container,
            text="Activity log and extracted previews:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(10, 5))

        res_frame = tk.Frame(main_container, bg="#0f172a")
        res_frame.pack(fill="both", expand=True)

        self.res_text = tk.Text(
            res_frame,
            bg="#0f172a",
            fg="#34d399",  # Beautiful green code color
            insertbackground="white",
            border=0,
            font=("Consolas", 10),
            padx=12,
            pady=12
        )
        scroll = ttk.Scrollbar(res_frame, command=self.res_text.yview)
        self.res_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.res_text.pack(fill="both", expand=True)

        # Context Menu for results
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy All Log Content", command=self._copy_all_log)
        self.context_menu.add_command(label="Clear Console", command=lambda: self.res_text.delete("1.0", tk.END))
        self.res_text.bind("<Button-3>", self._show_context_menu)



    def _on_selector_type_change(self, event=None):
        sel_type = self.selector_type_var.get()
        if sel_type == "Tag Name":
            self.attr_name_entry.config(state="normal", bg="#334155")
            self.attr_val_entry.config(state="normal", bg="#334155")
            self.attr_filter_lbl.config(fg="#94a3b8")
        else:
            self.attr_name_entry.config(state="disabled", bg="#1e293b")
            self.attr_val_entry.config(state="disabled", bg="#1e293b")
            self.attr_filter_lbl.config(fg="#475569")

    def _on_mode_change(self, event=None):
        mode = self.mode_var.get()
        if mode == "Single File":
            self.recursive_chk.config(state="disabled")
            self.ext_entry.config(state="disabled", bg="#1e293b", fg="#475569")
            self.filename_filter_combo.config(state="disabled")
            self.dtd_filter_combo.config(state="disabled")
            self.client_filter_combo.config(state="disabled")
            self.path_label.config(text="Source XML/HTML File:")
            self.options_lbl.config(fg="#475569")
        else:
            self.recursive_chk.config(state="normal")
            self.ext_entry.config(state="normal", bg="#334155", fg="white")
            self.filename_filter_combo.config(state="readonly")
            self.dtd_filter_combo.config(state="readonly")
            self.client_filter_combo.config(state="readonly")
            self.path_label.config(text="Source Folder Path:")
            self.options_lbl.config(fg="#94a3b8")

    def _browse_path(self):
        mode = self.mode_var.get()
        if mode == "Single File":
            path = filedialog.askopenfilename(
                title="Select XML/HTML File",
                filetypes=[
                    ("All Supported Markup", "*.xml *.html *.htm *.xhtml"),
                    ("XML Files", "*.xml"),
                    ("HTML Files", "*.html *.htm"),
                    ("All Files", "*.*")
                ]
            )
        else:
            path = filedialog.askdirectory(
                title="Select Directory to Scan"
            )
            
        if path:
            abs_path = os.path.abspath(path)
            self.path_var.set(abs_path)
            # Auto populate output folder if empty
            if not self.output_dir_var.get().strip():
                parent_dir = os.path.dirname(abs_path) if mode == "Single File" else abs_path
                self.output_dir_var.set(parent_dir)

    def _browse_output_dir(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.output_dir_var.set(os.path.abspath(path))

    def _log(self, message: str):
        """Append log message to the text console in a thread-safe way."""
        self.res_text.insert(tk.END, message + "\n")
        self.res_text.see(tk.END)

    def _show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def _copy_all_log(self):
        content = self.res_text.get("1.0", tk.END).strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self.status_var.set("Logs copied to clipboard.")

    @staticmethod
    def _parse_query_list(raw: str) -> list[str]:
        """Parse comma-separated query string into list of individual queries."""
        return [q.strip() for q in raw.split(",") if q.strip()]

    def _normalize_query_input(self, query_type: str, query_val: str) -> str:
        normalized = query_val.strip()
        if not normalized:
            raise ValueError("Please enter a tag, selector, or XPath query.")

        # Fix XPath label normalization - UI sends "XPath Query" but core expects "XPath"
        if query_type == "XPath Query":
            query_type = "XPath"

        if query_type == "CSS Selector":
            normalized = re.sub(r"\s+", " ", normalized).strip()
            try:
                BeautifulSoup("", "lxml").select(normalized)
            except Exception as exc:
                raise ValueError(f"Invalid CSS selector: {exc}") from exc

        return normalized

    @staticmethod
    def _slugify(text: str, fallback: str = "report") -> str:
        cleaned = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in text.strip())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        return cleaned or fallback

    @staticmethod
    def _history_summary(entry: dict) -> str:
        ts = str(entry.get("timestamp", "")).strip() or "Unknown time"
        mode = str(entry.get("mode", "")).strip() or "Mode?"
        query_type = str(entry.get("query_type", "")).strip() or "Query?"
        query_val = str(entry.get("query_value", "")).strip() or "?"
        source_name = Path(str(entry.get("source_path", "")).strip() or ".").name
        return f"{ts} | {mode} | {query_type}: {query_val} | {source_name}"

    def _restore_last_history_state(self) -> None:
        if not self.history_entries:
            return
        latest = self.history_entries[0]
        report_path = str(latest.get("report_path", "")).strip()
        if report_path and os.path.exists(report_path):
            self.last_report_path = report_path
            self.open_last_btn.config(state="normal")
        # Restore additional report paths from params if available
        params = latest.get("params", {})
        summary_path = str(params.get("summary_report_path", "")).strip()
        csv_path = str(params.get("csv_path", "")).strip()
        if summary_path and os.path.exists(summary_path):
            self.last_summary_report_path = summary_path
        if csv_path and os.path.exists(csv_path):
            self.last_csv_path = csv_path

    def _refresh_history_list(self) -> None:
        values = [self._history_summary(entry) for entry in self.filtered_history_entries]
        self.history_combo["values"] = values
        if values:
            self.history_combo.current(0)
        else:
            self.history_choice_var.set("")

    def _on_history_search_change(self, event=None) -> None:
        needle = self.history_search_var.get().strip().lower()
        if not needle:
            self.filtered_history_entries = list(self.history_entries)
        else:
            self.filtered_history_entries = [
                entry for entry in self.history_entries
                if needle in json.dumps(entry, ensure_ascii=False).lower()
            ]
        self._refresh_history_list()

    def _clear_history_search(self) -> None:
        self.history_search_var.set("")
        self.filtered_history_entries = list(self.history_entries)
        self._refresh_history_list()

    def _selected_history_entry(self) -> dict | None:
        index = self.history_combo.current()
        if index < 0 or index >= len(self.filtered_history_entries):
            return None
        return self.filtered_history_entries[index]

    def _apply_history_entry(self, entry: dict) -> None:
        mode = str(entry.get("mode", "Single File")).strip() or "Single File"
        self.mode_var.set(mode)
        self._on_mode_change()
        self.path_var.set(str(entry.get("source_path", "")).strip())
        self.selector_type_var.set(str(entry.get("query_type", "Tag Name")).strip() or "Tag Name")
        self._on_selector_type_change()
        self.query_var.set(str(entry.get("query_value", "")).strip())
        self.attr_name_var.set(str(entry.get("attr_name", "")).strip())
        self.attr_val_var.set(str(entry.get("attr_value", "")).strip())
        self.recursive_var.set(bool(entry.get("recursive", False)))
        self.extensions_var.set(str(entry.get("extensions", ".xml, .html, .htm, .xhtml")).strip() or ".xml, .html, .htm, .xhtml")
        self.filename_filter_var.set(str(entry.get("filename_filter", "None")).strip() or "None")
        self.dtd_filter_var.set(str(entry.get("dtd_filter", "None")).strip() or "None")
        self.client_filter_var.set(str(entry.get("client_filter", "None")).strip() or "None")
        self.output_dir_var.set(str(entry.get("output_dir", str(self._default_output_dir()))).strip() or str(self._default_output_dir()))
        self.open_report_var.set(bool(entry.get("open_report", True)))
        # Restore new report content options
        self.show_outer_xml_var.set(bool(entry.get("show_outer_xml", True)))
        self.show_inner_text_var.set(bool(entry.get("show_inner_text", True)))
        self.generate_csv_var.set(bool(entry.get("generate_csv", True)))
        self.copy_matched_files_var.set(bool(entry.get("copy_matched_files", False)))
        report_path = str(entry.get("report_path", "")).strip()
        if report_path:
            self.last_report_path = report_path
            self.open_last_btn.config(state="normal")
        self.status_var.set("History entry applied.")

    def apply_history_entry(self, entry: dict) -> bool:
        self._apply_history_entry(entry)
        return True

    def _apply_selected_history(self) -> None:
        entry = self._selected_history_entry()
        if not entry:
            messagebox.showinfo("Run History", "No saved history entry is selected.")
            return
        self._apply_history_entry(entry)

    def _open_selected_history_report(self) -> None:
        entry = self._selected_history_entry()
        if not entry:
            messagebox.showinfo("Run History", "No saved history entry is selected.")
            return
        report_path = str(entry.get("report_path", "")).strip()
        if not report_path or not os.path.exists(report_path):
            messagebox.showerror("Run History", "Saved report is missing for the selected history entry.")
            return
        self.last_report_path = report_path
        self.open_last_btn.config(state="normal")
        webbrowser.open(f"file:///{os.path.abspath(report_path)}")

    def _rerun_last_history(self) -> None:
        if not self.history_entries:
            messagebox.showinfo("Run History", "No previous run is available yet.")
            return
        self._apply_history_entry(self.history_entries[0])
        self._start_extraction()

    def rerun_history_entry(self, entry: dict) -> bool:
        self._apply_history_entry(entry)
        self._start_extraction()
        return True

    def _current_run_settings(self, source_path: str, query_val: str, output_dir: str, report_path: str,
                               summary_report_path: str = "", csv_path: str = "",
                               copied_files_count: int = 0, copied_folder_path: str = "") -> dict:
        return {
            "tool_id": self.history_tool_id,
            "tool_label": self.history_tool_label,
            "action": "extract",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mode": self.mode_var.get().strip(),
            "source_path": source_path,
            "query_type": self.selector_type_var.get().strip(),
            "query_value": query_val,
            "attr_name": self.attr_name_var.get().strip(),
            "attr_value": self.attr_val_var.get().strip(),
            "recursive": bool(self.recursive_var.get()),
            "extensions": self.extensions_var.get().strip(),
            "filename_filter": self.filename_filter_var.get().strip() or "None",
            "dtd_filter": self.dtd_filter_var.get().strip() or "None",
            "client_filter": self.client_filter_var.get().strip() or "None",
            "output_dir": output_dir,
            "open_report": bool(self.open_report_var.get()),
            "report_path": report_path,
            "summary": f"{self.mode_var.get().strip()} | {self.selector_type_var.get().strip()}: {query_val}",
            # New report content options
            "show_outer_xml": bool(self.show_outer_xml_var.get()),
            "show_inner_text": bool(self.show_inner_text_var.get()),
            "generate_csv": bool(self.generate_csv_var.get()),
            "copy_matched_files": bool(self.copy_matched_files_var.get()),
            "params": {
                "mode": self.mode_var.get().strip(),
                "query_type": self.selector_type_var.get().strip(),
                "query_value": query_val,
                "attr_name": self.attr_name_var.get().strip(),
                "attr_value": self.attr_val_var.get().strip(),
                "recursive": bool(self.recursive_var.get()),
                "extensions": self.extensions_var.get().strip(),
                "filename_filter": self.filename_filter_var.get().strip() or "None",
                "dtd_filter": self.dtd_filter_var.get().strip() or "None",
                "client_filter": self.client_filter_var.get().strip() or "None",
                "show_outer_xml": bool(self.show_outer_xml_var.get()),
                "show_inner_text": bool(self.show_inner_text_var.get()),
                "generate_csv": bool(self.generate_csv_var.get()),
                "copy_matched_files": bool(self.copy_matched_files_var.get()),
                "summary_report_path": summary_report_path,
                "csv_path": csv_path,
                "copied_files_count": copied_files_count,
                "copied_folder_path": copied_folder_path,
            },
        }

    def _record_history_entry(self, entry: dict) -> None:
        try:
            RunHistoryStore.add_entry(entry)
            # Schedule UI update on main thread (tkinter is not thread-safe)
            self.after(0, self._update_history_ui)
        except Exception as e:
            # Log error but don't fail the extraction due to history issues
            self.after(0, lambda msg=str(e): self._log(f"⚠️ Failed to save history: {msg}"))

    def _update_history_ui(self) -> None:
        """Update history UI - must be called from main thread."""
        try:
            self.history_entries = self._load_history_entries()
            self.filtered_history_entries = list(self.history_entries)
            self._refresh_history_list()
        except Exception as e:
            self._log(f"⚠️ Failed to refresh history UI: {e}")

    def _start_extraction(self):
        # Validate inputs
        source_path = self.path_var.get().strip()
        query_type = self.selector_type_var.get()
        raw_query_val = self.query_var.get().strip()
        output_dir = self.output_dir_var.get().strip()

        # Fix XPath label normalization before validation
        if query_type == "XPath Query":
            query_type = "XPath"

        # Parse comma-separated queries
        queries = self._parse_query_list(raw_query_val)
        if not queries:
            messagebox.showerror("Error", "Please enter a tag, selector, or XPath query.")
            return

        # Validate each query
        normalized_queries = []
        for query in queries:
            try:
                normalized = self._normalize_query_input(query_type, query)
                normalized_queries.append(normalized)
            except ValueError as exc:
                messagebox.showerror("Error", f"Invalid query '{query}': {str(exc)}")
                return

        if not source_path:
            messagebox.showerror("Error", "Please provide a valid source path (file or folder).")
            return
        if not os.path.exists(source_path):
            messagebox.showerror("Error", f"Source path does not exist:\n{source_path}")
            return
        if not output_dir:
            messagebox.showerror("Error", "Please specify an output folder to save the HTML report.")
            return
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create output directory:\n{str(e)}")
                return

        # Prepare UI
        self.res_text.delete("1.0", tk.END)
        self.run_btn.config(state="disabled", text="⏳ EXTRACTING ELEMENTS...")
        self.cancel_btn.config(state="normal")
        self.progress_bar.config(value=0)

        self.cancelled = False

        # Start Thread with multiple queries
        self.scan_thread = threading.Thread(
            target=self._run_extraction_thread,
            args=(source_path, normalized_queries, query_type, output_dir),
            daemon=True
        )
        self.scan_thread.start()

    def _cancel_extraction(self):
        self.cancelled = True
        self._log("\n⚠️ Cancellation requested. Stopping scan...")
        self.status_var.set("Cancellation requested...")
        self.cancel_btn.config(state="disabled")

    def _open_last_report(self):
        if self.last_report_path and os.path.exists(self.last_report_path):
            webbrowser.open(f"file:///{os.path.abspath(self.last_report_path)}")
        else:
            messagebox.showerror("Error", "Last report path is invalid or missing.")

    def _run_extraction_thread(self, source_path_str: str, queries: list[str], query_type: str, output_dir_str: str):
        try:
            mode = self.mode_var.get()
            # Fix XPath label normalization
            if query_type == "XPath Query":
                query_type = "XPath"
            attr_name = self.attr_name_var.get().strip()
            attr_val = self.attr_val_var.get().strip()

            # Report content options
            show_outer_xml = bool(self.show_outer_xml_var.get())
            show_inner_text = bool(self.show_inner_text_var.get())
            generate_csv = bool(self.generate_csv_var.get())

            source_path = Path(source_path_str)
            output_dir = Path(output_dir_str)

            is_single = (mode == "Single File")

            # Print scan meta
            self._log(f"🚀 Starting Element Extraction - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._log(f"  Mode:          {mode}")
            self._log(f"  Source Path:   {source_path}")
            self._log(f"  Query Type:    {query_type}")
            self._log(f"  Queries:       {len(queries)} selector(s) to process")
            for i, q in enumerate(queries, 1):
                self._log(f"    [{i}] {q}")
            if query_type == "Tag Name" and attr_name:
                self._log(f"  Attr Filter:   {attr_name} = '{attr_val}'")
            copy_matched_files = bool(self.copy_matched_files_var.get())
            self._log(f"  Report Options: Outer XML={'Yes' if show_outer_xml else 'No'}, Inner Text={'Yes' if show_inner_text else 'No'}, CSV={'Yes' if generate_csv else 'No'}, Copy Files={'Yes' if copy_matched_files else 'No'}")
            self._log("---------------------------------------------------------------------\n")

            # Collect results for all selectors
            all_selector_results = []
            grand_total_matches = 0
            total_files_scanned = 0

            # Pre-scan file list for folder mode to avoid re-scanning
            all_files = []
            if not is_single:
                recursive = self.recursive_var.get()
                ext_str = self.extensions_var.get()
                filename_filter = self.filename_filter_var.get().strip()
                dtd_filter = self.dtd_filter_var.get().strip()
                client_filter = self.client_filter_var.get().strip()
                extensions = [e.strip().lower() for e in ext_str.replace(" ", "").split(",") if e.strip()]
                if not extensions:
                    extensions = ['.xml', '.html', '.htm', '.xhtml']

                # Build file list once
                pattern = "**/*" if recursive else "*"
                normalized_filter = filename_filter.strip() if filename_filter else ""
                if normalized_filter and normalized_filter.lower() != "none" and not any(
                    char in normalized_filter for char in "*?[]"
                ):
                    normalized_filter = f"*{normalized_filter}"

                for file in source_path.glob(pattern):
                    if not file.is_file():
                        continue
                    if normalized_filter and normalized_filter.lower() != "none" and not self.extractor._matches_filename_filter(
                        file.name, normalized_filter
                    ):
                        continue
                    if file.suffix.lower() in extensions:
                        if not self.extractor._matches_config_filters(file, dtd_filter, client_filter):
                            continue
                        all_files.append(file)

                all_files = sorted(all_files)
                total_files_scanned = len(all_files)

                filter_label = filename_filter if filename_filter != "None" else "No filename filter"
                dtd_label = dtd_filter if dtd_filter != "None" else "No DTD filter"
                client_label = client_filter if client_filter != "None" else "No client filter"
                self._log(
                    f"Scanning directory with filters: {', '.join(extensions)} "
                    f"(Recursive: {'Yes' if recursive else 'No'}, Filename: {filter_label}, "
                    f"DTD: {dtd_label}, Client: {client_label})"
                )
                self._log(f"Found {total_files_scanned} file(s) to scan\n")

            # Process each query
            for query_idx, query_val in enumerate(queries):
                if self.cancelled:
                    self._log("\n❌ Process Cancelled by User.")
                    self.status_var.set("Extraction cancelled.")
                    return

                self._log(f"Processing query [{query_idx + 1}/{len(queries)}]: '{query_val}'")
                self.status_var.set(f"Processing query {query_idx + 1}/{len(queries)}: {query_val}")

                scan_results = {}
                total_matches = 0
                total_files = 0

                if is_single:
                    if source_path.is_dir():
                        raise ValueError("Single File mode selected, but a directory was provided.")

                    total_files = 1
                    matches = self.extractor.parse_and_extract(
                        source_path, query_type, query_val, attr_name, attr_val
                    )
                    scan_results[str(source_path.absolute())] = {
                        "ok": True,
                        "matches": matches
                    }
                    total_matches = len(matches)
                    self._log(f"  ✔ Found {total_matches} matching element(s)")

                else:
                    # Folder scan mode - use pre-built file list
                    if not source_path.is_dir():
                        raise ValueError("Folder Scan mode selected, but a file path was provided.")

                    total_files = total_files_scanned

                    def progress_update(current, total, file_name):
                        percent = int((current / total) * 100)
                        self.progress_bar.config(value=percent)
                        self.status_var.set(f"Query {query_idx + 1}/{len(queries)} - Scanning ({current}/{total}): {file_name}")

                    # Process each file with caching
                    for i, file_path in enumerate(all_files):
                        if self.cancelled:
                            break
                        progress_update(i + 1, total_files, file_path.name)

                        try:
                            cached = self.extractor._get_cached(file_path, query_type, query_val, attr_name, attr_val)
                            if cached is not None:
                                matches = cached
                            else:
                                matches = self.extractor.parse_and_extract(file_path, query_type, query_val, attr_name, attr_val)
                                self.extractor._set_cache(file_path, query_type, query_val, attr_name, attr_val, matches)

                            if matches:
                                scan_results[str(file_path.absolute())] = {
                                    "ok": True,
                                    "matches": matches
                                }
                                total_matches += len(matches)
                        except Exception as e:
                            scan_results[str(file_path.absolute())] = {
                                "ok": False,
                                "error": str(e),
                                "matches": []
                            }

                    # Log summary for this query
                    files_with_matches = sum(1 for data in scan_results.values() if data.get("matches"))
                    self._log(f"  ✔ Found {total_matches} match(es) in {files_with_matches} file(s)")

                # Store results for this selector
                all_selector_results.append({
                    "query_val": query_val,
                    "query_type": query_type,
                    "scan_results": scan_results,
                    "total_matches": total_matches,
                    "total_files": total_files
                })
                grand_total_matches += total_matches

            # Check for cancellation
            if self.cancelled:
                self._log("\n❌ Process Cancelled by User.")
                self.status_var.set("Extraction cancelled.")
                return

            self._log("\n---------------------------------------------------------------------")
            self._log(f"All queries complete! Total Files Checked: {total_files_scanned if not is_single else 1}")
            self._log(f"Total Matching Elements Found: {grand_total_matches} across {len(queries)} selector(s)")

            # Generate timestamp for file names
            safe_target_name = self._slugify(source_path.stem, "selected_file")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Build query slug (use first query + count if multiple)
            if len(queries) == 1:
                query_slug = self._slugify(queries[0][:60], "selector")
            else:
                query_slug = f"{self._slugify(queries[0][:30], 'selector')}_and_{len(queries)-1}_more"

            # Create run folder for all outputs (reports, CSV, copied files)
            run_folder_name = f"extraction_{safe_target_name}_{query_slug}_{ts}"
            run_folder = output_dir / run_folder_name
            run_folder.mkdir(exist_ok=True)

            # Generate and save detailed report (with display flags)
            self.status_var.set("Generating detailed HTML report...")
            report_html = self.extractor.generate_html_report(
                str(source_path), query_type, ", ".join(queries), attr_name, attr_val,
                all_selector_results, grand_total_matches, total_files_scanned if not is_single else 1, is_single,
                show_outer_xml=show_outer_xml, show_inner_text=show_inner_text
            )

            detailed_report_name = f"Element_Extraction_Report_{safe_target_name}_{query_slug}.html"
            detailed_report_path = run_folder / detailed_report_name

            with open(detailed_report_path, "w", encoding="utf-8") as f:
                f.write(report_html)

            self.last_report_path = str(detailed_report_path.absolute())
            self._log(f"\n📄 Detailed report saved: {run_folder_name}/{detailed_report_name}")

            # Generate and save consolidated summary report
            self.status_var.set("Generating consolidated summary report...")
            summary_html = self.extractor.generate_consolidated_summary_report(
                all_selector_results, str(source_path), ts, is_single
            )

            summary_report_name = f"Element_Extraction_Summary_{safe_target_name}_{query_slug}.html"
            summary_report_path = run_folder / summary_report_name

            with open(summary_report_path, "w", encoding="utf-8") as f:
                f.write(summary_html)

            self.last_summary_report_path = str(summary_report_path.absolute())
            self._log(f"📊 Summary report saved: {run_folder_name}/{summary_report_name}")

            # Generate and save CSV if enabled
            csv_path = ""
            if generate_csv:
                self.status_var.set("Generating CSV export...")
                csv_report_name = f"Element_Extraction_Report_{safe_target_name}_{query_slug}.csv"
                csv_report_path = run_folder / csv_report_name

                self.extractor.export_csv(all_selector_results, csv_report_path)

                self.last_csv_path = str(csv_report_path.absolute())
                csv_path = self.last_csv_path
                self._log(f"📋 CSV export saved: {run_folder_name}/{csv_report_name}")

            # Copy matched files if enabled
            copied_files_count = 0
            copied_folder_path = ""
            if copy_matched_files and grand_total_matches > 0:
                self.status_var.set("Copying matched files...")
                self._log("\n📁 Copying matched source files...")

                # Create subfolder inside run folder for matched files
                copy_folder = run_folder / "matched_files"
                copy_folder.mkdir(exist_ok=True)

                # Collect unique files with matches across all selectors
                files_to_copy = set()
                for selector_result in all_selector_results:
                    for file_path_str, data in selector_result["scan_results"].items():
                        if data.get("ok", True) and data.get("matches"):
                            files_to_copy.add(Path(file_path_str))

                # Copy each file with collision handling
                for src_path in files_to_copy:
                    try:
                        if not src_path.exists():
                            self._log(f"  ⚠️ Source file no longer exists: {src_path.name}")
                            continue

                        dst_path = copy_folder / src_path.name

                        # Handle name collisions
                        counter = 1
                        original_dst = dst_path
                        while dst_path.exists():
                            stem = original_dst.stem
                            suffix = original_dst.suffix
                            dst_path = original_dst.with_name(f"{stem}_{counter}{suffix}")
                            counter += 1

                        shutil.copy2(src_path, dst_path)  # copy2 preserves timestamps
                        copied_files_count += 1
                    except Exception as e:
                        self._log(f"  ⚠️ Could not copy {src_path.name}: {e}")

                copied_folder_path = str(copy_folder.absolute())
                self._log(f"  ✔ Copied {copied_files_count} file(s) to: {run_folder_name}/matched_files/")

            # Record history
            self._record_history_entry(
                self._current_run_settings(
                    str(source_path),
                    ", ".join(queries),
                    str(output_dir),
                    self.last_report_path,
                    self.last_summary_report_path,
                    csv_path,
                    copied_files_count if copy_matched_files else 0,
                    copied_folder_path if copy_matched_files else ""
                )
            )

            self._log(f"\nAll outputs saved to: {run_folder}")
            self.status_var.set(f"Complete! Found {grand_total_matches} match(es) across {len(queries)} selector(s).")
            self.open_last_btn.config(state="normal")

            # Auto-open detailed report if checked
            if self.open_report_var.get():
                webbrowser.open(f"file:///{self.last_report_path}")

        except Exception as e:
            self._log(f"\n❌ Error during extraction:\n{str(e)}")
            self.status_var.set("Extraction failed with errors.")
            messagebox.showerror("Extraction Error", f"An error occurred:\n{str(e)}")

        finally:
            self.run_btn.config(state="normal", text="🚀  RUN ELEMENT EXTRACTION")
            self.cancel_btn.config(state="disabled")

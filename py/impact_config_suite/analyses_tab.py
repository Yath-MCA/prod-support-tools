import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import os
import webbrowser
import json
from datetime import datetime

# Import from the recovered logic
from analyses.book_analyzer import (
    Config,
    Logger,
    Cache,
    ContentAnalyzer,
    ConfigParser,
    ReportGenerator,
)
from analyses.report_template import HTML_TEMPLATE


class AnalysesTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent)

        # Setup logic components
        self.config = Config()
        self.logger = Logger(self.config)
        self.cache = Cache(self.config.CACHE_FILE)
        self.analyzer = ContentAnalyzer(self.cache, self.logger)
        self.config_parser = ConfigParser(self.logger)

        self._build_ui()

    def _build_ui(self):
        # Premium dark theme styling for the frame
        self.style = ttk.Style()
        self.style.configure("Analysis.TFrame", background="#1e293b")
        self.style.configure(
            "Analysis.TLabel",
            background="#1e293b",
            foreground="#94a3b8",
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "AnalysisHeader.TLabel",
            background="#1e293b",
            foreground="#818cf8",
            font=("Segoe UI", 16, "bold"),
        )
        self.style.configure(
            "Analysis.TButton", font=("Segoe UI", 10, "bold"), padding=10
        )
        self.style.configure(
            "AnalysisAction.TButton", background="#10b981", foreground="white"
        )

        main_container = tk.Frame(self, bg="#1e293b", padx=30, pady=30)
        main_container.pack(fill="both", expand=True)

        # Header
        tk.Label(
            main_container,
            text="CONTENT ANALYSIS ENGINE",
            font=("Segoe UI", 18, "bold"),
            fg="#818cf8",
            bg="#1e293b",
        ).pack(pady=(0, 20))

        # Root Path Selection
        tk.Label(
            main_container,
            text="Root Path:",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        self.path_var = tk.StringVar(value=self.config.get("root_path"))
        path_frame = tk.Frame(main_container, bg="#1e293b")
        path_frame.pack(fill="x", pady=(5, 10))
        self.path_entry = tk.Entry(
            path_frame,
            textvariable=self.path_var,
            bg="#334155",
            fg="white",
            border=0,
            font=("Segoe UI", 11),
        )
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))
        browse_btn = tk.Button(
            path_frame,
            text="Browse",
            command=self._browse_path,
            bg="#4f46e5",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=15,
        )
        browse_btn.pack(side="right")

        # Parameter Input
        tk.Label(
            main_container,
            text="Document ID or Client (e.g., ACS, JCIM):",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        self.param_var = tk.StringVar(value=self.config.get("parameter"))
        self.param_entry = tk.Entry(
            main_container,
            textvariable=self.param_var,
            bg="#334155",
            fg="white",
            border=0,
            font=("Segoe UI", 11),
        )
        self.param_entry.pack(fill="x", pady=(5, 10), ipady=8)

        # Recursive Checkbox
        self.recursive_var = tk.BooleanVar(
            value=self.config.current_config.get("recursive")
            if hasattr(self.config, "current_config")
            else False
        )
        # Note: book_analyzer.py Config class has DEFAULTS and load() but uses self._config
        # Setting default from config
        self.recursive_var.set(self.config.get("recursive", False))

        chk = tk.Checkbutton(
            main_container,
            text="Recursive Sub-directory Scan",
            variable=self.recursive_var,
            bg="#1e293b",
            fg="#94a3b8",
            activebackground="#1e293b",
            activeforeground="#818cf8",
            selectcolor="#334155",
            font=("Segoe UI", 10),
        )
        chk.pack(anchor="w", pady=5)

        # Action Buttons
        btn_frame = tk.Frame(main_container, bg="#1e293b")
        btn_frame.pack(fill="x", pady=25)

        run_btn = tk.Button(
            btn_frame,
            text="🚀 GENERATE ANALYSIS REPORT",
            command=self._run_analysis,
            bg="#10b981",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            border=0,
            pady=12,
        )
        run_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            command=self._cancel_process,
            bg="#ef4444",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=15,
            pady=10,
            state="disabled",
        )
        self.cancel_btn.pack(side="left", padx=(0, 10))

        clear_btn = tk.Button(
            btn_frame,
            text="🗑️ Clear Cache",
            command=self._clear_cache,
            bg="#ef4444",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=15,
            pady=10,
        )
        clear_btn.pack(side="right")

        # Status and Info
        self.status_var = tk.StringVar(value="System Ready.")
        status_label = tk.Label(
            main_container,
            textvariable=self.status_var,
            bg="#1e293b",
            fg="#64748b",
            font=("Segoe UI", 10, "italic"),
        )
        status_label.pack(pady=(20, 5))

        self.cache_info = tk.Label(
            main_container,
            text=f"Cached Analysis Items: {len(self.cache)}",
            bg="#1e293b",
            fg="#475569",
            font=("Segoe UI", 9),
        )
        self.cache_info.pack()

    def _browse_path(self):
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(os.path.abspath(path))

    def _clear_cache(self):
        if messagebox.askyesno(
            "Clear Cache", "This will remove all stored analysis results. Proceed?"
        ):
            self.cache.clear()
            self.cache_info.config(text="Cached Analysis Items: 0")
            self.status_var.set("Cache cleared successfully.")

    def _cancel_process(self):
        self.cancelled = True
        self.status_var.set("Process cancelled.")
        self.cancel_btn.config(state="disabled")

    def _run_analysis(self):
        self.cancelled = False
        self.cancel_btn.config(state="normal")
        root_path = self.path_var.get().strip()
        parameter = self.param_var.get().strip()
        recursive = self.recursive_var.get()

        if not root_path or not os.path.exists(root_path):
            messagebox.showerror("Error", "Please provide a valid root directory path.")
            self.cancel_btn.config(state="disabled")
            return

        # Save current settings
        self.config.save(
            {"root_path": root_path, "parameter": parameter, "recursive": recursive}
        )

        self.status_var.set("Scanning document directories...")
        self.update_idletasks()

        # Logic from book_analyzer.py
        pot_doc = Path(root_path) / parameter
        is_id_mode = pot_doc.is_dir() and parameter != ""

        try:
            all_dirs = (
                [pot_doc]
                if is_id_mode
                else self.analyzer.find_doc_dirs(root_path, recursive=recursive)
            )

            if not all_dirs:
                self.status_var.set("No valid document directories found.")
                messagebox.showinfo(
                    "Scanner",
                    "No document folders containing 'impact_config.xml' were found in the specified path.",
                )
                self.cancel_btn.config(state="disabled")
                return

            doc_results = []
            global_stats = {"ch": 0, "fig": 0, "tab": 0, "labels": 0}
            target_client = parameter if parameter else "Full Scan"

            self.status_var.set(f"Analyzing {len(all_dirs)} directories...")

            for i, doc_dir in enumerate(all_dirs):
                if self.cancelled:
                    return

                cfg = self.config_parser.parse(doc_dir)

                # Filter by client if parameter is provided but not matching an ID
                if (
                    not is_id_mode
                    and parameter
                    and parameter.lower() not in cfg["client"].lower()
                    and parameter.lower() not in doc_dir.name.lower()
                ):
                    continue

                self.status_var.set(
                    f"Processing ({i + 1}/{len(all_dirs)}): {doc_dir.name}"
                )
                self.update_idletasks()

                data = self.analyzer.analyze(
                    str(doc_dir), doc_dir.name, is_specific=is_id_mode
                )
                if not data:
                    continue

                # Accummulate stats
                global_stats["ch"] += data["chapters"]
                global_stats["fig"] += len(data["categories"]["fig"]["items"])
                global_stats["tab"] += len(data["categories"]["tab"]["items"])
                for cat in data["categories"].values():
                    for itm in cat["items"]:
                        if itm["label"] != "N/A":
                            global_stats["labels"] += 1

                doc_results.append(
                    {"id": doc_dir.name, "path": doc_dir, "cfg": cfg, "data": data}
                )

            if not doc_results:
                self.status_var.set("No matching data found.")
                messagebox.showinfo(
                    "Analyzer",
                    "Found directories but no relevant content matching the filters.",
                )
                self.cancel_btn.config(state="disabled")
                return

            # Generate Report (using logic from BookAnalyzerUI._run_analysis)
            html_blocks = ReportGenerator.build_doc_blocks(doc_results)
            report = HTML_TEMPLATE.format(
                client=target_client,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                total_docs=len(doc_results),
                total_chapters=global_stats["ch"],
                total_figs=global_stats["fig"],
                total_tables=global_stats["tab"],
                total_labels=global_stats["labels"],
                rows=html_blocks,
            )

            # Save report
            out_name = (
                f"Analysis_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            )
            report_path = self.config.BASE_DIR / out_name

            # Save copies for traceability as in recovered code
            additional_paths = [
                dr["path"] / f"Analysis_Report_Local.html" for dr in doc_results
            ]
            ReportGenerator.save_report(report, str(report_path), additional_paths)

            # Open report
            self.status_var.set(f"Analysis Complete. Report saved to {out_name}")
            self.cache_info.config(text=f"Cached Analysis Items: {len(self.cache)}")
            webbrowser.open(f"file:///{report_path.absolute()}")

        except Exception as e:
            self.logger.error(f"Analysis failed: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror(
                "Error", f"An error occurred during analysis:\n{str(e)}"
            )
        finally:
            self.cancel_btn.config(state="disabled")

        self.status_var.set("🔍 Scanning document directories...")
        self.update_idletasks()

        # Logic from book_analyzer.py
        pot_doc = Path(root_path) / parameter
        is_id_mode = pot_doc.is_dir() and parameter != ""

        try:
            all_dirs = (
                [pot_doc]
                if is_id_mode
                else self.analyzer.find_doc_dirs(root_path, recursive=recursive)
            )

            if not all_dirs:
                self.status_var.set("⚠️ No valid document directories found.")
                messagebox.showinfo(
                    "Scanner",
                    "No document folders containing 'impact_config.xml' were found in the specified path.",
                )
                return

            doc_results = []
            global_stats = {"ch": 0, "fig": 0, "tab": 0, "labels": 0}
            target_client = parameter if parameter else "Full Scan"

            self.status_var.set(f"🧪 Analyzing {len(all_dirs)} directories...")

            for i, doc_dir in enumerate(all_dirs):
                cfg = self.config_parser.parse(doc_dir)

                # Filter by client if parameter is provided but not matching an ID
                if (
                    not is_id_mode
                    and parameter
                    and parameter.lower() not in cfg["client"].lower()
                    and parameter.lower() not in doc_dir.name.lower()
                ):
                    continue

                self.status_var.set(
                    f"Processing ({i + 1}/{len(all_dirs)}): {doc_dir.name}"
                )
                self.update_idletasks()

                data = self.analyzer.analyze(
                    str(doc_dir), doc_dir.name, is_specific=is_id_mode
                )
                if not data:
                    continue

                # Accummulate stats
                global_stats["ch"] += data["chapters"]
                global_stats["fig"] += len(data["categories"]["fig"]["items"])
                global_stats["tab"] += len(data["categories"]["tab"]["items"])
                for cat in data["categories"].values():
                    for itm in cat["items"]:
                        if itm["label"] != "N/A":
                            global_stats["labels"] += 1

                doc_results.append(
                    {"id": doc_dir.name, "path": doc_dir, "cfg": cfg, "data": data}
                )

            if not doc_results:
                self.status_var.set("⚠️ No matching data found.")
                messagebox.showinfo(
                    "Analyzer",
                    "Found directories but no relevant content matching the filters.",
                )
                return

            # Generate Report (using logic from BookAnalyzerUI._run_analysis)
            html_blocks = ReportGenerator.build_doc_blocks(doc_results)
            report = HTML_TEMPLATE.format(
                client=target_client,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                total_docs=len(doc_results),
                total_chapters=global_stats["ch"],
                total_figs=global_stats["fig"],
                total_tables=global_stats["tab"],
                total_labels=global_stats["labels"],
                rows=html_blocks,
            )

            # Save report
            out_name = (
                f"Analysis_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            )
            report_path = self.config.BASE_DIR / out_name

            # Save copies for traceability as in recovered code
            additional_paths = [
                dr["path"] / f"Analysis_Report_Local.html" for dr in doc_results
            ]
            ReportGenerator.save_report(report, str(report_path), additional_paths)

            # Open report
            self.status_var.set(f"✅ Analysis Complete. Report saved to {out_name}")
            self.cache_info.config(text=f"Cached Analysis Items: {len(self.cache)}")
            webbrowser.open(f"file:///{report_path.absolute()}")

        except Exception as e:
            self.logger.error(f"Analysis failed: {str(e)}")
            self.status_var.set(f"❌ Error: {str(e)}")
            messagebox.showerror(
                "Error", f"An error occurred during analysis:\n{str(e)}"
            )

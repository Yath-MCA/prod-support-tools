import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

from core.doi_extractor import DOIExtractor
from core.run_history import RunHistoryStore


class DOIExtractorTab(ttk.Frame):
    """
    Tkinter Tab for DOI Extraction.
    Scans a folder of XML/HTML files for DOI-bearing tags
    (article-id/pub-id/object-id with pub-id-type="doi", and
    ext-link with ext-link-type="doi"), and generates an HTML + CSV report.
    """

    DEFAULT_REPORT_FOLDER_NAME = "impact-support-log"
    HISTORY_LIMIT = 25
    history_tool_id = "doi_extractor"
    history_tool_label = "DOI Extractor"

    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent)
        self.extractor = DOIExtractor()
        self.scan_thread = None
        self.cancelled = False
        self.last_report_path = None
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
    def _load_history_entries(cls) -> list[dict]:
        valid_entries = []
        for item in RunHistoryStore.recent_for_tool(cls.history_tool_id):
            if str(item.get("source_path", "")).strip():
                valid_entries.append(item)
        return valid_entries[:cls.HISTORY_LIMIT]

    def _build_ui(self):
        main_container = tk.Frame(self, bg="#1e293b", padx=30, pady=25)
        main_container.pack(fill="both", expand=True)

        header_frame = tk.Frame(main_container, bg="#1e293b")
        header_frame.pack(fill="x", pady=(0, 15))

        tk.Label(
            header_frame,
            text="🔗 DOI EXTRACTOR",
            font=("Segoe UI", 18, "bold"),
            fg="#818cf8",
            bg="#1e293b",
        ).pack(anchor="w")

        tk.Label(
            header_frame,
            text="Scan a folder of XML/HTML files, extract every DOI (article-id, pub-id, "
                 "object-id, ext-link), and generate a report with validity checks.",
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

        # 1. Scan Root Path
        tk.Label(
            settings_frame,
            text="Scan Root Path:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=5)

        path_frame = tk.Frame(settings_frame, bg="#1e293b")
        path_frame.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5)
        path_frame.columnconfigure(0, weight=1)

        self.path_var = tk.StringVar()
        self.path_entry = tk.Entry(
            path_frame,
            textvariable=self.path_var,
            bg="#334155",
            fg="white",
            border=0,
            font=("Segoe UI", 10),
            insertbackground="white"
        )
        self.path_entry.grid(row=0, column=0, sticky="ew", ipady=6, padx=(0, 10))

        self.browse_btn = tk.Button(
            path_frame,
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

        # 2. Filename Filter
        tk.Label(
            settings_frame,
            text="Filename Filter:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
        ).grid(row=1, column=0, sticky="w", pady=5)

        self.filename_filter_var = tk.StringVar()
        self.filename_filter_entry = tk.Entry(
            settings_frame,
            textvariable=self.filename_filter_var,
            bg="#334155",
            fg="white",
            border=0,
            font=("Segoe UI", 10),
            insertbackground="white",
            width=30,
        )
        self.filename_filter_entry.grid(row=1, column=1, sticky="w", pady=5, ipady=4)

        tk.Label(
            settings_frame,
            text="(optional, e.g. *_original.xml)",
            bg="#1e293b", fg="#64748b", font=("Segoe UI", 8, "italic"),
        ).grid(row=1, column=2, sticky="w", padx=(8, 0))

        # 3. Recursive Search
        tk.Label(
            settings_frame,
            text="Search Options:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
        ).grid(row=2, column=0, sticky="w", pady=5)

        self.recursive_var = tk.BooleanVar(value=True)
        self.recursive_chk = tk.Checkbutton(
            settings_frame,
            text="Recursive Search",
            variable=self.recursive_var,
            bg="#1e293b", fg="#94a3b8", activebackground="#1e293b", activeforeground="#818cf8",
            selectcolor="#334155",
            font=("Segoe UI", 9)
        )
        self.recursive_chk.grid(row=2, column=1, sticky="w", pady=5)

        # 4. Output Folder
        tk.Label(
            settings_frame,
            text="Report Output Folder:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
        ).grid(row=3, column=0, sticky="w", pady=5)

        output_frame = tk.Frame(settings_frame, bg="#1e293b")
        output_frame.grid(row=3, column=1, columnspan=2, sticky="ew", pady=5)
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

        # 5. Open Report After Completion
        self.open_report_var = tk.BooleanVar(value=True)
        self.open_report_chk = tk.Checkbutton(
            settings_frame,
            text="Open HTML report automatically in web browser after completion",
            variable=self.open_report_var,
            bg="#1e293b", fg="#e2e8f0", activebackground="#1e293b", activeforeground="white",
            selectcolor="#334155",
            font=("Segoe UI", 9)
        )
        self.open_report_chk.grid(row=4, column=1, columnspan=2, sticky="w", pady=5)

        # --- History Frame ---
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

        # --- Progress Bar & Status Line ---
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
            text="🚀  RUN DOI EXTRACTION",
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
            text="Activity log and extraction progress:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(10, 5))

        res_frame = tk.Frame(main_container, bg="#0f172a")
        res_frame.pack(fill="both", expand=True)

        self.res_text = tk.Text(
            res_frame,
            bg="#0f172a",
            fg="#34d399",
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

    def _browse_path(self):
        path = filedialog.askdirectory(title="Select Root Directory to Scan")
        if path:
            abs_path = os.path.abspath(path)
            self.path_var.set(abs_path)
            if not self.output_dir_var.get().strip():
                self.output_dir_var.set(str(self._default_output_dir()))

    def _browse_output_dir(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.output_dir_var.set(os.path.abspath(path))

    def _log(self, message: str):
        """Append log message to the text console."""
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

    def _history_summary(self, entry: dict) -> str:
        ts = str(entry.get("timestamp", "")).strip() or "Unknown time"
        filename_filter = str(entry.get("filename_filter", "")).strip() or "All files"
        recursive = "recursive" if entry.get("recursive", True) else "non-recursive"
        source_name = Path(str(entry.get("source_path", "")).strip() or ".").name
        total_dois = entry.get("params", {}).get("total_dois", 0)
        return f"{ts} | {filename_filter} | {recursive} | {source_name} | {total_dois} DOIs"

    def _restore_last_history_state(self) -> None:
        if not self.history_entries:
            return
        latest = self.history_entries[0]
        report_path = str(latest.get("report_path", "")).strip()
        if report_path and os.path.exists(report_path):
            self.last_report_path = report_path
            self.open_last_btn.config(state="normal")

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
        self.path_var.set(str(entry.get("source_path", "")).strip())
        self.filename_filter_var.set(str(entry.get("filename_filter", "")).strip())
        self.recursive_var.set(bool(entry.get("recursive", True)))
        self.output_dir_var.set(str(entry.get("output_dir", str(self._default_output_dir()))).strip())
        self.open_report_var.set(bool(entry.get("open_report", True)))
        report_path = str(entry.get("report_path", "")).strip()
        if report_path:
            self.last_report_path = report_path
            self.open_last_btn.config(state="normal")
        self.status_var.set("History entry applied.")

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

    def _current_run_settings(self, source_path: str, output_dir: str, report_path: str,
                               csv_path: str, result: dict) -> dict:
        return {
            "tool_id": self.history_tool_id,
            "tool_label": self.history_tool_label,
            "action": "doi_extraction",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_path": source_path,
            "filename_filter": self.filename_filter_var.get().strip(),
            "recursive": bool(self.recursive_var.get()),
            "output_dir": output_dir,
            "open_report": bool(self.open_report_var.get()),
            "report_path": report_path,
            "csv_path": csv_path,
            "summary": f"{result.get('total_dois', 0)} DOIs in {result.get('total_files', 0)} files",
            "params": {
                "filename_filter": self.filename_filter_var.get().strip(),
                "recursive": bool(self.recursive_var.get()),
                "open_report": bool(self.open_report_var.get()),
                "total_files": result.get("total_files", 0),
                "total_dois": result.get("total_dois", 0),
                "unique_doi_count": result.get("unique_doi_count", 0),
                "invalid_doi_count": result.get("invalid_doi_count", 0),
            },
        }

    def _record_history_entry(self, entry: dict) -> None:
        try:
            RunHistoryStore.add_entry(entry)
            self.after(0, self._update_history_ui)
        except Exception as e:
            self.after(0, lambda msg=str(e): self._log(f"⚠️ Failed to save history: {msg}"))

    def _update_history_ui(self) -> None:
        try:
            self.history_entries = self._load_history_entries()
            self.filtered_history_entries = list(self.history_entries)
            self._refresh_history_list()
        except Exception as e:
            self._log(f"⚠️ Failed to refresh history UI: {e}")

    def _start_extraction(self):
        source_path = self.path_var.get().strip()
        output_dir = self.output_dir_var.get().strip()

        if not source_path:
            messagebox.showerror("Error", "Please provide a valid scan root path.")
            return
        if not os.path.exists(source_path):
            messagebox.showerror("Error", f"Source path does not exist:\n{source_path}")
            return
        if not os.path.isdir(source_path):
            messagebox.showerror("Error", f"Source path is not a directory:\n{source_path}")
            return
        if not output_dir:
            messagebox.showerror("Error", "Please specify an output folder to save the reports.")
            return
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create output directory:\n{str(e)}")
                return

        self.res_text.delete("1.0", tk.END)
        self.run_btn.config(state="disabled", text="⏳ EXTRACTING DOIs...")
        self.cancel_btn.config(state="normal")
        self.progress_bar.config(value=0)

        self.cancelled = False

        self.scan_thread = threading.Thread(
            target=self._run_extraction_thread,
            args=(source_path, output_dir),
            daemon=True
        )
        self.scan_thread.start()

    def _cancel_extraction(self):
        self.cancelled = True
        self._log("\n⚠️ Cancellation requested. Stopping extraction...")
        self.status_var.set("Cancellation requested...")
        self.cancel_btn.config(state="disabled")

    def _open_last_report(self):
        if self.last_report_path and os.path.exists(self.last_report_path):
            webbrowser.open(f"file:///{os.path.abspath(self.last_report_path)}")
        else:
            messagebox.showerror("Error", "Last report path is invalid or missing.")

    def _run_extraction_thread(self, source_path: str, output_dir: str):
        try:
            recursive = bool(self.recursive_var.get())
            filename_filter = self.filename_filter_var.get().strip() or None

            self._log(f"🚀 Starting DOI Extraction - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._log(f"  Source Path:      {source_path}")
            self._log(f"  Filename Filter:  {filename_filter or 'None (all XML/HTML files)'}")
            self._log(f"  Recursive:        {recursive}")
            self._log(f"  Output Folder:    {output_dir}")
            self._log("---------------------------------------------------------------------\n")

            def progress_callback(stage: str, current: int, total: int, message: str):
                if self.cancelled:
                    return
                if total > 0:
                    percent = int((current / total) * 100)
                    self.progress_bar.config(value=percent)

                stage_labels = {"scan": "Scanning files", "report": "Generating reports"}
                stage_label = stage_labels.get(stage, stage)
                self.status_var.set(f"{stage_label}: {message}")
                self._log(f"[{stage_label}] {message}")

            result = self.extractor.run_extraction(
                root_path=source_path,
                output_dir=output_dir,
                recursive=recursive,
                filename_filter=filename_filter,
                progress_callback=progress_callback,
            )

            if self.cancelled:
                self._log("\n❌ Extraction Cancelled by User.")
                self.status_var.set("Extraction cancelled.")
                return

            self._log("\n---------------------------------------------------------------------")
            self._log(f"✅ Extraction Complete!")
            self._log(f"  Files Scanned:      {result['total_files']}")
            self._log(f"  Files With DOI:     {result['files_with_doi']}")
            self._log(f"  Files Without DOI:  {result['files_without_doi']}")
            self._log(f"  Total DOI Matches:  {result['total_dois']}")
            self._log(f"  Unique DOIs:        {result['unique_doi_count']}")
            self._log(f"  Invalid DOIs:       {result['invalid_doi_count']}")
            self._log(f"\n📄 HTML Report: {result['html_path']}")
            self._log(f"📋 CSV Export:  {result['csv_path']}")
            self._log(f"📁 Run Folder:  {result['run_folder']}")

            self.last_report_path = result['html_path']
            self.last_csv_path = result['csv_path']

            history_entry = self._current_run_settings(
                source_path, output_dir, self.last_report_path, self.last_csv_path, result
            )
            self._record_history_entry(history_entry)

            self.status_var.set(
                f"Complete! {result['total_dois']} DOIs found across {result['total_files']} files."
            )
            self.open_last_btn.config(state="normal")

            if self.open_report_var.get():
                webbrowser.open(f"file:///{self.last_report_path}")

        except Exception as e:
            self._log(f"\n❌ Error during extraction:\n{str(e)}")
            self.status_var.set("Extraction failed with errors.")
            messagebox.showerror("Extraction Error", f"An error occurred:\n{str(e)}")

        finally:
            self.run_btn.config(state="normal", text="🚀  RUN DOI EXTRACTION")
            self.cancel_btn.config(state="disabled")

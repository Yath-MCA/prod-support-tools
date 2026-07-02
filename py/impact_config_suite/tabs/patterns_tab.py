import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import webbrowser
from datetime import datetime
import glob

from core.run_history import RunHistoryStore
# Import logic from recovered patterns module
from patterns import report_config as cfg
from patterns.report_log import log
from patterns.report_extract import process_config
from patterns.report_patterns import build_patterns, save_patterns_json
from patterns.report_writer import write_json, write_html, write_excel


class PatternsTab(ttk.Frame):
    history_tool_id = "patterns"
    history_tool_label = "Patterns"

    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent)
        self.last_report_path = ""
        self._build_ui()

    def _build_ui(self):
        main_container = tk.Frame(self, bg="#1e293b", padx=30, pady=30)
        main_container.pack(fill="both", expand=True)

        # Header
        tk.Label(
            main_container,
            text="JOURNAL PATTERNS REPORTER",
            font=("Segoe UI", 18, "bold"),
            fg="#a855f7",
            bg="#1e293b",
        ).pack(pady=(0, 20))

        # Config Source Path
        tk.Label(
            main_container,
            text="Source Config Directory (src/clientconfig):",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        self.path_var = tk.StringVar(value=cfg.CLIENTCONFIG_DIR)
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

        # Pattern Filter
        tk.Label(
            main_container,
            text="Search Pattern (Glob):",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        self.pattern_var = tk.StringVar(value="**/config.xml")
        self.pattern_entry = tk.Entry(
            main_container,
            textvariable=self.pattern_var,
            bg="#334155",
            fg="white",
            border=0,
            font=("Segoe UI", 11),
        )
        self.pattern_entry.pack(fill="x", pady=(5, 10), ipady=8)

        # Action Buttons
        btn_frame = tk.Frame(main_container, bg="#1e293b")
        btn_frame.pack(fill="x", pady=25)

        self.run_btn = tk.Button(
            btn_frame,
            text="📊 GENERATE GLOBAL PATTERNS REPORT",
            command=self._start_report_thread,
            bg="#a855f7",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            border=0,
            pady=12,
        )
        self.run_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

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
        self.cancel_btn.pack(side="left")

        # Log Display
        tk.Label(
            main_container,
            text="Processing Logs:",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(10, 0))
        self.log_text = tk.Text(
            main_container,
            bg="#0f172a",
            fg="#10b981",
            border=0,
            font=("Consolas", 10),
            height=10,
        )
        self.log_text.pack(fill="both", expand=True, pady=10)

        # Status
        self.status_var = tk.StringVar(value="Ready.")
        status_label = tk.Label(
            main_container,
            textvariable=self.status_var,
            bg="#1e293b",
            fg="#64748b",
            font=("Segoe UI", 10, "italic"),
        )
        status_label.pack()

    def _browse_path(self):
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(os.path.abspath(path))

    def _log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.update_idletasks()

    def _start_report_thread(self):
        self.run_btn.config(state="disabled", text="PROCESSING...")
        self.cancel_btn.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.cancelled = False
        threading.Thread(target=self._run_patterns_report, daemon=True).start()

    def _cancel_process(self):
        self.cancelled = True
        self._log("\n[CANCELLED] Process cancelled by user.")
        self.run_btn.config(state="normal", text="📊 GENERATE GLOBAL PATTERNS REPORT")
        self.cancel_btn.config(state="disabled")
        self.status_var.set("Process cancelled.")

    def _run_patterns_report(self):
        try:
            if self.cancelled:
                return

            source_dir = self.path_var.get()
            pattern = self.pattern_var.get()
            full_pattern = os.path.join(source_dir, pattern)

            self._log(f"Searching for configs in: {source_dir}")
            self._log(f"Pattern: {pattern}")

            files = glob.glob(full_pattern, recursive=True)
            self._log(f"Found {len(files)} XML configuration files.")

            if not files:
                self.status_var.set("No files found.")
                self.run_btn.config(
                    state="normal", text="📊 GENERATE GLOBAL PATTERNS REPORT"
                )
                self.cancel_btn.config(state="disabled")
                return

            self.status_var.set(f"Processing {len(files)} files...")
            reps = []
            for i, f in enumerate(files):
                if self.cancelled:
                    return
                self._log(
                    f"[{i + 1}/{len(files)}] Processing {os.path.basename(os.path.dirname(f))}"
                )
                r = process_config(f)
                if r:
                    reps.append(r)

            self._log("Analyzing pattern signatures...")
            patterns, mapping, sigs = build_patterns(reps)

            # Setup output paths
            run_ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            out_dir = os.path.join(os.path.dirname(cfg.OUT_HTML), "reports")
            os.makedirs(out_dir, exist_ok=True)

            out_html = os.path.join(out_dir, f"Patterns_Report_{run_ts}.html")
            out_json = os.path.join(out_dir, f"Patterns_Data_{run_ts}.json")
            out_xlsx = os.path.join(out_dir, f"Patterns_Audit_{run_ts}.xlsx")
            out_pats = os.path.join(out_dir, f"Patterns_Index_{run_ts}.json")

            self._log("Generating artifacts...")
            save_patterns_json(patterns, out_pats)
            write_json(reps, patterns, out_json)
            write_html(reps, patterns, mapping, sigs, out_html, run_ts)

            # Excel might fail if open or missing openpyxl
            try:
                write_excel(reps, patterns, out_xlsx)
            except Exception as e:
                self._log(f"Excel generation skipped: {e}")

            self._log(f"Done! Report saved to: {os.path.basename(out_html)}")
            self.status_var.set("Report Generated.")
            self.last_report_path = os.path.abspath(out_html)
            self._record_history(source_dir, pattern, out_dir, self.last_report_path)

            if messagebox.askyesno(
                "Success", f"Report generated successfully.\nView report now?"
            ):
                webbrowser.open(f"file:///{os.path.abspath(out_html)}")

        except Exception as e:
            self._log(f"ERROR: {str(e)}")
            self.status_var.set("Report failed.")
            messagebox.showerror("Error", f"Pattern analysis failed: {e}")
        finally:
            self.run_btn.config(
                state="normal", text="📊 GENERATE GLOBAL PATTERNS REPORT"
            )
            self.cancel_btn.config(state="disabled")

    def _record_history(self, source_dir: str, pattern: str, output_dir: str, report_path: str) -> None:
        RunHistoryStore.add_entry(
            {
                "tool_id": self.history_tool_id,
                "tool_label": self.history_tool_label,
                "action": "generate_report",
                "summary": f"Pattern: {pattern}",
                "source_path": source_dir,
                "output_dir": output_dir,
                "report_path": report_path,
                "params": {
                    "source_dir": source_dir,
                    "pattern": pattern,
                    "output_dir": output_dir,
                },
            }
        )

    def apply_history_entry(self, entry: dict) -> bool:
        params = entry.get("params", {})
        source_dir = str(params.get("source_dir", "")).strip() or str(entry.get("source_path", "")).strip()
        pattern = str(params.get("pattern", "")).strip()
        if source_dir:
            self.path_var.set(source_dir)
        if pattern:
            self.pattern_var.set(pattern)
        report_path = str(entry.get("report_path", "")).strip()
        if report_path:
            self.last_report_path = report_path
        return True

    def rerun_history_entry(self, entry: dict) -> bool:
        self.apply_history_entry(entry)
        self._start_report_thread()
        return True

"""Footnotes Group Report tab - GUI for core.fn_group_report (BITS books)."""
from __future__ import annotations

import os
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import ttk

from core import fn_group_report as fgr


class FnGroupReportTab(ttk.Frame):
    """Unique fn-group / ref-list patterns by client x DTD basename (BITS only)."""

    history_tool_id = "fn_group_report"
    history_tool_label = "Footnotes Group Report"

    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent)
        self.run_thread: threading.Thread | None = None
        self.cancelled = False
        self.last_report_path: str | None = None
        self.last_report_dir: str | None = None
        self.last_csv_path: str | None = None
        self.last_tsv_path: str | None = None
        self.last_id_csv_path: str | None = None
        self._build_ui()

    def _build_ui(self):
        main = tk.Frame(self, bg="#1e293b", padx=24, pady=18)
        main.pack(fill="both", expand=True)

        header = tk.Frame(main, bg="#1e293b")
        header.pack(fill="x", pady=(0, 12))
        tk.Label(
            header,
            text="FOOTNOTES GROUP REPORT",
            font=("Segoe UI", 18, "bold"),
            fg="#818cf8",
            bg="#1e293b",
        ).pack(anchor="w")
        tk.Label(
            header,
            text="BITS books only: unique fn-group and ref-list CSS-like patterns "
                 "(ids dropped), rolled up by client × DTD basename × placement "
                 "(chapter-end / book-end / front-matter). Optionally writes "
                 "dtd_basename into meta.json and documents.json.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b",
            wraplength=920,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

        settings = tk.LabelFrame(
            main, text="Input", bg="#1e293b", fg="#cbd5e1",
            font=("Segoe UI", 10, "bold"), padx=16, pady=12, bd=1, relief="flat",
        )
        settings.pack(fill="x", pady=(0, 10))
        settings.columnconfigure(1, weight=1)

        tk.Label(
            settings, text="Project / Folder:", bg="#1e293b", fg="#94a3b8",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=4)
        path_fr = tk.Frame(settings, bg="#1e293b")
        path_fr.grid(row=0, column=1, sticky="ew", pady=4)
        path_fr.columnconfigure(0, weight=1)
        self.root_var = tk.StringVar()
        tk.Entry(
            path_fr, textvariable=self.root_var, bg="#334155", fg="white", border=0,
            font=("Segoe UI", 10), insertbackground="white",
        ).grid(row=0, column=0, sticky="ew", ipady=5, padx=(0, 8))
        tk.Button(
            path_fr, text="Browse", command=self._browse_root, bg="#4f46e5", fg="white",
            font=("Segoe UI", 9, "bold"), border=0, padx=12, pady=4, cursor="hand2",
        ).grid(row=0, column=1)

        tk.Label(
            settings, text="Client filter:", bg="#1e293b", fg="#94a3b8",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=1, column=0, sticky="w", pady=4)
        self.client_var = tk.StringVar()
        tk.Entry(
            settings, textvariable=self.client_var, bg="#334155", fg="white", border=0,
            font=("Segoe UI", 10), insertbackground="white", width=40,
        ).grid(row=1, column=1, sticky="w", pady=4, ipady=4)
        tk.Label(
            settings,
            text="(optional; comma-separated, e.g. TNF,OSO)",
            bg="#1e293b", fg="#64748b", font=("Segoe UI", 8, "italic"),
        ).grid(row=1, column=2, sticky="w", padx=(8, 0))

        tk.Label(
            settings, text="Shortcode filter:", bg="#1e293b", fg="#94a3b8",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=2, column=0, sticky="w", pady=4)
        self.shortcode_var = tk.StringVar()
        tk.Entry(
            settings, textvariable=self.shortcode_var, bg="#334155", fg="white", border=0,
            font=("Segoe UI", 10), insertbackground="white", width=40,
        ).grid(row=2, column=1, sticky="w", pady=4, ipady=4)

        self.folder_mode_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            settings,
            text="Folder mode (scan *.xml; ignore documents.json index; still uses meta.json when present)",
            variable=self.folder_mode_var,
            bg="#1e293b", fg="#94a3b8", activebackground="#1e293b",
            activeforeground="#818cf8", selectcolor="#334155",
            font=("Segoe UI", 9),
        ).grid(row=3, column=1, sticky="w", pady=4)

        self.update_meta_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            settings,
            text="Update meta.json and documents.json with dtd_basename",
            variable=self.update_meta_var,
            bg="#1e293b", fg="#e2e8f0", activebackground="#1e293b",
            activeforeground="white", selectcolor="#334155",
            font=("Segoe UI", 9),
        ).grid(row=4, column=1, sticky="w", pady=4)

        self.open_report_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            settings,
            text="Open HTML report in browser when finished",
            variable=self.open_report_var,
            bg="#1e293b", fg="#e2e8f0", activebackground="#1e293b",
            activeforeground="white", selectcolor="#334155",
            font=("Segoe UI", 9),
        ).grid(row=5, column=1, sticky="w", pady=4)

        self.progress_frame = tk.Frame(main, bg="#1e293b")
        self.progress_frame.pack(fill="x", pady=(4, 0))
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, orient="horizontal", mode="determinate"
        )
        self.progress_bar.pack(fill="x", side="top", pady=(0, 5))
        self.status_var = tk.StringVar(
            value="Ready. Pick a BITS project folder and click Run."
        )
        tk.Label(
            self.progress_frame, textvariable=self.status_var,
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "italic"),
        ).pack(side="left")

        btn_fr = tk.Frame(main, bg="#1e293b")
        btn_fr.pack(fill="x", pady=(10, 12))
        self.run_btn = tk.Button(
            btn_fr, text="RUN FOOTNOTES GROUP REPORT", command=self._start_run,
            bg="#10b981", fg="white", font=("Segoe UI", 11, "bold"),
            border=0, padx=20, pady=12, cursor="hand2",
        )
        self.run_btn.pack(side="left", fill="x", expand=True)
        self.cancel_btn = tk.Button(
            btn_fr, text="Cancel", command=self._cancel_run,
            bg="#ef4444", fg="white", font=("Segoe UI", 10, "bold"),
            border=0, padx=16, pady=12, state="disabled", cursor="hand2",
        )
        self.cancel_btn.pack(side="left", padx=(10, 0))
        self.open_folder_btn = tk.Button(
            btn_fr, text="Open Report Folder", command=self._open_reports_folder,
            bg="#4f46e5", fg="white", font=("Segoe UI", 10, "bold"),
            border=0, padx=16, pady=12, state="disabled", cursor="hand2",
        )
        self.open_folder_btn.pack(side="right", padx=(10, 0))
        self.open_last_btn = tk.Button(
            btn_fr, text="Open Last HTML", command=self._open_last_report,
            bg="#7c3aed", fg="white", font=("Segoe UI", 10, "bold"),
            border=0, padx=16, pady=12, state="disabled", cursor="hand2",
        )
        self.open_last_btn.pack(side="right", padx=(10, 0))
        self.open_csv_btn = tk.Button(
            btn_fr, text="Open Unique CSV", command=self._open_unique_csv,
            bg="#0ea5e9", fg="white", font=("Segoe UI", 10, "bold"),
            border=0, padx=16, pady=12, state="disabled", cursor="hand2",
        )
        self.open_csv_btn.pack(side="right", padx=(10, 0))
        self.open_tsv_btn = tk.Button(
            btn_fr, text="Open Detail TSV", command=self._open_detail_tsv,
            bg="#0284c7", fg="white", font=("Segoe UI", 10, "bold"),
            border=0, padx=16, pady=12, state="disabled", cursor="hand2",
        )
        self.open_tsv_btn.pack(side="right", padx=(10, 0))
        self.open_id_csv_btn = tk.Button(
            btn_fr, text="Open ID Patterns CSV", command=self._open_id_patterns_csv,
            bg="#0369a1", fg="white", font=("Segoe UI", 10, "bold"),
            border=0, padx=16, pady=12, state="disabled", cursor="hand2",
        )
        self.open_id_csv_btn.pack(side="right")

        tk.Label(
            main, text="Activity log:", bg="#1e293b", fg="#94a3b8",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(4, 4))
        res_fr = tk.Frame(main, bg="#0f172a")
        res_fr.pack(fill="both", expand=True)
        self.res_text = tk.Text(
            res_fr, bg="#0f172a", fg="#34d399", insertbackground="white",
            border=0, font=("Consolas", 10), padx=12, pady=12,
        )
        scroll = ttk.Scrollbar(res_fr, command=self.res_text.yview)
        self.res_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.res_text.pack(fill="both", expand=True)

    def _log(self, msg: str):
        def append():
            self.res_text.insert(tk.END, msg + "\n")
            self.res_text.see(tk.END)

        self.after(0, append)

    def _browse_root(self):
        path = filedialog.askdirectory(title="Select Project Root or XML Folder")
        if path:
            self.root_var.set(os.path.abspath(path))

    def _start_run(self):
        root = self.root_var.get().strip().strip('"')
        if not root or not Path(root).is_dir():
            messagebox.showerror(
                "Footnotes Group Report", "Please select a valid project or folder path."
            )
            return
        if self.run_thread and self.run_thread.is_alive():
            messagebox.showinfo(
                "Footnotes Group Report", "A run is already in progress."
            )
            return

        sc_raw = self.shortcode_var.get().strip()
        shortcodes = [s.strip() for s in sc_raw.split(",") if s.strip()] if sc_raw else None
        cl_raw = self.client_var.get().strip()
        clients = [c.strip() for c in cl_raw.split(",") if c.strip()] if cl_raw else None
        folder_mode = bool(self.folder_mode_var.get())
        update_meta = bool(self.update_meta_var.get())

        self.cancelled = False
        self.run_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.progress_bar["value"] = 0
        self.status_var.set("Running.")
        self.res_text.delete("1.0", tk.END)
        self._log(f"Starting Footnotes Group Report v{fgr.REPORT_VERSION} on {root}")

        def worker():
            result = None
            error = None
            try:
                result = fgr.run_fn_group_report(
                    root,
                    shortcodes=shortcodes,
                    clients=clients,
                    folder_mode=folder_mode,
                    update_meta=update_meta,
                    log=self._log,
                    progress=self._on_progress,
                    cancel_check=lambda: self.cancelled,
                )
            except Exception as exc:  # noqa: BLE001
                error = exc
            self.after(0, lambda: self._on_finished(result, error))

        self.run_thread = threading.Thread(target=worker, daemon=True)
        self.run_thread.start()

    def _on_progress(self, current: int, total: int, message: str):
        def update():
            self.progress_bar["maximum"] = max(total, 1)
            self.progress_bar["value"] = current
            self.status_var.set(f"{current}/{total}: {message}")

        self.after(0, update)

    def _on_finished(self, result, error):
        self.run_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        if error is not None:
            self.status_var.set(f"Failed: {error}")
            self._log(f"ERROR: {error}")
            messagebox.showerror("Footnotes Group Report", str(error))
            return
        if not result:
            self.status_var.set("No result.")
            return
        self.last_report_path = result.get("html_path")
        self.last_report_dir = result.get("report_dir")
        self.last_csv_path = result.get("csv_path")
        self.last_tsv_path = result.get("tsv_path")
        self.last_id_csv_path = result.get("id_patterns_csv_path")
        self.open_folder_btn.config(state="normal")
        if self.last_report_path and Path(self.last_report_path).is_file():
            self.open_last_btn.config(state="normal")
        if self.last_csv_path and Path(self.last_csv_path).is_file():
            self.open_csv_btn.config(state="normal")
        if self.last_tsv_path and Path(self.last_tsv_path).is_file():
            self.open_tsv_btn.config(state="normal")
        if self.last_id_csv_path and Path(self.last_id_csv_path).is_file():
            self.open_id_csv_btn.config(state="normal")
        self.status_var.set(
            f"Done - {result.get('n_docs', 0)} BITS doc(s), "
            f"{result.get('n_unique', 0)} unique pattern(s), "
            f"{result.get('excluded_table_fn', 0)} table-fn skipped. "
            f"Report: {self.last_report_dir}"
        )
        self._log(f"Report folder: {self.last_report_dir}")
        if self.open_report_var.get() and self.last_report_path:
            try:
                webbrowser.open(Path(self.last_report_path).as_uri())
            except Exception:
                pass

    def _cancel_run(self):
        self.cancelled = True
        self.status_var.set("Cancelling.")

    def _open_reports_folder(self):
        folder = self.last_report_dir or str(fgr.default_report_root())
        path = Path(folder)
        if not path.is_dir():
            messagebox.showinfo("Footnotes Group Report", f"Folder not found:\n{folder}")
            return
        os.startfile(str(path))  # noqa: S606 - Windows open folder

    def _open_last_report(self):
        if not self.last_report_path or not Path(self.last_report_path).is_file():
            messagebox.showinfo("Footnotes Group Report", "No report available yet.")
            return
        webbrowser.open(Path(self.last_report_path).as_uri())

    def _open_path_file(self, path: str | None, label: str):
        if not path or not Path(path).is_file():
            messagebox.showinfo("Footnotes Group Report", f"No {label} available yet.")
            return
        os.startfile(str(path))  # noqa: S606 - Windows open file

    def _open_unique_csv(self):
        self._open_path_file(self.last_csv_path, "unique patterns CSV")

    def _open_detail_tsv(self):
        self._open_path_file(self.last_tsv_path, "detail TSV")

    def _open_id_patterns_csv(self):
        self._open_path_file(self.last_id_csv_path, "ID patterns CSV")

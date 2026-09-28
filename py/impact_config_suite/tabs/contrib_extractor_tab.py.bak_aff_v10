"""Contrib Extract tab — GUI for core.contrib_extractor."""
from __future__ import annotations

import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import ttk

from core import contrib_extractor as ce


class ContribExtractorTab(ttk.Frame):
    """Extract <contrib-group> per JATS shortcode and build HTML reports."""

    history_tool_id = "contrib_extractor"
    history_tool_label = "Contrib Extract"

    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent)
        self.run_thread: threading.Thread | None = None
        self.cancelled = False
        self.last_report_path: str | None = None
        self._docs: dict = {}
        self._metas: dict = {}
        self._index: dict = {}
        self._done: dict = {}
        self._overview: dict | None = None
        self._pair_keys: list[tuple[str, str]] = []  # listbox order
        self._build_ui()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        main = tk.Frame(self, bg="#1e293b", padx=24, pady=18)
        main.pack(fill="both", expand=True)

        header = tk.Frame(main, bg="#1e293b")
        header.pack(fill="x", pady=(0, 12))
        tk.Label(
            header,
            text="👥 CONTRIB EXTRACT",
            font=("Segoe UI", 18, "bold"),
            fg="#818cf8",
            bg="#1e293b",
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Extract <contrib-group> for JATS documents (meta.json client / shortcode), "
                 "write per-doc preview + one HTML report per shortcode, track progress in meta-contrib.json.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b",
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

        # --- Project root ---
        settings = tk.LabelFrame(
            main, text="Project", bg="#1e293b", fg="#cbd5e1",
            font=("Segoe UI", 10, "bold"), padx=16, pady=12, bd=1, relief="flat",
        )
        settings.pack(fill="x", pady=(0, 10))
        settings.columnconfigure(1, weight=1)

        tk.Label(settings, text="Project Root:", bg="#1e293b", fg="#94a3b8",
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=4)
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
        ).grid(row=0, column=1, padx=(0, 6))
        tk.Button(
            path_fr, text="Load / Refresh", command=self._load_overview, bg="#059669", fg="white",
            font=("Segoe UI", 9, "bold"), border=0, padx=12, pady=4, cursor="hand2",
        ).grid(row=0, column=2)

        tk.Label(settings, text="DTD:", bg="#1e293b", fg="#94a3b8",
                 font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=4)
        self.dtd_var = tk.StringVar(value=ce.RUN_DTD)
        tk.Entry(
            settings, textvariable=self.dtd_var, state="readonly",
            readonlybackground="#334155", fg="#94a3b8", border=0, font=("Segoe UI", 10), width=12,
        ).grid(row=1, column=1, sticky="w", pady=4, ipady=4)

        # --- Overview + selection ---
        mid = tk.Frame(main, bg="#1e293b")
        mid.pack(fill="both", expand=True, pady=(0, 10))
        mid.columnconfigure(0, weight=3)
        mid.columnconfigure(1, weight=2)
        mid.rowconfigure(0, weight=1)

        ov_fr = tk.LabelFrame(
            mid, text="Overview", bg="#1e293b", fg="#cbd5e1",
            font=("Segoe UI", 10, "bold"), padx=10, pady=8, bd=1, relief="flat",
        )
        ov_fr.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ov_fr.rowconfigure(0, weight=1)
        ov_fr.columnconfigure(0, weight=1)
        self.overview_text = tk.Text(
            ov_fr, height=14, bg="#0f172a", fg="#e2e8f0", insertbackground="white",
            font=("Consolas", 9), border=0, wrap="none",
        )
        self.overview_text.grid(row=0, column=0, sticky="nsew")
        ov_scroll = ttk.Scrollbar(ov_fr, command=self.overview_text.yview)
        ov_scroll.grid(row=0, column=1, sticky="ns")
        self.overview_text.configure(yscrollcommand=ov_scroll.set)

        sel_fr = tk.LabelFrame(
            mid, text="Selection", bg="#1e293b", fg="#cbd5e1",
            font=("Segoe UI", 10, "bold"), padx=10, pady=8, bd=1, relief="flat",
        )
        sel_fr.grid(row=0, column=1, sticky="nsew")
        sel_fr.rowconfigure(1, weight=1)
        sel_fr.rowconfigure(3, weight=2)
        sel_fr.columnconfigure(0, weight=1)

        tk.Label(sel_fr, text="Clients", bg="#1e293b", fg="#94a3b8",
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        self.client_list = tk.Listbox(
            sel_fr, selectmode="extended", bg="#334155", fg="white",
            font=("Segoe UI", 9), border=0, exportselection=False, height=6,
        )
        self.client_list.grid(row=1, column=0, sticky="nsew", pady=(2, 6))
        self.client_list.bind("<<ListboxSelect>>", self._on_client_select)

        tk.Label(sel_fr, text="Shortcodes (status)", bg="#1e293b", fg="#94a3b8",
                 font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w")
        self.sc_list = tk.Listbox(
            sel_fr, selectmode="extended", bg="#334155", fg="white",
            font=("Segoe UI", 9), border=0, exportselection=False, height=10,
        )
        self.sc_list.grid(row=3, column=0, sticky="nsew", pady=(2, 4))

        btn_row = tk.Frame(sel_fr, bg="#1e293b")
        btn_row.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        tk.Button(
            btn_row, text="Select pending", command=self._select_pending,
            bg="#475569", fg="white", font=("Segoe UI", 8, "bold"), border=0, padx=8, pady=3,
        ).pack(side="left", padx=(0, 4))
        tk.Button(
            btn_row, text="Select all", command=self._select_all_shortcodes,
            bg="#475569", fg="white", font=("Segoe UI", 8, "bold"), border=0, padx=8, pady=3,
        ).pack(side="left", padx=(0, 4))
        tk.Button(
            btn_row, text="Clear", command=self._clear_shortcodes,
            bg="#475569", fg="white", font=("Segoe UI", 8, "bold"), border=0, padx=8, pady=3,
        ).pack(side="left")

        # --- Delays + run ---
        run_fr = tk.LabelFrame(
            main, text="Run", bg="#1e293b", fg="#cbd5e1",
            font=("Segoe UI", 10, "bold"), padx=16, pady=10, bd=1, relief="flat",
        )
        run_fr.pack(fill="x", pady=(0, 10))

        delay_row = tk.Frame(run_fr, bg="#1e293b")
        delay_row.pack(fill="x", pady=(0, 8))
        tk.Label(delay_row, text="Pause between shortcodes (s):", bg="#1e293b", fg="#94a3b8",
                 font=("Segoe UI", 9)).pack(side="left")
        self.delay_sc_var = tk.DoubleVar(value=float(ce.DELAY_SHORTCODE_SEC))
        tk.Spinbox(
            delay_row, from_=0, to=600, increment=1, textvariable=self.delay_sc_var,
            width=6, bg="#334155", fg="white", buttonbackground="#475569",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(6, 16))
        tk.Label(delay_row, text="Pause between clients (s):", bg="#1e293b", fg="#94a3b8",
                 font=("Segoe UI", 9)).pack(side="left")
        self.delay_cl_var = tk.DoubleVar(value=float(ce.DELAY_CLIENT_SEC))
        tk.Spinbox(
            delay_row, from_=0, to=600, increment=1, textvariable=self.delay_cl_var,
            width=6, bg="#334155", fg="white", buttonbackground="#475569",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(6, 16))
        tk.Label(delay_row, text="(0 = no pause)", bg="#1e293b", fg="#64748b",
                 font=("Segoe UI", 8, "italic")).pack(side="left")

        self.regen_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            run_fr, text="Regenerate filled shortcodes if selected (same as CLI 'all' for selection)",
            variable=self.regen_var, bg="#1e293b", fg="#e2e8f0",
            activebackground="#1e293b", activeforeground="white",
            selectcolor="#334155", font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 6))

        action = tk.Frame(run_fr, bg="#1e293b")
        action.pack(fill="x")
        self.run_btn = tk.Button(
            action, text="Run Extract", command=self._start_run, bg="#4f46e5", fg="white",
            font=("Segoe UI", 10, "bold"), border=0, padx=18, pady=7, cursor="hand2",
        )
        self.run_btn.pack(side="left")
        self.cancel_btn = tk.Button(
            action, text="Cancel", command=self._cancel_run, bg="#dc2626", fg="white",
            font=("Segoe UI", 10, "bold"), border=0, padx=14, pady=7, cursor="hand2",
            state="disabled",
        )
        self.cancel_btn.pack(side="left", padx=(8, 0))
        tk.Button(
            action, text="Open reports folder", command=self._open_reports_folder,
            bg="#475569", fg="white", font=("Segoe UI", 9, "bold"), border=0, padx=12, pady=7,
        ).pack(side="left", padx=(8, 0))
        tk.Button(
            action, text="Open last report", command=self._open_last_report,
            bg="#475569", fg="white", font=("Segoe UI", 9, "bold"), border=0, padx=12, pady=7,
        ).pack(side="left", padx=(8, 0))

        self.progress_bar = ttk.Progressbar(run_fr, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", pady=(10, 4))
        self.status_var = tk.StringVar(value="Pick a project root and Load / Refresh.")
        tk.Label(run_fr, textvariable=self.status_var, bg="#1e293b", fg="#94a3b8",
                 font=("Segoe UI", 9)).pack(anchor="w")

        # --- Log ---
        log_fr = tk.LabelFrame(
            main, text="Activity log", bg="#1e293b", fg="#cbd5e1",
            font=("Segoe UI", 10, "bold"), padx=10, pady=8, bd=1, relief="flat",
        )
        log_fr.pack(fill="both", expand=True)
        log_fr.rowconfigure(0, weight=1)
        log_fr.columnconfigure(0, weight=1)
        self.log_text = tk.Text(
            log_fr, height=8, bg="#0f172a", fg="#e2e8f0", insertbackground="white",
            font=("Consolas", 9), border=0, wrap="word",
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_fr, command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)

    # -------------------------------------------------------------- helpers

    def _log(self, msg: str):
        def append():
            self.log_text.insert("end", msg.rstrip() + "\n")
            self.log_text.see("end")
        self.after(0, append)

    def _browse_root(self):
        path = filedialog.askdirectory(title="Select project root (documents.json + meta.json)")
        if path:
            self.root_var.set(path)

    def _load_overview(self):
        root = self.root_var.get().strip().strip('"')
        if not root:
            messagebox.showerror("Error", "Please choose a project root folder.")
            return
        base = Path(root)
        if not (base / ce.DOCS_NAME).exists() or not (base / ce.META_NAME).exists():
            messagebox.showerror(
                "Error",
                f"Missing {ce.DOCS_NAME} or {ce.META_NAME} in:\n{base}",
            )
            return
        try:
            base, docs, metas, index, done = ce.load_project(base)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load project:\n{exc}")
            return
        if not index:
            messagebox.showwarning(
                "No JATS docs",
                f"No {ce.RUN_DTD} documents found in {ce.META_NAME}.",
            )
        self._docs, self._metas, self._index, self._done = docs, metas, index, done
        self._overview = ce.build_overview(docs, metas, index, done)
        text = ce.format_overview_text(self._overview)
        self.overview_text.delete("1.0", "end")
        self.overview_text.insert("1.0", text)

        self.client_list.delete(0, "end")
        for row in self._overview["client_rows"]:
            pending = sum(1 for it in row["items"] if it["status_key"] != "done")
            tail = f"{pending} pending" if pending else "all filled"
            self.client_list.insert(
                "end",
                f"{row['client']}  ({row['shortcodes']} sc, {row['docs']} docs, {tail})",
            )
        # Select all clients by default
        self.client_list.select_set(0, "end")
        self._on_client_select()
        self._select_pending()
        self.status_var.set(
            f"Loaded: {self._overview['clients']} clients | "
            f"{self._overview['shortcodes']} shortcodes | {self._overview['docs']} docs  "
            f"(filled {self._overview['filled']} / not filled {self._overview['not_filled']} / "
            f"update {self._overview['update']})"
        )
        self._log(f"Loaded project: {base}")

    def _selected_client_names(self) -> list[str]:
        if not self._overview:
            return []
        names = []
        for i in self.client_list.curselection():
            names.append(self._overview["client_rows"][i]["client"])
        return names

    def _on_client_select(self, _event=None):
        clients = self._selected_client_names()
        self.sc_list.delete(0, "end")
        self._pair_keys = []
        if not self._overview:
            return
        for row in self._overview["client_rows"]:
            if row["client"] not in clients:
                continue
            for item in row["items"]:
                label = f"{row['client']} / {item['shortcode']:<12} {item['docs']:>4} docs  [{item['status']}]"
                self.sc_list.insert("end", label)
                self._pair_keys.append((row["client"], item["shortcode"]))

    def _select_pending(self):
        self.sc_list.selection_clear(0, "end")
        if not self._overview:
            return
        # Map status from overview
        status_map = {}
        for row in self._overview["client_rows"]:
            for item in row["items"]:
                status_map[(row["client"], item["shortcode"])] = item["status_key"]
        for i, key in enumerate(self._pair_keys):
            if status_map.get(key) != "done":
                self.sc_list.selection_set(i)

    def _select_all_shortcodes(self):
        self.sc_list.selection_set(0, "end")

    def _clear_shortcodes(self):
        self.sc_list.selection_clear(0, "end")

    def _selected_pairs(self) -> list[tuple[str, str]]:
        return [self._pair_keys[i] for i in self.sc_list.curselection()]

    # --------------------------------------------------------------- run

    def _start_run(self):
        if self.run_thread and self.run_thread.is_alive():
            messagebox.showinfo("Busy", "An extraction is already running.")
            return
        root = self.root_var.get().strip().strip('"')
        if not root or not self._index:
            messagebox.showerror("Error", "Load a project first.")
            return
        pairs = self._selected_pairs()
        if not pairs:
            messagebox.showinfo("Nothing selected", "Select one or more shortcodes to extract.")
            return

        # Confirm regenerating filled
        filled = []
        if self._overview:
            status_map = {
                (row["client"], it["shortcode"]): it["status_key"]
                for row in self._overview["client_rows"]
                for it in row["items"]
            }
            filled = [f"{c}/{sc}" for c, sc in pairs if status_map.get((c, sc)) == "done"]
        if filled and not self.regen_var.get():
            ans = messagebox.askyesno(
                "Regenerate filled?",
                f"{len(filled)} selected shortcode(s) are already filled:\n"
                + ", ".join(filled[:12])
                + ("…" if len(filled) > 12 else "")
                + "\n\nRegenerate them? (Cancel keeps only pending.)",
            )
            if not ans:
                pairs = [p for p in pairs if status_map.get(p) != "done"]
                if not pairs:
                    messagebox.showinfo("Nothing to do", "No pending shortcodes left.")
                    return
            else:
                self.regen_var.set(True)

        try:
            delay_sc = float(self.delay_sc_var.get())
            delay_cl = float(self.delay_cl_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Error", "Delay values must be numbers ≥ 0.")
            return
        if delay_sc < 0 or delay_cl < 0:
            messagebox.showerror("Error", "Delay values must be ≥ 0.")
            return

        self.cancelled = False
        self.run_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.progress_bar.config(value=0, maximum=max(len(pairs), 1))
        self.status_var.set(f"Running {len(pairs)} shortcode(s)…")
        self._log(f"--- Starting extract: {len(pairs)} shortcode(s) ---")

        root_path = Path(root)

        def worker():
            try:
                result = ce.run_contrib_extract(
                    root_path,
                    shortcodes=pairs,
                    delay_sc=delay_sc,
                    delay_cl=delay_cl,
                    log_callback=lambda m: self._log(m),
                    progress_callback=lambda cur, tot, msg: self.after(
                        0, lambda: self._on_progress(cur, tot, msg)
                    ),
                    cancel_check=lambda: self.cancelled,
                )
                self.after(0, lambda: self._on_finished(result, None))
            except Exception as exc:
                self.after(0, lambda: self._on_finished(None, exc))

        self.run_thread = threading.Thread(target=worker, daemon=True)
        self.run_thread.start()

    def _on_progress(self, current: int, total: int, message: str):
        self.progress_bar.config(maximum=max(total, 1), value=current)
        self.status_var.set(message)

    def _on_finished(self, result, error):
        self.run_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        if error is not None:
            self.status_var.set(f"Error: {error}")
            self._log(f"[ERROR] {error}")
            messagebox.showerror("Contrib Extract", str(error))
            return
        assert result is not None
        if result.get("last_report"):
            self.last_report_path = result["last_report"]
        n = len(result.get("finished") or [])
        total = result.get("total") or 0
        # Surface output paths (contrib HTML, elements HTML, issues CSV) in the log
        for item in result.get("finished") or []:
            if not isinstance(item, (tuple, list)) or len(item) < 3:
                continue
            client, shortcode, entry = item[0], item[1], item[2]
            if not isinstance(entry, dict):
                continue
            bits = []
            for key, label in (
                ("report", "contrib"),
                ("elements_report", "elements"),
                ("issues_csv", "issues"),
            ):
                if entry.get(key):
                    bits.append(f"{label}={entry[key]}")
            if bits:
                self._log(f"[PATHS] {client}/{shortcode}: " + " | ".join(bits))
        if result.get("cancelled"):
            self.status_var.set(f"Cancelled after {n}/{total} shortcode(s). Progress saved.")
        else:
            self.status_var.set(f"Done: {n}/{total} shortcode(s).")
            self.progress_bar.config(value=total)
        # Refresh overview from disk
        try:
            self._load_overview()
        except Exception:
            pass

    def _cancel_run(self):
        self.cancelled = True
        self.status_var.set("Cancelling… (finishing current shortcode if mid-write)")
        self.cancel_btn.config(state="disabled")
        self._log("[CANCEL] Stop requested — finished shortcodes stay in meta-contrib.json")

    def _open_reports_folder(self):
        # HTML/CSV reports live under Documents/impact-support-log/{ts}_contrib_reports/
        folder = ce.default_report_root()
        folder.mkdir(parents=True, exist_ok=True)
        webbrowser.open(folder.as_uri())

    def _open_last_report(self):
        if not self.last_report_path or not Path(self.last_report_path).exists():
            messagebox.showinfo("Info", "No report available yet.")
            return
        webbrowser.open(Path(self.last_report_path).as_uri())

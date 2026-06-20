import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import threading
import html
import json
import shutil
import subprocess
import webbrowser
from datetime import datetime
from core.pgm_processor import PGMProcessor


class PGMProcessorTab(ttk.Frame):
    processor_cls = PGMProcessor
    cache_filename = "pgm_processor_cache.json"
    header_text = "PGM HTML CLONE PROCESSOR"
    description_text = (
        "Converts PGM proofing HTML → IMPACT CKEditor-compatible HTML.\n"
        "Scoped to <body> only · clones attrs to data-pgm-* · adds class / data-name.\n"
        "Removes: span[data-bkmark] · Unwraps: whitespace-only font spans · Skips: header, style, title, meta, link, del, ins, insert"
    )
    process_button_text = "🚀  RUN CLONE PROCESSOR"
    output_token = "IMPACT"
    output_extension = ".html"
    archive_token = "PGM"
    report_title = "PGM Cleanup Report"
    start_log_message = "Starting transformation…"
    cleanup_log_message = "Cleanup   : removes bookmark/tab spans · strips style attrs · unwraps empty placeholder spans"

    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent)
        self.processor = self.processor_cls()
        self.cache_path = os.path.join(os.path.dirname(__file__), self.cache_filename)
        self.cache = self._load_cache()
        self._build_ui()
        self._restore_cached_values()

    # ------------------------------------------------------------------ #
    #  UI                                                                  #
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        main_container = tk.Frame(self, bg="#1e293b", padx=30, pady=20)
        main_container.pack(fill="both", expand=True)

        # Header
        tk.Label(
            main_container,
            text=self.header_text,
            font=("Segoe UI", 18, "bold"),
            fg="#10b981",
            bg="#1e293b",
        ).pack(pady=(0, 4))

        tk.Label(
            main_container,
            text=self.description_text,
            font=("Segoe UI", 9),
            fg="#64748b",
            bg="#1e293b",
            justify="center",
        ).pack(pady=(0, 18))

        # Mode selector
        mode_frame = tk.Frame(main_container, bg="#1e293b")
        mode_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            mode_frame, text="Mode:", bg="#1e293b", fg="#94a3b8",
            font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        self.mode_var = tk.StringVar(value="directory")
        tk.Radiobutton(
            mode_frame, text="Directory (batch)", variable=self.mode_var,
            value="directory", command=self._on_mode_change,
            bg="#1e293b", fg="#38bdf8", selectcolor="#0f766e",
            activebackground="#1e293b", activeforeground="#67e8f9",
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(12, 4))
        tk.Radiobutton(
            mode_frame, text="Single file", variable=self.mode_var,
            value="file", command=self._on_mode_change,
            bg="#1e293b", fg="#f59e0b", selectcolor="#92400e",
            activebackground="#1e293b", activeforeground="#fbbf24",
            font=("Segoe UI", 10),
        ).pack(side="left", padx=4)

        # Config Frame
        config_frame = tk.LabelFrame(
            main_container,
            text="Paths",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 11, "bold"),
            padx=20,
            pady=16,
        )
        config_frame.pack(fill="x", pady=(0, 16))
        config_frame.columnconfigure(0, weight=1)

        # Source row
        self._source_label = tk.Label(
            config_frame,
            text="Source Directory (HTML / XHTML / XML):",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10),
        )
        self._source_label.grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.input_path_var = tk.StringVar()
        self.input_entry = tk.Entry(
            config_frame, textvariable=self.input_path_var,
            bg="#334155", fg="white", border=0, font=("Segoe UI", 11),
        )
        self.input_entry.grid(row=1, column=0, sticky="ew", pady=(0, 12), ipady=5)

        self._browse_src_btn = tk.Button(
            config_frame, text="Browse…", command=self._browse_input,
            bg="#475569", fg="white", font=("Segoe UI", 9), border=0, padx=14,
        )
        self._browse_src_btn.grid(row=1, column=1, padx=(10, 0), pady=(0, 12), ipady=3)

        # Output row
        tk.Label(
            config_frame,
            text="Output Directory:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10),
        ).grid(row=2, column=0, sticky="w", pady=(0, 4))

        self.output_path_var = tk.StringVar()
        tk.Entry(
            config_frame, textvariable=self.output_path_var,
            bg="#334155", fg="white", border=0, font=("Segoe UI", 11),
        ).grid(row=3, column=0, sticky="ew", pady=(0, 4), ipady=5)

        tk.Button(
            config_frame, text="Browse…", command=self._browse_output,
            bg="#475569", fg="white", font=("Segoe UI", 9), border=0, padx=14,
        ).grid(row=3, column=1, padx=(10, 0), pady=(0, 4), ipady=3)

        mapping_frame = tk.LabelFrame(
            main_container,
            text="Additional Style Mapping JSON",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=10,
        )
        mapping_frame.pack(fill="x", pady=(0, 14))
        mapping_frame.columnconfigure(0, weight=1)

        self.mapping_text = tk.Text(
            mapping_frame,
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="white",
            border=0,
            font=("Consolas", 9),
            height=5,
            wrap="none",
        )
        self.mapping_text.grid(row=0, column=0, columnspan=3, sticky="ew", ipady=4)

        tk.Button(
            mapping_frame, text="Load JSON", command=self._load_mapping_json_file,
            bg="#475569", fg="white", font=("Segoe UI", 9), border=0, padx=12,
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        tk.Button(
            mapping_frame, text="Clear", command=lambda: self.mapping_text.delete("1.0", tk.END),
            bg="#334155", fg="white", font=("Segoe UI", 9), border=0, padx=12,
        ).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        tk.Button(
            mapping_frame, text="Validate", command=self._validate_mapping_json,
            bg="#0f766e", fg="white", font=("Segoe UI", 9), border=0, padx=12,
        ).grid(row=1, column=2, sticky="w", padx=(8, 0), pady=(8, 0))

        # Action button
        btn_row = tk.Frame(main_container, bg="#1e293b")
        btn_row.pack(fill="x", pady=(0, 16))

        self.process_btn = tk.Button(
            btn_row,
            text=self.process_button_text,
            command=self._start_processing,
            bg="#10b981",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            border=0,
            padx=30,
            pady=11,
        )
        self.process_btn.pack(side="left")

        self.reconvert_btn = tk.Button(
            btn_row,
            text="RECONVERT LAST",
            command=self._reconvert_last,
            bg="#2563eb",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=18,
            pady=11,
        )
        self.reconvert_btn.pack(side="left", padx=(10, 0))

        # Process Status
        tk.Label(
            main_container,
            text="Process Status:",
            bg="#1e293b", fg="#475569", font=("Segoe UI", 9),
        ).pack(anchor="w")

        log_frame = tk.Frame(main_container, bg="#f8fafc", relief="sunken", borderwidth=1)
        log_frame.pack(fill="both", expand=True, pady=(4, 0))

        self.log_text = tk.Text(
            log_frame,
            bg="#f8fafc", fg="#0f172a",
            border=0, font=("Segoe UI", 9),
            height=12,
        )
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)

        # Colour tags for the log
        self.log_text.tag_config("ok",    foreground="#10b981")
        self.log_text.tag_config("err",   foreground="#ef4444")
        self.log_text.tag_config("info",  foreground="#38bdf8")
        self.log_text.tag_config("muted", foreground="#64748b")

    # ------------------------------------------------------------------ #
    #  Mode toggle                                                         #
    # ------------------------------------------------------------------ #
    def _on_mode_change(self):
        if self.mode_var.get() == "file":
            self._source_label.config(text="Source File (HTML / XHTML / XML):")
        else:
            self._source_label.config(text="Source Directory (HTML / XHTML / XML):")
        self.input_path_var.set("")

    def _restore_cached_values(self):
        last = self.cache.get("last_run", {})
        if last.get("mode") in {"file", "directory"}:
            self.mode_var.set(last["mode"])
            self._on_mode_change()
        if last.get("source"):
            self.input_path_var.set(last["source"])
        if last.get("base"):
            self.output_path_var.set(last["base"])
        if last.get("extra_mapping_text"):
            self.mapping_text.delete("1.0", tk.END)
            self.mapping_text.insert("1.0", last["extra_mapping_text"])

    # ------------------------------------------------------------------ #
    #  Browse helpers                                                      #
    # ------------------------------------------------------------------ #
    def _browse_input(self):
        if self.mode_var.get() == "file":
            path = filedialog.askopenfilename(
                filetypes=[
                    ("HTML/XHTML/XML files", "*.html *.htm *.xhtml *.xml"),
                    ("All files", "*.*"),
                ]
            )
            if path:
                self.input_path_var.set(path)
                # Output name is stamped at run-time; leave blank so it auto-derives
                if not self.output_path_var.get():
                    self.output_path_var.set(os.path.dirname(path))
        else:
            directory = filedialog.askdirectory()
            if directory:
                self.input_path_var.set(directory)
                # Parent for the timestamped output folder — set to source's parent
                if not self.output_path_var.get():
                    self.output_path_var.set(os.path.dirname(directory))

    def _browse_output(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_path_var.set(directory)

    def _load_mapping_json_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("JSON root must be an object.")
            self.mapping_text.delete("1.0", tk.END)
            self.mapping_text.insert("1.0", json.dumps(data, indent=4, ensure_ascii=False))
            self._log(f"Loaded mapping JSON: {path}", "ok")
        except Exception as e:
            messagebox.showerror("Invalid JSON", str(e))

    def _validate_mapping_json(self):
        try:
            mapping = self._get_extra_mapping()
            messagebox.showinfo("Valid JSON", f"Additional mapping entries: {len(mapping)}")
        except Exception as e:
            messagebox.showerror("Invalid JSON", str(e))

    def _get_extra_mapping(self) -> dict:
        text = self.mapping_text.get("1.0", tk.END).strip()
        if not text:
            return {}
        mapping = json.loads(text)
        if not isinstance(mapping, dict):
            raise ValueError("Additional style mapping JSON must be an object.")
        for key, value in mapping.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                raise ValueError("Each mapping entry must be: selector/name string -> object.")
        return mapping

    def _load_cache(self) -> dict:
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {}

    def _save_cache(self, src: str, base: str, mode: str, mapping_text: str):
        self.cache["last_run"] = {
            "source": src,
            "base": base,
            "mode": mode,
            "extra_mapping_text": mapping_text.strip(),
            "saved_at": datetime.now().isoformat(timespec="seconds"),
        }
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log(f"Cache save warning: {e}", "err")

    def _reconvert_last(self):
        last = self.cache.get("last_run")
        if not last:
            messagebox.showinfo("No Cache", "No previous conversion is cached yet.")
            return
        self.mode_var.set(last.get("mode", "directory"))
        self._on_mode_change()
        self.input_path_var.set(last.get("source", ""))
        self.output_path_var.set(last.get("base", ""))
        self.mapping_text.delete("1.0", tk.END)
        self.mapping_text.insert("1.0", last.get("extra_mapping_text", ""))
        self._start_processing()

    # ------------------------------------------------------------------ #
    #  Processing                                                          #
    # ------------------------------------------------------------------ #
    def _log(self, message: str, tag: str = "info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.update_idletasks()

    @staticmethod
    def _make_timestamp() -> str:
        """Return a filesystem-safe timestamp string: YYYYMMDD_HHMMSS"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _start_processing(self):
        src  = self.input_path_var.get().strip()
        base = self.output_path_var.get().strip()   # base parent / stem chosen by user
        mode = self.mode_var.get()

        if not src:
            messagebox.showerror("Error", "Please select a source path.")
            return
        if mode == "directory" and not os.path.isdir(src):
            messagebox.showerror("Error", "Source path is not a valid directory.")
            return
        if mode == "file" and not os.path.isfile(src):
            messagebox.showerror("Error", "Source path is not a valid file.")
            return
        if not base:
            messagebox.showerror("Error", "Please select an output path.")
            return
        if mode == "file" and os.path.splitext(base)[1]:
            base = os.path.dirname(base)
            self.output_path_var.set(base)
        try:
            extra_mapping = self._get_extra_mapping()
        except Exception as e:
            messagebox.showerror("Invalid Additional Mapping JSON", str(e))
            return

        ts = self._make_timestamp()

        if mode == "file":
            # Always output using the selected processor extension.
            name, _ext = os.path.splitext(os.path.basename(src))
            stamped_out = os.path.join(base, f"{name}_{self.output_token}_{ts}{self.output_extension}")
        else:
            # e.g. /parent/dir/IMPACT_Transformed_20260508_221638/
            src_name = os.path.basename(src.rstrip("/\\"))
            stamped_out = os.path.join(base, f"{src_name}_{self.output_token}_{ts}")

        archived = self._archive_previous_outputs(src, base, mode, ts)
        mapping_text = self.mapping_text.get("1.0", tk.END).strip()
        self._save_cache(src, base, mode, mapping_text)

        self.process_btn.config(state="disabled", text="PROCESSING…", bg="#475569")
        self.reconvert_btn.config(state="disabled", bg="#475569")
        self.log_text.delete("1.0", tk.END)
        self._log(self.start_log_message, "info")
        self._log(f"Source    : {src}", "muted")
        self._log(f"Output    : {stamped_out}", "ok")
        self._log(f"Timestamp : {ts}", "muted")
        if extra_mapping:
            self._log(f"Extra map : {len(extra_mapping)} additional style mapping entry(s)", "ok")
        if archived:
            self._log(f"Archived  : {archived} old output item(s)", "muted")
        self._log(self.cleanup_log_message, "muted")
        self._log("Skipping  : header · style · title · meta · link · del · ins · insert", "muted")
        self._log("─" * 58, "muted")

        thread = threading.Thread(
            target=self._run_processor,
            args=(src, stamped_out, mode, ts, extra_mapping),
            daemon=True,
        )
        thread.start()

    def _run_processor(self, src: str, out: str, mode: str, ts: str, extra_mapping: dict):
        try:
            if mode == "file":
                # Ensure output directory exists
                os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
                result = self.processor.process_file(src, out, extra_mapping)
                if result['ok']:
                    report_path = self._write_cleanup_report(
                        [result], src, out, mode, ts
                    )
                    self._log(
                        f"✔ Done — {result['tags_processed']} tags transformed, "
                        f"{result['tags_skipped']} skipped", "ok"
                    )
                    self._log(
                        f"   ↳ {result['bkmark_removed']} bookmark span(s) removed, "
                        f"{result.get('tab_spans_removed', 0)} tab span(s) removed, "
                        f"{result.get('style_removed', 0)} style attribute(s) removed, "
                        f"{result.get('font_spans_unwrapped', result.get('span_unwrapped', 0))} placeholder span(s) unwrapped", "muted"
                    )
                    self._log(f"   Saved → {out}", "ok")
                    self._log(f"   Report → {report_path}", "ok")
                    self._open_after_convert(report_path, out)
                    messagebox.showinfo("Complete", "File processed successfully.")
                    print(f"SUCCESS: IMPACT to CEG conversion completed for {src}")
                else:
                    self._log(f"✘ Error: {result['error']}", "err")
                    messagebox.showerror("Error", result['error'])
                    print(f"ERROR: IMPACT to CEG conversion failed for {src}: {result['error']}")
            else:
                processed, errors, file_results = self.processor.process_directory(
                    src, out, callback=lambda m: self._log(m, "info"), extra_mapping=extra_mapping
                )
                report_path = self._write_cleanup_report(
                    file_results, src, out, mode, ts
                )
                self._log("─" * 58, "muted")
                self._log(
                    f"Complete — {processed} file(s) transformed, {errors} error(s).",
                    "ok" if errors == 0 else "err",
                )
                self._log(f"Report   → {report_path}", "ok")
                if processed:
                    self._open_after_convert(report_path, self._first_output_file(file_results) or out)
                if errors:
                    messagebox.showwarning(
                        "Complete with errors",
                        f"Processed {processed} files with {errors} error(s).\nSee log for details.",
                    )
                    print(f"ERROR: IMPACT to CEG conversion completed with {errors} errors for directory {src}")
                else:
                    messagebox.showinfo("Complete", f"Successfully processed {processed} file(s).")
                    print(f"SUCCESS: IMPACT to CEG conversion completed for directory {src} - {processed} files processed")
        except Exception as e:
            self._log(f"[CRITICAL] {e}", "err")
            messagebox.showerror("Error", str(e))
            print(f"CRITICAL ERROR: IMPACT to CEG conversion failed: {e}")
        finally:
            self.process_btn.config(
                state="normal", text=self.process_button_text, bg="#10b981"
            )
            self.reconvert_btn.config(state="normal", bg="#2563eb")

    def _archive_previous_outputs(self, src: str, base: str, mode: str, ts: str) -> int:
        if not os.path.isdir(base):
            return 0

        names_to_archive = []
        if mode == "file":
            stem = os.path.splitext(os.path.basename(src))[0]
            prefixes = (
                f"{stem}_{self.output_token}_",
                f"{stem}_{self.output_token}_cleanup_report_",
            )
            for name in os.listdir(base):
                full_path = os.path.join(base, name)
                if (
                    os.path.isfile(full_path)
                    and name.startswith(prefixes)
                ):
                    names_to_archive.append(name)
        else:
            src_name = os.path.basename(src.rstrip("/\\"))
            prefix = f"{src_name}_{self.output_token}_"
            for name in os.listdir(base):
                full_path = os.path.join(base, name)
                if name == "archive":
                    continue
                if os.path.isdir(full_path) and name.startswith(prefix):
                    names_to_archive.append(name)

        if not names_to_archive:
            return 0

        archive_dir = os.path.join(base, "archive", f"{self.archive_token}_archive_{ts}")
        os.makedirs(archive_dir, exist_ok=True)
        moved = 0
        for name in names_to_archive:
            src_path = os.path.join(base, name)
            dst_path = os.path.join(archive_dir, name)
            try:
                shutil.move(src_path, dst_path)
                moved += 1
            except Exception as e:
                self._log(f"Archive warning: {name} → {e}", "err")
        return moved

    def _first_output_file(self, results: list[dict]) -> str | None:
        for item in results:
            if item.get("ok") and item.get("output_path") and os.path.isfile(item["output_path"]):
                return item["output_path"]
        return None

    def _open_after_convert(self, report_path: str, output_path: str):
        try:
            webbrowser.open(f"file:///{os.path.abspath(report_path)}")
        except Exception as e:
            self._log(f"Browser open warning: {e}", "err")

        try:
            if os.path.isfile(output_path):
                self._open_in_notepad_plus_plus(output_path)
            elif os.path.isdir(output_path):
                os.startfile(output_path)
        except Exception as e:
            self._log(f"Editor open warning: {e}", "err")

    def _open_in_notepad_plus_plus(self, path: str):
        candidates = [
            "notepad++",
            r"C:\Program Files\Notepad++\notepad++.exe",
            r"C:\Program Files (x86)\Notepad++\notepad++.exe",
        ]
        for exe in candidates:
            try:
                subprocess.Popen([exe, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                continue
        subprocess.Popen(["notepad.exe", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _write_cleanup_report(
        self, results: list[dict], src: str, out: str, mode: str, ts: str
    ) -> str:
        report_path = self._cleanup_report_path(src, out, mode, ts)
        os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)

        ok_results = [item for item in results if item.get("ok")]
        totals = {
            "files": len(ok_results),
            "remove_attribute": sum(item.get("style_removed", 0) for item in ok_results),
            "remove_element": sum(
                item.get("bkmark_removed", 0) + item.get("tab_spans_removed", 0)
                for item in ok_results
            ),
            "unwrap_element": sum(item.get("font_spans_unwrapped", 0) for item in ok_results),
        }
        totals["cleanup_total"] = (
            totals["remove_attribute"]
            + totals["remove_element"]
            + totals["unwrap_element"]
        )
        error_count = len([item for item in results if not item.get("ok")])

        segment_rows = []
        detail_rows = []
        action_detail_rows = {
            "remove_attribute": [],
            "remove_element": [],
            "unwrap_element": [],
        }
        error_rows = []

        for item in results:
            file_label = item.get("relative_path") or item.get("input_path") or ""
            if not item.get("ok"):
                error_rows.append(
                    f"<tr><td>{self._h(file_label)}</td><td>{self._h(item.get('error', ''))}</td></tr>"
                )
                continue

            for segment in item.get("cleanup_segments", []):
                segment_rows.append(
                    "<tr>"
                    f"<td>{self._h(file_label)}</td>"
                    f"<td>{self._h(segment.get('segment', ''))}</td>"
                    f"<td>{segment.get('remove_attribute', 0)}</td>"
                    f"<td>{segment.get('remove_element', 0)}</td>"
                    f"<td>{segment.get('unwrap_element', 0)}</td>"
                    f"<td>{segment.get('total', 0)}</td>"
                    "</tr>"
                )

            for detail in item.get("cleanup_details", []):
                detail_row = (
                    "<tr>"
                    f"<td>{self._h(file_label)}</td>"
                    f"<td>{self._h(detail.get('segment', ''))}</td>"
                    f"<td>{self._format_action(detail.get('action', ''))}</td>"
                    f"<td>{self._h(detail.get('target', ''))}</td>"
                    f"<td>{self._h(detail.get('tag', ''))}</td>"
                    f"<td>{self._h(detail.get('path', ''))}</td>"
                    f"<td>{self._h(detail.get('value', ''))}</td>"
                    f"<td>{self._h(detail.get('text', ''))}</td>"
                    "</tr>"
                )
                detail_rows.append(detail_row)
                action = detail.get("action")
                if action in action_detail_rows:
                    action_detail_rows[action].append(detail_row)

        segment_count = len(segment_rows)
        if not segment_rows:
            segment_rows.append(
                "<tr><td colspan='6' class='empty'>No removed attributes, removed elements, or unwrapped elements.</td></tr>"
            )
        if not detail_rows:
            detail_rows.append("<tr><td colspan='8' class='empty'>No cleanup details.</td></tr>")
        for action, rows in action_detail_rows.items():
            if not rows:
                action_detail_rows[action].append(
                    f"<tr><td colspan='8' class='empty'>No {self._h(self._action_label(action).lower())} details.</td></tr>"
                )
        if not error_rows:
            error_rows.append("<tr><td colspan='2' class='empty'>No errors.</td></tr>")

        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{self._h(self.report_title)} {self._h(ts)}</title>
<style>
body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #f8fafc; color: #0f172a; }}
header {{ background: #0f172a; color: white; padding: 24px 32px; }}
h1 {{ margin: 0 0 8px; font-size: 24px; }}
h2 {{ margin-top: 28px; font-size: 18px; }}
main {{ padding: 24px 32px 40px; }}
.meta {{ color: #cbd5e1; font-size: 13px; line-height: 1.7; }}
.cards {{ display: grid; grid-template-columns: repeat(5, minmax(120px, 1fr)); gap: 12px; margin: 20px 0; }}
.card {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; }}
.card b {{ display: block; font-size: 24px; margin-bottom: 4px; }}
.card span {{ color: #64748b; font-size: 12px; text-transform: uppercase; }}
table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #e2e8f0; }}
th, td {{ border-bottom: 1px solid #e2e8f0; padding: 9px 10px; text-align: left; vertical-align: top; font-size: 13px; }}
th {{ background: #e2e8f0; font-size: 12px; text-transform: uppercase; color: #334155; }}
td {{ word-break: break-word; }}
.empty {{ color: #64748b; text-align: center; }}
.pill {{ display: inline-block; border-radius: 999px; padding: 2px 8px; background: #e0f2fe; color: #075985; font-size: 12px; white-space: nowrap; }}
.report-panel {{ margin-top: 16px; background: white; border: 1px solid #dbe4ef; border-radius: 8px; overflow: hidden; }}
.report-panel summary {{ cursor: pointer; display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 14px 16px; background: #f1f5f9; font-weight: 700; color: #0f172a; }}
.report-panel summary::-webkit-details-marker {{ display: none; }}
.report-panel summary::after {{ content: '+'; width: 24px; height: 24px; border-radius: 50%; background: #cbd5e1; color: #0f172a; display: inline-grid; place-items: center; flex: 0 0 auto; }}
.report-panel[open] summary::after {{ content: '-'; }}
.panel-body {{ padding: 14px; overflow-x: auto; }}
.panel-note {{ margin: 0 0 10px; color: #64748b; font-size: 13px; }}
.quick-panels {{ display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); gap: 12px; margin-top: 18px; }}
.quick-panels .report-panel {{ margin-top: 0; }}
.quick-panels table {{ min-width: 760px; }}
.count {{ display: inline-block; min-width: 28px; padding: 2px 8px; border-radius: 999px; background: #0f172a; color: white; text-align: center; font-size: 12px; }}
@media (max-width: 900px) {{ .cards, .quick-panels {{ grid-template-columns: 1fr; }} main {{ padding: 18px; }} }}
</style>
</head>
<body>
<header>
<h1>{self._h(self.report_title)}</h1>
<div class="meta">
<div><b>Timestamp:</b> {self._h(ts)}</div>
<div><b>Generated:</b> {self._h(generated_at)}</div>
<div><b>Source:</b> {self._h(src)}</div>
<div><b>Output:</b> {self._h(out)}</div>
</div>
</header>
<main>
<section class="cards">
<div class="card"><b>{totals['files']}</b><span>Files processed</span></div>
<div class="card"><b>{totals['cleanup_total']}</b><span>Total cleanup</span></div>
<div class="card"><b>{totals['remove_attribute']}</b><span>Remove attributes</span></div>
<div class="card"><b>{totals['remove_element']}</b><span>Remove elements</span></div>
<div class="card"><b>{totals['unwrap_element']}</b><span>Unwrap</span></div>
</section>

<details class="report-panel" open>
<summary><span>Segment-wise Summary</span><span class="count">{segment_count}</span></summary>
<div class="panel-body">
<p class="panel-note">Counts are grouped by segment so cleanup volume is easy to review chapter or section wise.</p>
<table>
<thead><tr><th>File</th><th>Segment</th><th>Remove attributes</th><th>Remove elements</th><th>Unwrap</th><th>Total</th></tr></thead>
<tbody>{''.join(segment_rows)}</tbody>
</table>
</div>
</details>

<section class="quick-panels">
<details class="report-panel">
<summary><span>Remove attributes</span><span class="count">{totals['remove_attribute']}</span></summary>
<div class="panel-body"><table>
<thead><tr><th>File</th><th>Segment</th><th>Action</th><th>Target</th><th>Tag</th><th>Path</th><th>Removed value</th><th>Text preview</th></tr></thead>
<tbody>{''.join(action_detail_rows['remove_attribute'])}</tbody>
</table></div>
</details>
<details class="report-panel">
<summary><span>Remove elements</span><span class="count">{totals['remove_element']}</span></summary>
<div class="panel-body"><table>
<thead><tr><th>File</th><th>Segment</th><th>Action</th><th>Target</th><th>Tag</th><th>Path</th><th>Removed value</th><th>Text preview</th></tr></thead>
<tbody>{''.join(action_detail_rows['remove_element'])}</tbody>
</table></div>
</details>
<details class="report-panel">
<summary><span>Unwrap</span><span class="count">{totals['unwrap_element']}</span></summary>
<div class="panel-body"><table>
<thead><tr><th>File</th><th>Segment</th><th>Action</th><th>Target</th><th>Tag</th><th>Path</th><th>Removed value</th><th>Text preview</th></tr></thead>
<tbody>{''.join(action_detail_rows['unwrap_element'])}</tbody>
</table></div>
</details>
</section>

<details class="report-panel">
<summary><span>All Cleanup Details</span><span class="count">{totals['cleanup_total']}</span></summary>
<div class="panel-body">
<table>
<thead><tr><th>File</th><th>Segment</th><th>Action</th><th>Target</th><th>Tag</th><th>Path</th><th>Removed value</th><th>Text preview</th></tr></thead>
<tbody>{''.join(detail_rows)}</tbody>
</table>
</div>
</details>

<details class="report-panel">
<summary><span>Errors</span><span class="count">{error_count}</span></summary>
<div class="panel-body">
<table>
<thead><tr><th>File</th><th>Error</th></tr></thead>
<tbody>{''.join(error_rows)}</tbody>
</table>
</div>
</details>
</main>
</body>
</html>"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        return report_path

    def _cleanup_report_path(self, src: str, out: str, mode: str, ts: str) -> str:
        if mode == "file":
            name, _ext = os.path.splitext(os.path.basename(src))
            return os.path.join(
                os.path.dirname(os.path.abspath(out)),
                f"{name}_{self.output_token}_cleanup_report_{ts}.html",
            )
        return os.path.join(out, f"{self.archive_token}_cleanup_report_{ts}.html")

    @staticmethod
    def _h(value) -> str:
        return html.escape("" if value is None else str(value), quote=True)

    def _format_action(self, action: str) -> str:
        return f"<span class='pill'>{self._h(self._action_label(action))}</span>"

    @staticmethod
    def _action_label(action: str) -> str:
        labels = {
            "remove_attribute": "Remove attributes",
            "remove_element": "Remove elements",
            "unwrap_element": "Unwrap",
        }
        return labels.get(action, action)

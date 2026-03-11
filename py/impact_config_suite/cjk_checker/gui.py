from __future__ import annotations

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
import webbrowser

from .pipeline import run_cjk_compare, run_cjk_compare_from_files


class CJKIntegrityTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent)
        self.report_path = None
        self.original_file_var = tk.StringVar()
        self.revised_file_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.force_fetch_var = tk.BooleanVar(value=False)
        self.impact_logo_img = None
        self.newgen_logo_img = None
        self._load_user_settings()
        self._build_ui()

    def _settings_path(self) -> Path:
        return Path.home() / "Documents" / "CJK_COMPARE" / "user_settings.json"

    def _load_user_settings(self) -> None:
        settings_path = self._settings_path()
        if not settings_path.exists():
            return
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            return

        last_output_dir = settings.get("last_output_dir", "")
        if isinstance(last_output_dir, str):
            self.output_dir_var.set(last_output_dir)

    def _save_user_settings(self) -> None:
        settings_path = self._settings_path()
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings = {
            "last_output_dir": self.output_dir_var.get().strip(),
        }
        settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(5, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 6))
        top.columnconfigure(0, weight=0)
        top.columnconfigure(1, weight=1)
        top.columnconfigure(2, weight=0)

        self.impact_logo_img = self._load_logo_image("IMPACT_5_4.png", subsample=4)
        self.newgen_logo_img = self._load_logo_image("Newgen.png", subsample=4)
        if self.impact_logo_img:
            ttk.Label(top, image=self.impact_logo_img).grid(row=0, column=0, sticky="w", padx=(0, 10))

        title_block = ttk.Frame(top)
        title_block.grid(row=0, column=1, sticky="w")

        ttk.Label(title_block, text="CJK Integrity Checker", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, sticky="w"
        )

        if self.newgen_logo_img:
            ttk.Label(top, image=self.newgen_logo_img).grid(row=0, column=2, sticky="e", padx=(10, 0))

        form = ttk.LabelFrame(self, text="Compare Options")
        form.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=6)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Unique ID:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.doc_id_var = tk.StringVar()
        self.doc_entry = ttk.Entry(form, textvariable=self.doc_id_var)
        self.doc_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        ttk.Label(form, text="Domain:").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        self.domain_var = tk.StringVar(value="UAT")
        self.domain_combo = ttk.Combobox(
            form,
            textvariable=self.domain_var,
            state="readonly",
            values=["PROD", "UAT", "LOCAL", "DEV"],
            width=10,
        )
        self.domain_combo.grid(row=0, column=3, sticky="w", padx=(0, 8), pady=6)

        self.mode_var = tk.StringVar(value="server")
        ttk.Radiobutton(
            form,
            text="Default (Original vs Revised by Unique ID)",
            variable=self.mode_var,
            value="server",
            command=self._toggle_mode,
        ).grid(row=1, column=0, columnspan=4, sticky="w", padx=8, pady=(2, 2))

        ttk.Radiobutton(
            form,
            text="Custom HTML Files",
            variable=self.mode_var,
            value="custom",
            command=self._toggle_mode,
        ).grid(row=2, column=0, columnspan=4, sticky="w", padx=8, pady=(2, 2))

        self.force_fetch_check = ttk.Checkbutton(
            form,
            text="Force Fetch (refresh local backup from server)",
            variable=self.force_fetch_var,
        )
        self.force_fetch_check.grid(row=2, column=2, columnspan=2, sticky="e", padx=8, pady=(2, 2))

        ttk.Label(form, text="Original HTML:").grid(row=3, column=0, sticky="w", padx=8, pady=4)
        self.original_entry = ttk.Entry(form, textvariable=self.original_file_var)
        self.original_entry.grid(row=3, column=1, columnspan=2, sticky="ew", padx=8, pady=4)
        self.original_browse = ttk.Button(form, text="Browse", command=self._browse_original)
        self.original_browse.grid(row=3, column=3, sticky="w", padx=8, pady=4)

        ttk.Label(form, text="Revised HTML:").grid(row=4, column=0, sticky="w", padx=8, pady=4)
        self.revised_entry = ttk.Entry(form, textvariable=self.revised_file_var)
        self.revised_entry.grid(row=4, column=1, columnspan=2, sticky="ew", padx=8, pady=4)
        self.revised_browse = ttk.Button(form, text="Browse", command=self._browse_revised)
        self.revised_browse.grid(row=4, column=3, sticky="w", padx=8, pady=4)

        ttk.Label(form, text="Report Output Path:").grid(row=5, column=0, sticky="w", padx=8, pady=4)
        self.output_dir_entry = ttk.Entry(form, textvariable=self.output_dir_var)
        self.output_dir_entry.grid(row=5, column=1, columnspan=2, sticky="ew", padx=8, pady=4)
        self.output_dir_browse = ttk.Button(form, text="Browse", command=self._browse_output_dir)
        self.output_dir_browse.grid(row=5, column=3, sticky="w", padx=8, pady=4)

        self.compare_btn = ttk.Button(self, text="Fetch & Compare", command=self._on_compare)
        self.compare_btn.grid(row=2, column=2, sticky="e", padx=(0, 10), pady=6)

        ttk.Label(self, text="Status Log").grid(row=3, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 2))
        self.log_text = scrolledtext.ScrolledText(self, height=16, wrap="word")
        self.log_text.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 8))

        self.open_btn = ttk.Button(self, text="Open Report", command=self._open_report, state="disabled")
        self.open_btn.grid(row=6, column=2, sticky="e", padx=10, pady=(0, 10))

        self.open_folder_btn = ttk.Button(
            self,
            text="Open Output Folder",
            command=self._open_output_folder,
            state="disabled",
        )
        self.open_folder_btn.grid(row=6, column=1, sticky="e", padx=10, pady=(0, 10))

        self._toggle_mode()

    def _load_logo_image(self, file_name: str, subsample: int = 1) -> tk.PhotoImage | None:
        assets_dir = Path(__file__).resolve().parent.parent / "assets"
        image_path = assets_dir / file_name
        if not image_path.exists():
            return None
        try:
            image = tk.PhotoImage(file=str(image_path))
            if subsample > 1:
                image = image.subsample(subsample)
            return image
        except Exception:
            return None

    def _toggle_mode(self) -> None:
        is_custom = self.mode_var.get() == "custom"

        state = "normal" if is_custom else "disabled"
        for widget in [self.original_entry, self.original_browse, self.revised_entry, self.revised_browse]:
            widget.configure(state=state)

        self.domain_combo.configure(state="disabled" if is_custom else "readonly")
        self.force_fetch_check.configure(state="disabled" if is_custom else "normal")
        self.compare_btn.configure(text="Compare Custom Files" if is_custom else "Fetch & Compare")

    def _browse_original(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Original HTML file",
            filetypes=[("HTML files", "*.html;*.htm"), ("All files", "*.*")],
        )
        if path:
            self.original_file_var.set(path)

    def _browse_revised(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Revised HTML file",
            filetypes=[("HTML files", "*.html;*.htm"), ("All files", "*.*")],
        )
        if path:
            self.revised_file_var.set(path)

    def _browse_output_dir(self) -> None:
        path = filedialog.askdirectory(title="Select report output folder")
        if path:
            self.output_dir_var.set(path)
            self._save_user_settings()

    def _log(self, message: str) -> None:
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def _queue_log(self, message: str) -> None:
        self.after(0, self._log, message)

    def _on_compare(self) -> None:
        doc_id = self.doc_id_var.get().strip()
        if not doc_id:
            messagebox.showerror("Input Error", "Please enter a document ID.")
            return

        is_custom = self.mode_var.get() == "custom"
        original_file = Path(self.original_file_var.get().strip()) if self.original_file_var.get().strip() else None
        revised_file = Path(self.revised_file_var.get().strip()) if self.revised_file_var.get().strip() else None
        output_dir = Path(self.output_dir_var.get().strip()) if self.output_dir_var.get().strip() else None
        self._save_user_settings()

        if is_custom:
            if not original_file or not original_file.exists():
                messagebox.showerror("Input Error", "Please select a valid Original HTML file.")
                return
            if not revised_file or not revised_file.exists():
                messagebox.showerror("Input Error", "Please select a valid Revised HTML file.")
                return
            assert original_file is not None and revised_file is not None

        self.compare_btn.config(state="disabled")
        self.open_btn.config(state="disabled")
        self.open_folder_btn.config(state="disabled")
        self.report_path = None
        self.log_text.delete("1.0", "end")
        self._log("Starting comparison...")

        def job() -> None:
            try:
                if is_custom:
                    assert original_file is not None and revised_file is not None
                    report_path, summary = run_cjk_compare_from_files(
                        doc_id,
                        original_file=original_file,
                        revised_file=revised_file,
                        output_dir=output_dir,
                        log=self._queue_log,
                    )
                else:
                    report_path, summary = run_cjk_compare(
                        doc_id,
                        domain=self.domain_var.get().strip(),
                        force_fetch=bool(self.force_fetch_var.get()),
                        output_dir=output_dir,
                        log=self._queue_log,
                    )
                self.report_path = report_path
                self.after(0, self._log, f"Summary: {summary}")
                self.after(0, self.open_btn.config, {"state": "normal"})
                self.after(0, self.open_folder_btn.config, {"state": "normal"})
            except Exception as exc:
                self.after(0, self._log, f"Error: {exc}")
                self.after(0, messagebox.showerror, "CJK Checker Error", str(exc))
            finally:
                self.after(0, self.compare_btn.config, {"state": "normal"})

        threading.Thread(target=job, daemon=True).start()

    def _open_report(self) -> None:
        if not self.report_path:
            messagebox.showinfo("No Report", "Generate a report first.")
            return
        webbrowser.open(self.report_path.as_uri())

    def _open_output_folder(self) -> None:
        if not self.report_path:
            messagebox.showinfo("No Report", "Generate a report first.")
            return
        webbrowser.open(self.report_path.parent.as_uri())


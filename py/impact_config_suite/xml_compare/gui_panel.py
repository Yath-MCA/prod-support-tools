"""GUI panel for XML Compare functionality with dark theme."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import TYPE_CHECKING, Callable

from .models import CompareOptions
from .pipeline import run_xml_compare

if TYPE_CHECKING:
    pass


class XmlComparePanel(ttk.Frame):
    """Panel for XML comparison with option checkboxes and file pickers.

    Provides a dark-themed interface matching the compare_tab.py styling
    with file selection, comparison options, status logging, and report
    opening capabilities.
    """

    def __init__(
        self,
        parent: tk.Widget,
        first_path_var: tk.StringVar | None = None,
        second_path_var: tk.StringVar | None = None,
    ):
        """Initialize the XML compare panel.

        Args:
            parent: Parent widget to contain this panel
            first_path_var: Optional external StringVar for original path binding
            second_path_var: Optional external StringVar for revised path binding
        """
        super().__init__(parent)
        self._external_first_var = first_path_var
        self._external_second_var = second_path_var
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the panel UI with dark theme."""
        self.configure(style="Card.TFrame")

        # Title section
        title_frame = tk.Frame(self, bg="#1e293b", padx=20, pady=12)
        title_frame.pack(fill="x")
        tk.Label(
            title_frame,
            text="XML TO XML COMPARISON",
            font=("Segoe UI", 14, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
        ).pack(anchor="w")
        tk.Label(
            title_frame,
            text="Compare two XML files and generate a detailed HTML report with categorized differences.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b",
            wraplength=600,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        # Options Frame
        options_frame = tk.LabelFrame(
            self,
            text="Comparison Options",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 10, "bold"),
            padx=16,
            pady=12,
        )
        options_frame.pack(fill="x", padx=12, pady=8)

        # Option variables with defaults per spec
        self.text_corr_var = tk.BooleanVar(value=True)
        self.format_only_var = tk.BooleanVar(value=True)
        self.full_compare_var = tk.BooleanVar(value=True)
        self.include_attr_var = tk.BooleanVar(value=False)  # Expensive, off by default
        self.structure_changes_var = tk.BooleanVar(value=True)
        self.gen_stats_var = tk.BooleanVar(value=True)

        # Create checkboxes in two columns
        left_col = tk.Frame(options_frame, bg="#0f172a")
        left_col.pack(side="left", fill="y", expand=True)
        right_col = tk.Frame(options_frame, bg="#0f172a")
        right_col.pack(side="left", fill="y", expand=True)

        self._create_checkbutton(
            left_col, "Text Corrections + Formatting", self.text_corr_var
        )
        self._create_checkbutton(left_col, "Formatting Only", self.format_only_var)
        self._create_checkbutton(left_col, "Full Compare", self.full_compare_var)
        self._create_checkbutton(
            right_col, "Attribute Level Compare (expensive)", self.include_attr_var
        )
        self._create_checkbutton(right_col, "Structure Changes", self.structure_changes_var)
        self._create_checkbutton(
            right_col, "Generate Statistics Dashboard", self.gen_stats_var
        )

        # File selection frame
        files_frame = tk.Frame(self, bg="#0f172a", padx=12, pady=8)
        files_frame.pack(fill="x")

        # Use external vars if provided, otherwise create local ones
        self.original_path_var = self._external_first_var or tk.StringVar()
        self.revised_path_var = self._external_second_var or tk.StringVar()

        self._create_file_row(
            files_frame, "Original XML:", self.original_path_var, 0, self._browse_original
        )
        self._create_file_row(
            files_frame, "Revised XML:", self.revised_path_var, 1, self._browse_revised
        )

        # Action buttons
        btn_frame = tk.Frame(self, bg="#0f172a", padx=12, pady=8)
        btn_frame.pack(fill="x")

        self.run_btn = tk.Button(
            btn_frame,
            text="Run XML Compare",
            command=self._on_run,
            bg="#10b981",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=20,
            pady=8,
            cursor="hand2",
        )
        self.run_btn.pack(side="left", padx=(0, 8))

        self.open_report_btn = tk.Button(
            btn_frame,
            text="Open Report",
            command=self._open_report,
            bg="#3b82f6",
            fg="white",
            font=("Segoe UI", 10),
            border=0,
            padx=16,
            pady=8,
            state="disabled",
            cursor="hand2",
        )
        self.open_report_btn.pack(side="left", padx=(0, 8))

        self.open_folder_btn = tk.Button(
            btn_frame,
            text="Open Folder",
            command=self._open_folder,
            bg="#475569",
            fg="white",
            font=("Segoe UI", 10),
            border=0,
            padx=16,
            pady=8,
            state="disabled",
            cursor="hand2",
        )
        self.open_folder_btn.pack(side="left")

        # Status log
        log_frame = tk.Frame(self, bg="#0f172a", padx=12, pady=8)
        log_frame.pack(fill="both", expand=True)

        tk.Label(
            log_frame,
            text="Status Log",
            font=("Segoe UI", 9, "bold"),
            fg="#94a3b8",
            bg="#0f172a",
        ).pack(anchor="w", pady=(0, 4))

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            wrap="word",
            bg="#1e293b",
            fg="#cbd5e1",
            font=("Consolas", 9),
            relief="flat",
            highlightthickness=1,
            highlightbackground="#334155",
        )
        self.log_text.pack(fill="both", expand=True)

        self._last_report_path: Path | None = None
        self._compare_thread: threading.Thread | None = None

    def _create_checkbutton(
        self, parent: tk.Widget, text: str, variable: tk.BooleanVar
    ) -> tk.Checkbutton:
        """Create a themed checkbox."""
        return tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            bg="#0f172a",
            fg="#cbd5e1",
            selectcolor="#1e293b",
            activebackground="#0f172a",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
        )

    def _create_file_row(
        self,
        parent: tk.Widget,
        label: str,
        var: tk.StringVar,
        row: int,
        browse_cmd: Callable[[], None],
    ) -> None:
        """Create a file picker row."""
        frame = tk.Frame(parent, bg="#0f172a")
        frame.pack(fill="x", pady=4)

        tk.Label(frame, text=label, bg="#0f172a", fg="#94a3b8", width=14, anchor="w").pack(
            side="left"
        )

        entry = tk.Entry(
            frame,
            textvariable=var,
            bg="#1e293b",
            fg="white",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#334155",
            font=("Segoe UI", 9),
        )
        entry.pack(side="left", fill="x", expand=True, padx=(8, 8), ipady=4)

        tk.Button(
            frame,
            text="Browse",
            command=browse_cmd,
            bg="#475569",
            fg="white",
            font=("Segoe UI", 9),
            border=0,
            padx=12,
            pady=4,
            cursor="hand2",
        ).pack(side="left")

    def _browse_original(self) -> None:
        """Browse for original XML file."""
        path = filedialog.askopenfilename(
            title="Select Original XML",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
        )
        if path:
            self.original_path_var.set(path)

    def _browse_revised(self) -> None:
        """Browse for revised XML file."""
        path = filedialog.askopenfilename(
            title="Select Revised XML",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
        )
        if path:
            self.revised_path_var.set(path)

    def get_options(self) -> CompareOptions:
        """Get current comparison options from UI.

        Returns:
            CompareOptions configured from checkbox states
        """
        return CompareOptions(
            text_corrections=self.text_corr_var.get(),
            formatting_only=self.format_only_var.get(),
            full_compare=self.full_compare_var.get(),
            include_attributes=self.include_attr_var.get(),
            structure_changes=self.structure_changes_var.get(),
            generate_statistics=self.gen_stats_var.get(),
        )

    def set_paths(self, original: str, revised: str) -> None:
        """Set file paths programmatically.

        Args:
            original: Path to original XML file
            revised: Path to revised XML file
        """
        self.original_path_var.set(original)
        self.revised_path_var.set(revised)

    def _log(self, message: str) -> None:
        """Append message to status log."""
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.update_idletasks()

    def _on_run(self) -> None:
        """Run the comparison on a background thread."""
        original = self.original_path_var.get().strip()
        revised = self.revised_path_var.get().strip()

        if not original:
            messagebox.showerror("Error", "Please select an Original XML file.")
            return
        if not revised:
            messagebox.showerror("Error", "Please select a Revised XML file.")
            return

        orig_path = Path(original)
        rev_path = Path(revised)

        if not orig_path.exists():
            messagebox.showerror("Error", f"Original file not found:\n{original}")
            return
        if not rev_path.exists():
            messagebox.showerror("Error", f"Revised file not found:\n{revised}")
            return

        self.run_btn.config(state="disabled", text="Comparing...")
        self.open_report_btn.config(state="disabled")
        self.open_folder_btn.config(state="disabled")
        self._log("Starting comparison...")

        def log_callback(msg: str) -> None:
            self.after(0, lambda: self._log(msg))

        def on_complete(report_path: Path) -> None:
            self._last_report_path = report_path
            self.after(0, self._on_compare_complete, report_path)

        def on_error(err: Exception) -> None:
            self.after(0, self._on_compare_error, err)

        self._compare_thread = threading.Thread(
            target=self._run_compare_thread,
            args=(orig_path, rev_path, self.get_options(), log_callback, on_complete, on_error),
            daemon=True,
        )
        self._compare_thread.start()

    def _run_compare_thread(
        self,
        original: Path,
        revised: Path,
        options: CompareOptions,
        log: Callable[[str], None],
        on_complete: Callable[[Path], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """Background thread worker for comparison."""
        try:
            report_path = run_xml_compare(
                original, revised, options, log_callback=log
            )
            on_complete(report_path)
        except Exception as e:
            on_error(e)

    def _on_compare_complete(self, report_path: Path) -> None:
        """Handle successful comparison completion."""
        self._log(f"Report saved: {report_path}")
        self.run_btn.config(state="normal", text="Run XML Compare")
        self.open_report_btn.config(state="normal")
        self.open_folder_btn.config(state="normal")
        messagebox.showinfo(
            "Success",
            f"Comparison completed.\n\nReport saved:\n{report_path}",
        )

    def _on_compare_error(self, err: Exception) -> None:
        """Handle comparison error."""
        self._log(f"Error: {err}")
        self.run_btn.config(state="normal", text="Run XML Compare")
        messagebox.showerror("Comparison Failed", str(err))

    def _open_report(self) -> None:
        """Open the last generated report in browser."""
        if self._last_report_path and self._last_report_path.exists():
            webbrowser.open(f"file://{self._last_report_path.absolute()}")
        else:
            messagebox.showwarning("No Report", "No report available to open.")

    def _open_folder(self) -> None:
        """Open the folder containing the last report."""
        if self._last_report_path and self._last_report_path.exists():
            import subprocess
            subprocess.run(["explorer", "/select,", str(self._last_report_path)])
        else:
            messagebox.showwarning("No Report", "No report folder to open.")

    def validate_paths(self) -> tuple[Path, Path] | None:
        """Validate and return the selected file paths.

        Returns:
            Tuple of (original_path, revised_path) if valid, None otherwise.
            Shows error messageboxes for invalid inputs.
        """
        original = self.original_path_var.get().strip()
        revised = self.revised_path_var.get().strip()

        if not original:
            messagebox.showerror("Error", "Please select an Original XML file.")
            return None
        if not revised:
            messagebox.showerror("Error", "Please select a Revised XML file.")
            return None

        orig_path = Path(original)
        rev_path = Path(revised)

        if not orig_path.exists():
            messagebox.showerror("Error", f"Original file not found:\n{original}")
            return None
        if not rev_path.exists():
            messagebox.showerror("Error", f"Revised file not found:\n{revised}")
            return None

        # Validate file extensions
        if orig_path.suffix.lower() not in (".xml", ".xhtml"):
            messagebox.showwarning(
                "File Warning", f"Original file may not be XML: {orig_path.suffix}\nProceeding anyway."
            )
        if rev_path.suffix.lower() not in (".xml", ".xhtml"):
            messagebox.showwarning(
                "File Warning", f"Revised file may not be XML: {rev_path.suffix}\nProceeding anyway."
            )

        return orig_path, rev_path

    def clear_log(self) -> None:
        """Clear the status log text area."""
        self.log_text.delete("1.0", "end")

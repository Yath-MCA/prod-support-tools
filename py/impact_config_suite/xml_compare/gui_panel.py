"""GUI Panel for XML Compare functionality.

Provides a reusable Tkinter panel for XML comparison options and file selection.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext
from typing import Callable

from .models import CompareOptions


class XmlComparePanel(tk.Frame):
    """
    A reusable panel for XML comparison configuration.
    
    Provides checkboxes for comparison options, file pickers for original/revised
    XML files, status log, and action buttons.
    """

    def __init__(
        self,
        parent: tk.Widget,
        first_path_var: tk.StringVar | None = None,
        second_path_var: tk.StringVar | None = None,
        on_compare: Callable[[], None] | None = None,
    ):
        """
        Initialize the XML compare panel.
        
        Args:
            parent: Parent widget
            first_path_var: StringVar for original XML path (optional, will create if not provided)
            second_path_var: StringVar for revised XML path (optional, will create if not provided)
            on_compare: Callback when compare button is clicked
        """
        super().__init__(parent, bg="#0f172a")
        
        # Use provided StringVars or create new ones
        self.first_path_var = first_path_var or tk.StringVar()
        self.second_path_var = second_path_var or tk.StringVar()
        self.on_compare = on_compare
        
        # Report tracking
        self.last_report_path: Path | None = None
        self.last_output_dir: Path | None = None
        
        # Build the UI
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the panel UI components."""
        self.columnconfigure(0, weight=1)
        
        row = 0
        
        # ── File Selection Frame ─────────────────────────────────────────────
        file_frame = tk.LabelFrame(
            self,
            text="XML Files",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 11, "bold"),
            padx=15,
            pady=10,
        )
        file_frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        file_frame.columnconfigure(1, weight=1)
        row += 1

        # Original XML file
        tk.Label(
            file_frame,
            text="Original XML:",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        tk.Entry(
            file_frame,
            textvariable=self.first_path_var,
            bg="#1f2937",
            fg="white",
            border=0,
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="ew", ipady=5)
        tk.Button(
            file_frame,
            text="Browse…",
            command=lambda: self._browse_xml_file(self.first_path_var, "original"),
            bg="#475569",
            fg="white",
            font=("Segoe UI", 9),
            border=0,
            padx=10,
            pady=6,
        ).grid(row=1, column=1, padx=(10, 0))

        # Revised XML file
        tk.Label(
            file_frame,
            text="Revised XML:",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).grid(row=2, column=0, sticky="w", pady=(14, 4))
        tk.Entry(
            file_frame,
            textvariable=self.second_path_var,
            bg="#1f2937",
            fg="white",
            border=0,
            font=("Segoe UI", 10),
        ).grid(row=3, column=0, sticky="ew", ipady=5)
        tk.Button(
            file_frame,
            text="Browse…",
            command=lambda: self._browse_xml_file(self.second_path_var, "revised"),
            bg="#475569",
            fg="white",
            font=("Segoe UI", 9),
            border=0,
            padx=10,
            pady=6,
        ).grid(row=3, column=1, padx=(10, 0))

        # ── Options Frame ───────────────────────────────────────────────────
        options_frame = tk.LabelFrame(
            self,
            text="Compare Options",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 11, "bold"),
            padx=15,
            pady=10,
        )
        options_frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        row += 1

        # Option checkboxes
        self.text_corrections_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame,
            text="Text Corrections",
            variable=self.text_corrections_var,
            bg="#0f172a",
            fg="#cbd5e1",
            selectcolor="#1f2937",
            activebackground="#0f172a",
            activeforeground="#ffffff",
            font=("Segoe UI", 10),
        ).grid(row=0, column=0, sticky="w", pady=2)

        self.formatting_only_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame,
            text="Formatting Only",
            variable=self.formatting_only_var,
            bg="#0f172a",
            fg="#cbd5e1",
            selectcolor="#1f2937",
            activebackground="#0f172a",
            activeforeground="#ffffff",
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", pady=2)

        self.full_compare_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame,
            text="Full Compare",
            variable=self.full_compare_var,
            bg="#0f172a",
            fg="#cbd5e1",
            selectcolor="#1f2937",
            activebackground="#0f172a",
            activeforeground="#ffffff",
            font=("Segoe UI", 10),
        ).grid(row=2, column=0, sticky="w", pady=2)

        self.include_attributes_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            options_frame,
            text="Attribute Level Compare (expensive)",
            variable=self.include_attributes_var,
            bg="#0f172a",
            fg="#cbd5e1",
            selectcolor="#1f2937",
            activebackground="#0f172a",
            activeforeground="#ffffff",
            font=("Segoe UI", 10),
        ).grid(row=0, column=1, sticky="w", pady=2, padx=(20, 0))

        self.structure_changes_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame,
            text="Structure Changes",
            variable=self.structure_changes_var,
            bg="#0f172a",
            fg="#cbd5e1",
            selectcolor="#1f2937",
            activebackground="#0f172a",
            activeforeground="#ffffff",
            font=("Segoe UI", 10),
        ).grid(row=1, column=1, sticky="w", pady=2, padx=(20, 0))

        self.generate_statistics_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame,
            text="Generate Statistics Dashboard",
            variable=self.generate_statistics_var,
            bg="#0f172a",
            fg="#cbd5e1",
            selectcolor="#1f2937",
            activebackground="#0f172a",
            activeforeground="#ffffff",
            font=("Segoe UI", 10),
        ).grid(row=2, column=1, sticky="w", pady=2, padx=(20, 0))

        # ── Status/Log Frame ────────────────────────────────────────────────
        log_frame = tk.LabelFrame(
            self,
            text="Status Log",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 11, "bold"),
            padx=15,
            pady=10,
        )
        log_frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        log_frame.columnconfigure(0, weight=1)
        row += 1

        self.status_text = scrolledtext.ScrolledText(
            log_frame,
            bg="#1f2937",
            fg="#e2e8f0",
            font=("Consolas", 9),
            height=8,
            wrap=tk.WORD,
            border=0,
            padx=8,
            pady=8,
        )
        self.status_text.grid(row=0, column=0, sticky="ew")
        self.status_text.config(state=tk.DISABLED)

        # ── Action Buttons ──────────────────────────────────────────────────
        button_frame = tk.Frame(self, bg="#0f172a")
        button_frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        row += 1

        self.open_report_btn = tk.Button(
            button_frame,
            text="📄 Open Report",
            command=self._open_report,
            bg="#10b981",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=16,
            pady=8,
            state=tk.DISABLED,
        )
        self.open_report_btn.pack(side="left", padx=(0, 10))

        self.open_folder_btn = tk.Button(
            button_frame,
            text="📁 Open Folder",
            command=self._open_folder,
            bg="#6366f1",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=16,
            pady=8,
            state=tk.DISABLED,
        )
        self.open_folder_btn.pack(side="left")

    def _browse_xml_file(self, target_var: tk.StringVar, file_type: str) -> None:
        """Open file dialog to select an XML file."""
        selected = filedialog.askopenfilename(
            title=f"Select {file_type.capitalize()} XML file",
            filetypes=[("XML Files", "*.xml"), ("All Files", "*")],
        )
        if selected:
            target_var.set(selected)

    def get_options(self) -> CompareOptions:
        """
        Get the current comparison options as a CompareOptions dataclass.
        
        Returns:
            CompareOptions with current checkbox states
        """
        return CompareOptions(
            text_corrections=self.text_corrections_var.get(),
            formatting_only=self.formatting_only_var.get(),
            full_compare=self.full_compare_var.get(),
            include_attributes=self.include_attributes_var.get(),
            structure_changes=self.structure_changes_var.get(),
            generate_statistics=self.generate_statistics_var.get(),
            fast_match=False,  # Could add UI control for this if needed
        )

    def get_paths(self) -> tuple[str, str]:
        """
        Get the current original and revised file paths.
        
        Returns:
            Tuple of (original_path, revised_path)
        """
        return self.first_path_var.get().strip(), self.second_path_var.get().strip()

    def log(self, message: str, level: str = "info") -> None:
        """
        Add a message to the status log.
        
        Args:
            message: Message to display
            level: Log level (info, success, error, warning)
        """
        self.status_text.config(state=tk.NORMAL)
        
        # Add color prefix based on level
        prefixes = {
            "info": "ℹ️ ",
            "success": "✅ ",
            "error": "❌ ",
            "warning": "⚠️ ",
        }
        prefix = prefixes.get(level, "ℹ️ ")
        
        self.status_text.insert(tk.END, f"{prefix}{message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)

    def clear_log(self) -> None:
        """Clear the status log."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)

    def set_report_path(self, report_path: Path | None) -> None:
        """
        Set the path to the generated report and update button states.
        
        Args:
            report_path: Path to the generated HTML report
        """
        self.last_report_path = report_path
        if report_path:
            self.last_output_dir = report_path.parent
            self.open_report_btn.config(state=tk.NORMAL)
            self.open_folder_btn.config(state=tk.NORMAL)
        else:
            self.open_report_btn.config(state=tk.DISABLED)
            self.open_folder_btn.config(state=tk.DISABLED)

    def _open_report(self) -> None:
        """Open the generated report in the default browser."""
        if self.last_report_path and self.last_report_path.exists():
            import webbrowser
            webbrowser.open(f"file:///{self.last_report_path.resolve()}")
        else:
            messagebox.showinfo("No Report", "Generate a report first.")

    def _open_folder(self) -> None:
        """Open the output folder in the file explorer."""
        if self.last_output_dir and self.last_output_dir.exists():
            import subprocess
            import os
            if os.name == 'nt':  # Windows
                subprocess.run(['explorer', str(self.last_output_dir.resolve())])
            elif os.name == 'posix':  # macOS or Linux
                subprocess.run(['open' if os.uname().sysname == 'Darwin' else 'xdg-open', 
                            str(self.last_output_dir.resolve())])
        else:
            messagebox.showinfo("No Folder", "Generate a report first.")

    def validate_paths(self) -> tuple[Path, Path] | None:
        """
        Validate that both paths are set and are XML files.
        
        Returns:
            Tuple of (original_path, revised_path) as Path objects if valid,
            None if invalid (shows error message)
        """
        original_str, revised_str = self.get_paths()
        
        if not original_str or not revised_str:
            messagebox.showerror("Error", "Please select both Original and Revised XML files.")
            return None
        
        original_path = Path(original_str)
        revised_path = Path(revised_str)
        
        if not original_path.exists():
            messagebox.showerror("Error", f"Original file not found:\n{original_str}")
            return None
        
        if not revised_path.exists():
            messagebox.showerror("Error", f"Revised file not found:\n{revised_str}")
            return None
        
        # Check file extensions
        if original_path.suffix.lower() != '.xml':
            messagebox.showerror("Error", f"Original file must be an XML file:\n{original_str}")
            return None
        
        if revised_path.suffix.lower() != '.xml':
            messagebox.showerror("Error", f"Revised file must be an XML file:\n{revised_str}")
            return None
        
        return original_path, revised_path

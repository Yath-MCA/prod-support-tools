import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import threading
from datetime import datetime
from core.new_config_processor import NewConfigProcessor

# Try to import generator/validator if they are in the path
try:
    from config_generator import generate_html_form
    GENERATOR_AVAILABLE = True
except ImportError:
    GENERATOR_AVAILABLE = False

try:
    # We'll assume for now it might be available in the main app's environment
    # or we can add it later.
    from config_validator import validate_folder, print_validation_report
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False


class NewConfigTab(ttk.Frame):
    processor_cls = NewConfigProcessor
    header_text = "NEW JOURNAL CONFIG PROCESSOR"
    description_text = (
        "Processes new journal configurations: renames covers, generates CSS files, "
        "validates XML, and merges XML files into a combined output."
    )

    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent)
        self.processor = self.processor_cls()
        self._build_ui()

    def _build_ui(self):
        main_container = tk.Frame(self, bg="#1e293b", padx=30, pady=20)
        main_container.pack(fill="both", expand=True)

        # Header
        tk.Label(
            main_container,
            text=self.header_text,
            font=("Segoe UI", 18, "bold"),
            fg="#38bdf8",
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

        # Config Frame
        config_frame = tk.LabelFrame(
            main_container,
            text="Settings",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 11, "bold"),
            padx=20,
            pady=16,
        )
        config_frame.pack(fill="x", pady=(0, 16))
        config_frame.columnconfigure(1, weight=1)

        # Base Folder row
        tk.Label(
            config_frame,
            text="Base Project Folder:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10),
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.base_path_var = tk.StringVar()
        tk.Entry(
            config_frame, textvariable=self.base_path_var,
            bg="#334155", fg="white", border=0, font=("Segoe UI", 11),
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12), ipady=5)

        tk.Button(
            config_frame, text="Browse…", command=self._browse_base,
            bg="#475569", fg="white", font=("Segoe UI", 9), border=0, padx=14,
        ).grid(row=1, column=2, padx=(10, 0), pady=(0, 12), ipady=3)

        # Prefix row
        tk.Label(
            config_frame,
            text="Prefix for copy-by (e.g. YA):",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10),
        ).grid(row=2, column=0, sticky="w", pady=(0, 4))

        self.prefix_var = tk.StringVar(value="YA")
        tk.Entry(
            config_frame, textvariable=self.prefix_var,
            bg="#334155", fg="white", border=0, font=("Segoe UI", 11),
        ).grid(row=3, column=0, sticky="ew", pady=(0, 12), ipady=5)

        # Ticket row
        tk.Label(
            config_frame,
            text="Mantis Ticket Number:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10),
        ).grid(row=2, column=1, sticky="w", padx=(20, 0), pady=(0, 4))

        self.ticket_var = tk.StringVar(value="NO-TICKET")
        tk.Entry(
            config_frame, textvariable=self.ticket_var,
            bg="#334155", fg="white", border=0, font=("Segoe UI", 11),
        ).grid(row=3, column=1, columnspan=2, sticky="ew", padx=(20, 0), pady=(0, 12), ipady=5)

        # Action buttons
        actions_frame = tk.Frame(main_container, bg="#1e293b")
        actions_frame.pack(fill="x", pady=(0, 16))

        self.run_all_btn = tk.Button(
            actions_frame,
            text="🚀 RUN FULL WORKFLOW",
            command=lambda: self._start_task("all"),
            bg="#10b981",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            border=0,
            padx=20,
            pady=10,
        )
        self.run_all_btn.pack(side="left", padx=(0, 10))

        tk.Button(
            actions_frame,
            text="🖼️ RENAME COVERS",
            command=lambda: self._start_task("rename"),
            bg="#3b82f6",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=15,
            pady=10,
        ).pack(side="left", padx=5)

        tk.Button(
            actions_frame,
            text="🎨 GENERATE CSS",
            command=lambda: self._start_task("css"),
            bg="#8b5cf6",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=15,
            pady=10,
        ).pack(side="left", padx=5)

        tk.Button(
            actions_frame,
            text="🔗 MERGE XML",
            command=lambda: self._start_task("merge"),
            bg="#f59e0b",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=15,
            pady=10,
        ).pack(side="left", padx=5)

        if GENERATOR_AVAILABLE:
            tk.Button(
                actions_frame,
                text="📝 HTML FORM",
                command=self._generate_form,
                bg="#ec4899",
                fg="white",
                font=("Segoe UI", 10, "bold"),
                border=0,
                padx=15,
                pady=10,
            ).pack(side="left", padx=5)

        # Log Area
        tk.Label(
            main_container,
            text="Operation Log:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9),
        ).pack(anchor="w")

        log_frame = tk.Frame(main_container, bg="#0f172a", relief="sunken", borderwidth=1)
        log_frame.pack(fill="both", expand=True, pady=(4, 0))

        self.log_text = tk.Text(
            log_frame,
            bg="#0f172a", fg="#e2e8f0",
            border=0, font=("Consolas", 10),
            height=15,
        )
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)

    def _browse_base(self):
        path = filedialog.askdirectory()
        if path:
            self.base_path_var.set(path)

    def _log(self, message, tag=None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.update_idletasks()

    def _start_task(self, task_type):
        base_path = self.base_path_var.get().strip()
        if not base_path or not os.path.exists(base_path):
            messagebox.showerror("Error", "Please select a valid base project folder.")
            return

        self.run_all_btn.config(state="disabled")
        thread = threading.Thread(target=self._run_task, args=(task_type, base_path), daemon=True)
        thread.start()

    def _run_task(self, task_type, base_path):
        prefix = self.prefix_var.get().strip() or "YA"
        ticket = self.ticket_var.get().strip() or "NO-TICKET"
        
        cover_folder = os.path.join(base_path, 'Cover')
        config_folder = os.path.join(base_path, 'config')

        self.log_text.delete("1.0", tk.END)
        self._log(f"Starting task: {task_type.upper()}")
        self._log(f"Base Path: {base_path}")
        self._log("-" * 50)

        try:
            if task_type in ("all", "rename"):
                self._log("1️⃣ Processing covers...")
                count = self.processor.rename_covers(cover_folder, self._log)
                self._log(f"Finished renaming. {count} files processed.")

            if task_type in ("all", "css"):
                self._log("2️⃣ Generating CSS...")
                count = self.processor.create_css_from_covers(cover_folder, ticket, self._log)
                self._log(f"Finished CSS generation. {count} files created.")

            if task_type in ("all", "merge"):
                self._log("3️⃣ Merging XML files...")
                success = self.processor.merge_xml(config_folder, prefix, self._log)
                if success:
                    self._log("XML Merge completed successfully.")
                else:
                    self._log("XML Merge failed or no files found.", "err")

            self._log("-" * 50)
            self._log("✅ Operations completed.")
            messagebox.showinfo("Success", f"Task {task_type.upper()} completed.")
        except Exception as e:
            self._log(f"❌ Error: {str(e)}")
            messagebox.showerror("Error", str(e))
        finally:
            self.run_all_btn.config(state="normal")

    def _generate_form(self):
        if GENERATOR_AVAILABLE:
            try:
                self._log("🎨 Generating HTML Config Form...")
                path = generate_html_form()
                if path:
                    self._log(f"✅ Form generated: {path}")
                    import webbrowser
                    webbrowser.open(f'file://{os.path.abspath(path)}')
            except Exception as e:
                self._log(f"❌ Error: {str(e)}")
                messagebox.showerror("Error", str(e))
        else:
            messagebox.showwarning("Warning", "Generator module not available.")

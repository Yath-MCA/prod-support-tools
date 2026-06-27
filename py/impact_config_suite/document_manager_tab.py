"""Document Manager tab for the Common Tools application."""
from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Import Document Manager modules
from manage_documents_v3.modules.database import DocumentDatabase
from manage_documents_v3.modules.scanner import DocumentScanner
from manage_documents_v3.modules.organizer import FolderOrganizer
from manage_documents_v3.modules.downloader import ConfigDownloader
from manage_documents_v3.modules.comparer import CompareManager
from manage_documents_v3.modules.reporter import ReportManager
from xml_compare.models import CompareOptions


class DocumentManagerTab(ttk.Frame):
    """Document Manager tab with full workflow controls."""
    
    def __init__(self, parent: ttk.Notebook):
        """Initialize the Document Manager tab."""
        super().__init__(parent)
        self._project_path: Path | None = None
        self._db: DocumentDatabase | None = None
        self._worker_thread: threading.Thread | None = None
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the complete tab UI with dark theme."""
        self.configure(style="Card.TFrame")
        
        # Title section
        self._build_title_section()
        
        # Project selection
        self._build_project_section()
        
        # Action buttons
        self._build_buttons_section()
        
        # Progress bar
        self._build_progress_section()
        
        # Statistics display
        self._build_stats_section()
        
        # Status log
        self._build_log_section()
    
    def _build_title_section(self) -> None:
        """Build title and description."""
        title_frame = tk.Frame(self, bg="#1e293b", padx=20, pady=12)
        title_frame.pack(fill="x")
        
        tk.Label(
            title_frame,
            text="DOCUMENT MANAGER",
            font=("Segoe UI", 14, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
        ).pack(anchor="w")
        
        tk.Label(
            title_frame,
            text="Scan, organize, download configs, compare XML files, and generate reports.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b",
            wraplength=600,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))
    
    def _build_project_section(self) -> None:
        """Build project folder selection."""
        project_frame = tk.Frame(self, bg="#0f172a", padx=12, pady=8)
        project_frame.pack(fill="x", padx=12, pady=8)
        
        tk.Label(
            project_frame,
            text="Project Folder:",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")
        
        self.project_var = tk.StringVar()
        self.project_entry = tk.Entry(
            project_frame,
            textvariable=self.project_var,
            bg="#1e293b",
            fg="white",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#334155",
            font=("Segoe UI", 9),
        )
        self.project_entry.pack(side="left", fill="x", expand=True, padx=(8, 8), ipady=4)
        
        tk.Button(
            project_frame,
            text="Browse",
            command=self._browse_project,
            bg="#475569",
            fg="white",
            font=("Segoe UI", 9),
            border=0,
            padx=12,
            pady=4,
            cursor="hand2",
        ).pack(side="left")
        
        self.load_btn = tk.Button(
            project_frame,
            text="Load",
            command=self._load_project,
            bg="#2563eb",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            border=0,
            padx=16,
            pady=4,
            cursor="hand2",
        )
        self.load_btn.pack(side="left", padx=(8, 0))
        
        # Batch size input
        tk.Label(
            project_frame,
            text="Batch Size:",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(20, 5))
        
        self.batch_size_var = tk.IntVar(value=499)
        tk.Spinbox(
            project_frame,
            from_=1,
            to=9999,
            textvariable=self.batch_size_var,
            width=6,
            bg="#1e293b",
            fg="white",
            font=("Segoe UI", 9),
        ).pack(side="left")
    
    def _build_buttons_section(self) -> None:
        """Build action buttons row."""
        buttons_frame = tk.Frame(self, bg="#0f172a", padx=12, pady=8)
        buttons_frame.pack(fill="x", padx=12)
        
        # Row 1: Main actions
        row1 = tk.Frame(buttons_frame, bg="#0f172a")
        row1.pack(fill="x", pady=(0, 4))
        
        self.scan_btn = self._create_action_button(row1, "Scan", self._on_scan, "#10b981")
        self.organize_btn = self._create_action_button(row1, "Organize", self._on_organize, "#3b82f6")
        self.download_btn = self._create_action_button(row1, "Download Config", self._on_download, "#8b5cf6")
        
        # Row 2: Secondary actions
        row2 = tk.Frame(buttons_frame, bg="#0f172a")
        row2.pack(fill="x", pady=(4, 0))
        
        self.compare_btn = self._create_action_button(row2, "Compare", self._on_compare, "#f59e0b")
        self.report_btn = self._create_action_button(row2, "Report", self._on_report, "#06b6d4")
        self.complete_btn = self._create_action_button(
            row2, "Complete Workflow", self._on_complete_workflow, "#ef4444", is_primary=True
        )
        
        self._update_button_states()
    
    def _create_action_button(
        self,
        parent: tk.Widget,
        text: str,
        command: callable,
        color: str,
        is_primary: bool = False,
    ) -> tk.Button:
        """Create a themed action button."""
        font = ("Segoe UI", 9, "bold") if is_primary else ("Segoe UI", 9)
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="white",
            font=font,
            border=0,
            padx=16 if is_primary else 12,
            pady=8,
            cursor="hand2",
        )
        btn.pack(side="left", padx=(0, 8))
        return btn
    
    def _build_progress_section(self) -> None:
        """Build progress bar."""
        progress_frame = tk.Frame(self, bg="#0f172a", padx=12, pady=8)
        progress_frame.pack(fill="x", padx=12)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_label = tk.Label(
            progress_frame,
            text="Ready",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 9),
        )
        self.progress_label.pack(anchor="w", pady=(0, 4))
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
        )
        self.progress_bar.pack(fill="x")
    
    def _build_stats_section(self) -> None:
        """Build statistics display."""
        stats_frame = tk.LabelFrame(
            self,
            text="Statistics",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=8,
        )
        stats_frame.pack(fill="x", padx=12, pady=8)
        
        self.stats_text = tk.StringVar(value="No project loaded")
        tk.Label(
            stats_frame,
            textvariable=self.stats_text,
            bg="#0f172a",
            fg="#cbd5e1",
            font=("Consolas", 10),
            justify="left",
        ).pack(anchor="w")
    
    def _build_log_section(self) -> None:
        """Build status log area."""
        log_frame = tk.Frame(self, bg="#0f172a", padx=12, pady=8)
        log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        
        tk.Label(
            log_frame,
            text="Status Log",
            font=("Segoe UI", 9, "bold"),
            fg="#94a3b8",
            bg="#0f172a",
        ).pack(anchor="w", pady=(0, 4))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=12,
            wrap="word",
            bg="#1e293b",
            fg="#cbd5e1",
            font=("Consolas", 9),
            relief="flat",
            highlightthickness=1,
            highlightbackground="#334155",
        )
        self.log_text.pack(fill="both", expand=True)
    
    def _browse_project(self) -> None:
        """Browse for project folder."""
        folder = filedialog.askdirectory(title="Select Project Folder")
        if folder:
            self.project_var.set(folder)
    
    def _load_project(self) -> None:
        """Load project and database."""
        path_str = self.project_var.get().strip()
        if not path_str:
            messagebox.showerror("Error", "Please select a project folder.")
            return
        
        path = Path(path_str)
        if not path.exists():
            messagebox.showerror("Error", f"Folder not found: {path}")
            return
        
        try:
            self._project_path = path
            self._db = DocumentDatabase(path)
            self._log(f"Loaded project: {path}")
            
            # Count source files
            source_counts = self._count_source_files(path)
            self._log(f"Source files available:")
            self._log(f"  HTML files (originalhtml): {source_counts['html']}")
            self._log(f"  XML files (originalxml): {source_counts['xml']}")
            self._log(f"  Updated HTML (updatedhtmlfiles): {source_counts['updated_html']}")
            
            # Count documents and completion status
            doc_stats = self._count_document_status(path)
            self._log(f"\nDocument status:")
            self._log(f"  Total documents in database: {doc_stats['total']}")
            self._log(f"  Completed (all steps): {doc_stats['completed']}")
            self._log(f"  With config XML downloaded: {doc_stats['with_config']}")
            self._log(f"  Organized: {doc_stats['organized']}")
            self._log(f"  Compared: {doc_stats['compared']}")
            
            self._update_stats()
            self._update_button_states()
            self._log("\nProject loaded successfully - buttons enabled")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load project: {e}")
            import traceback
            traceback.print_exc()
    
    def _count_source_files(self, project_path: Path) -> dict:
        """Count available source files in the project folders."""
        counts = {"html": 0, "xml": 0, "updated_html": 0, "impact_config": 0}
        
        # Count HTML files in originalhtml folder
        html_folder = project_path / "originalhtml"
        if html_folder.exists():
            counts["html"] = len([f for f in html_folder.iterdir() 
                                  if f.is_file() and f.suffix.lower() == ".html"])
        
        # Count XML files in originalxml folder
        xml_folder = project_path / "originalxml"
        if xml_folder.exists():
            counts["xml"] = len([f for f in xml_folder.iterdir() 
                                 if f.is_file() and f.suffix.lower() == ".xml"])
        
        # Count updated HTML files
        updated_folder = project_path / "updatedhtmlfiles"
        if updated_folder.exists():
            counts["updated_html"] = len([f for f in updated_folder.iterdir() 
                                          if f.is_file() and f.suffix.lower() == ".html"])
        
        # Count impact_config.xml files in document folders
        for item in project_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                config_file = item / "impact_config.xml"
                if config_file.exists():
                    counts["impact_config"] += 1
        
        return counts
    
    def _count_document_status(self, project_path: Path) -> dict:
        """Count document completion status from database."""
        if not self._db:
            return {"total": 0, "completed": 0, "organized": 0, "with_config": 0, "compared": 0}
        
        all_docs = self._db.get_all()
        stats = {"total": len(all_docs), "completed": 0, "organized": 0, "with_config": 0, "compared": 0}
        
        for docid, doc in all_docs.items():
            if docid.startswith("_"):
                continue
            
            process = doc.get("process", {})
            if process.get("organized", False):
                stats["organized"] += 1
            if process.get("config_downloaded", False):
                stats["with_config"] += 1
            if process.get("compared", False):
                stats["compared"] += 1
            # Completed = all steps done
            if (process.get("organized", False) and 
                process.get("config_downloaded", False) and 
                process.get("compared", False) and 
                process.get("report_generated", False)):
                stats["completed"] += 1
        
        return stats
    
    def _log(self, message: str) -> None:
        """Append message to log."""
        # Check if log_text widget exists (may not during early init or from threads)
        if hasattr(self, 'log_text') and self.log_text.winfo_exists():
            self.log_text.insert("end", f"{message}\n")
            self.log_text.see("end")
            self.update_idletasks()
        else:
            # Fallback to print if widget not ready
            print(message)
    
    def _update_progress(self, current: int, total: int) -> None:
        """Update progress bar."""
        if total > 0:
            percent = (current / total) * 100
            self.progress_var.set(percent)
            self.progress_label.config(text=f"Processing {current}/{total} ({percent:.1f}%)")
        else:
            self.progress_var.set(0)
            self.progress_label.config(text="Ready")
        self.update_idletasks()
    
    def _update_stats(self) -> None:
        """Update statistics display."""
        if not self._db:
            self.stats_text.set("No project loaded")
            return
        
        stats = self._db.get_statistics()
        scan_stats = self._db.get_scan_stats()
        text = (
            f"Files in database: {scan_stats['total_scanned']} | "
            f"Organized: {stats['steps']['organized']} | "
            f"Downloaded: {stats['steps']['config_downloaded']} | "
            f"Compared: {stats['steps']['compared']} | "
            f"Errors: {stats['with_errors']}"
        )
        self.stats_text.set(text)
    
    def _update_button_states(self) -> None:
        """Enable/disable buttons based on project state."""
        self._log(f"Calling _update_button_states")
        has_project = self._db is not None
        state = "normal" if has_project else "disabled"
        
        # Check if buttons exist before configuring
        buttons = [
            ("scan_btn", getattr(self, 'scan_btn', None)),
            ("organize_btn", getattr(self, 'organize_btn', None)),
            ("download_btn", getattr(self, 'download_btn', None)),
            ("compare_btn", getattr(self, 'compare_btn', None)),
            ("report_btn", getattr(self, 'report_btn', None)),
            ("complete_btn", getattr(self, 'complete_btn', None)),
        ]
        
        for name, btn in buttons:
            if btn is not None and hasattr(btn, 'config'):
                try:
                    btn.config(state=state)
                except Exception as e:
                    self._log(f"Warning: Could not update {name}: {e}")
            else:
                self._log(f"Warning: Button {name} not found")
    
    def _run_in_thread(
        self,
        target: callable,
        on_complete: callable = None,
        on_error: callable = None,
    ) -> None:
        """Run operation in background thread."""
        def wrapper():
            try:
                result = target()
                if on_complete:
                    self.after(0, lambda: on_complete(result))
            except Exception as e:
                if on_error:
                    self.after(0, lambda: on_error(e))
        
        self._worker_thread = threading.Thread(target=wrapper, daemon=True)
        self._worker_thread.start()
    
    def _on_scan(self) -> None:
        """Handle Scan button."""
        if not self._db:
            return
        
        self._set_buttons_busy(True)
        self._log("Starting scan...")
        
        def do_scan():
            batch_size = self.batch_size_var.get()
            # Marshal log callback to main thread
            def safe_log(msg):
                self.after(0, lambda: self._log(msg))
            scanner = DocumentScanner(self._db, safe_log)
            return scanner.scan(batch_size=batch_size)
        
        def on_complete(result):
            processed, remaining = result
            self._set_buttons_busy(False)
            self._update_stats()
            
            if remaining > 0:
                message = f"Batch complete. Processed: {processed}, Remaining: {remaining}.\nClick Scan again to continue."
                self.scan_btn.config(text="Continue Scan")
                self._log(f"Batch complete. Processed: {processed}, Remaining: {remaining}")
            else:
                message = f"Scan complete. All {processed} files processed."
                self.scan_btn.config(text="Scan")
                self._log(f"Scan complete. All {processed} files processed.")
            
            messagebox.showinfo("Scan Complete", message)
        
        def on_error(e):
            self._set_buttons_busy(False)
            self._log(f"Scan failed: {e}")
            messagebox.showerror("Error", str(e))
        
        self._run_in_thread(do_scan, on_complete, on_error)
    
    def _on_organize(self) -> None:
        """Handle Organize button."""
        if not self._db:
            return
        
        self._set_buttons_busy(True)
        self._log("Starting organization...")
        
        def do_organize():
            # Marshal callbacks to main thread
            def safe_log(msg):
                self.after(0, lambda: self._log(msg))
            def safe_progress(current, total):
                self.after(0, lambda: self._update_progress(current, total))
            organizer = FolderOrganizer(
                self._db,
                log_callback=safe_log,
                progress_callback=safe_progress,
            )
            return organizer.organize()
        
        def on_complete(result):
            self._set_buttons_busy(False)
            success, failed = result
            self._log(f"Organization complete. Success: {success}, Failed: {failed}")
            self._update_stats()
            messagebox.showinfo("Organize Complete", f"Success: {success}, Failed: {failed}")
        
        def on_error(e):
            self._set_buttons_busy(False)
            self._log(f"Organization failed: {e}")
            messagebox.showerror("Error", str(e))
        
        self._run_in_thread(do_organize, on_complete, on_error)
    
    def _on_download(self) -> None:
        """Handle Download Config button."""
        if not self._db:
            return
        
        self._set_buttons_busy(True)
        self._log("Starting config downloads...")
        
        def do_download():
            # Marshal callbacks to main thread
            def safe_log(msg):
                self.after(0, lambda: self._log(msg))
            def safe_progress(current, total):
                self.after(0, lambda: self._update_progress(current, total))
            downloader = ConfigDownloader(
                self._db,
                log_callback=safe_log,
                progress_callback=safe_progress,
            )
            return downloader.download_all()
        
        def on_complete(result):
            self._set_buttons_busy(False)
            success, skipped, failed = result
            self._log(f"Downloads complete. Success: {success}, Skipped: {skipped}, Failed: {failed}")
            self._update_stats()
            messagebox.showinfo("Download Complete", f"Success: {success}, Skipped: {skipped}, Failed: {failed}")
        
        def on_error(e):
            self._set_buttons_busy(False)
            self._log(f"Download failed: {e}")
            messagebox.showerror("Error", str(e))
        
        self._run_in_thread(do_download, on_complete, on_error)
    
    def _on_compare(self) -> None:
        """Handle Compare button."""
        if not self._db:
            return
        
        self._set_buttons_busy(True)
        self._log("Starting comparisons...")
        
        def do_compare():
            # Marshal callbacks to main thread
            def safe_log(msg):
                self.after(0, lambda: self._log(msg))
            def safe_progress(current, total):
                self.after(0, lambda: self._update_progress(current, total))
            comparer = CompareManager(
                self._db,
                log_callback=safe_log,
                progress_callback=safe_progress,
            )
            options = CompareOptions()
            return comparer.compare_all(options=options)
        
        def on_complete(result):
            self._set_buttons_busy(False)
            success, skipped, failed = result
            self._log(f"Comparisons complete. Success: {success}, Skipped: {skipped}, Failed: {failed}")
            self._update_stats()
            messagebox.showinfo("Compare Complete", f"Success: {success}, Skipped: {skipped}, Failed: {failed}")
        
        def on_error(e):
            self._set_buttons_busy(False)
            self._log(f"Comparison failed: {e}")
            messagebox.showerror("Error", str(e))
        
        self._run_in_thread(do_compare, on_complete, on_error)
    
    def _on_report(self) -> None:
        """Handle Report button."""
        if not self._db:
            return
        
        self._set_buttons_busy(True)
        self._log("Generating reports...")
        
        def do_report():
            # Marshal callback to main thread
            def safe_log(msg):
                self.after(0, lambda: self._log(msg))
            reporter = ReportManager(self._db, safe_log)
            html_path = reporter.generate_html_summary()
            csv_path = reporter.generate_csv()
            return html_path, csv_path
        
        def on_complete(result):
            self._set_buttons_busy(False)
            html_path, csv_path = result
            self._log(f"Reports generated: {html_path}, {csv_path}")
            self._update_stats()
            
            if messagebox.askyesno("Reports Generated", "Open HTML report?"):
                # Use as_uri() for proper file URL format on all platforms
                webbrowser.open(html_path.as_uri())
        
        def on_error(e):
            self._set_buttons_busy(False)
            self._log(f"Report generation failed: {e}")
            messagebox.showerror("Error", str(e))
        
        self._run_in_thread(do_report, on_complete, on_error)
    
    def _on_complete_workflow(self) -> None:
        """Handle Complete Workflow button (runs all steps)."""
        if not self._db:
            return
        
        if not messagebox.askyesno(
            "Complete Workflow",
            "This will run: Scan → Organize → Download → Compare → Report.\n\nContinue?"
        ):
            return
        
        self._set_buttons_busy(True)
        self._log("=== Starting Complete Workflow ===")
        
        def do_complete():
            results = {}
            
            # Marshal callbacks to main thread
            def safe_log(msg):
                self.after(0, lambda: self._log(msg))
            def safe_progress(current, total):
                self.after(0, lambda: self._update_progress(current, total))
            
            # Scan (loop until all files scanned)
            safe_log("Step 1/5: Scanning...")
            scanner = DocumentScanner(self._db, safe_log)
            total_scanned = 0
            while True:
                processed, remaining = scanner.scan()
                total_scanned += processed
                if remaining == 0:
                    break
            results['scan'] = (total_scanned, 0)
            
            # Organize
            safe_log("Step 2/5: Organizing...")
            organizer = FolderOrganizer(self._db, safe_log, safe_progress)
            results['organize'] = organizer.organize()
            
            # Download
            safe_log("Step 3/5: Downloading configs...")
            downloader = ConfigDownloader(self._db, safe_log, safe_progress)
            results['download'] = downloader.download_all()
            
            # Compare
            safe_log("Step 4/5: Comparing...")
            comparer = CompareManager(self._db, safe_log, safe_progress)
            options = CompareOptions()
            results['compare'] = comparer.compare_all(options=options)
            
            # Report
            safe_log("Step 5/5: Generating reports...")
            reporter = ReportManager(self._db, safe_log)
            results['report'] = (
                reporter.generate_html_summary(),
                reporter.generate_csv(),
            )
            
            return results
        
        def on_complete(results):
            self._set_buttons_busy(False)
            self._log("=== Workflow Complete ===")
            self._update_stats()
            scan_processed, scan_remaining = results['scan']
            messagebox.showinfo(
                "Workflow Complete",
                f"Scan: {scan_processed} docs processed, {scan_remaining} remaining\n"
                f"Organize: {results['organize'][0]} success\n"
                f"Download: {results['download'][0]} success\n"
                f"Compare: {results['compare'][0]} success\n"
                f"Reports: Generated"
            )
        
        def on_error(e):
            self._set_buttons_busy(False)
            self._log(f"Workflow failed: {e}")
            messagebox.showerror("Workflow Error", str(e))
        
        self._run_in_thread(do_complete, on_complete, on_error)
    
    def _set_buttons_busy(self, busy: bool) -> None:
        """Set all action buttons to busy/disabled state."""
        state = "disabled" if busy else "normal"
        for btn in [self.scan_btn, self.organize_btn, self.download_btn,
                    self.compare_btn, self.report_btn, self.complete_btn, self.load_btn]:
            btn.config(state=state)
    
    def get_tab_name(self) -> str:
        """Return display name for tab."""
        return "Document Manager"

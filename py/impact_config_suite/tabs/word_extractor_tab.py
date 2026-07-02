import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from core.word_extractor import WordExtractor

class WordExtractorTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent)
        self.extractor = WordExtractor()
        self._build_ui()

    def _build_ui(self):
        # Main container with dark background
        main_container = tk.Frame(self, bg="#1e293b", padx=30, pady=25)
        main_container.pack(fill="both", expand=True)

        # Header
        tk.Label(
            main_container,
            text="WORD EXTRACTION TOOL",
            font=("Segoe UI", 18, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
        ).pack(pady=(0, 5))

        tk.Label(
            main_container,
            text="Extract comma-separated values from TXT files based on character patterns.",
            font=("Segoe UI", 10),
            fg="#94a3b8",
            bg="#1e293b",
        ).pack(pady=(0, 25))

        # --- Settings Frame ---
        settings_frame = tk.LabelFrame(
            main_container,
            text="Extraction Settings",
            bg="#1e293b",
            fg="#cbd5e1",
            font=("Segoe UI", 11, "bold"),
            padx=20,
            pady=15,
            bd=1,
            relief="flat"
        )
        settings_frame.pack(fill="x", pady=(0, 20))
        settings_frame.columnconfigure(1, weight=1)

        # File Selection
        tk.Label(
            settings_frame,
            text="Source TXT File:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10),
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.file_path_var = tk.StringVar()
        self.file_entry = tk.Entry(
            settings_frame,
            textvariable=self.file_path_var,
            bg="#334155",
            fg="white",
            border=0,
            font=("Segoe UI", 11),
        )
        self.file_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15), ipady=6)

        self.browse_btn = tk.Button(
            settings_frame,
            text="Browse File",
            command=self._browse_file,
            bg="#475569",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            border=0,
            padx=15,
            pady=5
        )
        self.browse_btn.grid(row=1, column=2, padx=(10, 0), pady=(0, 15))

        # Segment Selection
        tk.Label(
            settings_frame,
            text="Target Segment:",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10),
        ).grid(row=2, column=0, sticky="w", pady=(0, 5))

        self.segment_var = tk.StringVar(value="Non-Alphabetic")
        self.segment_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.segment_var,
            values=["Non-Alphabetic", "Alphabetic Only", "Numeric Only"],
            state="readonly",
            font=("Segoe UI", 10)
        )
        self.segment_combo.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 5), ipady=4)

        # --- Action Buttons ---
        btn_frame = tk.Frame(main_container, bg="#1e293b")
        btn_frame.pack(fill="x", pady=(0, 15))

        self.extract_btn = tk.Button(
            btn_frame,
            text="🚀  RUN EXTRACTION",
            command=self._start_extraction,
            bg="#0ea5e9",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            border=0,
            padx=30,
            pady=12,
        )
        self.extract_btn.pack(side="left", fill="x", expand=True)

        self.auto_btn = tk.Button(
            btn_frame,
            text="⚡  AUTO PROCESS (ALL)",
            command=self._start_auto_process,
            bg="#f59e0b",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            border=0,
            padx=30,
            pady=12,
        )
        self.auto_btn.pack(side="left", fill="x", expand=True, padx=(15, 0))

        self.export_list_btn = tk.Button(
            btn_frame,
            text="📥  Export (List)",
            command=lambda: self._export_results("list"),
            bg="#10b981",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=15,
            pady=12,
            state="disabled"
        )
        self.export_list_btn.pack(side="left", padx=(15, 0))

        self.export_comma_btn = tk.Button(
            btn_frame,
            text="🔗  Export (Comma)",
            command=lambda: self._export_results("comma"),
            bg="#059669",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=15,
            pady=12,
            state="disabled"
        )
        self.export_comma_btn.pack(side="left", padx=(10, 0))

        # --- Results Area ---
        tk.Label(
            main_container,
            text="Results Console:",
            bg="#1e293b", fg="#64748b", font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(10, 5))

        res_frame = tk.Frame(main_container, bg="#0f172a")
        res_frame.pack(fill="both", expand=True)

        self.res_text = tk.Text(
            res_frame,
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="white",
            border=0,
            font=("Consolas", 10),
            padx=10,
            pady=10
        )
        scroll = ttk.Scrollbar(res_frame, command=self.res_text.yview)
        self.res_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.res_text.pack(fill="both", expand=True)

        # Context Menu for results
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy All", command=self._copy_all)
        self.context_menu.add_command(label="Clear", command=lambda: self.res_text.delete("1.0", tk.END))
        self.res_text.bind("<Button-3>", self._show_context_menu)

        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(
            main_container,
            textvariable=self.status_var,
            bg="#1e293b",
            fg="#475569",
            font=("Segoe UI", 9, "italic"),
        )
        self.status_label.pack(anchor="w", pady=(10, 0))

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select File",
            filetypes=[("All Supported", "*.txt *.html *.xml *.xhtml *.htm"), ("Text Files", "*.txt"), ("HTML/XML", "*.html *.xml"), ("All Files", "*.*")]
        )
        if path:
            self.file_path_var.set(os.path.abspath(path))

    def _start_extraction(self):
        file_path = self.file_path_var.get().strip()
        segment = self.segment_var.get()

        if not file_path:
            messagebox.showerror("Error", "Please select a source file.")
            return

        self.extract_btn.config(state="disabled", text="EXTRACTING...")
        self.status_var.set(f"Processing {os.path.basename(file_path)}...")
        self.res_text.delete("1.0", tk.END)

        # Run in thread to keep UI responsive
        threading.Thread(target=self._run_extraction_logic, args=(file_path, segment), daemon=True).start()

    def _run_extraction_logic(self, file_path, segment):
        try:
            result = self.extractor.extract(file_path, segment)
            if result["ok"]:
                vals = result["result"]
                self.res_text.insert(tk.END, f"--- {segment} Results ---\n")
                self.res_text.insert(tk.END, "\n".join(vals))
                self.status_var.set(f"Extraction complete. Total unique items: {result['total']}")
                self.export_list_btn.config(state="normal")
                self.export_comma_btn.config(state="normal")
            else:
                messagebox.showerror("Error", result["error"])
                self.status_var.set("Extraction failed.")
        except Exception as e:
            messagebox.showerror("Critical Error", str(e))
            self.status_var.set("An error occurred.")
        finally:
            self.extract_btn.config(state="normal", text="🚀  RUN EXTRACTION")

    def _start_auto_process(self):
        file_path = self.file_path_var.get().strip()
        if not file_path:
            messagebox.showerror("Error", "Please select a source file.")
            return

        self.auto_btn.config(state="disabled", text="AUTO PROCESSING...")
        self.res_text.delete("1.0", tk.END)
        self.res_text.insert(tk.END, "🚀 Starting Auto-Process workflow...\n")
        
        threading.Thread(target=self._run_auto_process_logic, args=(file_path,), daemon=True).start()

    def _run_auto_process_logic(self, file_path):
        import datetime
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            input_dir = os.path.dirname(file_path)
            input_name = os.path.splitext(os.path.basename(file_path))[0]
            is_html = file_path.lower().endswith(('.html', '.xml', '.xhtml', '.htm'))

            # Step 1: Handle HTML/XML specific text extraction and unique words
            if is_html:
                self.res_text.insert(tk.END, "Step 1: Extracting text from markup...\n")
                raw_text = self.extractor.extract_text_from_html(file_path)
                unique_words = self.extractor.get_unique_words(raw_text, filter_stop_words=True)
                
                txt_out = os.path.join(input_dir, f"{input_name}_UniqueWords_{ts}.txt")
                with open(txt_out, "w", encoding="utf-8") as f:
                    f.write("\n".join(unique_words))
                self.res_text.insert(tk.END, f"✔ Saved Unique Words: {os.path.basename(txt_out)}\n")

            # Step 2: Run all segments
            self.res_text.insert(tk.END, "Step 2: Running all extraction segments...\n")
            all_results = self.extractor.process_all(file_path)
            
            # Step 3: Save Comma-Separated TXT (All Items)
            self.res_text.insert(tk.END, "Step 3: Generating comma-separated export...\n")
            # Flatten all results into one list for the CSV-like output
            flat_list = []
            for seg_vals in all_results.values():
                flat_list.extend(seg_vals)
            flat_list = sorted(list(set(flat_list))) # Unique and sorted
            
            comma_out = os.path.join(input_dir, f"{input_name}_CommaSeparated_{ts}.txt")
            with open(comma_out, "w", encoding="utf-8") as f:
                f.write(", ".join(flat_list))
            self.res_text.insert(tk.END, f"✔ Saved Comma TXT: {os.path.basename(comma_out)}\n")

            # Step 4: Generate and Save Master HTML Report
            self.res_text.insert(tk.END, "Step 4: Creating Master HTML Report...\n")
            report_html = self.extractor.generate_html_report(all_results, file_path)
            report_out = os.path.join(input_dir, f"{input_name}_MasterReport_{ts}.html")
            
            with open(report_out, "w", encoding="utf-8") as f:
                f.write(report_html)
            
            self.res_text.insert(tk.END, f"✔ Saved Master Report: {os.path.basename(report_out)}\n")
            self.res_text.insert(tk.END, "\n✨ WORKFLOW COMPLETE ✨\n")
            
            self.status_var.set("Auto-Process Complete (3 files generated).")
            
            import webbrowser
            webbrowser.open(f"file:///{os.path.abspath(report_out)}")
            
        except Exception as e:
            self.res_text.insert(tk.END, f"\n❌ ERROR: {str(e)}\n")
            messagebox.showerror("Auto Process Error", str(e))
        finally:
            self.auto_btn.config(state="normal", text="⚡  AUTO PROCESS (ALL)")

    def _export_results(self, mode="list"):
        content_list = [c for c in self.res_text.get("1.0", tk.END).strip().split("\n") if c.strip() and not c.startswith("---")]
        input_file = self.file_path_var.get()
        segment = self.segment_var.get()

        if not content_list or not input_file:
            return

        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        input_dir = os.path.dirname(input_file)
        input_name = os.path.splitext(os.path.basename(input_file))[0]
        
        ext = ".html" if mode == "list" else ".txt"
        default_name = f"{input_name}_Extracted_{ts}{ext}"

        path = filedialog.asksaveasfilename(
            initialdir=input_dir,
            initialfile=default_name,
            defaultextension=ext,
            filetypes=[("HTML Files", "*.html"), ("Text Files", "*.txt")],
            title=f"Export Results ({mode.capitalize()})"
        )
        
        if path:
            try:
                if path.endswith(".html"):
                    report_html = self.extractor.generate_html_report({segment: content_list}, input_file)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(report_html)
                elif mode == "comma":
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(", ".join(content_list))
                else:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write("\n".join(content_list))
                
                messagebox.showinfo("Success", f"Results exported to {os.path.basename(path)}")
                import webbrowser
                webbrowser.open(f"file:///{os.path.abspath(path)}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def _show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def _copy_all(self):
        content = self.res_text.get("1.0", tk.END).strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self.status_var.set("Copied to clipboard.")

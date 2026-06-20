"""
Add inline report table (Treeview) to HTMLCompareReplaceTab._build_ui and
populate it in _load_and_compare so users can filter/find diffs inside the GUI.
"""
from pathlib import Path

SRC = Path(__file__).parent.parent / "compare_tab.py"
content = SRC.read_text(encoding="utf-8")

# ── 1. Replace _build_ui in HTMLCompareReplaceTab ────────────────────────────
OLD_BUILD = '''    def _build_ui(self) -> None:
        # Header
        header = tk.Frame(self, bg="#1e293b", padx=20, pady=15)
        header.pack(fill="x")
        
        tk.Label(header, text="VISUAL COMPARE & SYNC", font=("Segoe UI", 16, "bold"), fg="#818cf8", bg="#1e293b").pack(side="left")
        
        tk.Checkbutton(
            header,
            text="Raw View (Faster for Large Files)",
            variable=self.raw_view_var,
            command=self._load_and_compare,
            bg="#1e293b",
            fg="#94a3b8",
            selectcolor="#1e293b",
            activebackground="#1e293b",
            activeforeground="#ffffff",
            font=("Segoe UI", 9)
        ).pack(side="right")
        
        # File Selectors
        file_frame = tk.Frame(self, bg="#0f172a", padx=20, pady=10)
        file_frame.pack(fill="x")
        file_frame.columnconfigure(1, weight=1)
        file_frame.columnconfigure(4, weight=1)

        tk.Label(file_frame, text="Source:", fg="#94a3b8", bg="#0f172a").grid(row=0, column=0, sticky="w")
        tk.Entry(file_frame, textvariable=self.source_path, bg="#1f2937", fg="white", border=0).grid(row=0, column=1, sticky="ew", padx=5, ipady=3)
        tk.Button(file_frame, text="...", command=lambda: self._browse(self.source_path)).grid(row=0, column=2)

        tk.Label(file_frame, text="Update:", fg="#94a3b8", bg="#0f172a").grid(row=0, column=3, sticky="w", padx=(20, 0))
        tk.Entry(file_frame, textvariable=self.update_path, bg="#1f2937", fg="white", border=0).grid(row=0, column=4, sticky="ew", padx=5, ipady=3)
        tk.Button(file_frame, text="...", command=lambda: self._browse(self.update_path)).grid(row=0, column=5)

        # Selector
        sel_frame = tk.Frame(self, bg="#0f172a", padx=20, pady=5)
        sel_frame.pack(fill="x")
        tk.Label(sel_frame, text="Query Selector:", fg="#94a3b8", bg="#0f172a").pack(side="left")
        tk.Entry(sel_frame, textvariable=self.selector_var, bg="#1f2937", fg="white", width=40, border=0).pack(side="left", padx=10, ipady=3)
        tk.Button(sel_frame, text="🚀 Load & Compare", command=self._load_and_compare, bg="#6366f1", fg="white", border=0, padx=15).pack(side="left")

        # Main View (Two Columns)
        self.paned = ttk.PanedWindow(self, orient="horizontal")
        self.paned.pack(fill="both", expand=True, padx=10, pady=10)

        self.src_text = tk.Text(self.paned, wrap="word", bg="#0f172a", fg="#e2e8f0", font=("Consolas", 11), padx=10, pady=10, border=0)
        self.upd_text = tk.Text(self.paned, wrap="word", bg="#0f172a", fg="#e2e8f0", font=("Consolas", 11), padx=10, pady=10, border=0)
        
        # Synchronized Scrolling
        def sync_scroll(*args):
            self.src_text.yview(*args)
            self.upd_text.yview(*args)
            
        self.src_text.config(yscrollcommand=lambda *args: self._on_scroll(self.upd_text, *args))
        self.upd_text.config(yscrollcommand=lambda *args: self._on_scroll(self.src_text, *args))

        self.paned.add(self.src_text, weight=1)
        self.paned.add(self.upd_text, weight=1)

        # Setup Tags
        for txt in [self.src_text, self.upd_text]:
            txt.tag_config("diff", background="#312e81", borderwidth=1, relief="solid")
            txt.tag_config("current", background="#4338ca", borderwidth=2, relief="raised")
            txt.tag_config("del", foreground="#f87171")
            txt.tag_config("ins", foreground="#4ade80")
            txt.tag_config("anchor", foreground="#60a5fa", font=("Consolas", 11, "bold"))

        # Footer
        footer = tk.Frame(self, bg="#1e293b", padx=20, pady=10)
        footer.pack(fill="x")
        
        self.status_label = tk.Label(footer, text="Load files to start.", fg="#94a3b8", bg="#1e293b")
        self.status_label.pack(side="left")

        btn_frame = tk.Frame(footer, bg="#1e293b")
        btn_frame.pack(side="right")

        tk.Button(btn_frame, text="⬅ Prev", command=self._prev_diff, bg="#475569", fg="white", border=0, padx=10, pady=5).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Next ➡", command=self._next_diff, bg="#475569", fg="white", border=0, padx=10, pady=5).pack(side="left", padx=5)
        self.replace_btn = tk.Button(btn_frame, text="♻ Replace Current", command=self._replace_current, bg="#f43f5e", fg="white", border=0, padx=20, pady=5, state="disabled")
        self.replace_btn.pack(side="left", padx=(20, 0))'''

NEW_BUILD = '''    def _build_ui(self) -> None:
        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(self, bg="#1e293b", padx=20, pady=15)
        header.pack(fill="x")
        tk.Label(header, text="VISUAL COMPARE & SYNC", font=("Segoe UI", 16, "bold"),
                 fg="#818cf8", bg="#1e293b").pack(side="left")
        tk.Checkbutton(header, text="Raw View (Faster for Large Files)",
                       variable=self.raw_view_var, command=self._load_and_compare,
                       bg="#1e293b", fg="#94a3b8", selectcolor="#1e293b",
                       activebackground="#1e293b", activeforeground="#ffffff",
                       font=("Segoe UI", 9)).pack(side="right")

        # ── File Selectors ────────────────────────────────────────────────────
        file_frame = tk.Frame(self, bg="#0f172a", padx=20, pady=10)
        file_frame.pack(fill="x")
        file_frame.columnconfigure(1, weight=1)
        file_frame.columnconfigure(4, weight=1)
        tk.Label(file_frame, text="Source:", fg="#94a3b8", bg="#0f172a").grid(row=0, column=0, sticky="w")
        tk.Entry(file_frame, textvariable=self.source_path, bg="#1f2937", fg="white", border=0).grid(row=0, column=1, sticky="ew", padx=5, ipady=3)
        tk.Button(file_frame, text="...", command=lambda: self._browse(self.source_path)).grid(row=0, column=2)
        tk.Label(file_frame, text="Update:", fg="#94a3b8", bg="#0f172a").grid(row=0, column=3, sticky="w", padx=(20, 0))
        tk.Entry(file_frame, textvariable=self.update_path, bg="#1f2937", fg="white", border=0).grid(row=0, column=4, sticky="ew", padx=5, ipady=3)
        tk.Button(file_frame, text="...", command=lambda: self._browse(self.update_path)).grid(row=0, column=5)

        # ── Selector + Load ───────────────────────────────────────────────────
        sel_frame = tk.Frame(self, bg="#0f172a", padx=20, pady=5)
        sel_frame.pack(fill="x")
        tk.Label(sel_frame, text="Query Selector:", fg="#94a3b8", bg="#0f172a").pack(side="left")
        tk.Entry(sel_frame, textvariable=self.selector_var, bg="#1f2937", fg="white",
                 width=40, border=0).pack(side="left", padx=10, ipady=3)
        tk.Button(sel_frame, text="🚀 Load & Compare", command=self._load_and_compare,
                  bg="#6366f1", fg="white", border=0, padx=15).pack(side="left")

        # ── Vertical split: top = text panels, bottom = report table ─────────
        self.main_paned = ttk.PanedWindow(self, orient="vertical")
        self.main_paned.pack(fill="both", expand=True, padx=10, pady=(6, 0))

        # Text panels (horizontal split)
        self.paned = ttk.PanedWindow(self.main_paned, orient="horizontal")
        self.src_text = tk.Text(self.paned, wrap="word", bg="#0f172a", fg="#e2e8f0",
                                font=("Consolas", 11), padx=10, pady=10, border=0)
        self.upd_text = tk.Text(self.paned, wrap="word", bg="#0f172a", fg="#e2e8f0",
                                font=("Consolas", 11), padx=10, pady=10, border=0)
        self.src_text.config(yscrollcommand=lambda *a: self._on_scroll(self.upd_text, *a))
        self.upd_text.config(yscrollcommand=lambda *a: self._on_scroll(self.src_text, *a))
        self.paned.add(self.src_text, weight=1)
        self.paned.add(self.upd_text, weight=1)
        self.main_paned.add(self.paned, weight=2)

        for txt in [self.src_text, self.upd_text]:
            txt.tag_config("diff", background="#312e81", borderwidth=1, relief="solid")
            txt.tag_config("current", background="#4338ca", borderwidth=2, relief="raised")
            txt.tag_config("del", foreground="#f87171")
            txt.tag_config("ins", foreground="#4ade80")
            txt.tag_config("anchor", foreground="#60a5fa", font=("Consolas", 11, "bold"))

        # ── Inline Report Panel ───────────────────────────────────────────────
        report_outer = tk.Frame(self.main_paned, bg="#0f172a")
        self.main_paned.add(report_outer, weight=1)

        # Filter + Find bar
        bar = tk.Frame(report_outer, bg="#0f172a", padx=8, pady=6)
        bar.pack(fill="x")
        bar.columnconfigure(1, weight=1)
        bar.columnconfigure(4, weight=1)

        tk.Label(bar, text="Filter:", bg="#0f172a", fg="#94a3b8",
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
        self.rpt_filter_var = tk.StringVar()
        tk.Entry(bar, textvariable=self.rpt_filter_var, bg="#1f2937", fg="white",
                 border=0, font=("Segoe UI", 10)).grid(row=0, column=1, sticky="ew", padx=(6, 0), ipady=3)

        tk.Label(bar, text="Status:", bg="#0f172a", fg="#94a3b8",
                 font=("Segoe UI", 9)).grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.rpt_status_var = tk.StringVar(value="")
        self.rpt_status_cb = ttk.Combobox(bar, textvariable=self.rpt_status_var,
                                           state="readonly", width=18)
        self.rpt_status_cb.grid(row=0, column=3, padx=(4, 0))

        tk.Label(bar, text="Parent:", bg="#0f172a", fg="#94a3b8",
                 font=("Segoe UI", 9)).grid(row=0, column=4, sticky="w", padx=(10, 0))
        self.rpt_parent_var = tk.StringVar(value="")
        self.rpt_parent_cb = ttk.Combobox(bar, textvariable=self.rpt_parent_var,
                                           state="readonly", width=24)
        self.rpt_parent_cb.grid(row=0, column=5, padx=(4, 0))

        tk.Button(bar, text="Apply", command=self._rpt_apply_filter,
                  bg="#3b82f6", fg="white", border=0, padx=10, pady=3,
                  font=("Segoe UI", 9, "bold")).grid(row=0, column=6, padx=(8, 0))
        tk.Button(bar, text="Clear", command=self._rpt_clear_filter,
                  bg="#475569", fg="white", border=0, padx=10, pady=3,
                  font=("Segoe UI", 9, "bold")).grid(row=0, column=7, padx=(4, 0))

        # Find bar
        find_bar = tk.Frame(report_outer, bg="#111827", padx=8, pady=4)
        find_bar.pack(fill="x")
        tk.Label(find_bar, text="🔍 Find:", bg="#111827", fg="#94a3b8",
                 font=("Segoe UI", 9)).pack(side="left")
        self.rpt_find_var = tk.StringVar()
        tk.Entry(find_bar, textvariable=self.rpt_find_var, bg="#1f2937", fg="white",
                 border=0, font=("Segoe UI", 10), width=28).pack(side="left", padx=6, ipady=3)
        tk.Button(find_bar, text="Find ↓", command=lambda: self._rpt_find(1),
                  bg="#6366f1", fg="white", border=0, padx=8, pady=3,
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        tk.Button(find_bar, text="↑ Prev", command=lambda: self._rpt_find(-1),
                  bg="#6366f1", fg="white", border=0, padx=8, pady=3,
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        tk.Button(find_bar, text="Clear", command=self._rpt_find_clear,
                  bg="#475569", fg="white", border=0, padx=8, pady=3,
                  font=("Segoe UI", 9, "bold")).pack(side="left")
        self.rpt_find_label = tk.Label(find_bar, text="", bg="#111827", fg="#60a5fa",
                                        font=("Segoe UI", 9))
        self.rpt_find_label.pack(side="left", padx=(8, 0))

        # Treeview
        RPT_COLS = ("anchor_id", "data_user", "data_time", "file_0", "file_1",
                    "status", "parent_status", "reason")
        RPT_HEADS = ("Anchor ID", "data-username", "data-time", "Source",
                     "Update", "Status", "Parent Status", "Reason")
        tree_frame = tk.Frame(report_outer, bg="#111827")
        tree_frame.pack(fill="both", expand=True)
        self.rpt_tree = ttk.Treeview(tree_frame, columns=RPT_COLS,
                                      show="headings", height=8)
        for col, head in zip(RPT_COLS, RPT_HEADS):
            self.rpt_tree.heading(col, text=head)
            w = 260 if col in ("file_0", "file_1") else 150
            self.rpt_tree.column(col, width=w, anchor="w")
        self.rpt_tree.tag_configure("same",    background="#1a2e1a", foreground="#86efac")
        self.rpt_tree.tag_configure("changed", background="#2e1a1a", foreground="#fca5a5")
        self.rpt_tree.tag_configure("other",   background="#1e1a2e", foreground="#c4b5fd")
        self.rpt_tree.tag_configure("default", background="#111827", foreground="#cbd5e1")
        self.rpt_tree.tag_configure("find",    background="#78350f", foreground="#fde68a")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.rpt_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.rpt_tree.xview)
        self.rpt_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.rpt_tree.pack(fill="both", expand=True)
        self.rpt_tree.bind("<<TreeviewSelect>>", self._rpt_on_select)
        self._rpt_all_rows: list[dict] = []
        self._rpt_find_matches: list = []
        self._rpt_find_idx: int = -1

        # ── Footer ─────────────────────────────────────────────────────────
        footer = tk.Frame(self, bg="#1e293b", padx=20, pady=8)
        footer.pack(fill="x")
        self.status_label = tk.Label(footer, text="Load files to start.",
                                      fg="#94a3b8", bg="#1e293b")
        self.status_label.pack(side="left")
        btn_frame = tk.Frame(footer, bg="#1e293b")
        btn_frame.pack(side="right")
        tk.Button(btn_frame, text="⬅ Prev", command=self._prev_diff,
                  bg="#475569", fg="white", border=0, padx=10, pady=5).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Next ➡", command=self._next_diff,
                  bg="#475569", fg="white", border=0, padx=10, pady=5).pack(side="left", padx=5)
        self.replace_btn = tk.Button(btn_frame, text="♻ Replace Current",
                                      command=self._replace_current,
                                      bg="#f43f5e", fg="white", border=0,
                                      padx=20, pady=5, state="disabled")
        self.replace_btn.pack(side="left", padx=(20, 0))'''

assert OLD_BUILD in content, "OLD_BUILD not found"
content = content.replace(OLD_BUILD, NEW_BUILD, 1)

# ── 2. Replace _load_and_compare to also populate the report table ────────────
OLD_LOAD = '''    def _load_and_compare(self):
        src_path = self.source_path.get().strip()
        upd_path = self.update_path.get().strip()
        if not src_path or not upd_path:
            messagebox.showwarning("Warning", "Please select both Source and Update files.")
            return

        # Use logic from HTMLCompareTab to get diffs
        temp_comp = HTMLCompareTab(self.master) # Dummy to reuse logic
        rows, _, _, _ = temp_comp._compare_two_html(src_path, upd_path, self.selector_var.get())
        
        # Filter for changes only
        self.diffs = [r for r in rows if "Same" not in r["status"]]
        self.current_idx = -1
        
        # Display content
        self._display_file(self.src_text, src_path)
        self._display_file(self.upd_text, upd_path)
        
        self._update_status()
        if self.diffs:
            self.replace_btn.config(state="normal")
            self._next_diff()
        else:
            self.replace_btn.config(state="disabled")'''

NEW_LOAD = '''    def _load_and_compare(self):
        src_path = self.source_path.get().strip()
        upd_path = self.update_path.get().strip()
        if not src_path or not upd_path:
            messagebox.showwarning("Warning", "Please select both Source and Update files.")
            return

        temp_comp = HTMLCompareTab(self.master)
        rows, _, headings, _ = temp_comp._compare_two_html(src_path, upd_path, self.selector_var.get())

        # Store ALL rows for the inline report
        self._rpt_all_rows = rows
        self._rpt_populate(rows, headings)

        # Filter changed-only rows for diff navigation
        self.diffs = [r for r in rows if "Same" not in r["status"]]
        self.current_idx = -1

        self._display_file(self.src_text, src_path)
        self._display_file(self.upd_text, upd_path)

        self._update_status()
        if self.diffs:
            self.replace_btn.config(state="normal")
            self._next_diff()
        else:
            self.replace_btn.config(state="disabled")

    # ── Inline Report helpers ─────────────────────────────────────────────────

    _RPT_COLS = ("anchor_id", "data_user", "data_time", "file_0", "file_1",
                 "status", "parent_status", "reason")

    def _row_tag(self, row: dict) -> str:
        st = str(row.get("status", "")).lower()
        ps = str(row.get("parent_status", ""))
        if "same" in st:
            return "same"
        if "changed" in st:
            return "changed"
        if ps and ps != "\u2014":
            return "other"
        return "default"

    def _rpt_populate(self, rows: list[dict], headings: dict | None = None) -> None:
        """Fill the inline report treeview and update filter dropdowns."""
        self.rpt_tree.delete(*self.rpt_tree.get_children())
        self._rpt_find_matches = []
        self._rpt_find_idx = -1
        self.rpt_find_label.config(text="")

        # Update file_0/file_1 column headings if available
        if headings:
            for col, label in (("file_0", headings.get("file_0", "Source")),
                                ("file_1", headings.get("file_1", "Update"))):
                self.rpt_tree.heading(col, text=label)

        statuses = sorted({str(r.get("status", "")) for r in rows if r.get("status")})
        parents  = sorted({str(r.get("parent_status", "")) for r in rows
                           if r.get("parent_status") and r.get("parent_status") != "\u2014"})

        self.rpt_status_cb["values"] = [""] + statuses
        self.rpt_parent_cb["values"] = [""] + parents

        for row in rows:
            vals = [str(row.get(c, "")) for c in self._RPT_COLS]
            tag  = self._row_tag(row)
            self.rpt_tree.insert("", tk.END, values=vals, tags=(tag,))

    def _rpt_apply_filter(self) -> None:
        txt  = self.rpt_filter_var.get().strip().lower()
        st   = self.rpt_status_var.get().strip()
        ps   = self.rpt_parent_var.get().strip()
        rows = [r for r in self._rpt_all_rows
                if (not txt or txt in " ".join(str(v) for v in r.values()).lower())
                and (not st or str(r.get("status", "")) == st)
                and (not ps or str(r.get("parent_status", "")) == ps)]
        self._rpt_populate(rows)

    def _rpt_clear_filter(self) -> None:
        self.rpt_filter_var.set("")
        self.rpt_status_var.set("")
        self.rpt_parent_var.set("")
        self._rpt_populate(self._rpt_all_rows)

    def _rpt_find(self, direction: int = 1) -> None:
        query = self.rpt_find_var.get().strip().lower()
        if not query:
            return
        children = self.rpt_tree.get_children()
        matches = [iid for iid in children
                   if query in " ".join(str(v) for v in self.rpt_tree.item(iid, "values")).lower()]
        if not matches:
            self.rpt_find_label.config(text="Not found")
            return
        if matches != self._rpt_find_matches:
            self._rpt_find_matches = matches
            self._rpt_find_idx = 0 if direction > 0 else len(matches) - 1
        else:
            self._rpt_find_idx = (self._rpt_find_idx + direction) % len(matches)

        # Clear previous find highlight
        for iid in self._rpt_find_matches:
            existing_tags = list(self.rpt_tree.item(iid, "tags"))
            if "find" in existing_tags:
                existing_tags.remove("find")
            self.rpt_tree.item(iid, tags=tuple(existing_tags))

        target = self._rpt_find_matches[self._rpt_find_idx]
        self.rpt_tree.item(target, tags=("find",))
        self.rpt_tree.see(target)
        self.rpt_tree.selection_set(target)
        self.rpt_find_label.config(
            text=f"{self._rpt_find_idx + 1} / {len(matches)}"
        )

    def _rpt_find_clear(self) -> None:
        self.rpt_find_var.set("")
        self._rpt_find_matches = []
        self._rpt_find_idx = -1
        self.rpt_find_label.config(text="")
        # Re-apply tags
        for iid in self.rpt_tree.get_children():
            vals = self.rpt_tree.item(iid, "values")
            row = dict(zip(self._RPT_COLS, vals))
            self.rpt_tree.item(iid, tags=(self._row_tag(row),))

    def _rpt_on_select(self, _event) -> None:
        """Clicking a report row jumps the text panels to that diff."""
        sel = self.rpt_tree.selection()
        if not sel:
            return
        vals = self.rpt_tree.item(sel[0], "values")
        if not vals:
            return
        row = dict(zip(self._RPT_COLS, vals))
        raw0 = row.get("file_0", "")
        raw1 = row.get("file_1", "")
        self._highlight_and_scroll(self.src_text, raw0)
        self._highlight_and_scroll(self.upd_text, raw1)'''

assert OLD_LOAD in content, "OLD_LOAD not found"
content = content.replace(OLD_LOAD, NEW_LOAD, 1)

SRC.write_text(content, encoding="utf-8")
print(f"Done. Lines: {content.count(chr(10))}")

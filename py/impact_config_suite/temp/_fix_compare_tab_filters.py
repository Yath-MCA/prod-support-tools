"""
Add Status dropdown, Parent Status dropdown, and Find bar to HTMLCompareTab.
Also update _apply_filter and _show_rows to populate the new dropdowns.
"""
from pathlib import Path

SRC = Path(__file__).parent.parent / "compare_tab.py"
content = SRC.read_text(encoding="utf-8")

# ── 1. Extend filter_frame with Status + Parent Status dropdowns + Find bar ──
OLD_STRICT = '''        self.strict_review_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            filter_frame,
            text="Strict Review Mode (Copyeditor only, No interference)",
            variable=self.strict_review_var,
            command=self._apply_filter,
            bg="#0f172a",
            fg="#f43f5e",
            selectcolor="#0f172a",
            activebackground="#0f172a",
            activeforeground="#ffffff",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(4, 0))'''

NEW_STRICT = '''        self.strict_review_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            filter_frame,
            text="Strict Review Mode (Copyeditor only, No interference)",
            variable=self.strict_review_var,
            command=self._apply_filter,
            bg="#0f172a",
            fg="#f43f5e",
            selectcolor="#0f172a",
            activebackground="#0f172a",
            activeforeground="#ffffff",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(4, 0))

        # ── Status + Parent Status dropdowns ─────────────────────────────────
        tk.Label(filter_frame, text="Status:", bg="#0f172a", fg="#94a3b8",
                 font=("Segoe UI", 10)).grid(row=4, column=0, sticky="w", pady=(10, 0))
        self.status_filter_var = tk.StringVar(value="")
        self.status_filter_cb = ttk.Combobox(
            filter_frame, textvariable=self.status_filter_var,
            state="readonly", width=22, font=("Segoe UI", 10)
        )
        self.status_filter_cb.grid(row=4, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        self.status_filter_cb.bind("<<ComboboxSelected>>", lambda _e: self._apply_filter())

        tk.Label(filter_frame, text="Parent Status:", bg="#0f172a", fg="#94a3b8",
                 font=("Segoe UI", 10)).grid(row=4, column=2, sticky="w",
                                             padx=(16, 0), pady=(10, 0))
        self.parent_filter_var = tk.StringVar(value="")
        self.parent_filter_cb = ttk.Combobox(
            filter_frame, textvariable=self.parent_filter_var,
            state="readonly", width=28, font=("Segoe UI", 10)
        )
        self.parent_filter_cb.grid(row=4, column=3, sticky="w", padx=(6, 0), pady=(10, 0))
        self.parent_filter_cb.bind("<<ComboboxSelected>>", lambda _e: self._apply_filter())

        # ── Find bar ─────────────────────────────────────────────────────────
        find_frame = tk.Frame(filter_frame, bg="#0f172a")
        find_frame.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(10, 0))

        tk.Label(find_frame, text="🔍 Find:", bg="#0f172a", fg="#94a3b8",
                 font=("Segoe UI", 10)).pack(side="left")
        self.find_var = tk.StringVar()
        tk.Entry(find_frame, textvariable=self.find_var, bg="#1f2937", fg="white",
                 border=0, font=("Segoe UI", 10), width=30).pack(
                     side="left", padx=(8, 0), ipady=4)
        tk.Button(find_frame, text="Find ↓", command=lambda: self._find_in_tree(1),
                  bg="#6366f1", fg="white", border=0, padx=12, pady=4,
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(8, 0))
        tk.Button(find_frame, text="↑ Prev", command=lambda: self._find_in_tree(-1),
                  bg="#6366f1", fg="white", border=0, padx=12, pady=4,
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(4, 0))
        tk.Button(find_frame, text="Clear", command=self._find_clear,
                  bg="#475569", fg="white", border=0, padx=12, pady=4,
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(4, 0))
        self.find_label = tk.Label(find_frame, text="", bg="#0f172a", fg="#60a5fa",
                                    font=("Segoe UI", 9))
        self.find_label.pack(side="left", padx=(8, 0))
        self._find_matches: list = []
        self._find_idx: int = -1'''

assert OLD_STRICT in content, "OLD_STRICT not found"
content = content.replace(OLD_STRICT, NEW_STRICT, 1)

# ── 2. Update _show_rows to populate status/parent dropdowns ─────────────────
OLD_SHOW = '''    def _show_rows(self, rows: list[dict], columns: list[str], headings: dict[str, str]) -> None:
        self._configure_tree(columns, headings)
        
        priority_user = self.priority_user_var.get().strip().lower()
        
        # Sort rows: priority user first, then by anchor id
        def sort_key(r):
            user = str(r.get("data_user", "")).lower()
            is_priority = 0 if priority_user and priority_user in user else 1
            return (is_priority, r.get("anchor_id", ""), r.get("data_time", ""))

        sorted_rows = sorted(rows, key=sort_key)
        
        for row in sorted_rows:
            values = [row.get(col, "") for col in columns]
            user = str(row.get("data_user", "")).lower()
            tag = "priority" if priority_user and priority_user in user else "default"
            self.tree.insert("", tk.END, values=values, tags=(tag,))'''

NEW_SHOW = '''    def _show_rows(self, rows: list[dict], columns: list[str], headings: dict[str, str]) -> None:
        self._configure_tree(columns, headings)

        priority_user = self.priority_user_var.get().strip().lower()

        # Sort rows: priority user first, then by anchor id
        def sort_key(r):
            user = str(r.get("data_user", "")).lower()
            is_priority = 0 if priority_user and priority_user in user else 1
            return (is_priority, r.get("anchor_id", ""), r.get("data_time", ""))

        sorted_rows = sorted(rows, key=sort_key)

        for row in sorted_rows:
            values = [row.get(col, "") for col in columns]
            user = str(row.get("data_user", "")).lower()
            tag = "priority" if priority_user and priority_user in user else "default"
            self.tree.insert("", tk.END, values=values, tags=(tag,))

    def _refresh_filter_dropdowns(self, rows: list[dict]) -> None:
        """Populate Status and Parent Status comboboxes from current result rows."""
        if not hasattr(self, "status_filter_cb"):
            return
        statuses = sorted({str(r.get("status", "")) for r in rows if r.get("status")})
        parents  = sorted({str(r.get("parent_status", "")) for r in rows
                           if r.get("parent_status") and r.get("parent_status") != "\u2014"})
        self.status_filter_cb["values"] = [""] + statuses
        self.parent_filter_cb["values"] = [""] + parents'''

assert OLD_SHOW in content, "OLD_SHOW not found"
content = content.replace(OLD_SHOW, NEW_SHOW, 1)

# ── 3. Update _apply_filter to honour new dropdowns ──────────────────────────
OLD_APPLY = '''    def _apply_filter(self) -> None:
        query = self.filter_var.get().strip().lower()
        show_changes_only = self.show_changes_only_var.get()
        strict_review = self.strict_review_var.get()
        priority_user = self.priority_user_var.get().strip().lower()
        
        filtered = []
        for row in self.result_rows:
            status = str(row.get("status", ""))
            other_users = str(row.get("other_users", ""))
            user = str(row.get("data_user", "")).lower()
            
            # Strict Review logic
            if strict_review:
                if priority_user and priority_user not in user:
                    continue
                if other_users:
                    continue
                if status == "Same":
                    continue
            
            # Show Changes Only logic
            elif show_changes_only:
                is_clean_same = (status == "Same" and not other_users)
                if is_clean_same:
                    continue

            # Check for text query
            combined = " ".join(str(value) for value in row.values()).lower()
            if not query or query in combined:
                filtered.append(row)

        self._show_rows(filtered, self.current_columns, self.current_headings)
        msg = f"Showing {len(filtered)} rows"
        if query: msg += f" (Filter: '{query}')"
        if strict_review: msg += " (Strict Review Mode)"
        elif show_changes_only: msg += " (Changes only)"
        self.summary_label.config(text=msg)'''

NEW_APPLY = '''    def _apply_filter(self) -> None:
        query = self.filter_var.get().strip().lower()
        show_changes_only = self.show_changes_only_var.get()
        strict_review = self.strict_review_var.get()
        priority_user = self.priority_user_var.get().strip().lower()
        status_filter = self.status_filter_var.get().strip() if hasattr(self, "status_filter_var") else ""
        parent_filter = self.parent_filter_var.get().strip() if hasattr(self, "parent_filter_var") else ""

        filtered = []
        for row in self.result_rows:
            status = str(row.get("status", ""))
            other_users = str(row.get("other_users", ""))
            parent_status = str(row.get("parent_status", ""))
            user = str(row.get("data_user", "")).lower()

            # Strict Review logic
            if strict_review:
                if priority_user and priority_user not in user:
                    continue
                if other_users:
                    continue
                if status == "Same":
                    continue

            # Show Changes Only logic
            elif show_changes_only:
                if status == "Same" and not other_users:
                    continue

            # Status dropdown filter
            if status_filter and status != status_filter:
                continue

            # Parent Status dropdown filter
            if parent_filter and parent_filter not in parent_status:
                continue

            # Text query filter
            combined = " ".join(str(v) for v in row.values()).lower()
            if not query or query in combined:
                filtered.append(row)

        self._show_rows(filtered, self.current_columns, self.current_headings)
        msg = f"Showing {len(filtered)} rows"
        if query:         msg += f" (Filter: '{query}')"
        if status_filter: msg += f" (Status: {status_filter})"
        if parent_filter: msg += f" (Parent: {parent_filter})"
        if strict_review: msg += " (Strict Review Mode)"
        elif show_changes_only: msg += " (Changes only)"
        self.summary_label.config(text=msg)'''

assert OLD_APPLY in content, "OLD_APPLY not found"
content = content.replace(OLD_APPLY, NEW_APPLY, 1)

# ── 4. Update _clear_filter to also reset new dropdowns ──────────────────────
OLD_CLEAR = '''    def _clear_filter(self) -> None:
        self.filter_var.set("")
        self.show_changes_only_var.set(False)
        self._show_rows(self.result_rows, self.current_columns, self.current_headings)
        self.summary_label.config(text=f"Showing {len(self.result_rows)} rows")'''

NEW_CLEAR = '''    def _clear_filter(self) -> None:
        self.filter_var.set("")
        self.show_changes_only_var.set(False)
        if hasattr(self, "status_filter_var"):
            self.status_filter_var.set("")
        if hasattr(self, "parent_filter_var"):
            self.parent_filter_var.set("")
        self._find_clear()
        self._show_rows(self.result_rows, self.current_columns, self.current_headings)
        self.summary_label.config(text=f"Showing {len(self.result_rows)} rows")'''

assert OLD_CLEAR in content, "OLD_CLEAR not found"
content = content.replace(OLD_CLEAR, NEW_CLEAR, 1)

# ── 5. Update _run_compare to refresh dropdowns after compare ─────────────────
OLD_RUN = '''        self.result_rows = rows
        self.current_columns = columns
        self.current_headings = headings
        self.last_export_folder = export_folder
        self._show_rows(rows, columns, headings)'''

NEW_RUN = '''        self.result_rows = rows
        self.current_columns = columns
        self.current_headings = headings
        self.last_export_folder = export_folder
        self._refresh_filter_dropdowns(rows)
        self._show_rows(rows, columns, headings)'''

assert OLD_RUN in content, "OLD_RUN not found"
content = content.replace(OLD_RUN, NEW_RUN, 1)

# ── 6. Add Find methods before _export_html_report ───────────────────────────
FIND_METHODS = '''    def _find_in_tree(self, direction: int = 1) -> None:
        """Navigate tree rows matching the find query."""
        query = self.find_var.get().strip().lower()
        if not query:
            return
        children = self.tree.get_children()
        matches = [iid for iid in children
                   if query in " ".join(str(v) for v in self.tree.item(iid, "values")).lower()]
        if not matches:
            self.find_label.config(text="Not found")
            return
        if matches != self._find_matches:
            self._find_matches = matches
            self._find_idx = 0 if direction > 0 else len(matches) - 1
        else:
            self._find_idx = (self._find_idx + direction) % len(matches)
        # Clear old selection highlight
        self.tree.selection_remove(*self.tree.selection())
        target = self._find_matches[self._find_idx]
        self.tree.selection_set(target)
        self.tree.see(target)
        self.find_label.config(text=f"{self._find_idx + 1} / {len(matches)}")

    def _find_clear(self) -> None:
        if not hasattr(self, "find_var"):
            return
        self.find_var.set("")
        self._find_matches = []
        self._find_idx = -1
        self.find_label.config(text="")
        self.tree.selection_remove(*self.tree.selection())

'''

INSERT_BEFORE = "    def _export_html_report"
assert INSERT_BEFORE in content, "Insert point not found"
content = content.replace(INSERT_BEFORE, FIND_METHODS + INSERT_BEFORE, 1)

SRC.write_text(content, encoding="utf-8")
print(f"Done. Lines: {content.count(chr(10))}")

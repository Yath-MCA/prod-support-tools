import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from html import escape
from datetime import datetime
from copy import deepcopy

try:
    from bs4 import BeautifulSoup
except ImportError:  # fallback if bs4 isn't installed
    BeautifulSoup = None

# XML Compare package import
try:
    from xml_compare.gui_panel import XmlComparePanel
    from xml_compare.pipeline import run_xml_compare
    from xml_compare.models import CompareOptions
    XML_COMPARE_AVAILABLE = True
except ImportError:
    XmlComparePanel = None
    run_xml_compare = None
    CompareOptions = None
    XML_COMPARE_AVAILABLE = False

PRIORITY_WRAPPER_ORDER = ("sup", "sub", "a", "em", "strong", "sc")
PRIORITY_DEL_SELECTOR = "del[data-username]"


class DelMergeManagerPy:
    def __init__(self, soup, allowed_wrappers=None, error_logger=None):
        self.soup = soup
        self.allowed_wrappers = tuple(allowed_wrappers or (
            "sup", "sub", "a", "span", "strong", "em", "i", "b", "sc"
        ))
        self.error_logger = error_logger or (lambda method, message: None)

    def _handle_error(self, method, err):
        self.error_logger(method, str(err))

    def get_del_node(self, element):
        try:
            if not getattr(element, "name", None):
                return None
            if element.name == "del":
                return element
            parent_del = element.find_parent("del")
            if parent_del:
                return parent_del
            return element.find("del")
        except Exception as err:
            self._handle_error("get_del_node", err)
            return None

    def get_adjacent_nodes(self, element):
        try:
            return {"prev": element.previous_sibling, "next": element.next_sibling}
        except Exception as err:
            self._handle_error("get_adjacent_nodes", err)
            return None

    def find_matching_del_target(self, prev, next_):
        try:
            if getattr(prev, "name", "").lower() == "del":
                return prev
            if getattr(next_, "name", "").lower() == "del":
                return next_
            return None
        except Exception as err:
            self._handle_error("find_matching_del_target", err)
            return None

    def merge_into_del_node(self, target_del, source_element, is_prev):
        try:
            if not target_del or not source_element:
                return
            source_del = self.get_del_node(source_element)
            source_container = source_del if source_del and source_del is not target_del else source_element
            if is_prev:
                while source_container.contents:
                    target_del.append(source_container.contents[0].extract())
            else:
                while source_container.contents:
                    target_del.insert(0, source_container.contents[-1].extract())
            if source_del and source_del is not source_element and not source_del.contents:
                source_del.decompose()
            if not source_element.contents:
                source_element.decompose()
        except Exception as err:
            self._handle_error("merge_into_del_node", err)

    def unwrap(self, element):
        try:
            if not element or not element.parent:
                return
            element.unwrap()
        except Exception as err:
            self._handle_error("unwrap", err)

    def unwrap_inner_del(self, element, del_node):
        try:
            if not getattr(element, "name", None):
                return
            element_name = element.name.lower()
            is_wrapper = element_name in self.allowed_wrappers
            has_inner_del = bool(element.select_one("del"))
            if is_wrapper and has_inner_del:
                for del_element in list(element.select("del")):
                    self.unwrap(del_element)
            elif del_node == element:
                self.unwrap(element)
        except Exception as err:
            self._handle_error("unwrap_inner_del", err)

    def process_element_collection(self, collection=None):
        try:
            for element in collection or []:
                if not getattr(element, "name", None) or not element.parent:
                    continue
                del_node = self.get_del_node(element)
                if not del_node:
                    continue
                adjacent = self.get_adjacent_nodes(element)
                if not adjacent:
                    continue
                prev = adjacent["prev"]
                next_ = adjacent["next"]
                target_del = self.find_matching_del_target(prev, next_)
                is_prev_del = getattr(prev, "name", "").lower() == "del"
                if target_del:
                    self.merge_into_del_node(target_del, element, is_prev_del)
                    self.unwrap_inner_del(element, del_node)
        except Exception as err:
            self._handle_error("process_element_collection", err)

    def contains_del_only(self, element, target_del):
        try:
            if not getattr(element, "name", None):
                return False
            del_node = element.find("del")
            if del_node != target_del:
                return False
            for child in element.contents:
                child_name = getattr(child, "name", None)
                if child_name is None:
                    if str(child).strip():
                        return False
                    continue
                if child_name == "del":
                    continue
                if not child.find("del"):
                    return False
            return True
        except Exception as err:
            self._handle_error("contains_del_only", err)
            return False

    def is_allowed_wrapper(self, element):
        try:
            return getattr(element, "name", "").lower() in self.allowed_wrappers
        except Exception as err:
            self._handle_error("is_allowed_wrapper", err)
            return False

    def has_same_user_role(self, del1, del2):
        try:
            return (
                del1.get("data-username") == del2.get("data-username")
                and del1.get("data-rolename") == del2.get("data-rolename")
            )
        except Exception as err:
            self._handle_error("has_same_user_role", err)
            return False

    def is_consecutive(self, del1, del2):
        try:
            current = del1
            while current:
                next_ = current.next_sibling
                if next_ is None:
                    break
                if next_ == del2:
                    return True
                if self.contains_del_only(next_, del2):
                    return True
                if getattr(next_, "name", None) is None and str(next_).strip():
                    break
                if self.is_allowed_wrapper(next_):
                    current = next_
                    continue
                break
            return False
        except Exception as err:
            self._handle_error("is_consecutive", err)
            return False

    def get_consecutive_del_elements(self, container):
        try:
            all_dels = list(container.select("del"))
            grouped_dels = []
            for idx in range(len(all_dels) - 1):
                current_del = all_dels[idx]
                next_del = all_dels[idx + 1]
                if not self.has_same_user_role(current_del, next_del):
                    continue
                if self.is_consecutive(current_del, next_del):
                    grouped_dels.append(next_del)
            return grouped_dels
        except Exception as err:
            self._handle_error("get_consecutive_del_elements", err)
            return []

    def get_wrapped_del_collections(self, container, selector):
        try:
            collections = []
            for element in list(container.select(selector)):
                selected = None
                for tag_name in PRIORITY_WRAPPER_ORDER:
                    asc_node = element.find_parent(tag_name)
                    if asc_node and asc_node.name == "sup" and element.find_parent("a"):
                        asc_node = element.find_parent("a")
                    if asc_node:
                        selected = asc_node
                        break
                collections.append(selected)
            return collections
        except Exception as err:
            self._handle_error("get_wrapped_del_collections", err)
            return []

    def merge_del_sequences(self, container=None):
        selector = "sup del, a del, sub del, em del, strong del, sc del"
        try:
            container = container or self.soup
            wrapped_dels = self.get_wrapped_del_collections(container, selector)
            self.process_element_collection(wrapped_dels)
            consecutive_dels = self.get_consecutive_del_elements(container)
            self.process_element_collection(consecutive_dels)
        except Exception as err:
            self._handle_error("merge_del_sequences", err)


class HTMLCompareTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent)
        self.multi_html_files: list[str] = []
        self.result_rows: list[dict] = []
        self.current_columns: list[str] = []
        self.current_headings: dict[str, str] = {}
        self.last_export_folder: Path | None = None
        self.report_docid: str | None = None
        self.report_timestamp: int | None = None
        self.last_report_mode: str | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.configure(style="Card.TFrame")

        title_frame = tk.Frame(self, bg="#1e293b", padx=30, pady=20)
        title_frame.pack(fill="x")

        tk.Label(
            title_frame,
            text="HTML COMPARE TOOL",
            font=("Segoe UI", 20, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
        ).pack(anchor="w")

        description = (
            "Compare Source vs To-be-updated HTML files and restore specific content blocks. "
            "Track changes by [data-username] and sync Source Divs to the Update file using Anchor IDs."
        )
        tk.Label(
            title_frame,
            text=description,
            font=("Segoe UI", 10),
            fg="#94a3b8",
            bg="#1e293b",
            wraplength=880,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        control_frame = tk.Frame(self, bg="#0f172a", padx=30, pady=16)
        control_frame.pack(fill="x")
        control_frame.columnconfigure(1, weight=1)

        self.method_var = tk.StringVar(value="method1")
        method_frame = tk.LabelFrame(
            control_frame,
            text="Compare Mode",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 11, "bold"),
            padx=20,
            pady=14,
        )
        method_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 16))

        tk.Radiobutton(
            method_frame,
            text="HTML to HTML",
            variable=self.method_var,
            value="method1",
            command=self._on_method_change,
            bg="#0f172a",
            fg="#cbd5e1",
            selectcolor="#0f172a",
            activebackground="#0f172a",
            activeforeground="#ffffff",
        ).pack(side="left", padx=(0, 16))
        tk.Radiobutton(
            method_frame,
            text="Multi HTML by Selector",
            variable=self.method_var,
            value="method2",
            command=self._on_method_change,
            bg="#0f172a",
            fg="#cbd5e1",
            selectcolor="#0f172a",
            activebackground="#0f172a",
            activeforeground="#ffffff",
        ).pack(side="left")
        tk.Radiobutton(
            method_frame,
            text="Original HTML Before/After DelMerge",
            variable=self.method_var,
            value="method3",
            command=self._on_method_change,
            bg="#0f172a",
            fg="#cbd5e1",
            selectcolor="#0f172a",
            activebackground="#0f172a",
            activeforeground="#ffffff",
        ).pack(side="left", padx=(16, 0))
        tk.Radiobutton(
            method_frame,
            text="XML to XML",
            variable=self.method_var,
            value="method4",
            command=self._on_method_change,
            bg="#0f172a",
            fg="#cbd5e1",
            selectcolor="#0f172a",
            activebackground="#0f172a",
            activeforeground="#ffffff",
        ).pack(side="left", padx=(16, 0))

        self.selector_var = tk.StringVar(value="[data-username][data-time]")
        self.compare_mode_var = tk.StringVar(value="data-time")
        
        self.compare_mode_label = tk.Label(
            control_frame,
            text="Compare Mode:",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        )
        self.compare_mode_label.grid(row=1, column=0, sticky="w")

        self.mode_frame = tk.Frame(control_frame, bg="#0f172a")
        self.mode_frame.grid(row=1, column=1, sticky="w", padx=(10, 0))
        tk.Radiobutton(
            self.mode_frame,
            text="data-time",
            variable=self.compare_mode_var,
            value="data-time",
            bg="#0f172a",
            fg="#cbd5e1",
            selectcolor="#0f172a",
            activebackground="#0f172a",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(0, 12))
        tk.Radiobutton(
            self.mode_frame,
            text="data-cid",
            variable=self.compare_mode_var,
            value="data-cid",
            bg="#0f172a",
            fg="#cbd5e1",
            selectcolor="#0f172a",
            activebackground="#0f172a",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(0, 12))
        
        self.selector_label = tk.Label(
            control_frame,
            text="Query selector:",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        )
        self.selector_label.grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.selector_entry = tk.Entry(
            control_frame,
            textvariable=self.selector_var,
            bg="#1f2937",
            fg="white",
            border=0,
            font=("Segoe UI", 11),
        )
        self.selector_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=(10, 0), ipady=5)
        self.selector_help = tk.Label(
            control_frame,
            text="e.g. [data-username='copyeditor'][data-time]  or  [data-username][data-time]",
            bg="#0f172a",
            fg="#64748b",
            font=("Segoe UI", 9),
        )
        self.selector_help.grid(row=2, column=2, sticky="w", padx=(10, 0), pady=(10, 0))

        self.first_html_var = tk.StringVar()
        self.second_html_var = tk.StringVar()
        self.single_html_var = tk.StringVar()
        self.multi_files_var = tk.StringVar(value="No files selected")

        self._build_file_selector(control_frame)

        self.compare_btn = tk.Button(
            control_frame,
            text="🔎 Run Compare",
            command=self._run_compare,
            bg="#10b981",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            border=0,
            padx=20,
            pady=10,
        )
        self.compare_btn.grid(row=6, column=0, columnspan=3, pady=(12, 0))

        self.filter_frame = tk.Frame(control_frame, bg="#0f172a")
        self.filter_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        self.filter_frame.columnconfigure(1, weight=1)

        self.filter_var = tk.StringVar()
        tk.Label(
            self.filter_frame,
            text="Filter:",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).grid(row=0, column=0, sticky="w")
        tk.Entry(
            self.filter_frame,
            textvariable=self.filter_var,
            bg="#1f2937",
            fg="white",
            border=0,
            font=("Segoe UI", 11),
        ).grid(row=0, column=1, sticky="ew", padx=(10, 0), ipady=5)
        tk.Button(
            self.filter_frame,
            text="Apply Filter",
            command=self._apply_filter,
            bg="#3b82f6",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            border=0,
            padx=14,
            pady=6,
        ).grid(row=0, column=2, padx=(10, 0))
        tk.Button(
            self.filter_frame,
            text="Clear",
            command=self._clear_filter,
            bg="#475569",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            border=0,
            padx=14,
            pady=6,
        ).grid(row=0, column=3, padx=(10, 0))

        self.show_changes_only_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self.filter_frame,
            text="Show Changes Only (Hide clean 'Same' rows)",
            variable=self.show_changes_only_var,
            command=self._apply_filter,
            bg="#0f172a",
            fg="#94a3b8",
            selectcolor="#0f172a",
            activebackground="#0f172a",
            activeforeground="#ffffff",
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 0))

        self.priority_user_var = tk.StringVar(value="copyeditor")
        tk.Label(
            self.filter_frame,
            text="Priority User:",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))
        tk.Entry(
            self.filter_frame,
            textvariable=self.priority_user_var,
            bg="#1f2937",
            fg="white",
            border=0,
            font=("Segoe UI", 10),
        ).grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=(8, 0), ipady=3)
        tk.Button(
            self.filter_frame,
            text="Update Priority",
            command=self._apply_filter,
            bg="#6366f1",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            border=0,
            padx=14,
            pady=4,
        ).grid(row=2, column=2, padx=(10, 0), pady=(8, 0))

        self.strict_review_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self.filter_frame,
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
        tk.Label(self.filter_frame, text="Status:", bg="#0f172a", fg="#94a3b8",
                 font=("Segoe UI", 10)).grid(row=4, column=0, sticky="w", pady=(10, 0))
        self.status_filter_var = tk.StringVar(value="")
        self.status_filter_cb = ttk.Combobox(
            self.filter_frame, textvariable=self.status_filter_var,
            state="readonly", width=22, font=("Segoe UI", 10)
        )
        self.status_filter_cb.grid(row=4, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        self.status_filter_cb.bind("<<ComboboxSelected>>", lambda _e: self._apply_filter())

        tk.Label(filter_frame, text="Parent Status:", bg="#0f172a", fg="#94a3b8",
                 font=("Segoe UI", 10)).grid(row=4, column=2, sticky="w",
                                             padx=(16, 0), pady=(10, 0))
        self.parent_filter_var = tk.StringVar(value="")
        self.parent_filter_cb = ttk.Combobox(
            self.filter_frame, textvariable=self.parent_filter_var,
            state="readonly", width=28, font=("Segoe UI", 10)
        )
        self.parent_filter_cb.grid(row=4, column=3, sticky="w", padx=(6, 0), pady=(10, 0))
        self.parent_filter_cb.bind("<<ComboboxSelected>>", lambda _e: self._apply_filter())

        # ── Find bar ─────────────────────────────────────────────────────────
        find_frame = tk.Frame(self.filter_frame, bg="#0f172a")
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
        self._find_idx: int = -1

        self.export_btn = tk.Button(
            control_frame,
            text="📄 Export HTML Report",
            command=self._export_html_report,
            bg="#f59e0b",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            border=0,
            padx=20,
            pady=10,
            state="disabled",
        )
        self.export_btn.grid(row=8, column=0, columnspan=3, pady=(10, 0))

        self.restore_btn = tk.Button(
            control_frame,
            text="♻️ Restore Selected from Source to Update",
            command=self._restore_from_source,
            bg="#8b5cf6",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            border=0,
            padx=20,
            pady=10,
            state="disabled",
        )
        self.restore_btn.grid(row=9, column=0, columnspan=3, pady=(10, 0))

        # ── XML Compare Panel (hidden by default, shown for method4) ──────────
        if XML_COMPARE_AVAILABLE:
            self.xml_panel = XmlComparePanel(
                control_frame,
                first_path_var=self.first_html_var,
                second_path_var=self.second_html_var,
            )
            self.xml_panel.grid(row=10, column=0, columnspan=3, sticky="ew", pady=(12, 0))
            self.xml_panel.grid_remove()  # Hidden by default

        self.summary_frame = tk.Frame(self, bg="#111827", padx=30, pady=18)
        self.summary_frame.pack(fill="both", expand=True)
        self.summary_frame.columnconfigure(0, weight=1)

        self.summary_label = tk.Label(
            self.summary_frame,
            text="No comparison run yet.",
            bg="#111827",
            fg="#cbd5e1",
            font=("Segoe UI", 10),
            anchor="w",
        )
        self.summary_label.pack(fill="x", pady=(0, 10))

        self._build_result_table(self.summary_frame)

        self._on_method_change()

    def _build_file_selector(self, parent: tk.Frame) -> None:
        self.file_frame = tk.Frame(parent, bg="#0f172a")
        self.file_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        self.file_frame.columnconfigure(1, weight=1)

        tk.Label(
            self.file_frame,
            text="Source HTML:",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).grid(row=0, column=0, sticky="w")
        tk.Entry(
            self.file_frame,
            textvariable=self.first_html_var,
            bg="#1f2937",
            fg="white",
            border=0,
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="ew", ipady=5)
        tk.Button(
            self.file_frame,
            text="Browse…",
            command=lambda: self._browse_html_file(self.first_html_var),
            bg="#475569",
            fg="white",
            font=("Segoe UI", 9),
            border=0,
            padx=10,
            pady=6,
        ).grid(row=1, column=1, padx=(10, 0))

        tk.Label(
            self.file_frame,
            text="To-be-updated HTML:",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).grid(row=2, column=0, sticky="w", pady=(14, 0))
        tk.Entry(
            self.file_frame,
            textvariable=self.second_html_var,
            bg="#1f2937",
            fg="white",
            border=0,
            font=("Segoe UI", 10),
        ).grid(row=3, column=0, sticky="ew", ipady=5)
        tk.Button(
            self.file_frame,
            text="Browse…",
            command=lambda: self._browse_html_file(self.second_html_var),
            bg="#475569",
            fg="white",
            font=("Segoe UI", 9),
            border=0,
            padx=10,
            pady=6,
        ).grid(row=3, column=1, padx=(10, 0))

        self.multi_frame = tk.Frame(parent, bg="#0f172a")
        self.multi_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        self.multi_frame.columnconfigure(0, weight=1)

        tk.Label(
            self.multi_frame,
            text="Multi HTML files:",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            self.multi_frame,
            textvariable=self.multi_files_var,
            bg="#0f172a",
            fg="#e2e8f0",
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=680,
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))
        tk.Button(
            self.multi_frame,
            text="Select HTML Files…",
            command=self._browse_multiple_html,
            bg="#4361ee",
            fg="white",
            font=("Segoe UI", 9),
            border=0,
            padx=10,
            pady=6,
        ).grid(row=1, column=1, padx=(12, 0), sticky="n")

        self.single_frame = tk.Frame(parent, bg="#0f172a")
        self.single_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        self.single_frame.columnconfigure(0, weight=1)
        tk.Label(
            self.single_frame,
            text="Original HTML:",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).grid(row=0, column=0, sticky="w")
        tk.Entry(
            self.single_frame,
            textvariable=self.single_html_var,
            bg="#1f2937",
            fg="white",
            border=0,
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="ew", ipady=5)
        tk.Button(
            self.single_frame,
            text="Browse…",
            command=lambda: self._browse_html_file(self.single_html_var),
            bg="#475569",
            fg="white",
            font=("Segoe UI", 9),
            border=0,
            padx=10,
            pady=6,
        ).grid(row=1, column=1, padx=(10, 0))

    def _build_result_table(self, parent: tk.Frame) -> None:
        self.tree_frame = tk.Frame(parent, bg="#111827")
        self.tree_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(self.tree_frame, columns=(), show="headings", height=14)
        self.tree_scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree_xscrollbar = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.tree_scrollbar.set, xscrollcommand=self.tree_xscrollbar.set)
        self.tree_scrollbar.pack(side="right", fill="y")
        self.tree_xscrollbar.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        
        # Configure highlighting tags
        self.tree.tag_configure("priority", background="#1e3a8a", foreground="#ffffff")
        self.tree.tag_configure("default", background="#111827", foreground="#cbd5e1")

    def _configure_tree(self, columns: list[str], headings: dict[str, str]) -> None:
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = columns
        for col in columns:
            self.tree.heading(col, text=headings.get(col, col))
            width = 160
            if col in ("anchor_id", "tag_name", "data_user", "data_time", "data_cid", "status", "parent_status", "reason"):
                width = 180
            elif col.startswith("file_"):
                width = 320
            self.tree.column(col, width=width, anchor="w")

    def _show_rows(self, rows: list[dict], columns: list[str], headings: dict[str, str]) -> None:
        self._configure_tree(columns, headings)

        priority_user = self.priority_user_var.get().strip().lower()

        # Sort rows: priority user first, then by anchor id
        def sort_key(r):
            user = str(r.get("data_user", "")).lower()
            is_priority = 0 if priority_user and priority_user in user else 1
            return (is_priority, r.get("anchor_id", ""), r.get("data_time", ""))

        sorted_rows = sorted(rows,
            key=lambda r: (
                r.get("div_idx", 999999),
                r.get("node_order", 999999),
                r.get("document_order", 999999),
            ))

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
                           if r.get("parent_status") and r.get("parent_status") != "—"})
        self.status_filter_cb["values"] = [""] + statuses
        self.parent_filter_cb["values"] = [""] + parents

    def _apply_filter(self) -> None:
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
        self.summary_label.config(text=msg)

    def _clear_filter(self) -> None:
        self.filter_var.set("")
        self.show_changes_only_var.set(False)
        if hasattr(self, "status_filter_var"):
            self.status_filter_var.set("")
        if hasattr(self, "parent_filter_var"):
            self.parent_filter_var.set("")
        self._find_clear()
        self._show_rows(self.result_rows, self.current_columns, self.current_headings)
        self.summary_label.config(text=f"Showing {len(self.result_rows)} rows")

    def _find_in_tree(self, direction: int = 1) -> None:
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

    def _export_html_report(self, export_folder=None) -> None:
        if not self.result_rows or not self.current_columns:
            messagebox.showwarning("Export Warning", "No compare results available to export.")
            return

        if export_folder is None:
            export_folder = self.last_export_folder
        if isinstance(export_folder, (str, Path)):
            export_folder = Path(export_folder)
        else:
            export_folder = Path.cwd()
        export_folder.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.report_docid:
            save_path = export_folder / f"html_compare_report_{self.report_docid}_{timestamp}.html"
        else:
            save_path = export_folder / f"html_compare_report_{timestamp}.html"

        dcols = ["anchor_id", "tag_name", "data_user", "data_time", "data_cid", "file_0", "file_1", "status", "parent_status", "reason"]
        dheads = {
            "anchor_id": "Anchor ID", "tag_name": "Tag Name", "data_user": "data-username", "data_time": "data-time", "data_cid": "data-cid",
            "file_0": self.current_headings.get("file_0", "Source"),
            "file_1": self.current_headings.get("file_1", "Update"),
            "status": "Status", "parent_status": "Parent Status", "reason": "Reason",
        }
        header_cells = "".join(f"<th>{escape(dheads[c])}</th>" for c in dcols)
        body_rows = []
        for idx, row in enumerate(self.result_rows):
            st = str(row.get("status", "")).strip()
            ps = str(row.get("parent_status", "\u2014")).strip()
            anchor = str(row.get("anchor_id", "")).strip()
            cells = "".join(f"<td>{escape(str(row.get(c, '')))}</td>" for c in dcols)
            body_rows.append(
                f'<tr data-index="{idx}" data-status="{escape(st)}" data-parent="{escape(ps)}" data-anchor="{escape(anchor)}">{cells}</tr>'
            )

        summary_text = escape(self.summary_label.cget("text"))
        generated = escape(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        rows_body = "".join(body_rows)

        CSS = """\
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Segoe UI",Arial,sans-serif;background:#f1f5f9;color:#1e293b;padding:24px}
.container{max-width:1600px;margin:0 auto}
h1{font-size:1.35rem;font-weight:700;color:#0f172a;margin-bottom:4px}
.meta{font-size:.82rem;color:#64748b;margin-bottom:14px}
.filters{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px;align-items:center}
.filters input,.filters select{padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:.84rem;background:#fff}
.filters input{flex:1;min-width:200px}
.filters label{font-size:.82rem;color:#475569;white-space:nowrap}
.count{font-size:.82rem;color:#6366f1;font-weight:600;margin-left:auto}
.find-bar{display:flex;gap:8px;align-items:center;margin-bottom:10px;background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:8px 12px}
.find-bar input{flex:1;padding:5px 8px;border:1px solid #cbd5e1;border-radius:4px;font-size:.84rem}
.find-bar button{padding:5px 12px;border:none;border-radius:4px;cursor:pointer;font-size:.82rem;font-weight:600}
.btn-f{background:#6366f1;color:#fff}.btn-fn{background:#059669;color:#fff}.btn-cl{background:#e2e8f0;color:#475569}
.mb{font-size:.8rem;color:#64748b;white-space:nowrap}
.table-wrap{overflow-x:auto;border-radius:8px;border:1px solid #e2e8f0;box-shadow:0 1px 4px rgba(0,0,0,.06)}
table{border-collapse:collapse;width:100%;font-size:.83rem}
th{background:#0f172a;color:#fff;padding:9px 10px;text-align:left;white-space:nowrap;position:sticky;top:0;z-index:2}
td{border-bottom:1px solid #e2e8f0;padding:7px 10px;vertical-align:top;max-width:320px;word-break:break-word}
tr:hover td{background:#eff6ff!important}
tr[data-status="Same"] td{background:#f0fdf4}
tr[data-status="Changed"] td{background:#fef2f2}
tr[data-status="Missing in update"] td{background:#f8fafc;color:#94a3b8}
tr[data-status="New in update"] td{background:#fffbeb}
tr[data-status="Changed (Div Replace)"] td{background:#fdf4ff}
.ring{outline:2px solid #f59e0b}"""

        JS = """\
        var fm=[],fi=-1;
        var mainRows=[],delmergeRows=[],currentMainIndex=-1,currentDelmergeIndex=-1;
        var delmergeSection=null,delmergeTable=null;
        var mainTable=null;

        function af(){
        var t=(document.getElementById('tf').value||'').toLowerCase(),s=document.getElementById('sf').value,p=document.getElementById('pf').value,v=0;
        mainRows.forEach(function(r){
        var ok=((!t||r.textContent.toLowerCase().includes(t))&&(!s||r.dataset.status===s)&&(!p||(r.dataset.parent||'').includes(p)));
        r.style.display=ok?'':'none';
        if(ok)v++;
        });
        document.getElementById('rc').textContent=v+' rows';
        }

        function bd(){
        var ss=document.getElementById('sf'),ps=document.getElementById('pf'),sv=new Set(),pv=new Set();
        mainRows.forEach(function(r){
        if(r.dataset.status)sv.add(r.dataset.status);
        if(r.dataset.parent&&r.dataset.parent!=='—')pv.add(r.dataset.parent);
        });
        [...sv].sort().forEach(function(s){
        var o=document.createElement('option');o.value=s;o.textContent=s;ss.appendChild(o);
        });
        [...pv].sort().forEach(function(s){
        var o=document.createElement('option');o.value=s;o.textContent=s;ps.appendChild(o);
        });
        document.getElementById('rc').textContent=mainRows.length+' rows';
        }

        function df(){
        var q=(document.getElementById('fi').value||'').toLowerCase();
        if(!q){cf();return;}
        fm=[];fi=-1;
        mainRows.forEach(function(r){
        if(r.style.display!=='none'&&r.textContent.toLowerCase().includes(q))fm.push(r);
        });
        document.getElementById('fc').textContent=fm.length+' found';
        if(fm.length){fi=0;sm();}
        }

        function sm(){
        fm.forEach(function(r){r.classList.remove('ring');});
        if(fi>=0&&fi<fm.length){
        fm[fi].classList.add('ring');fm[fi].scrollIntoView({block:'center',behavior:'smooth'});
        }
        }

        function fn(){if(!fm.length)return;fi=(fi+1)%fm.length;sm();}
        function fp(){if(!fm.length)return;fi=(fi-1+fm.length)%fm.length;sm();}

        function cf(){
        document.getElementById('fi').value='';fm=[];fi=-1;document.getElementById('fc').textContent='';
        mainRows.forEach(function(r){r.classList.remove('ring');});
        }

        function getVisibleDelmergeRows(){
        return delmergeRows.filter(function(r){return r.style.display!=='none';});
        }

       function focusDelmergeRow(anchor){
        if(!anchor||!delmergeTable)return;
        var first=null;
        delmergeRows.forEach(function(r){
        var same=r.dataset.anchor===anchor;
        r.style.display=same?'':'none';
        r.classList.toggle('focused',same);
        if(same&&!first){first=r;}
        });
        if(first){
        first.scrollIntoView({
        block:'center',
        behavior:'smooth'
        });
        }
        }

        function moveDelmerge(step){
        if(!mainRows.length)return;
        var currentAnchor='';
        if(currentMainIndex>=0&&currentMainIndex<mainRows.length){
        currentAnchor=mainRows[currentMainIndex].dataset.anchor||'';
        }

        for(var i=currentMainIndex+step;step>0?i<mainRows.length:i>=0;i+=step){
        var row=mainRows[i];
        if(row.style.display==='none'){
        continue;
        }

        var nextAnchor=row.dataset.anchor||'';
        if(nextAnchor&&nextAnchor!==currentAnchor){
        currentMainIndex=i;
        mainRows.forEach(function(r){
        r.classList.remove('ring');
        });
        row.classList.add('ring');
        row.scrollIntoView({block:'center',behavior:'smooth'});
        focusDelmergeRow(nextAnchor);
        return;
        }
        }
        }
        function gotoDelmergeNext(){
        moveDelmerge(1);
        }

        function gotoDelmergePrev(){
        moveDelmerge(-1);
        }

        function toggleDelmergeDel(mode){
        console.log("toggleDelmergeDel", mode);
        if(delmergeSection)delmergeSection.classList[mode==='hide'?'add':'remove']('hide-del');
        }

        function toggleHtmlView(mode){
        console.log("toggleHtmlView");
        if(mainTable){
        mainTable.querySelectorAll('.html-preview').forEach(function(el){el.style.display=mode==='preview'?'block':'none';});
        mainTable.querySelectorAll('.html-raw').forEach(function(el){el.style.display=mode==='preview'?'none':'block';});
        }
        }

        function toggleHtmlViewDelmerge(mode){
        console.log("toggleHtmlViewDelmerge");
        if(delmergeTable){
        delmergeTable.querySelectorAll('.html-preview').forEach(function(el){el.style.display=mode==='preview'?'block':'none';});
        delmergeTable.querySelectorAll('.html-raw').forEach(function(el){el.style.display=mode==='preview'?'none':'block';});
        }
        }

        function bindMainReportClicks(){
        console.log("bindMainReportClicks");
        mainRows.forEach(function(r){
        r.addEventListener('dblclick',function(){
        var anchor=r.dataset.anchor||'';
        if(delmergeTable){focusDelmergeRow(anchor);}
        });
        });
        }

        function initReport(){
        console.log("initReport");
        mainTable=document.getElementById('main-report-table');
        delmergeTable=document.getElementById('delmerge-table');
        delmergeSection=document.getElementById('delmerge-section');
        if(mainTable)mainRows=[].slice.call(mainTable.querySelectorAll('tbody tr'));
        if(delmergeTable)delmergeRows=[].slice.call(delmergeTable.querySelectorAll('tbody tr'));
        bd();
        bindMainReportClicks();
        }
        window.onload=initReport;"""

        has_parent_preview = any(
            row.get("file_0_parent_raw") or row.get("file_1_parent_raw")
            for row in self.result_rows
        )
        extra_section = self._build_delmerge_parent_view_section() if (self.last_report_mode == "method3" or has_parent_preview) else ""

        report_html = (
            f"<!DOCTYPE html>\n<html lang=en>\n<head><meta charset=utf-8>"
            f"<title>HTML Compare Report</title>\n"
            f"<style>\n{CSS}\n</style>\n"
            f"<script>\n{JS}\n</script>\n"
            f"</head><body><div class=container>\n"
            f"<h1>&#128202; HTML Compare Report</h1>\n"
            f"<p class=meta>{summary_text} &nbsp;|&nbsp; Generated: {generated}</p>\n"
            f"<div class=filters>"
            f"<input id=tf type=text placeholder='Filter rows by any text...' oninput='af()'>"
            f"<label>Status:</label><select id=sf onchange='af()'><option value=''>\u2014 All \u2014</option></select>"
            f"<label>Parent&nbsp;Status:</label><select id=pf onchange='af()'><option value=''>\u2014 All \u2014</option></select>"
            f"<span class=count id=rc></span></div>\n"
            f"<div class=find-bar>"
            f"<span style='font-size:.82rem;color:#475569'>&#128269; Find:</span>"
            f"<input id=fi type=text placeholder='Find in visible rows...' onkeydown=\"if(event.key==='Enter')df()\">"
            f"<button class=btn-f onclick='df()'>Find</button>"
            f"<button class=btn-fn onclick='fp()'>&#8593; Prev</button>"
            f"<button class=btn-fn onclick='fn()'>Next &#8595;</button>"
            f"<button class=btn-cl onclick='cf()'>Clear</button>"
            f"<span class=mb id=fc></span></div>\n"
            f"<div class=table-wrap><table id=main-report-table>"
            f"<thead><tr>{header_cells}</tr></thead>"
            f"<tbody>{rows_body}</tbody>"
            f"</table></div>{extra_section}</div></body></html>"
        )

        with open(save_path, "w", encoding="utf-8") as handle:
            handle.write(report_html)
        messagebox.showinfo("Export Complete", f"Report saved to:\n{save_path}")

    def _build_delmerge_parent_view_section(self) -> str:
        """Build parent div preview section - ONE row per anchor ID.
        
        Deduplicates by anchor and selects richest available HTML content.
        """
        preview_rows = [
            row for row in self.result_rows
            if row.get("file_0_parent_raw") or row.get("file_1_parent_raw") or row.get("file_0_raw") or row.get("file_1_raw")
        ]
        
        # Build anchor map: ONE row per anchor, selecting richest content
        anchor_map = {}
        for row in preview_rows:
            anchor = row.get("anchor_id") or row.get("file_0_anchor_id") or row.get("file_1_anchor_id")
            if not anchor:
                continue
            
            existing = anchor_map.get(anchor)
            if not existing:
                anchor_map[anchor] = row
                continue
            
            # Prefer row with richer file_1_parent_raw, then file_0_parent_raw
            existing_f1_len = len(str(existing.get("file_1_parent_raw") or ""))
            current_f1_len = len(str(row.get("file_1_parent_raw") or ""))
            if current_f1_len > existing_f1_len:
                anchor_map[anchor] = row
            elif current_f1_len == existing_f1_len:
                existing_f0_len = len(str(existing.get("file_0_parent_raw") or ""))
                current_f0_len = len(str(row.get("file_0_parent_raw") or ""))
                if current_f0_len > existing_f0_len:
                    anchor_map[anchor] = row

        preview_rows = list(anchor_map.values())

        file_0_heading = escape(str(self.current_headings.get("file_0", "INPUT")))
        file_1_heading = escape(str(self.current_headings.get("file_1", "OUTPUT")))
        report_hint = escape(f"{self.current_headings.get('file_0', 'INPUT')} -> {self.current_headings.get('file_1', 'OUTPUT')}")
        
        rows_html = []
        for row in preview_rows:
            anchor = escape(str(row.get("anchor_id", "")).strip())
            source_anchor = str(row.get("file_0_anchor_id", "")).strip()
            update_anchor = str(row.get("file_1_anchor_id", "")).strip()
            
            # Display anchor: show transition if different
            if source_anchor and update_anchor and source_anchor != update_anchor:
                anchor_display = f"{source_anchor} ➜ {update_anchor}"
            else:
                anchor_display = source_anchor or update_anchor or anchor
            
            # Select richest content: parent_raw > raw > text fallback
            source_html = row.get("file_0_parent_raw") or row.get("file_0_raw") or row.get("file_0") or ""
            update_html = row.get("file_1_parent_raw") or row.get("file_1_raw") or row.get("file_1") or ""
            if not update_html:
                update_html = "[missing]"
            
            rows_html.append(
                f"<tr data-anchor=\"{anchor}\" class=\"preview-row\">"
                f"<td>{escape(anchor_display)}</td>"
                f"<td>"
                f"<div class=\"html-preview\">{source_html}</div>"
                f"<pre class=\"html-snippet html-raw\" style=\"display:none;\">{escape(str(source_html))}</pre>"
                f"</td>"
                f"<td>"
                f"<div class=\"html-preview\">{update_html}</div>"
                f"<pre class=\"html-snippet html-raw\" style=\"display:none;\">{escape(str(update_html))}</pre>"
                f"</td>"
                f"</tr>"
            )
        
        return (
            "<style>"
            ".delmerge-view{margin-top:24px;padding-top:18px;border-top:2px solid #cbd5e1}"
            ".delmerge-view h2{font-size:1.1rem;font-weight:700;color:#0f172a;margin-bottom:8px}"
            ".delmerge-view .meta{font-size:.82rem;color:#64748b;margin-bottom:10px}"
            ".delmerge-view .hint{font-size:.8rem;color:#94a3b8;margin-bottom:10px}"
            ".delmerge-view .toggle-bar{display:flex;gap:14px;align-items:center;margin-bottom:10px;font-size:.85rem;color:#334155}"
            ".delmerge-view .toggle-bar label{display:inline-flex;gap:6px;align-items:center;cursor:pointer}"
            ".delmerge-view .html-snippet{margin:0;white-space:pre-wrap;word-break:break-word;font-family:Consolas,monospace;font-size:.78rem}"
            ".delmerge-view table,.delmerge-view td,.delmerge-view th{border:1px solid #000}"
            ".delmerge-view table{border-collapse:collapse;width:100%;background:#fff}"
            ".delmerge-view td,.delmerge-view th{padding:10px;vertical-align:top}"
            ".delmerge-view del{color:red}"
            ".delmerge-view ins,.delmerge-view insert{color:#00f;text-decoration:none}"
            ".delmerge-view.hide-del del{display:none}"
            ".preview-row.focused{background-color:#fffacd}"
            "</style>"
            "<section class=\"delmerge-view\" id=\"delmerge-section\">"
            "<h2>Parent Div Preview Report</h2>"
            f"<p class=\"meta\">Preview rows: {len(preview_rows)} (one per anchor)</p>"
            f"<p class=\"hint\">{report_hint}</p>"
            "<div class=\"toggle-bar\">"
            "<label><input type=\"radio\" name=\"delmerge-del-toggle\" checked onchange=\"toggleDelmergeDel(this.value)\" value=\"hide\">Hide DEL</label>"
            "<label><input type=\"radio\" name=\"delmerge-del-toggle\" onchange=\"toggleDelmergeDel(this.value)\" value=\"show\">Show DEL</label>"
            "</div>"
            "<div class=\"toggle-bar\">"
            "<label><input type=\"radio\" name=\"html-view-toggle\" checked onchange=\"toggleHtmlViewDelmerge(this.value)\" value=\"preview\">HTML Preview</label>"
            "<label><input type=\"radio\" name=\"html-view-toggle\" onchange=\"toggleHtmlViewDelmerge(this.value)\" value=\"raw\">HTML Raw</label>"
            "</div>"
            "<div class=\"find-bar\">"
            "<button type=\"button\" class=\"btn-fn\" onclick=\"gotoDelmergePrev();\">Prev</button>"
            "<button type=\"button\" class=\"btn-fn\" onclick=\"gotoDelmergeNext();\">Next</button>"
            "</div>"
            f"<table id=\"delmerge-table\"><thead><tr><th>Anchor ID</th><th>{file_0_heading}</th><th>{file_1_heading}</th></tr></thead>"
            f"<tbody>{''.join(rows_html)}</tbody></table>"
            "</section>"
        )


    def _on_method_change(self) -> None:
        method = self.method_var.get()
        if method == "method1":
            self.multi_frame.grid_remove()
            self.single_frame.grid_remove()
            self.file_frame.grid()
            self._show_html_ui(True)
            self._show_xml_ui(False)
        elif method == "method2":
            self.file_frame.grid_remove()
            self.single_frame.grid_remove()
            self.multi_frame.grid()
            self.first_html_var.set("")
            self.second_html_var.set("")
            self._show_html_ui(True)
            self._show_xml_ui(False)
        elif method == "method3":
            self.file_frame.grid_remove()
            self.multi_frame.grid_remove()
            self.single_frame.grid()
            self.first_html_var.set("")
            self.second_html_var.set("")
            self.multi_html_files = []
            self.multi_files_var.set("No files selected")
            self._show_html_ui(True)
            self._show_xml_ui(False)
        elif method == "method4":
            # XML mode: show xml_panel, hide HTML-specific UI
            self.multi_frame.grid_remove()
            self.single_frame.grid_remove()
            self.file_frame.grid_remove()
            self._show_html_ui(False)
            self._show_xml_ui(True)

    def _show_html_ui(self, show: bool) -> None:
        """Show or hide HTML comparison specific UI elements."""
        # Toggle Compare Mode label and radios (row 1)
        if hasattr(self, 'compare_mode_label'):
            if show:
                self.compare_mode_label.grid()
                self.mode_frame.grid()
            else:
                self.compare_mode_label.grid_remove()
                self.mode_frame.grid_remove()
        # Toggle Query selector row (row 2)
        if hasattr(self, 'selector_label'):
            if show:
                self.selector_label.grid()
                self.selector_entry.grid()
                self.selector_help.grid()
            else:
                self.selector_label.grid_remove()
                self.selector_entry.grid_remove()
                self.selector_help.grid_remove()
        # Toggle filter frame (row 7)
        if hasattr(self, 'filter_frame'):
            if show:
                self.filter_frame.grid()
            else:
                self.filter_frame.grid_remove()
        # Toggle summary frame (contains tree results)
        if hasattr(self, 'summary_frame'):
            if show:
                self.summary_frame.pack(fill="both", expand=True)
            else:
                self.summary_frame.pack_forget()
        # Toggle export/restore buttons
        if hasattr(self, 'export_btn'):
            if show:
                self.export_btn.grid()
                self.restore_btn.grid()
            else:
                self.export_btn.grid_remove()
                self.restore_btn.grid_remove()

    def _show_xml_ui(self, show: bool) -> None:
        """Show or hide XML comparison specific UI elements."""
        if XML_COMPARE_AVAILABLE and hasattr(self, 'xml_panel'):
            if show:
                self.xml_panel.grid()
                self.xml_panel.clear_log()
            else:
                self.xml_panel.grid_remove()

    def _browse_html_file(self, target_var: tk.StringVar) -> None:
        selected = filedialog.askopenfilename(
            title="Select HTML file",
            filetypes=[("HTML Files", "*.html;*.htm"), ("All Files", "*")],
        )
        if selected:
            target_var.set(selected)

    def _browse_multiple_html(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select HTML files",
            filetypes=[("HTML Files", "*.html;*.htm"), ("All Files", "*")],
        )
        if paths:
            self.multi_html_files = self._sort_paths_by_filename_timestamp(list(paths))
            display = "; ".join(Path(path).name for path in self.multi_html_files)
            self.multi_files_var.set(display)

    def _run_compare(self) -> None:
        if BeautifulSoup is None:
            messagebox.showerror(
                "Dependency Missing",
                "BeautifulSoup is required for HTML comparison. Install beautifulsoup4.",
            )
            return

        selector = self.selector_var.get().strip() or "body"
        self.filter_var.set("")
        self.tree.delete(*self.tree.get_children())

        if self.method_var.get() == "method1":
            source = self.first_html_var.get().strip()
            target = self.second_html_var.get().strip()
            if not source or not target:
                messagebox.showerror("Error", "Please select both Source and Update HTML files.")
                return
            rows, columns, headings, summary = self._compare_two_html(source, target, selector)
            export_folder = Path(source or target).parent
            report_paths = [source, target]
            self.last_report_mode = "method1"
        elif self.method_var.get() == "method2":
            if not self.multi_html_files:
                messagebox.showerror("Error", "Please select one or more HTML files for multi-file selector compare.")
                return
            rows, columns, headings, summary = self._compare_multiple_html(self.multi_html_files, selector)
            export_folder = Path(self.multi_html_files[0]).parent
            report_paths = self.multi_html_files
            self.last_report_mode = "method2"
        else:
            source = self.single_html_var.get().strip()
            if not source:
                messagebox.showerror("Error", "Please select an original HTML file.")
                return
            rows, columns, headings, summary = self._compare_html_before_after_delmerge(source, selector)
            export_folder = Path(source).parent
            report_paths = [source]
            self.last_report_mode = "method3"

        self.report_docid, self.report_timestamp = self._report_metadata(report_paths)
        self.result_rows = rows
        self.current_columns = columns
        self.current_headings = headings
        self.last_export_folder = export_folder
        self._refresh_filter_dropdowns(rows)
        self._show_rows(rows, columns, headings)
        self.summary_label.config(text=summary)
        self.export_btn.config(state="normal" if rows else "disabled")
        self.restore_btn.config(state="normal" if rows and self.method_var.get() == "method1" else "disabled")
        self._export_html_report()

    def _compare_html_before_after_delmerge(self, source: str, selector: str) -> tuple[list[dict], list[str], dict[str, str], str]:
        original_doc = self._parse_html(source)
        if original_doc is None:
            return [], [], {}, "Could not parse original HTML."
        merged_doc = deepcopy(original_doc)
        manager = DelMergeManagerPy(
            merged_doc,
            error_logger=lambda method, message: None,
        )
        manager.merge_del_sequences()
        compare_mode = self.compare_mode_var.get()
        before_items = self._extract_items_from_doc(original_doc, selector, compare_mode)
        after_items = self._extract_items_from_doc(merged_doc, selector, compare_mode)
        file_name = Path(source).name
        return self._compare_item_sets(
            before_items,
            after_items,
            f"Original ({file_name})",
            f"After DelMerge ({file_name})",
            summary_prefix=f"Compared original vs DelMerge output for {file_name}"
        )

    def _restore_from_source(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select one or more rows to restore.")
            return

        anchor_ids = set()
        for item_id in selected:
            values = self.tree.item(item_id, "values")
            if not values: continue
            
            try:
                idx = self.current_columns.index("anchor_id")
                anchor_ids.add(values[idx])
            except (ValueError, IndexError):
                continue
        
        anchor_ids.discard("")
        if not anchor_ids:
            messagebox.showwarning("No Anchor", "Selected rows have no Anchor ID. Cannot restore.")
            return

        if not messagebox.askyesno("Confirm Restore", f"Are you sure you want to overwrite {len(anchor_ids)} Div(s) in the Update file with content from the Source file?"):
            return

        source_path = self.first_html_var.get().strip()
        target_path = self.second_html_var.get().strip()

        try:
            src_soup = self._parse_html(source_path)
            tgt_soup = self._parse_html(target_path)
            
            if not src_soup or not tgt_soup:
                messagebox.showerror("Error", "Could not parse one or both HTML files.")
                return

            changes_made = 0
            for aid in anchor_ids:
                # Find in source
                s_div = src_soup.find("div", id=aid) or src_soup.find("div", attrs={"data-para-id": aid})
                if not s_div: continue
                
                # Find in target
                t_div = tgt_soup.find("div", id=aid) or tgt_soup.find("div", attrs={"data-para-id": aid})
                if t_div:
                    t_div.replace_with(s_div)
                    changes_made += 1
            
            if changes_made > 0:
                with open(target_path, "w", encoding="utf-8") as f:
                    # Use prettify or str depending on preference, here str is safer for exact content
                    f.write(str(tgt_soup))
                messagebox.showinfo("Success", f"Successfully restored {changes_made} Div(s) to the Update file.")
                self._run_compare()
            else:
                messagebox.showinfo("No Match", "No matching Divs found in both files for the selected anchors.")
        except Exception as e:
            messagebox.showerror("Error", f"Restoration failed: {str(e)}")

    def _compare_two_html(self, source: str, target: str, selector: str) -> tuple[list[dict], list[str], dict[str, str], str]:
        compare_mode = self.compare_mode_var.get()
        source_items = self._extract_items(source, selector, compare_mode)
        target_items = self._extract_items(target, selector, compare_mode)
        file_names = [Path(source).name, Path(target).name]
        return self._compare_item_sets(
            source_items,
            target_items,
            f"Source ({file_names[0]})",
            f"Update ({file_names[1]})",
            summary_prefix=f"Compared Source ({file_names[0]}) to Update ({file_names[1]})"
        )

    def _compare_item_sets(
        self,
        source_items: list[dict],
        target_items: list[dict],
        file_0_heading: str,
        file_1_heading: str,
        summary_prefix: str,
    ) -> tuple[list[dict], list[str], dict[str, str], str]:
        columns = ["anchor_id", "tag_name", "data_user", "data_time", "data_cid", "file_0", "file_1", "status", "parent_status", "reason"]
        headings = {
            "anchor_id": "Anchor ID",
            "tag_name": "Tag Name",
            "data_user": "data-username",
            "data_time": "data-time",
            "data_cid": "data-cid",
            "file_0": file_0_heading,
            "file_1": file_1_heading,
            "status": "Status",
            "parent_status": "Parent Status",
            "reason": "Reason"
        }

        source_map = {item["key"]: item for item in source_items}
        target_map = {item["key"]: item for item in target_items}
        
        # Group source items by anchor for structural analysis
        source_items_in_div = {}
        for item in source_items:
            anc = item.get("anchor_id", "")
            if anc:
                source_items_in_div.setdefault(anc, []).append(item)
        
        # Primary matching: by data-username and data-time (key)
        matched_keys_src = set(source_map) & set(target_map)
        unmatched_src = set(source_map) - matched_keys_src
        unmatched_tgt = set(target_map) - matched_keys_src

        # Secondary reconciliation: tolerate data-time drift and ignorable
        # attrs on otherwise identical tracked changes.
        reconciled_pairs, unmatched_src, unmatched_tgt = self._reconcile_unmatched_items(
            unmatched_src, unmatched_tgt, source_map, target_map
        )

        final_rows: list[dict] = []
        handled_tgt = set()

        # 1. Process matched keys
        for key in sorted(matched_keys_src):
            s_item = source_map[key]
            t_item = target_map[key]
            text_a = s_item["text"]
            text_b = t_item["text"]

            # Node-level comparison — purely text content, attribute order ignored.
            parent_text_a = s_item.get("parent_text", "")
            parent_text_b = t_item.get("parent_text", "")
            node_same = (text_a == text_b)
            parent_same = (not parent_text_a and not parent_text_b) or (parent_text_a == parent_text_b)

            # --- STATUS: reflects only the node's own text comparison.
            # Attribute-order differences on the node itself never affect this.
            if node_same:
                status = "Same"
                reason = "Identical metadata and text"
            else:
                status = "Changed"
                reason = "Text change"

            # Refinement for Div Replace — only when node text truly changed
            anchor = s_item.get("anchor_id", "")
            if status == "Changed" and anchor:
                s_div_items = source_items_in_div.get(anchor, [])
                t_div_items = [t for t in target_items if t.get("anchor_id") == anchor]
                if len(s_div_items) > len(t_div_items):
                    status = "Changed (Div Replace)"
                    reason = "Consolidated/Wrapped in Div"

            # --- PARENT STATUS: other users' corrections in the same paragraph.
            # Kept strictly separate from Status so the table is unambiguous.
            other_users = t_item.get("other_users_in_div", [])
            if other_users:
                parent_status = f"Other: {', '.join(other_users)}"
            elif not parent_same:
                parent_status = "Parent Changed"
            else:
                parent_status = "—"

            final_rows.append({
                "div_idx": s_item.get("div_idx", -1),
                "node_order": s_item.get("node_order", -1),
                "document_order": s_item.get("document_order", -1),
                "anchor_id": anchor,
                "file_0_anchor_id": s_item.get("anchor_id", ""),
                "file_1_anchor_id": t_item.get("anchor_id", ""),
                "tag_name": s_item.get("tag_name", "") or t_item.get("tag_name", ""),
                "data_user": s_item.get("username", ""),
                "data_time": s_item.get("data_time", ""),
                "data_cid": s_item.get("data_cid", ""),
                "file_0": text_a,
                "file_1": text_b,
                "file_0_raw": s_item.get("outer_html", ""),
                "file_1_raw": t_item.get("outer_html", ""),
                "file_0_parent_raw": s_item.get("parent_raw", ""),
                "file_1_parent_raw": t_item.get("parent_raw", ""),
                "status": status,
                "parent_status": parent_status,
                "other_users": ", ".join(other_users) if other_users else "",  # kept for filter logic
                "reason": reason
            })
            handled_tgt.add(key)

        # 1a. Process reconciled matches where the primary key drifted but the
        # change identity is otherwise stable (cid/text/context).
        for s_key, t_key in reconciled_pairs:
            s_item = source_map[s_key]
            t_item = target_map[t_key]
            text_a = s_item["text"]
            text_b = t_item["text"]
            parent_text_a = s_item.get("parent_text", "")
            parent_text_b = t_item.get("parent_text", "")
            node_same = (text_a == text_b)
            parent_same = (not parent_text_a and not parent_text_b) or (parent_text_a == parent_text_b)

            if node_same:
                status = "Same"
                reason = "Matched despite tracking metadata drift"
            else:
                status = "Changed"
                reason = "Text change"

            anchor = s_item.get("anchor_id", "")
            if status == "Changed" and anchor:
                s_div_items = source_items_in_div.get(anchor, [])
                t_div_items = [t for t in target_items if t.get("anchor_id") == anchor]
                if len(s_div_items) > len(t_div_items):
                    status = "Changed (Div Replace)"
                    reason = "Consolidated/Wrapped in Div"

            other_users = t_item.get("other_users_in_div", [])
            if other_users:
                parent_status = f"Other: {', '.join(other_users)}"
            elif not parent_same:
                parent_status = "Parent Changed"
            else:
                parent_status = "—"

            final_rows.append({
                "anchor_id": anchor,
                "file_0_anchor_id": s_item.get("anchor_id", ""),
                "file_1_anchor_id": t_item.get("anchor_id", ""),
                "tag_name": s_item.get("tag_name", "") or t_item.get("tag_name", ""),
                "data_user": s_item.get("username", ""),
                "data_time": f"{s_item.get('data_time', '')}->{t_item.get('data_time', '')}" if s_item.get("data_time") != t_item.get("data_time") else s_item.get("data_time", ""),
                "data_cid": s_item.get("data_cid", "") or t_item.get("data_cid", ""),
                "file_0": text_a,
                "file_1": text_b,
                "file_0_raw": s_item.get("outer_html", ""),
                "file_1_raw": t_item.get("outer_html", ""),
                "file_0_parent_raw": s_item.get("parent_raw", ""),
                "file_1_parent_raw": t_item.get("parent_raw", ""),
                "status": status,
                "parent_status": parent_status,
                "other_users": ", ".join(other_users) if other_users else "",
                "reason": reason
            })
            handled_tgt.add(t_key)

        # 2. Process unmatched source with div-fallback logic
        for s_key in sorted(unmatched_src):
            s_item = source_map[s_key]
            s_div = s_item.get("div_idx", -1)
            
            # Fallback check: find item in same div in target
            match_found = False
            if s_div != -1:
                candidates = [t_k for t_k in unmatched_tgt if t_k not in handled_tgt and target_map[t_k].get("div_idx") == s_div]
                if len(candidates) == 1:
                    t_key = candidates[0]
                    t_item = target_map[t_key]
                    # "no insert,del,ins with other copy-editor" -> check if other users involved
                    other_users = t_item.get("other_users_in_div", [])
                    if not other_users:
                        # Success fallback match
                        final_rows.append({
                            "anchor_id": s_item.get("anchor_id", ""),
                            "file_0_anchor_id": s_item.get("anchor_id", ""),
                            "file_1_anchor_id": t_item.get("anchor_id", ""),
                            "tag_name": s_item.get("tag_name", "") or t_item.get("tag_name", ""),
                            "data_user": f"{s_item['username']}->{t_item['username']}" if s_item['username'] != t_item['username'] else s_item['username'],
                            "data_time": f"{s_item['data_time']}->{t_item['data_time']}" if s_item['data_time'] != t_item['data_time'] else s_item['data_time'],
                            "data_cid": f"{s_item['data_cid']}->{t_item['data_cid']}" if s_item.get('data_cid') != t_item.get('data_cid') else s_item.get('data_cid', ''),
                            "file_0": s_item["text"],
                            "file_1": t_item["text"],
                            "file_0_raw": s_item.get("outer_html", ""),
                            "file_1_raw": t_item.get("outer_html", ""),
                            "file_0_parent_raw": s_item.get("parent_raw", ""),
                            "file_1_parent_raw": t_item.get("parent_raw", ""),
                            "status": "Matched (Div Anchor)",
                            "parent_status": "—",
                            "other_users": "",
                            "reason": "Structural match via Parent Div"
                        })
                        handled_tgt.add(t_key)
                        match_found = True
            
            if not match_found:
                reason = ""
                anchor = s_item.get("anchor_id", "")
                if anchor:
                    # Check if div exists in target but with different tag count
                    t_div_items = [t for t in target_items if t.get("anchor_id") == anchor]
                    if t_div_items:
                        reason = f"Div {anchor} structural update"
                        if len(source_items_in_div[anchor]) > len(t_div_items):
                            reason = "Consolidated/Wrapped in Div"
                
                final_rows.append({
                    "anchor_id": anchor,
                    "file_0_anchor_id": s_item.get("anchor_id", ""),
                    "file_1_anchor_id": "",
                    "tag_name": s_item.get("tag_name", ""),
                    "data_user": s_item.get("username", ""),
                    "data_time": s_item.get("data_time", ""),
                    "data_cid": s_item.get("data_cid", ""),
                    "file_0": s_item["text"],
                    "file_1": "[missing]",
                    "file_0_parent_raw": s_item.get("parent_raw", ""),
                    "file_1_parent_raw": "",
                    "status": "Missing in update",
                    "parent_status": "—",
                    "other_users": "",
                    "reason": reason
                })

        # 3. Process remaining new items in target
        for t_key in sorted(unmatched_tgt):
            if t_key in handled_tgt: continue
            t_item = target_map[t_key]
            other_users = t_item.get("other_users_in_div", [])
            status = "New in update"
            reason = ""

            anchor = t_item.get("anchor_id", "")
            if anchor:
                s_div_items = source_items_in_div.get(anchor, [])
                if s_div_items:
                    status = "New (Div Updated)"
                    if len(s_div_items) > 1 and len([t for t in target_items if t.get("anchor_id") == anchor]) == 1:
                        reason = "Consolidated multiple tags"

            # Parent status: note other users in same paragraph separately
            parent_status = f"Other: {', '.join(other_users)}" if other_users else "—"

            final_rows.append({
                "anchor_id": anchor,
                "file_0_anchor_id": "",
                "file_1_anchor_id": t_item.get("anchor_id", ""),
                "tag_name": t_item.get("tag_name", ""),
                "data_user": t_item.get("username", ""),
                "data_time": t_item.get("data_time", ""),
                "data_cid": t_item.get("data_cid", ""),
                "file_0": "[missing]",
                "file_1": t_item["text"],
                "file_0_parent_raw": "",
                "file_1_parent_raw": t_item.get("parent_raw", ""),
                "status": status,
                "parent_status": parent_status,
                "other_users": ", ".join(other_users) if other_users else "",
                "reason": reason
            })

        # Add Anchor ID to existing rows and check for "Div Updated" status
        for row in final_rows:
            if row.get("status") == "Missing in revised":
                anchor = row.get("anchor_id", "")
                if anchor and any(r.get("anchor_id") == anchor and "Update" in str(r.get("status")) for r in final_rows):
                    row["status"] = "Missing (Div Updated)"

        rows = final_rows
        summary = (
            f"{summary_prefix}: "
            f"{len(source_items)} selector matches in source, {len(target_items)} in update. "
            f"Rows: {len(rows)}"
        )
        return rows, columns, headings, summary

    def _reconcile_unmatched_items(
        self,
        unmatched_src: set[str],
        unmatched_tgt: set[str],
        source_map: dict[str, dict],
        target_map: dict[str, dict],
    ) -> tuple[list[tuple[str, str]], set[str], set[str]]:
        pairs: list[tuple[str, str]] = []
        remaining_src = set(unmatched_src)
        remaining_tgt = set(unmatched_tgt)

        src_groups: dict[str, list[str]] = {}
        tgt_groups: dict[str, list[str]] = {}
        for s_key in unmatched_src:
            sig = self._reconcile_signature(source_map[s_key])
            if sig:
                src_groups.setdefault(sig, []).append(s_key)
        for t_key in unmatched_tgt:
            sig = self._reconcile_signature(target_map[t_key])
            if sig:
                tgt_groups.setdefault(sig, []).append(t_key)

        for sig in sorted(set(src_groups) & set(tgt_groups)):
            src_keys = sorted(src_groups[sig])
            tgt_keys = sorted(tgt_groups[sig])
            if len(src_keys) != len(tgt_keys):
                continue
            for s_key, t_key in zip(src_keys, tgt_keys):
                pairs.append((s_key, t_key))
                remaining_src.discard(s_key)
                remaining_tgt.discard(t_key)

        return pairs, remaining_src, remaining_tgt

    def _reconcile_signature(self, item: dict) -> str:
        username = item.get("username", "")
        text = item.get("text", "")
        data_cid = item.get("data_cid", "")
        anchor = item.get("anchor_id", "")
        parent_text = item.get("parent_text", "")

        if data_cid and username:
            return f"user:{username}|cid:{data_cid}|anchor:{anchor}|text:{text}|parent:{parent_text}"
        if data_cid:
            return f"cid:{data_cid}|anchor:{anchor}|text:{text}|parent:{parent_text}"
        if username:
            return f"user:{username}|anchor:{anchor}|text:{text}|parent:{parent_text}"
        return ""

    def _compare_multiple_html(self, paths: list[str], selector: str) -> tuple[list[dict], list[str], dict[str, str], str]:
        compare_mode = self.compare_mode_var.get()
        paths = self._sort_paths_by_filename_timestamp(paths)
        extracted = [self._extract_items(path, selector, compare_mode) for path in paths]
        file_names = [Path(path).name for path in paths]
        maps = [{item["key"]: item for item in file_items} for file_items in extracted]
        all_keys = sorted({key for item_map in maps for key in item_map})

        columns = ["tag_name", "data_user", "data_time", "data_cid"] + [f"file_{idx}" for idx in range(len(paths))] + ["status", "parent_status"]
        headings = {
            "tag_name": "Tag Name",
            "data_user": "data-username",
            "data_time": "data-time",
            "data_cid": "data-cid",
            **{f"file_{idx}": file_name for idx, file_name in enumerate(file_names)},
            "status": "Status",
            "parent_status": "Parent Status",
        }

        rows: list[dict] = []
        for key in all_keys:
            row = {"tag_name": "", "data_user": "", "data_time": "", "data_cid": "", "status": "", "parent_status": "—", "other_users": ""}
            values: list[str] = []
            tag_names: set[str] = set()
            users: set[str] = set()
            times: set[str] = set()
            cids: set[str] = set()
            other_user_set: set[str] = set()
            present_count = 0

            for idx, item_map in enumerate(maps):
                item = item_map.get(key)
                cell_value = item["text"] if item else ""
                row[f"file_{idx}"] = cell_value if cell_value else "[missing]"
                if item:
                    present_count += 1
                    if item.get("tag_name"):
                        tag_names.add(item["tag_name"])
                    if item["username"]:
                        users.add(item["username"])
                    if item["data_time"]:
                        times.add(item["data_time"])
                    if item.get("data_cid"):
                        cids.add(item["data_cid"])
                    for u in item.get("other_users_in_div", []):
                        other_user_set.add(u)
                values.append(cell_value)

            if tag_names:
                row["tag_name"] = "/".join(sorted(tag_names)) if len(tag_names) > 1 else next(iter(tag_names))
            if users:
                row["data_user"] = "/".join(sorted(users)) if len(users) > 1 else next(iter(users))
            if times:
                row["data_time"] = "/".join(sorted(times)) if len(times) > 1 else next(iter(times))
            if cids:
                row["data_cid"] = "/".join(sorted(cids)) if len(cids) > 1 else next(iter(cids))

            present_texts = [value for value in values if value]
            if not present_texts:
                row["status"] = "Missing"
            elif present_count == len(paths):
                row["status"] = "Same" if len(set(present_texts)) == 1 else "Changed"
            elif present_count == 1:
                row["status"] = f"Only in {file_names[values.index(present_texts[0])]}"
            else:
                row["status"] = "Partial"

            # Parent Status: other users present in the same paragraph
            if other_user_set:
                row["parent_status"] = f"Other: {', '.join(sorted(other_user_set))}"
                row["other_users"] = ", ".join(sorted(other_user_set))
            else:
                row["parent_status"] = "—"

            rows.append(row)

        summary = (
            f"Compared {len(paths)} HTML files with selector '{selector}': "
            f"Total rows: {len(rows)}. Reference file: {file_names[0]}."
        )
        return rows, columns, headings, summary

    def _extract_items(self, location: str, selector: str, compare_mode: str = "data-time") -> list[dict]:
        """Extract items from HTML file with caching."""
        cache_path = self._get_cache_path(location)
        
        # Check if cache is valid
        if self._cache_is_valid(cache_path, location, selector, compare_mode):
            cached = self._load_extract_cache(cache_path)
            if cached is not None:
                return cached
        
        # Extract from document
        doc = self._parse_html(location)
        if doc is None:
            return []
        
        items = self._extract_items_from_doc(doc, selector, compare_mode)
        
        # Save to cache
        self._save_extract_cache(cache_path, location, selector, compare_mode, items)
        
        return items

    def _extract_items_from_doc(self, doc, selector: str, compare_mode: str = "data-time") -> list[dict]:
        items: list[dict] = []

        # sequential document order
        global_order = 0

        # process div-by-div instead of global selector search
        all_divs = doc.find_all("div")

        for div_idx, parent_div in enumerate(all_divs):

            selected = [
                node
                for node in self._select_compare_nodes(parent_div, selector)
                if node.find_parent("div") is parent_div
            ]

            if not selected:
                continue

            anchor_id = (
                parent_div.get("id")
                or parent_div.get("data-para-id")
                or ""
            )

            parent_text = self._normalize_text(parent_div)
            parent_raw = str(parent_div)

            # sequential inside same div
            for node_order, node in enumerate(selected, start=1):

                text = self._normalize_text(node)

                username = node.get("data-username") or ""
                data_time = node.get("data-time", "")
                data_cid = node.get("data-cid", "")

                tag_name = node.name or ""

                compare_value = (data_cid or data_time)

                key = "||".join([
                    tag_name,
                    username,
                    compare_value,
                    text
                ])

                # collect other users in same div
                other_users = set()

                for other in selected:
                    if other is node:
                        continue

                    other_user = (
                        other.get("data-username")
                        or ""
                    ).strip()

                    if other_user and other_user != username:
                        other_users.add(other_user)

                items.append({
                    "key": key,
                    "text": text,
                    "username": username,
                    "data_time": data_time,
                    "data_cid": data_cid,
                    "tag_name": tag_name,

                    # IMPORTANT
                    "anchor_id": anchor_id,
                    "div_idx": div_idx,
                    "node_order": node_order,
                    "document_order": global_order,

                    # helpful for report
                    "group_index": node_order,
                    "group_size": len(selected),

                    "parent_text": parent_text,
                    "parent_raw": parent_raw,
                    "outer_html": str(node),

                    "other_users_in_div": sorted(other_users),
                })

                global_order += 1

        return items

    def _select_compare_nodes(self, doc, selector: str):
        ordered_nodes = []
        seen_ids = set()

        selectors = self._priority_compare_selectors()
        if selector and selector not in selectors:
            selectors.append(selector)

        for css_selector in selectors:
            try:
                matches = doc.select(css_selector)
            except Exception:
                continue
            for node in matches:
                node_id = id(node)
                if node_id in seen_ids:
                    continue
                seen_ids.add(node_id)
                ordered_nodes.append(node)
        return ordered_nodes

    def _priority_compare_selectors(self) -> list[str]:
        selectors = []
        for tag_name in PRIORITY_WRAPPER_ORDER:
            selectors.append(f"{tag_name} {PRIORITY_DEL_SELECTOR}")
        for tag_name in PRIORITY_WRAPPER_ORDER:
            selectors.append(f"{PRIORITY_DEL_SELECTOR} > {tag_name}")
        for tag_name in PRIORITY_WRAPPER_ORDER:
            selectors.append(f"{PRIORITY_DEL_SELECTOR} + {tag_name} > {PRIORITY_DEL_SELECTOR}")
        return selectors

    def _build_item_key(self, node, index: int, compare_mode: str = "data-time") -> str:
        """Build a stable, unique key for a change node.

        Priority (varies by compare_mode):
        
        For compare_mode="data-time":
          1. username + data-time + data-cid (most specific)
          2. username + data-time (fallback)
          3. data-time alone
          4. username + positional index
          5. positional index

        For compare_mode="data-cid":
          1. username + data-cid + data-time (most specific)
          2. username + data-cid (fallback)
          3. data-cid alone
          4. username + positional index
          5. positional index

        Attribute ORDER on the node is intentionally ignored.
        """
        data_time = node.get("data-time")
        username = node.get("data-username")
        cid = node.get("data-cid")

        if compare_mode == "data-cid":
            # Priority: cid-based
            if cid and username:
                return f"{username}|cid:{cid}" + (f"|time:{data_time}" if data_time else "")
            if cid:
                return f"cid:{cid}" + (f"|time:{data_time}" if data_time else "")
            # Fallback to data-time if cid not available
            if data_time and username:
                return f"{username}|{data_time}"
            if data_time:
                return f"time:{data_time}"
            if username:
                return f"{username}:{index}"
            return str(index)
        else:
            # Default: data-time based
            if data_time and username:
                if cid:
                    return f"{username}|{data_time}|cid:{cid}"
                return f"{username}|{data_time}"
            if data_time:
                return f"time:{data_time}" + (f"|cid:{cid}" if cid else "")
            if username:
                return f"{username}:{index}"
            return str(index)

    def _extract_docid_and_timestamp_from_filename(self, path: str) -> tuple[str | None, int | None]:
        name = Path(path).name
        parts = name.split("_")
        if len(parts) < 2:
            return None, None
        docid = parts[0]
        timestamp_str = parts[1].split(".", 1)[0]
        try:
            return docid, int(timestamp_str)
        except ValueError:
            return docid, None

    def _report_metadata(self, paths: list[str]) -> tuple[str | None, int | None]:
        docid = None
        latest_timestamp = 0
        for path in paths:
            item_docid, item_ts = self._extract_docid_and_timestamp_from_filename(path)
            if item_docid:
                if docid is None:
                    docid = item_docid
                elif item_docid != docid:
                    docid = None
            if item_ts and item_ts > latest_timestamp:
                latest_timestamp = item_ts
        return docid, latest_timestamp if latest_timestamp > 0 else None

    def _extract_timestamp_from_filename(self, path: str) -> int:
        name = Path(path).name
        parts = name.rsplit("_", 1)
        if len(parts) != 2:
            return 0
        timestamp_str = parts[1].rsplit(".", 1)[0]
        try:
            return int(timestamp_str)
        except ValueError:
            return 0

    def _sort_paths_by_filename_timestamp(self, paths: list[str]) -> list[str]:
        return sorted(paths, key=self._extract_timestamp_from_filename)

    def _parse_html(self, location: str):
        if not location:
            return None
        with open(location, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        try:
            # html.parser preserves attribute order better than lxml
            return BeautifulSoup(content, "html.parser")
        except Exception:
            return BeautifulSoup(content, "lxml")

    def _normalize_text(self, node) -> str:
        raw_text = node.get_text(separator=" ", strip=False)
        normalized = " ".join(raw_text.split())
        if normalized:
            return normalized

        if raw_text and raw_text.strip() == "":
            return "[whitespace]"

        if hasattr(node, "name") and node.name:
            return f"<{node.name}/>"

        return ""

    def _get_cache_path(self, file_path: str) -> str:
        """Return cache file path for the given HTML file."""
        return f"{file_path}.compare.json"

    def _cache_is_valid(self, cache_path: str, file_path: str, selector: str, compare_mode: str) -> bool:
        """Check if extraction cache is still valid."""
        if not os.path.exists(cache_path):
            return False
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if not isinstance(cache, dict):
                return False
            stat = os.stat(file_path)
            return (
                cache.get("modified_time") == stat.st_mtime and
                cache.get("file_size") == stat.st_size and
                cache.get("selector") == selector and
                cache.get("compare_mode") == compare_mode
            )
        except Exception:
            return False

    def _load_extract_cache(self, cache_path: str) -> list[dict] | None:
        """Load cached extraction items."""
        if not os.path.exists(cache_path):
            return None
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
            items = cache.get("extracted_items", [])
            return items if isinstance(items, list) else None
        except Exception:
            return None

    def _save_extract_cache(self, cache_path: str, file_path: str, selector: str, compare_mode: str, items: list[dict]) -> None:
        """Save extraction results to cache."""
        try:
            stat = os.stat(file_path)
            cache = {
                "modified_time": stat.st_mtime,
                "file_size": stat.st_size,
                "selector": selector,
                "compare_mode": compare_mode,
                "extracted_items": items
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False)
        except Exception:
            pass


class HTMLCompareReplaceTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent)
        self.source_path = tk.StringVar()
        self.update_path = tk.StringVar()
        self.selector_var = tk.StringVar(value="[data-username='copyeditor'][data-time]")
        self.raw_view_var = tk.BooleanVar(value=False)
        self.diffs: list[dict] = []
        self.current_idx = -1
        self._build_ui()

    def _build_ui(self) -> None:
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
        RPT_COLS = ("anchor_id", "tag_name", "data_user", "data_time", "file_0", "file_1",
                    "status", "parent_status", "reason")
        RPT_HEADS = ("Anchor ID", "Tag Name", "data-username", "data-time", "Source",
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
        self.replace_btn.pack(side="left", padx=(20, 0))

    def _browse(self, var: tk.StringVar):
        path = filedialog.askopenfilename(filetypes=[("HTML/XML Files", "*.html;*.htm;*.xml"), ("All Files", "*")])
        if path: var.set(path)

    def _load_and_compare(self):
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
        if ps and ps != "—":
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
                           if r.get("parent_status") and r.get("parent_status") != "—"})

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
        self._highlight_and_scroll(self.upd_text, raw1)

    def _display_file(self, widget: tk.Text, path: str):
        widget.config(state="normal")
        widget.delete("1.0", tk.END)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            widget.insert("1.0", content)
            
            # Apply highlighting ONLY if NOT in Raw Mode
            if not self.raw_view_var.get():
                self._highlight_tags(widget)
        except Exception as e:
            widget.insert("1.0", f"Error loading file: {e}")
        widget.config(state="disabled")

    def _highlight_tags(self, widget: tk.Text):
        content = widget.get("1.0", tk.END)
        # Very basic regex-like search for tags
        import re
        patterns = [
            (r"<del.*?>.*?</del>", "del"),
            (r"<ins.*?>.*?</ins>", "ins"),
            (r"<insert.*?>.*?</insert>", "ins"),
            (r"<div.*?>", "anchor")
        ]
        for pattern, tag in patterns:
            for m in re.finditer(pattern, content, re.DOTALL):
                start = widget.index(f"1.0 + {m.start()} chars")
                end = widget.index(f"1.0 + {m.end()} chars")
                widget.tag_add(tag, start, end)

    def _update_status(self):
        count = len(self.diffs)
        if count == 0:
            self.status_label.config(text="No differences found.")
        else:
            self.status_label.config(text=f"Difference {self.current_idx + 1} of {count}")

    def _jump_to_diff(self, idx: int):
        if not self.diffs or idx < 0 or idx >= len(self.diffs): return
        self.current_idx = idx
        diff = self.diffs[idx]
        
        # Search for content in widgets (using raw outer_html for precision)
        self._highlight_and_scroll(self.src_text, diff.get("file_0_raw") or diff["file_0"])
        self._highlight_and_scroll(self.upd_text, diff.get("file_1_raw") or diff["file_1"])
        self._update_status()

    def _highlight_and_scroll(self, widget: tk.Text, text: str):
        widget.tag_remove("current", "1.0", tk.END)
        if not text or text == "[missing]": return
        
        pos = widget.search(text, "1.0", tk.END)
        if pos:
            end_pos = widget.index(f"{pos} + {len(text)} chars")
            widget.tag_add("current", pos, end_pos)
            widget.see(pos)

    def _next_diff(self):
        if self.current_idx < len(self.diffs) - 1:
            self._jump_to_diff(self.current_idx + 1)

    def _prev_diff(self):
        if self.current_idx > 0:
            self._jump_to_diff(self.current_idx - 1)

    def _replace_current(self):
        if self.current_idx < 0 or self.current_idx >= len(self.diffs): return
        diff = self.diffs[self.current_idx]
        aid = diff.get("anchor_id")
        if not aid:
            messagebox.showwarning("No Anchor", "This difference has no Anchor ID. Cannot replace.")
            return

        # Reuse restore logic
        temp_comp = HTMLCompareTab(self.master)
        # Mocking required values for _restore_from_source
        temp_comp.first_html_var.set(self.source_path.get())
        temp_comp.second_html_var.set(self.update_path.get())
        
        # Manually invoke the replacement for this one anchor
        try:
            src_soup = temp_comp._parse_html(self.source_path.get())
            tgt_soup = temp_comp._parse_html(self.update_path.get())
            s_div = src_soup.find("div", id=aid) or src_soup.find("div", attrs={"data-para-id": aid})
            t_div = tgt_soup.find("div", id=aid) or tgt_soup.find("div", attrs={"data-para-id": aid})
            if s_div and t_div:
                t_div.replace_with(s_div)
                with open(self.update_path.get(), "w", encoding="utf-8") as f:
                    f.write(str(tgt_soup))
                # Refresh
                self._load_and_compare()
                messagebox.showinfo("Success", f"Div {aid} replaced successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Replacement failed: {e}")

    def _on_scroll(self, other_widget, *args):
        # Sync the other widget's view
        other_widget.yview_moveto(args[0])
        return "break" # Prevents default handling if needed or just syncs


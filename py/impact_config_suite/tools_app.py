from __future__ import annotations

import json
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from analyses_tab import AnalysesTab
from patterns_tab import PatternsTab
from search_tab import SearchTab
from cjk_checker.gui import CJKIntegrityTab
from data_transfer_tab import DataTransferTab
from impact_to_ceg_tab import ImpactToCEGTab
from pgm_processor_tab import PGMProcessorTab
from word_extractor_tab import WordExtractorTab
from id_pattern_extractor_tab import IDPatternExtractorTab
from new_config_tab import NewConfigTab
from compare_tab import HTMLCompareTab, HTMLCompareReplaceTab
from element_extractor_tab import ElementExtractorTab
from core.run_history import RunHistoryStore


class CommonToolsApp:
    APP_METADATA_NAME = "build_metadata.json"
    NAVIGATION_CONFIG_NAME = "tools_navigation.json"
    TOOL_CLASS_BY_ID = {
        "analyses": AnalysesTab,
        "patterns": PatternsTab,
        "search": SearchTab,
        "cjk_integrity": CJKIntegrityTab,
        "data_transfer": DataTransferTab,
        "pgm_html_clone_processor": PGMProcessorTab,
        "impact_to_ceg_pgm": ImpactToCEGTab,
        "word_extractor": WordExtractorTab,
        "id_pattern_extractor": IDPatternExtractorTab,
        "compare_html": HTMLCompareTab,
        "compare_replace": HTMLCompareReplaceTab,
        "new_journal_config": NewConfigTab,
        "element_extractor": ElementExtractorTab,
    }
    DEFAULT_NAVIGATION = {
        "default_category": "Analysis",
        "default_tool": "analyses",
        "categories": [
            {
                "name": "Analysis",
                "tools": [
                    {"id": "analyses", "label": "Analyses"},
                    {"id": "patterns", "label": "Patterns"},
                    {"id": "search", "label": "Search"},
                    {"id": "cjk_integrity", "label": "CJK Integrity"},
                ],
            },
            {
                "name": "Process",
                "tools": [
                    {"id": "data_transfer", "label": "Data Transfer"},
                    {"id": "pgm_html_clone_processor", "label": "PGM HTML Clone Processor"},
                    {"id": "impact_to_ceg_pgm", "label": "IMPACT to CEG/PGM"},
                    {"id": "word_extractor", "label": "Word Extractor"},
                ],
            },
            {
                "name": "Comparison",
                "tools": [
                    {"id": "compare_html", "label": "Compare HTML"},
                    {"id": "compare_replace", "label": "Compare & Replace"},
                ],
            },
            {
                "name": "Configuration",
                "tools": [
                    {"id": "new_journal_config", "label": "New Journal Config"},
                    {"id": "element_extractor", "label": "Element Extractor"},
                ],
            },
        ],
    }

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.app_metadata = self._load_app_metadata()
        self.root.title(self.app_metadata.get("display_name", "Framework Tools"))
        self.root.geometry("1120x820")
        self.is_dark_mode = False
        self.images = {}
        self.navigation_config = self._load_navigation_config()
        self.category_order = [item["name"] for item in self.navigation_config["categories"]]
        self.category_by_name = {item["name"]: item for item in self.navigation_config["categories"]}
        self.navigation_config_path = self._resolve_navigation_config_path()
        self.navigation_config_mtime = self._config_mtime(self.navigation_config_path)
        self._nav_watch_active = True
        self._set_window_icon()
        self._setup_menu()
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    @classmethod
    def _resource_base_dir(cls) -> Path:
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            return Path(bundle_dir)
        return Path(__file__).resolve().parent

    @classmethod
    def _config_paths(cls) -> list[Path]:
        paths = []
        paths.append(cls._resource_base_dir() / cls.NAVIGATION_CONFIG_NAME)
        if getattr(sys, "frozen", False):
            paths.append(Path(sys.executable).resolve().with_name(cls.NAVIGATION_CONFIG_NAME))
        paths.append(Path.cwd() / cls.NAVIGATION_CONFIG_NAME)
        return paths

    @classmethod
    def _app_metadata_paths(cls) -> list[Path]:
        paths = []
        paths.append(cls._resource_base_dir() / cls.APP_METADATA_NAME)
        if getattr(sys, "frozen", False):
            paths.append(Path(sys.executable).resolve().with_name(cls.APP_METADATA_NAME))
        paths.append(Path.cwd() / cls.APP_METADATA_NAME)
        return paths

    @classmethod
    def _resolve_navigation_config_path(cls) -> Path | None:
        for path in cls._config_paths():
            if path.is_file():
                return path
        return None

    @staticmethod
    def _config_mtime(path: Path | None) -> float | None:
        if not path:
            return None
        try:
            return path.stat().st_mtime
        except OSError:
            return None

    @classmethod
    def _normalize_navigation_config(cls, data: dict) -> dict:
        categories = []
        seen_categories = set()
        for category in data.get("categories", []):
            category_name = str(category.get("name", "")).strip()
            if not category_name or category_name in seen_categories:
                continue
            tools = []
            seen_tool_ids = set()
            for tool in category.get("tools", []):
                tool_id = str(tool.get("id", "")).strip()
                tool_label = str(tool.get("label", "")).strip()
                if not tool_id or not tool_label or tool_id in seen_tool_ids:
                    continue
                if tool_id not in cls.TOOL_CLASS_BY_ID:
                    continue
                tools.append({"id": tool_id, "label": tool_label})
                seen_tool_ids.add(tool_id)
            if tools:
                categories.append({"name": category_name, "tools": tools})
                seen_categories.add(category_name)

        if not categories:
            return {
                "categories": cls.DEFAULT_NAVIGATION["categories"],
                "default_category": cls.DEFAULT_NAVIGATION["default_category"],
                "default_tool": cls.DEFAULT_NAVIGATION["default_tool"],
            }

        default_category = str(data.get("default_category", categories[0]["name"])).strip()
        if default_category not in {item["name"] for item in categories}:
            default_category = categories[0]["name"]

        default_tool = str(data.get("default_tool", categories[0]["tools"][0]["id"])).strip()
        if not any(tool["id"] == default_tool for category in categories for tool in category["tools"]):
            default_tool = categories[0]["tools"][0]["id"]

        return {
            "categories": categories,
            "default_category": default_category,
            "default_tool": default_tool,
        }

    @classmethod
    def _load_navigation_config(cls) -> dict:
        for path in cls._config_paths():
            if not path.is_file():
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                return cls._normalize_navigation_config(raw)
            except Exception as exc:
                print(f"Navigation config error at {path}: {exc}")
        return cls._normalize_navigation_config(cls.DEFAULT_NAVIGATION)

    @classmethod
    def _load_app_metadata(cls) -> dict:
        defaults = {"display_name": "IMPACT_ConfigSuite", "version": "5.1.0"}
        for path in cls._app_metadata_paths():
            if not path.is_file():
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                target = raw.get("common", {}) if isinstance(raw, dict) else {}
                display_name = str(target.get("display_name", defaults["display_name"])).strip()
                version = str(target.get("version", defaults["version"])).strip()
                return {
                    "display_name": display_name or defaults["display_name"],
                    "version": version or defaults["version"],
                }
            except Exception as exc:
                print(f"App metadata error at {path}: {exc}")
        return defaults

    def _set_window_icon(self) -> None:
        assets_dir = self._resource_base_dir() / "assets"
        for icon_name in ("favicon.ico", "ng_favicon.ico"):
            icon_path = assets_dir / icon_name
            if icon_path.exists():
                try:
                    self.root.iconbitmap(icon_path)
                    return
                except Exception:
                    continue

    def _setup_menu(self) -> None:
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        # File Menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self._on_close)

        history_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="History", menu=history_menu)
        history_menu.add_command(label="View Run History", command=self._open_history_browser)
        history_menu.add_command(label="Open History Folder", command=self._open_history_folder)
        history_menu.add_command(label="Open History File", command=self._open_history_file)

        # Tools menu mirrors the categorized selectors.
        tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Tools", menu=tools_menu)
        for category in self.navigation_config["categories"]:
            category_menu = tk.Menu(tools_menu, tearoff=0)
            tools_menu.add_cascade(label=category["name"], menu=category_menu)
            for tool in category["tools"]:
                category_menu.add_command(
                    label=tool["label"],
                    command=lambda c=category["name"], t=tool["id"]: self._select_tool(c, t),
                )

        # Help Menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        about_text = f"{self.app_metadata['display_name']}\nVersion {self.app_metadata['version']}\n© 2026 IMPACT Team"
        help_menu.add_command(label="About", command=lambda: messagebox.showinfo("About", about_text))
        help_menu.add_command(label="Reload Navigation", command=self.reload_navigation)

    def _setup_header(self) -> None:
        self.header_frame = tk.Frame(self.root, bg="#ffffff", pady=10)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.columnconfigure(1, weight=1)

        assets_dir = self._resource_base_dir() / "assets"
        try:
            # Resize IMPACT Image
            imp_img = Image.open(str(assets_dir / "IMPACT_5_4.png"))
            imp_img = imp_img.resize((120, 40), Image.Resampling.LANCZOS)
            self.images['impact'] = ImageTk.PhotoImage(imp_img)
            
            # Resize Newgen Image
            ng_img = Image.open(str(assets_dir / "Newgen.png"))
            ng_img = ng_img.resize((100, 30), Image.Resampling.LANCZOS)
            self.images['newgen'] = ImageTk.PhotoImage(ng_img)
            
            # Col 1: IMPACT Image
            tk.Label(self.header_frame, image=self.images['impact'], bg="#ffffff").grid(row=0, column=0, padx=20)
        except Exception as e:
            print(f"Image load error: {e}")
            tk.Label(self.header_frame, text="IMPACT", font=("Arial", 12, "bold"), bg="#ffffff").grid(row=0, column=0, padx=20)

        # Col 2: Title Text
        self.header_title = tk.Label(
            self.header_frame, 
            text="Developer Supporting Framework", 
            font=("Segoe UI", 22, "bold"), 
            bg="#ffffff", 
            fg="#1e293b"
        )
        self.header_title.grid(row=0, column=1, sticky="w")

        # Col 3: Newgen Image + Toggle
        self.right_header = tk.Frame(self.header_frame, bg="#ffffff")
        self.right_header.grid(row=0, column=2, padx=20)

        try:
            tk.Label(self.right_header, image=self.images['newgen'], bg="#ffffff").pack(side="top")
        except Exception:
            tk.Label(self.right_header, text="NEWGEN", font=("Arial", 10, "bold"), bg="#ffffff").pack(side="top")

        self.theme_btn = tk.Button(
            self.right_header, 
            text="🌙 Dark Mode", 
            command=self._toggle_theme,
            bg="#f1f5f9", 
            fg="#475569", 
            relief="flat", 
            font=("Segoe UI", 9, "bold"),
            padx=10, 
            pady=5,
            cursor="hand2"
        )
        self.theme_btn.pack(side="bottom", pady=(5, 0))

    def _toggle_theme(self) -> None:
        self.is_dark_mode = not self.is_dark_mode
        self._configure_tab_styles()
        if self.is_dark_mode:
            bg_color = "#0f172a"
            fg_color = "#f8fafc"
            btn_bg = "#1e293b"
            header_bg = "#1e293b"
            self.theme_btn.config(text="☀️ Bright Mode", bg=btn_bg, fg=fg_color)
        else:
            bg_color = "#f8fafc"
            fg_color = "#1e293b"
            btn_bg = "#f1f5f9"
            header_bg = "#ffffff"
            self.theme_btn.config(text="🌙 Dark Mode", bg=btn_bg, fg="#475569")
        
        self.root.config(bg=bg_color)
        self.header_frame.config(bg=header_bg)
        self.header_title.config(bg=header_bg, fg=fg_color)
        self.right_header.config(bg=header_bg)
        self.body_container.config(bg=bg_color)
        self.canvas.config(bg=bg_color)
        self.scrollable_frame.config(bg=bg_color)
        
        # Update children recursively to apply theme to all tabs
        self._apply_theme_recursively(self.scrollable_frame, bg_color, fg_color)

    def _apply_theme_recursively(self, widget, bg, fg):
        """Recursively apply background and foreground colors to standard Tkinter widgets."""
        widget_type = widget.winfo_class()
        
        # Don't force theme on buttons as they have their own styles
        if widget_type in ("Frame", "Label", "Canvas"):
            try:
                widget.config(bg=bg)
            except tk.TclError:
                pass
                
        if widget_type == "Label":
            try:
                widget.config(fg=fg)
            except tk.TclError:
                pass

        for child in widget.winfo_children():
            self._apply_theme_recursively(child, bg, fg)

    def _build(self) -> None:
        self._setup_header()

        # Body container with extra padding
        self.body_container = tk.Frame(self.root, bg="#f3f4f6", padx=30, pady=25)
        self.body_container.pack(fill="both", expand=True)

        # Enable auto-scroll body using a canvas + scrollbar
        self.canvas = tk.Canvas(self.body_container, bg="#f3f4f6", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.body_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#f3f4f6")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        def _on_canvas_configure(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        
        self.canvas.bind("<Configure>", _on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self._build_navigation()
        self._schedule_navigation_watch()

    def _tool_location_by_id(self, tool_id: str) -> tuple[str, str] | None:
        for category in self.navigation_config["categories"]:
            for tool in category["tools"]:
                if tool["id"] == tool_id:
                    return category["name"], tool_id
        return None

    def _open_history_folder(self) -> None:
        history_dir = RunHistoryStore.base_dir()
        history_dir.mkdir(parents=True, exist_ok=True)
        webbrowser.open(history_dir.as_uri())

    def _open_history_file(self) -> None:
        history_path = RunHistoryStore.history_file_path()
        history_path.parent.mkdir(parents=True, exist_ok=True)
        if not history_path.exists():
            RunHistoryStore.save_entries(RunHistoryStore.load_entries())
        webbrowser.open(history_path.as_uri())

    def _open_history_browser(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Global Run History")
        dialog.geometry("980x560")
        dialog.configure(bg="#1e293b")
        dialog.transient(self.root)

        tk.Label(
            dialog,
            text="GLOBAL RUN HISTORY",
            font=("Segoe UI", 16, "bold"),
            fg="#f8fafc",
            bg="#1e293b",
        ).pack(anchor="w", padx=20, pady=(18, 10))

        search_frame = tk.Frame(dialog, bg="#1e293b")
        search_frame.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(search_frame, text="Search:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10, "bold")).pack(side="left")
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var, bg="#334155", fg="white", border=0, font=("Segoe UI", 10))
        search_entry.pack(side="left", fill="x", expand=True, padx=(10, 0), ipady=6)

        list_frame = tk.Frame(dialog, bg="#1e293b")
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        listbox = tk.Listbox(
            list_frame,
            bg="#0f172a",
            fg="#e2e8f0",
            selectbackground="#2563eb",
            selectforeground="white",
            border=0,
            font=("Consolas", 10),
        )
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        details_var = tk.StringVar(value="Select a history entry to inspect details.")
        tk.Label(dialog, textvariable=details_var, bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9), justify="left", anchor="w").pack(fill="x", padx=20, pady=(0, 10))

        state = {"entries": RunHistoryStore.load_entries()}

        def format_entry(entry: dict) -> str:
            ts = str(entry.get("timestamp", "")).strip() or "Unknown time"
            tool_label = str(entry.get("tool_label", "")).strip() or str(entry.get("tool_id", "")).strip() or "Tool"
            action = str(entry.get("action", "")).strip() or "run"
            summary = str(entry.get("summary", "")).strip()
            return f"{ts} | {tool_label} | {action} | {summary}"

        def refresh_entries(*_args) -> None:
            state["entries"] = RunHistoryStore.search_entries(search_var.get())
            listbox.delete(0, tk.END)
            for entry in state["entries"]:
                listbox.insert(tk.END, format_entry(entry))
            details_var.set("Select a history entry to inspect details.")

        def selected_entry() -> dict | None:
            if not listbox.curselection():
                return None
            index = listbox.curselection()[0]
            if index >= len(state["entries"]):
                return None
            return state["entries"][index]

        def update_details(_event=None) -> None:
            entry = selected_entry()
            if not entry:
                details_var.set("Select a history entry to inspect details.")
                return
            source_path = str(entry.get("source_path", "")).strip() or "NA"
            output_dir = str(entry.get("output_dir", "")).strip() or "NA"
            report_path = str(entry.get("report_path", "")).strip() or "NA"
            details_var.set(f"Source: {source_path}\nOutput: {output_dir}\nArtifact: {report_path}")

        def select_tool_for_entry(entry: dict):
            location = self._tool_location_by_id(str(entry.get("tool_id", "")).strip())
            if not location:
                return None
            category, tool_id = location
            self._select_tool(category, tool_id)
            return self.tool_views.get((category, tool_id))

        def apply_selected() -> None:
            entry = selected_entry()
            if not entry:
                messagebox.showinfo("Run History", "Please select a history entry.")
                return
            view = select_tool_for_entry(entry)
            if view is None or not hasattr(view, "apply_history_entry"):
                messagebox.showinfo("Run History", "The selected tool does not support applying history yet.")
                return
            view.apply_history_entry(entry)

        def rerun_selected() -> None:
            entry = selected_entry()
            if not entry:
                messagebox.showinfo("Run History", "Please select a history entry.")
                return
            view = select_tool_for_entry(entry)
            if view is None or not hasattr(view, "rerun_history_entry"):
                messagebox.showinfo("Run History", "The selected tool does not support rerun yet.")
                return
            view.rerun_history_entry(entry)

        def open_artifact() -> None:
            entry = selected_entry()
            if not entry:
                messagebox.showinfo("Run History", "Please select a history entry.")
                return
            target = str(entry.get("report_path", "")).strip()
            if not target:
                messagebox.showinfo("Run History", "No report or artifact path is saved for this entry.")
                return
            if target.startswith("http://") or target.startswith("https://"):
                webbrowser.open(target)
                return
            artifact_path = Path(target)
            if artifact_path.exists():
                webbrowser.open(artifact_path.as_uri())
                return
            messagebox.showerror("Run History", "Saved artifact path is no longer available.")

        def open_output_folder() -> None:
            entry = selected_entry()
            if not entry:
                messagebox.showinfo("Run History", "Please select a history entry.")
                return
            output_dir = str(entry.get("output_dir", "")).strip()
            if output_dir and Path(output_dir).exists():
                webbrowser.open(Path(output_dir).as_uri())
                return
            report_path = str(entry.get("report_path", "")).strip()
            if report_path and Path(report_path).exists():
                webbrowser.open(Path(report_path).parent.as_uri())
                return
            messagebox.showerror("Run History", "Output folder is not available for this entry.")

        def copy_json() -> None:
            entry = selected_entry()
            if not entry:
                messagebox.showinfo("Run History", "Please select a history entry.")
                return
            dialog.clipboard_clear()
            dialog.clipboard_append(json.dumps(entry, ensure_ascii=False, indent=2))

        search_var.trace_add("write", refresh_entries)
        listbox.bind("<<ListboxSelect>>", update_details)

        button_frame = tk.Frame(dialog, bg="#1e293b")
        button_frame.pack(fill="x", padx=20, pady=(0, 18))
        tk.Button(button_frame, text="Apply To Tool", command=apply_selected, bg="#2563eb", fg="white", font=("Segoe UI", 9, "bold"), border=0, padx=14, pady=8).pack(side="left", padx=(0, 8))
        tk.Button(button_frame, text="Rerun", command=rerun_selected, bg="#0f766e", fg="white", font=("Segoe UI", 9, "bold"), border=0, padx=14, pady=8).pack(side="left", padx=(0, 8))
        tk.Button(button_frame, text="Open Artifact", command=open_artifact, bg="#7c3aed", fg="white", font=("Segoe UI", 9, "bold"), border=0, padx=14, pady=8).pack(side="left", padx=(0, 8))
        tk.Button(button_frame, text="Open Output Folder", command=open_output_folder, bg="#475569", fg="white", font=("Segoe UI", 9, "bold"), border=0, padx=14, pady=8).pack(side="left", padx=(0, 8))
        tk.Button(button_frame, text="Copy JSON", command=copy_json, bg="#1d4ed8", fg="white", font=("Segoe UI", 9, "bold"), border=0, padx=14, pady=8).pack(side="right")

        refresh_entries()
        search_entry.focus_set()

    def _build_navigation(self, preserve=None) -> None:
        if hasattr(self, "navigation_frame"):
            self.navigation_frame.destroy()

        self.navigation_frame = tk.Frame(self.scrollable_frame, bg="#f3f4f6")
        self.navigation_frame.pack(fill="both", expand=True, padx=5, pady=(5, 12))

        self._configure_tab_styles()

        self.category_notebook = ttk.Notebook(self.navigation_frame, style="CategoryTabs.TNotebook")
        self.category_notebook.pack(fill="both", expand=True)

        self.tool_views = {}
        self.tool_notebooks = {}
        for category in self.navigation_config["categories"]:
            category_frame = ttk.Frame(self.category_notebook)
            self.category_notebook.add(category_frame, text=category["name"])

            tool_notebook = ttk.Notebook(category_frame, style="ToolTabs.TNotebook")
            tool_notebook.pack(fill="both", expand=True)
            self.tool_notebooks[category["name"]] = tool_notebook

            for tool in category["tools"]:
                tool_class = self.TOOL_CLASS_BY_ID[tool["id"]]
                view = tool_class(tool_notebook)
                tool_notebook.add(view, text=tool["label"])
                self.tool_views[(category["name"], tool["id"])] = view

        previous_search_tab = getattr(self, "search_tab", None)
        self.search_tab = self.tool_views.get(("Analysis", "search"), previous_search_tab)
        target_category = self.navigation_config["default_category"]
        target_tool = self.navigation_config["default_tool"]
        if preserve:
            preserve_category, preserve_tool = preserve
            if self._tool_exists(preserve_category, preserve_tool):
                target_category, target_tool = preserve_category, preserve_tool
        self._select_tool(target_category, target_tool)

    def _tool_exists(self, category: str, tool_id: str) -> bool:
        return category in self.category_by_name and any(tool["id"] == tool_id for tool in self.category_by_name[category]["tools"])

    def _configure_tab_styles(self) -> None:
        style = ttk.Style()
        if self.is_dark_mode:
            style.theme_use("clam")
            category_bg = "#1e293b"
            tool_bg = "#334155"
            fg = "#f8fafc"
        else:
            style.theme_use("default")
            category_bg = "#dbeafe"
            tool_bg = "#eff6ff"
            fg = "#0f172a"

        style.configure("CategoryTabs.TNotebook", padding=(8, 8))
        style.configure(
            "CategoryTabs.TNotebook.Tab",
            padding=(22, 12),
            font=("Segoe UI", 12, "bold"),
        )
        style.configure("ToolTabs.TNotebook", padding=(6, 6))
        style.configure(
            "ToolTabs.TNotebook.Tab",
            padding=(16, 9),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "CategoryTabs.TNotebook.Tab",
            background=[("selected", category_bg)],
            foreground=[("selected", fg)],
        )
        style.map(
            "ToolTabs.TNotebook.Tab",
            background=[("selected", tool_bg)],
            foreground=[("selected", fg)],
        )

    def _select_tool(self, category: str, tool_name: str) -> None:
        category_names = self.category_order
        if category not in self.category_by_name:
            category = self.navigation_config["default_category"]

        tools = self.category_by_name[category]["tools"]
        valid_tool_ids = {tool["id"] for tool in tools}
        if tool_name not in valid_tool_ids:
            tool_name = tools[0]["id"]

        self.category_notebook.select(category_names.index(category))
        tool_notebook = self.tool_notebooks[category]
        view = self.tool_views[(category, tool_name)]
        tool_notebook.select(view)
        self.canvas.yview_moveto(0)

    def _current_selection(self) -> tuple[str, str] | None:
        if not hasattr(self, "category_notebook") or not self.tool_views:
            return None
        category_index = self.category_notebook.index(self.category_notebook.select())
        category = self.category_order[category_index]
        tool_notebook = self.tool_notebooks.get(category)
        if tool_notebook is None:
            return None
        selected_tool_tab = tool_notebook.select()
        if not selected_tool_tab:
            return None
        selected_label = tool_notebook.tab(selected_tool_tab, "text")
        for tool in self.category_by_name.get(category, {}).get("tools", []):
            if tool["label"] == selected_label:
                return category, tool["id"]
        return None

    def _schedule_navigation_watch(self) -> None:
        if not self._nav_watch_active:
            return
        try:
            self.root.after(1000, self._watch_navigation_config)
        except tk.TclError:
            pass

    def _watch_navigation_config(self) -> None:
        if not self._nav_watch_active:
            return
        current_path = self._resolve_navigation_config_path()
        current_mtime = self._config_mtime(current_path)
        if current_path != self.navigation_config_path or current_mtime != self.navigation_config_mtime:
            self.navigation_config_path = current_path
            self.navigation_config_mtime = current_mtime
            self.reload_navigation()
        self._schedule_navigation_watch()

    def reload_navigation(self) -> None:
        preserve = self._current_selection()
        old_search_tab = getattr(self, "search_tab", None)
        if old_search_tab is not None:
            old_search_tab.shutdown(wait=True)
        self.navigation_config = self._load_navigation_config()
        self.category_order = [item["name"] for item in self.navigation_config["categories"]]
        self.category_by_name = {item["name"]: item for item in self.navigation_config["categories"]}
        self.navigation_config_path = self._resolve_navigation_config_path()
        self.navigation_config_mtime = self._config_mtime(self.navigation_config_path)
        self._setup_menu()
        self._build_navigation(preserve=preserve)

    def _on_close(self) -> None:
        self._nav_watch_active = False
        if self.search_tab is not None:
            self.search_tab.shutdown(wait=True)
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def launch_tools_app() -> None:
    CommonToolsApp().run()


if __name__ == "__main__":
    launch_tools_app()

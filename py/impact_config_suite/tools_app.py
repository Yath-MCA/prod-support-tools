from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from analyses_tab import AnalysesTab
from patterns_tab import PatternsTab
from search_tab import SearchTab
from cjk_checker.gui import CJKIntegrityTab
from data_transfer_tab import DataTransferTab


class CommonToolsApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("IMPACT Common Tools GUI")
        self.root.geometry("1060x760")
        self._set_window_icon()
        self._build()

    def _set_window_icon(self) -> None:
        assets_dir = Path(__file__).resolve().parent / "assets"
        for icon_name in ("favicon.ico", "ng_favicon.ico"):
            icon_path = assets_dir / icon_name
            if icon_path.exists():
                try:
                    self.root.iconbitmap(icon_path)
                    return
                except Exception:
                    continue

    def _build(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        notebook.add(AnalysesTab(notebook), text="Analyses")
        notebook.add(PatternsTab(notebook), text="Patterns")
        notebook.add(SearchTab(notebook), text="Search")
        notebook.add(CJKIntegrityTab(notebook), text="CJK Integrity")
        notebook.add(DataTransferTab(notebook), text="Data Transfer")

    def run(self) -> None:
        self.root.mainloop()


def launch_tools_app() -> None:
    CommonToolsApp().run()


if __name__ == "__main__":
    launch_tools_app()

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from cjk_checker.gui import CJKIntegrityTab


def run() -> None:
    root = tk.Tk()
    root.title("CJK Integrity Checker")
    root.geometry("980x720")

    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    for icon_name in ("favicon.ico", "ng_favicon.ico"):
        icon_path = assets_dir / icon_name
        if icon_path.exists():
            try:
                root.iconbitmap(icon_path)
                break
            except Exception:
                continue

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    notebook.add(CJKIntegrityTab(notebook), text="CJK Integrity")

    root.mainloop()


if __name__ == "__main__":
    run()

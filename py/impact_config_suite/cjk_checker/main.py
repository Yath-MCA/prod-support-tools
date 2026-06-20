from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from cjk_checker.gui import CJKIntegrityTab


def run() -> None:
    root = tk.Tk()
    root.title("CJK Integrity Checker")
    root.geometry("980x720")

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    notebook.add(CJKIntegrityTab(notebook), text="CJK Integrity")

    root.mainloop()


if __name__ == "__main__":
    run()

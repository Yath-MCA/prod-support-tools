import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from lxml import etree
from xmldiff import main, formatting
import html as html_lib
import re


def parse_xml_with_entity_handling(xml_path: Path):
    """
    Read XML as text and safely handle HTML named entities like &rsquo;
    so lxml can parse without failing.
    """
    raw = xml_path.read_text(encoding="utf-8", errors="replace")

    # Convert HTML named entities to Unicode chars (e.g., &rsquo; -> ’)
    raw = html_lib.unescape(raw)

    # Escape stray '&' that are not valid XML entities
    # Keep only XML 5 predefined entities untouched
    raw = re.sub(r"&(?!(amp;|lt;|gt;|quot;|apos;))", "&amp;", raw)

    parser = etree.XMLParser(recover=True, remove_blank_text=False)
    root = etree.fromstring(raw.encode("utf-8"), parser=parser)
    return etree.ElementTree(root)


def generate_html_diff(original_xml: Path, revised_xml: Path, output_html: Path):
    left_tree = parse_xml_with_entity_handling(original_xml)
    right_tree = parse_xml_with_entity_handling(revised_xml)

    formatter = formatting.XMLFormatter(
        normalize=formatting.WS_BOTH,
        pretty_print=True
    )

    diff_xml_string = main.diff_trees(left_tree, right_tree, formatter=formatter)
    escaped_diff = html_lib.escape(diff_xml_string)

    html_content = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>XML Compare Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    h2 {{ margin-bottom: 8px; }}
    .meta {{ margin-bottom: 16px; color: #444; }}
    pre {{
      background: #f7f7f7;
      border: 1px solid #ddd;
      padding: 12px;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: Consolas, monospace;
      font-size: 13px;
      line-height: 1.45;
    }}
    .ok {{ color: #2e7d32; font-weight: bold; }}
  </style>
</head>
<body>
  <h2>XML Comparison Report</h2>
  <div class="meta">
    <b>Original:</b> {original_xml}<br/>
    <b>Revised:</b> {revised_xml}<br/>
    <b>Output:</b> {output_html}
  </div>
  <pre>{escaped_diff}</pre>
</body>
</html>
"""
    output_html.write_text(html_content, encoding="utf-8")


class XmlCompareApp:
    def __init__(self, root):
        self.root = root
        self.root.title("XML Compare Tool")
        self.root.geometry("760x280")
        self.root.resizable(False, False)

        self.original_path = tk.StringVar()
        self.revised_path = tk.StringVar()

        # Original XML
        tk.Label(root, text="Original XML:", anchor="w").place(x=20, y=20, width=100)
        tk.Entry(root, textvariable=self.original_path).place(x=120, y=20, width=520, height=24)
        tk.Button(root, text="Browse", command=self.browse_original).place(x=650, y=20, width=90, height=24)

        # Revised XML
        tk.Label(root, text="Revised XML:", anchor="w").place(x=20, y=60, width=100)
        tk.Entry(root, textvariable=self.revised_path).place(x=120, y=60, width=520, height=24)
        tk.Button(root, text="Browse", command=self.browse_revised).place(x=650, y=60, width=90, height=24)

        # Info text
        info = (
            "Output HTML will be saved in the same folder as Revised XML\n"
            "with name: <revised_file_name>_compare_report.html"
        )
        tk.Label(root, text=info, justify="left", fg="#444").place(x=20, y=105)

        # Compare button
        tk.Button(
            root,
            text="Compare and Save HTML",
            command=self.compare,
            bg="#1976d2",
            fg="white",
            activebackground="#1565c0",
            activeforeground="white"
        ).place(x=280, y=185, width=200, height=36)

    def browse_original(self):
        file_path = filedialog.askopenfilename(
            title="Select Original XML",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if file_path:
            self.original_path.set(file_path)

    def browse_revised(self):
        file_path = filedialog.askopenfilename(
            title="Select Revised XML",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if file_path:
            self.revised_path.set(file_path)

    def compare(self):
        try:
            org = Path(self.original_path.get().strip())
            rev = Path(self.revised_path.get().strip())

            if not org.exists():
                messagebox.showerror("Error", "Please select a valid Original XML file.")
                return
            if not rev.exists():
                messagebox.showerror("Error", "Please select a valid Revised XML file.")
                return

            # Save report in same folder as revised XML
            output_html = rev.with_name(f"{rev.stem}_compare_report.html")

            generate_html_diff(org, rev, output_html)

            messagebox.showinfo(
                "Success",
                f"Comparison completed.\n\nHTML report saved at:\n{output_html}"
            )

        except Exception as ex:
            messagebox.showerror("Error", f"Comparison failed:\n{ex}")


if __name__ == "__main__":
    # Install once:
    #   py -m pip install lxml xmldiff
    root = tk.Tk()
    app = XmlCompareApp(root)
    root.mainloop()
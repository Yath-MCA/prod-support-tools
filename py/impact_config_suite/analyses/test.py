import xml.etree.ElementTree as ET
from collections import defaultdict
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import os


# Allow only first occurrence
SUPPRESS_AFTER_FIRST = {
    "table-wrap/table/tgroup/tbody/row/entry",
    "table-wrap/table/tgroup/tbody/row/entry/p",
    "list/list-item",
    "list/list-item/p",
    "list-item/label",
    "sec/p",
    "ref-list/ref",
    "table-wrap/table/tgroup/tbody/row",
    "table-wrap/table/tgroup/colspe",
}

# Fully ignore (never log)
FULLY_IGNORE = {
    "p/italic",
    "p/uri",
    "p/xref",
    "p/bold",
    "xref/sup",
}


def strip_namespace(tag):
    return tag.split('}', 1)[-1] if '}' in tag else tag


def normalize_xpath(path):
    return path.lstrip("/")


def is_fully_ignored(xpath):
    normalized = normalize_xpath(xpath)
    return any(normalized.endswith(rule) for rule in FULLY_IGNORE)


def suppress_after_first(xpath, count):
    normalized = normalize_xpath(xpath)
    return any(normalized.endswith(rule) for rule in SUPPRESS_AFTER_FIRST) and count > 1


def traverse(element, parent_path="", depth=1, report=None, xpath_counter=None):
    if report is None:
        report = []
    if xpath_counter is None:
        xpath_counter = defaultdict(int)

    tag = strip_namespace(element.tag)
    current_path = f"{parent_path}/{tag}" if parent_path else f"/{tag}"

    xpath_counter[current_path] += 1
    occurrence = xpath_counter[current_path]

    # ❌ Fully ignore
    if is_fully_ignored(current_path):
        return report

    # ❌ Ignore after first occurrence
    if suppress_after_first(current_path, occurrence):
        return report

    # ✅ Log only first occurrence
    if occurrence == 1:
        report.append({
            "xpath": current_path,
            "depth": depth
        })

    for child in element:
        traverse(child, current_path, depth + 1, report, xpath_counter)

    return report


def write_html_report(xml_file, report):
    output_file = os.path.splitext(xml_file)[0] + "_xml_structure_report.html"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>XML Structure Report</title>
<style>
body { font-family: Consolas, monospace; background:#f7f7f7; padding:20px; }
h1 { font-size:18px; }
.entry { white-space:pre; }
.meta { color:#444; margin-bottom:12px; }
</style>
</head>
<body>
""")

        f.write("<h1>XML Structure Report</h1>")
        f.write(f"<div class='meta'><b>Generated:</b> {timestamp}</div>")
        f.write("<hr>")

        for item in report:
            indent = "&nbsp;" * 4 * (item["depth"] - 1)
            f.write(f"<div class='entry'>{indent}{item['xpath']}</div>\n")

        f.write("</body></html>")

    return output_file


def select_xml_file():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(
        title="Select XML File",
        filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")]
    )


def main():
    xml_file = select_xml_file()
    if not xml_file:
        print("No file selected.")
        return

    tree = ET.parse(xml_file)
    root = tree.getroot()

    report = traverse(root)
    output = write_html_report(xml_file, report)

    print("HTML report generated:")
    print(output)


if __name__ == "__main__":
    main()

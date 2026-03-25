import os
import re
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import shutil

app = Flask(__name__)

# Versioning
APP_VERSION = "2.0.0"
LAST_UPDATE = datetime.now().strftime("%Y-%m-%d %H:%M")

# Configuration
# Note: In a real app, these would be user-provided paths.
# We'll handle path selection in the UI.


@app.route("/")
def index():
    return render_template("index.html", version=APP_VERSION, last_update=LAST_UPDATE)


@app.route("/api/rename_covers", methods=["POST"])
def rename_covers():
    data = request.json
    folder_path = data.get("path")
    if not folder_path or not os.path.exists(folder_path):
        return jsonify({"success": False, "message": "Invalid path"}), 400

    renamed = []
    for filename in os.listdir(folder_path):
        old_path = os.path.join(folder_path, filename)
        if os.path.isdir(old_path):
            continue

        new_name = filename
        if re.search(r"_cover", new_name, re.IGNORECASE):
            new_name = re.sub(r"_cover", "", new_name, flags=re.IGNORECASE)
        if new_name.endswith(".PNG"):
            new_name = new_name[:-4] + ".png"

        if new_name != filename:
            new_path = os.path.join(folder_path, new_name)
            os.rename(old_path, new_path)
            renamed.append({"old": filename, "new": new_name})

    return jsonify({"success": True, "count": len(renamed), "details": renamed})


@app.route("/api/generate_css", methods=["POST"])
def generate_css():
    data = request.json
    folder_path = data.get("path")
    jira_ticket = data.get("ticket", "NO-TICKET")

    if not folder_path or not os.path.exists(folder_path):
        return jsonify({"success": False, "message": "Invalid path"}), 400

    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"}
    created_files = []

    for filename in os.listdir(folder_path):
        name, ext = os.path.splitext(filename)
        if ext.lower() in image_extensions:
            css_filename = f"{name}.css"
            css_path = os.path.join(folder_path, css_filename)

            css_content = f"""/* Auto-generated CSS for cover: {filename} */
/* Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} */
/* Mantis Ticket: {jira_ticket} */

div.ref .mixed-citation .source {{ font-style: italic !important; }}
div.ref .mixed-citation .etal {{ font-style: italic !important; }}
div.ref .mixed-citation .volume {{ font-weight: bold !important; }}
div.ref .mixed-citation .year {{ font-weight: bold !important; }}
"""
            with open(css_path, "w", encoding="utf-8") as f:
                f.write(css_content)
            created_files.append(css_filename)

    # Master file
    if created_files:
        master_path = os.path.join(folder_path, "covers-master.css")
        with open(master_path, "w", encoding="utf-8") as f:
            f.write(f"/* Master CSS - Imports {len(created_files)} files */\n")
            for f_name in created_files:
                f.write(f"@import url('./{f_name}');\n")

    return jsonify({"success": True, "count": len(created_files)})


@app.route("/api/merge_xml", methods=["POST"])
def merge_xml():
    data = request.json
    folder_path = data.get("path")
    prefix = data.get("prefix", "YA")

    if not folder_path or not os.path.exists(folder_path):
        return jsonify({"success": False, "message": "Invalid path"}), 400

    output_file = os.path.join(folder_path, "combined_output.xml")
    copy_by_value = f"{prefix}_{datetime.now().strftime('%d_%b_%y')}"

    combined_root = ET.Element("CombinedConfigs")
    processed = 0

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".xml") and filename != "combined_output.xml":
            file_path = os.path.join(folder_path, filename)
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                root.set("copy-by", copy_by_value)
                combined_root.append(root)
                processed += 1
            except:
                continue

    if processed > 0:
        combined_tree = ET.ElementTree(combined_root)
        combined_tree.write(output_file, encoding="utf-8", xml_declaration=True)
        return jsonify({"success": True, "processed": processed, "file": output_file})

    return jsonify({"success": False, "message": "No XML files found to merge"})


if __name__ == "__main__":
    app.run(debug=True, port=5001)

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import sys
import json
import threading
import shutil
from pymongo import MongoClient
from datetime import datetime


class DataTransferTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent)
        self.process = None
        self._build_ui()

    def _build_ui(self):
        main_container = tk.Frame(self, bg="#1e293b", padx=30, pady=30)
        main_container.pack(fill="both", expand=True)

        tk.Label(
            main_container,
            text="OCI FILE DOWNLOAD & MONGO INSERT",
            font=("Segoe UI", 18, "bold"),
            fg="#10b981",
            bg="#1e293b",
        ).pack(pady=(0, 20))

        # OCI File Download Section
        download_frame = tk.LabelFrame(
            main_container,
            text="OCI File Download",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 12, "bold"),
            padx=20,
            pady=20,
        )
        download_frame.pack(fill="x", pady=(0, 20))

        tk.Label(
            download_frame,
            text="UniqueId:",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        self.unique_id_var = tk.StringVar()
        self.unique_id_entry = tk.Entry(
            download_frame,
            textvariable=self.unique_id_var,
            bg="#334155",
            fg="white",
            border=0,
            font=("Segoe UI", 11),
            width=40,
        )
        self.unique_id_entry.pack(anchor="w", pady=(5, 15), ipady=5)

        btn_row = tk.Frame(download_frame, bg="#1e293b")
        btn_row.pack(anchor="w", pady=(0, 10))

        self.download_btn = tk.Button(
            btn_row,
            text="Download from OCI",
            command=self._download_files,
            bg="#4f46e5",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            border=0,
            padx=20,
            pady=10,
        )
        self.download_btn.pack(side="left", padx=(0, 10))

        self.cancel_btn = tk.Button(
            btn_row,
            text="Cancel",
            command=self._cancel_download,
            bg="#ef4444",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            border=0,
            padx=20,
            pady=10,
            state="disabled",
        )
        self.cancel_btn.pack(side="left")

        tk.Label(
            download_frame,
            text="Destination: C:/_IMPACT/_LOCAL_FILES/IMPACT/{UniqueId}",
            bg="#1e293b",
            fg="#64748b",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(5, 0))

        tk.Label(
            download_frame,
            text="After download: Files moved to C:/_IMPACT/_LOCAL_FILES/{UniqueId}",
            bg="#1e293b",
            fg="#64748b",
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        # Download output - Console style
        console_frame = tk.Frame(download_frame, bg="#0d1117")
        console_frame.pack(fill="x", pady=(10, 0))

        tk.Label(
            console_frame,
            text="Console Output:",
            bg="#0d1117",
            fg="#64748b",
            font=("Consolas", 9),
            anchor="w",
        ).pack(fill="x", padx=5, pady=(0, 2))

        self.download_log = tk.Text(
            console_frame,
            bg="#0d1117",
            fg="#10b981",
            border=0,
            font=("Consolas", 9),
            height=8,
        )
        self.download_log.pack(fill="x", padx=5, pady=(0, 5))

        # MongoDB Insert Section
        mongo_frame = tk.LabelFrame(
            main_container,
            text="MongoDB Insert (rfilelist)",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 12, "bold"),
            padx=20,
            pady=20,
        )
        mongo_frame.pack(fill="both", expand=True)

        tk.Label(
            mongo_frame,
            text="JSON Record:",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        self.json_text = tk.Text(
            mongo_frame,
            bg="#0d1117",
            fg="#94a3b8",
            border=0,
            font=("Consolas", 10),
            height=10,
            insertbackground="white",
        )
        self.json_text.pack(fill="both", expand=True, pady=(5, 10))
        self.json_text.insert(
            "1.0",
            '{\n  "uniqueId": "YOUR_UNIQUE_ID",\n  "filename": "example.pdf",\n  "status": "pending"\n}',
        )

        mongo_btn_row = tk.Frame(mongo_frame, bg="#1e293b")
        mongo_btn_row.pack(fill="x", pady=(0, 10))

        self.validate_btn = tk.Button(
            mongo_btn_row,
            text="Validate JSON",
            command=self._validate_json,
            bg="#f59e0b",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            border=0,
            padx=20,
            pady=10,
        )
        self.validate_btn.pack(side="left", padx=(0, 10))

        self.insert_btn = tk.Button(
            mongo_btn_row,
            text="Insert Record (status=active)",
            command=self._insert_record,
            bg="#10b981",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            border=0,
            padx=20,
            pady=10,
        )
        self.insert_btn.pack(side="left")

        self.mongo_status = tk.Label(
            mongo_frame, text="", bg="#1e293b", fg="#10b981", font=("Segoe UI", 10)
        )
        self.mongo_status.pack(anchor="e")

    def _log(self, message):
        self.download_log.insert(tk.END, f"{message}\n")
        self.download_log.see(tk.END)
        self.download_log.update_idletasks()

    def _download_files(self):
        unique_id = self.unique_id_var.get().strip()
        if not unique_id:
            messagebox.showwarning("Input Required", "Please enter a UniqueId")
            return

        self.download_btn.config(state="disabled", text="Downloading...")
        self.cancel_btn.config(state="normal")
        self.download_log.delete("1.0", tk.END)

        self._log(
            f"[{datetime.now().strftime('%H:%M:%S')}] Downloading files for: {unique_id}"
        )
        self._log(
            f"[{datetime.now().strftime('%H:%M:%S')}] Command: oci os object bulk-download --bucket-name bucket-impact --prefix IMPACT/{unique_id} --dest-dir C:/_IMPACT/_LOCAL_FILES"
        )
        self._log("-" * 60)

        self.thread = threading.Thread(
            target=self._run_download, args=(unique_id,), daemon=True
        )
        self.thread.start()

    def _cancel_download(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self._log(
                f"\n[{datetime.now().strftime('%H:%M:%S')}] [CANCELLED] Download cancelled by user."
            )
            self._reset_buttons()
        else:
            self._log(
                f"\n[{datetime.now().strftime('%H:%M:%S')}] No active download to cancel."
            )

    def _reset_buttons(self):
        self.download_btn.config(state="normal", text="Download from OCI")
        self.cancel_btn.config(state="disabled")

    def _run_download(self, unique_id):
        dest_dir = "C:/_IMPACT/_LOCAL_FILES"
        os.makedirs(dest_dir, exist_ok=True)

        command = [
            "oci",
            "os",
            "object",
            "bulk-download",
            "--bucket-name",
            "bucket-impact",
            "--prefix",
            f"IMPACT/{unique_id}",
            "--dest-dir",
            dest_dir,
        ]

        try:
            self._log(
                f"[{datetime.now().strftime('%H:%M:%S')}] Starting download process..."
            )
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW
                if sys.platform == "win32"
                else 0,
            )

            for line in iter(self.process.stdout.readline, ""):
                if not self.process or self.process.poll() is not None:
                    break
                self._log(line.rstrip())

            self.process.wait()
            result = self.process
            returncode = result.returncode

            self._log("-" * 60)

            if returncode == 0:
                self._log(
                    f"[{datetime.now().strftime('%H:%M:%S')}] [SUCCESS] Download completed!"
                )
                self._move_downloaded_folder(unique_id)
            else:
                self._log(
                    f"[{datetime.now().strftime('%H:%M:%S')}] [FAILED] Download failed with code: {returncode}"
                )
        except Exception as e:
            self._log(f"\n[{datetime.now().strftime('%H:%M:%S')}] [ERROR] {str(e)}")
        finally:
            self.process = None
            self.after(100, self._reset_buttons)

    def _move_downloaded_folder(self, unique_id):
        source_path = f"C:/_IMPACT/_LOCAL_FILES/IMPACT/{unique_id}"
        dest_path = f"C:/_IMPACT/_LOCAL_FILES/{unique_id}"

        self._log(
            f"\n[{datetime.now().strftime('%H:%M:%S')}] Moving folder to final location..."
        )
        self._log(f"[{datetime.now().strftime('%H:%M:%S')}] Source: {source_path}")
        self._log(f"[{datetime.now().strftime('%H:%M:%S')}] Destination: {dest_path}")

        try:
            if os.path.exists(dest_path):
                self._log(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Destination exists, removing old folder..."
                )
                shutil.rmtree(dest_path)

            if os.path.exists(source_path):
                shutil.move(source_path, dest_path)
                self._log(
                    f"[{datetime.now().strftime('%H:%M:%S')}] [SUCCESS] Files moved to: {dest_path}"
                )

                file_count = sum(len(files) for _, _, files in os.walk(dest_path))
                self._log(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Total files: {file_count}"
                )
            else:
                self._log(
                    f"[{datetime.now().strftime('%H:%M:%S')}] [WARNING] Source folder not found: {source_path}"
                )
        except Exception as e:
            self._log(
                f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] Failed to move folder: {str(e)}"
            )

    def _validate_json(self):
        json_str = self.json_text.get("1.0", tk.END).strip()
        if not json_str:
            messagebox.showwarning("Input Required", "Please enter a JSON record")
            return

        try:
            parsed = json.loads(json_str)

            signoff_fields = ["signoff", "signOff", "signedOff", "approved", "approval"]
            has_signoff = any(field in parsed for field in signoff_fields)

            if has_signoff:
                signoff_value = None
                for field in signoff_fields:
                    if field in parsed:
                        signoff_value = parsed[field]
                        break

                if signoff_value:
                    self._log(
                        f"\n[{datetime.now().strftime('%H:%M:%S')}] [VALIDATE] Signoff detected: {signoff_value}"
                    )
                    self._log(
                        f"[{datetime.now().strftime('%H:%M:%S')}] [VALIDATE] Status will be set to: active"
                    )

            self._log(
                f"\n[{datetime.now().strftime('%H:%M:%S')}] [VALIDATE] JSON is valid!"
            )
            self._log(
                f"[{datetime.now().strftime('%H:%M:%S')}] [VALIDATE] Fields: {list(parsed.keys())}"
            )

            self.mongo_status.config(text="JSON Valid", fg="#10b981")
            messagebox.showinfo(
                "Validation",
                "JSON is valid!"
                + (
                    " Signoff detected - will set status to active."
                    if has_signoff
                    else ""
                ),
            )

        except json.JSONDecodeError as e:
            self._log(
                f"\n[{datetime.now().strftime('%H:%M:%S')}] [VALIDATE ERROR] {str(e)}"
            )
            self.mongo_status.config(text="Invalid JSON", fg="#ef4444")
            messagebox.showerror("Invalid JSON", f"JSON parse error: {e}")

    def _insert_record(self):
        json_str = self.json_text.get("1.0", tk.END).strip()
        if not json_str:
            messagebox.showwarning("Input Required", "Please enter a JSON record")
            return

        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as e:
            messagebox.showerror("Invalid JSON", f"JSON parse error: {e}")
            return

        signoff_fields = ["signoff", "signOff", "signedOff", "approved", "approval"]
        has_signoff = any(field in parsed for field in signoff_fields)
        status_to_set = "active" if has_signoff else parsed.get("status", "active")

        try:
            client = MongoClient("mongodb://localhost:27017/")
            db = client["impact_db"]
            collection = db["rfilelist"]

            doc = {
                **parsed,
                "status": status_to_set,
                "createdAt": datetime.now().isoformat(),
            }

            self._log(
                f"\n[{datetime.now().strftime('%H:%M:%S')}] [MONGO] Inserting record..."
            )
            self._log(
                f"[{datetime.now().strftime('%H:%M:%S')}] [MONGO] Collection: impact_db.rfilelist"
            )
            self._log(
                f"[{datetime.now().strftime('%H:%M:%S')}] [MONGO] Status: {status_to_set}"
                + (" (auto-set from signoff)" if has_signoff else "")
            )

            result = collection.insert_one(doc)
            client.close()

            self._log(
                f"[{datetime.now().strftime('%H:%M:%S')}] [SUCCESS] Inserted ID: {result.inserted_id}"
            )

            self.mongo_status.config(
                text=f"Inserted ID: {result.inserted_id}", fg="#10b981"
            )
            messagebox.showinfo(
                "Success", f"Record inserted with ID: {result.inserted_id}"
            )
        except Exception as e:
            self._log(f"[{datetime.now().strftime('%H:%M:%S')}] [MONGO ERROR] {str(e)}")
            self.mongo_status.config(text="Insert failed", fg="#ef4444")
            messagebox.showerror("MongoDB Error", str(e))

from __future__ import annotations

import queue
import socket
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import messagebox, ttk

import requests
import uvicorn

from core.run_history import RunHistoryStore

from .service.app import app as metadata_harvester_app

DEFAULT_PORT = 7100


class MetadataHarvesterTab(ttk.Frame):
    history_tool_id = "metadata_harvester"
    history_tool_label = "Metadata Harvester"

    def __init__(self, parent):
        super().__init__(parent)
        self.server = None
        self.server_thread = None
        self._stopping = False
        self._ui_polling = True
        self._ui_queue = queue.SimpleQueue()
        self.last_service_url = ""
        self._poll_stats_active = False
        self._build_ui()
        self.after(50, self._drain_ui_queue)

    def _build_ui(self):
        main_container = tk.Frame(self, bg="#1e293b", padx=30, pady=30)
        main_container.pack(fill="both", expand=True)

        tk.Label(
            main_container,
            text="METADATA HARVESTER",
            font=("Segoe UI", 18, "bold"),
            fg="#10b981",
            bg="#1e293b",
        ).pack(pady=(0, 10))

        desc = (
            "Runs two embedded harvesters behind one local API: a paid-token "
            "Crossref DOI/affiliation harvester, and a free ROR + OpenAlex "
            "alphabetical geo harvester. Start the service, then trigger "
            "either harvest below."
        )
        tk.Label(
            main_container, text=desc, bg="#1e293b", fg="#94a3b8",
            font=("Segoe UI", 10), wraplength=700, justify="left",
        ).pack(pady=(0, 20))

        # --- Service controls ---
        service_frame = tk.Frame(main_container, bg="#1e293b")
        service_frame.pack(fill="x", pady=(0, 15))

        tk.Label(service_frame, text="Service Port:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10)).pack(side="left")
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        self.port_entry = tk.Entry(service_frame, textvariable=self.port_var, bg="#334155", fg="white", border=0, font=("Segoe UI", 11), width=8)
        self.port_entry.pack(side="left", padx=(8, 20), ipady=4)

        self.status_circle = tk.Canvas(service_frame, width=18, height=18, bg="#1e293b", highlightthickness=0)
        self.status_circle.pack(side="left", padx=(0, 8))
        self.circle = self.status_circle.create_oval(2, 2, 16, 16, fill="#ef4444")

        self.status_var = tk.StringVar(value="Service Stopped")
        tk.Label(service_frame, textvariable=self.status_var, bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 10, "bold")).pack(side="left")

        btn_frame = tk.Frame(main_container, bg="#1e293b")
        btn_frame.pack(fill="x", pady=(0, 20))

        self.start_btn = tk.Button(
            btn_frame, text="START SERVICE", command=self._start_service,
            bg="#10b981", fg="white", font=("Segoe UI", 11, "bold"), border=0, padx=20, pady=10,
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        self.stop_btn = tk.Button(
            btn_frame, text="STOP SERVICE", command=self._stop_service,
            bg="#ef4444", fg="white", font=("Segoe UI", 11, "bold"), border=0, padx=20, pady=10, state="disabled",
        )
        self.stop_btn.pack(side="left", padx=(0, 10))

        self.open_btn = tk.Button(
            btn_frame, text="OPEN SWAGGER IN BROWSER", command=self._open_browser,
            bg="#4f46e5", fg="white", font=("Segoe UI", 10, "bold"), border=0, padx=15, pady=10, state="disabled",
        )
        self.open_btn.pack(side="left")

        # --- Crossref section ---
        crossref_frame = tk.LabelFrame(
            main_container, text="Crossref (paid token)", bg="#1e293b", fg="#94a3b8",
            font=("Segoe UI", 12, "bold"), padx=20, pady=15,
        )
        crossref_frame.pack(fill="x", pady=(0, 15))

        row1 = tk.Frame(crossref_frame, bg="#1e293b")
        row1.pack(fill="x", pady=(0, 8))
        tk.Label(row1, text="Crossref Token:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10), width=16, anchor="w").pack(side="left")
        self.crossref_token_var = tk.StringVar()
        tk.Entry(row1, textvariable=self.crossref_token_var, show="*", bg="#334155", fg="white", border=0, font=("Segoe UI", 10), width=40).pack(side="left", ipady=4)

        row2 = tk.Frame(crossref_frame, bg="#1e293b")
        row2.pack(fill="x", pady=(0, 8))
        tk.Label(row2, text="Contact Email:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10), width=16, anchor="w").pack(side="left")
        self.crossref_email_var = tk.StringVar()
        tk.Entry(row2, textvariable=self.crossref_email_var, bg="#334155", fg="white", border=0, font=("Segoe UI", 10), width=40).pack(side="left", ipady=4)

        row3 = tk.Frame(crossref_frame, bg="#1e293b")
        row3.pack(fill="x", pady=(0, 8))
        tk.Label(row3, text="Rows/Request:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10), width=16, anchor="w").pack(side="left")
        self.crossref_rows_var = tk.StringVar(value="100")
        tk.Entry(row3, textvariable=self.crossref_rows_var, bg="#334155", fg="white", border=0, font=("Segoe UI", 10), width=10).pack(side="left", padx=(0, 20), ipady=4)
        tk.Label(row3, text="Max Records:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10)).pack(side="left")
        self.crossref_max_var = tk.StringVar(value="1000")
        tk.Entry(row3, textvariable=self.crossref_max_var, bg="#334155", fg="white", border=0, font=("Segoe UI", 10), width=10).pack(side="left", padx=(8, 0), ipady=4)

        self.crossref_start_btn = tk.Button(
            crossref_frame, text="Start Crossref Harvest", command=self._start_crossref_harvest,
            bg="#f59e0b", fg="white", font=("Segoe UI", 10, "bold"), border=0, padx=15, pady=8, state="disabled",
        )
        self.crossref_start_btn.pack(anchor="w", pady=(5, 0))

        # --- Geo section ---
        geo_frame = tk.LabelFrame(
            main_container, text="ROR + OpenAlex (free)", bg="#1e293b", fg="#94a3b8",
            font=("Segoe UI", 12, "bold"), padx=20, pady=15,
        )
        geo_frame.pack(fill="x", pady=(0, 15))

        grow1 = tk.Frame(geo_frame, bg="#1e293b")
        grow1.pack(fill="x", pady=(0, 8))
        tk.Label(grow1, text="Contact Email:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10), width=16, anchor="w").pack(side="left")
        self.geo_email_var = tk.StringVar()
        tk.Entry(grow1, textvariable=self.geo_email_var, bg="#334155", fg="white", border=0, font=("Segoe UI", 10), width=40).pack(side="left", ipady=4)

        grow2 = tk.Frame(geo_frame, bg="#1e293b")
        grow2.pack(fill="x", pady=(0, 8))
        tk.Label(grow2, text="Workers:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10), width=16, anchor="w").pack(side="left")
        self.geo_workers_var = tk.StringVar(value="6")
        tk.Entry(grow2, textvariable=self.geo_workers_var, bg="#334155", fg="white", border=0, font=("Segoe UI", 10), width=10).pack(side="left", ipady=4)

        self.geo_start_btn = tk.Button(
            geo_frame, text="Start Geo Harvest", command=self._start_geo_harvest,
            bg="#0ea5e9", fg="white", font=("Segoe UI", 10, "bold"), border=0, padx=15, pady=8, state="disabled",
        )
        self.geo_start_btn.pack(anchor="w", pady=(5, 0))

        # --- Log ---
        tk.Label(main_container, text="Log:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9)).pack(anchor="w")
        self.log_text = tk.Text(main_container, bg="#0d1117", fg="#94a3b8", border=0, font=("Consolas", 9), height=10)
        self.log_text.pack(fill="both", expand=True, pady=5)

    # ------------------------------------------------------------------
    # Service lifecycle
    # ------------------------------------------------------------------
    def _start_service(self):
        if self.server_thread and self.server_thread.is_alive():
            return

        try:
            port = int(self.port_var.get().strip())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Port", "Enter a port between 1 and 65535.")
            return

        if not self._port_available(port):
            messagebox.showerror("Port Unavailable", f"Port {port} is already in use.")
            self._set_status("Service Start Failed", "#ef4444")
            return

        self._stopping = False
        self.log_text.delete("1.0", tk.END)
        self._log(f"Starting Metadata Harvester service on http://127.0.0.1:{port}")
        self._set_controls(starting=True)
        self._set_status("Service Starting...", "#f59e0b")

        config = uvicorn.Config(
            metadata_harvester_app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            access_log=False,
        )
        self.server = uvicorn.Server(config)
        self.server_thread = threading.Thread(
            target=self._run_server, name="impact-metadata-harvester-service", daemon=True
        )
        self.server_thread.start()
        threading.Thread(
            target=self._check_health, args=(port,), name="impact-metadata-harvester-health", daemon=True
        ).start()

    @staticmethod
    def _port_available(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return True
            except OSError:
                return False

    def _run_server(self):
        try:
            self.server.run()
        except Exception as exc:
            self._schedule(self._handle_server_failure, str(exc))
        finally:
            if not self._stopping:
                self._schedule(self._handle_server_exit)

    def _check_health(self, port):
        url = f"http://127.0.0.1:{port}/health"
        for _attempt in range(30):
            if self._stopping or not self.server_thread or not self.server_thread.is_alive():
                return
            try:
                response = requests.get(url, timeout=0.5)
                if response.status_code == 200:
                    self._schedule(self._handle_server_ready)
                    return
            except requests.RequestException:
                pass
            time.sleep(0.2)
        self._schedule(self._handle_server_failure, "Health check timed out.")
        if self.server:
            self.server.should_exit = True

    def _stop_service(self):
        if self._stopping or not self.server_thread or not self.server_thread.is_alive():
            self._handle_server_exit()
            return
        self._stopping = True
        self._set_status("Service Stopping...", "#f59e0b")
        self.stop_btn.config(state="disabled")
        self.open_btn.config(state="disabled")
        self._log("Stopping Metadata Harvester service...")
        if self.server:
            self.server.should_exit = True
        threading.Thread(target=self._wait_for_stop, daemon=True).start()

    def _wait_for_stop(self):
        if self.server_thread:
            self.server_thread.join(timeout=5)
        self._schedule(self._handle_server_exit)

    def _handle_server_ready(self):
        if self._stopping:
            return
        port = self.port_var.get().strip()
        self.last_service_url = f"http://127.0.0.1:{port}/docs"
        self._set_status("Service Running", "#10b981")
        self.start_btn.config(text="SERVICE RUNNING", state="disabled")
        self.stop_btn.config(state="normal")
        self.open_btn.config(state="normal")
        self.crossref_start_btn.config(state="normal")
        self.geo_start_btn.config(state="normal")
        self._log("Metadata Harvester service is ready.")
        self._record_history("service_ready")

    def _handle_server_failure(self, detail):
        self._log(f"Service failed: {detail}")
        self._set_status("Service Start Failed", "#ef4444")
        if self.server and self.server_thread and self.server_thread.is_alive():
            self._stopping = True
            self.stop_btn.config(state="disabled")
            self.open_btn.config(state="disabled")
            self.server.should_exit = True
            threading.Thread(target=self._wait_for_stop, daemon=True).start()
        else:
            self._handle_server_exit()

    def _handle_server_exit(self):
        was_active = self.server is not None or self._stopping
        self.server = None
        self.server_thread = None
        self._stopping = False
        self._set_status("Service Stopped", "#ef4444")
        self._reset_controls()
        if was_active:
            self._log("Metadata Harvester service stopped.")

    def _set_controls(self, starting=False):
        self.port_entry.config(state="disabled")
        self.start_btn.config(text="STARTING..." if starting else "SERVICE RUNNING", state="disabled")
        self.stop_btn.config(state="normal")
        self.open_btn.config(state="disabled")

    def _reset_controls(self):
        self.port_entry.config(state="normal")
        self.start_btn.config(text="START SERVICE", state="normal")
        self.stop_btn.config(state="disabled")
        self.open_btn.config(state="disabled")
        self.crossref_start_btn.config(state="disabled")
        self.geo_start_btn.config(state="disabled")

    def _set_status(self, text, color):
        self.status_var.set(text)
        self.status_circle.itemconfig(self.circle, fill=color)

    def _open_browser(self):
        port = self.port_var.get().strip()
        self.last_service_url = f"http://127.0.0.1:{port}/docs"
        self._record_history("open_swagger")
        webbrowser.open(self.last_service_url)

    def _log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def _schedule(self, callback, *args):
        self._ui_queue.put((callback, args))

    def _drain_ui_queue(self):
        try:
            while True:
                callback, args = self._ui_queue.get_nowait()
                try:
                    callback(*args)
                except Exception as exc:
                    self._log(f"UI update failed: {exc}")
        except queue.Empty:
            pass

        if self._ui_polling:
            try:
                self.after(50, self._drain_ui_queue)
            except tk.TclError:
                pass

    def shutdown(self, wait=False):
        """Stop the embedded server safely when the application closes."""
        thread = self.server_thread
        self._ui_polling = False
        self._poll_stats_active = False
        self._stopping = True
        if self.server:
            self.server.should_exit = True
        if wait and thread and thread.is_alive():
            thread.join(timeout=5)

    # ------------------------------------------------------------------
    # Harvest triggers
    # ------------------------------------------------------------------
    def _service_running(self) -> bool:
        return bool(
            self.server_thread
            and self.server_thread.is_alive()
            and self.status_var.get() == "Service Running"
        )

    def _start_crossref_harvest(self):
        if not self._service_running():
            messagebox.showwarning("Service Not Running", "Start the service first.")
            return

        token = self.crossref_token_var.get().strip()
        email = self.crossref_email_var.get().strip()
        if not token:
            messagebox.showwarning("Input Required", "Please enter a Crossref Plus API token.")
            return
        if not email:
            messagebox.showwarning("Input Required", "Please enter a contact email.")
            return

        try:
            rows = int(self.crossref_rows_var.get().strip() or 100)
            max_records = int(self.crossref_max_var.get().strip() or 1000)
        except ValueError:
            messagebox.showerror("Invalid Input", "Rows/Request and Max Records must be numbers.")
            return

        port = self.port_var.get().strip()
        payload = {
            "crossref_token": token,
            "user_agent_email": email,
            "rows_per_request": rows,
            "max_total_records": max_records,
        }
        # GOTCHA: never log or record the token itself -- only non-secret fields.
        self._log(f"Starting Crossref harvest (email={email}, rows={rows}, max={max_records})")
        threading.Thread(
            target=self._post_harvest,
            args=(f"http://127.0.0.1:{port}/crossref/harvest/start", payload, "crossref"),
            daemon=True,
        ).start()
        self._record_history(
            "start_crossref_harvest",
            params={"email": email, "rows_per_request": rows, "max_total_records": max_records},
        )

    def _start_geo_harvest(self):
        if not self._service_running():
            messagebox.showwarning("Service Not Running", "Start the service first.")
            return

        email = self.geo_email_var.get().strip()
        if not email:
            messagebox.showwarning("Input Required", "Please enter a contact email.")
            return

        try:
            workers = int(self.geo_workers_var.get().strip() or 6)
        except ValueError:
            messagebox.showerror("Invalid Input", "Workers must be a number.")
            return

        port = self.port_var.get().strip()
        payload = {"contact_email": email, "num_workers": workers}
        self._log(f"Starting ROR + OpenAlex geo harvest (email={email}, workers={workers})")
        threading.Thread(
            target=self._post_harvest,
            args=(f"http://127.0.0.1:{port}/geo/harvest/start-all", payload, "geo"),
            daemon=True,
        ).start()
        self._record_history("start_geo_harvest", params={"email": email, "num_workers": workers})
        self._start_stats_polling(port)

    def _post_harvest(self, url, payload, label):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code >= 400:
                self._schedule(self._log, f"[{label}] harvest request failed: {response.status_code} {response.text}")
            else:
                self._schedule(self._log, f"[{label}] harvest queued: {response.json()}")
        except requests.RequestException as exc:
            self._schedule(self._log, f"[{label}] harvest request error: {exc}")

    def _start_stats_polling(self, port):
        if self._poll_stats_active:
            return
        self._poll_stats_active = True
        threading.Thread(target=self._poll_stats, args=(port,), daemon=True).start()

    def _poll_stats(self, port):
        last_total = -1
        for _ in range(60):  # ~3 minutes at 3s intervals
            if self._stopping or not self._service_running():
                break
            try:
                response = requests.get(f"http://127.0.0.1:{port}/geo/stats", timeout=5)
                if response.status_code == 200:
                    rows = response.json()
                    total = sum(row["count"] for row in rows)
                    if total != last_total:
                        self._schedule(self._log, f"[geo] total records so far: {total}")
                        last_total = total
            except requests.RequestException:
                pass
            time.sleep(3)
        self._poll_stats_active = False

    # ------------------------------------------------------------------
    # Run History
    # ------------------------------------------------------------------
    def _history_entry(self, action: str, params: dict | None = None) -> dict:
        port = self.port_var.get().strip()
        service_url = self.last_service_url or f"http://127.0.0.1:{port}/docs"
        return {
            "tool_id": self.history_tool_id,
            "tool_label": self.history_tool_label,
            "action": action,
            "summary": f"{action} | port {port}",
            "source_path": "",
            "output_dir": "",
            "report_path": service_url,
            "params": {"port": port, "service_url": service_url, **(params or {})},
        }

    def _record_history(self, action: str, params: dict | None = None) -> None:
        # GOTCHA: params must never include the Crossref token -- see _start_crossref_harvest.
        RunHistoryStore.add_entry(self._history_entry(action, params))

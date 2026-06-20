import queue
import socket
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

import requests
import uvicorn

from core.run_history import RunHistoryStore
from search_service.app.app import app as search_app


class SearchTab(ttk.Frame):
    history_tool_id = "search"
    history_tool_label = "Search"

    def __init__(self, parent):
        super().__init__(parent)
        self.server = None
        self.server_thread = None
        self._stopping = False
        self._ui_polling = True
        self._ui_queue = queue.SimpleQueue()
        self.last_service_url = ""
        self._build_ui()
        self.after(50, self._drain_ui_queue)

    def _build_ui(self):
        main_container = tk.Frame(self, bg="#1e293b", padx=30, pady=30)
        main_container.pack(fill="both", expand=True)

        tk.Label(
            main_container,
            text="DISTRIBUTED SEARCH SERVICE",
            font=("Segoe UI", 18, "bold"),
            fg="#10b981",
            bg="#1e293b",
        ).pack(pady=(0, 20))

        desc = (
            "Start the local search service, then use its browser interface to "
            "fetch, copy, and search IMPACT XML and HTML files."
        )
        tk.Label(
            main_container,
            text=desc,
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 10),
            wraplength=600,
            justify="left",
        ).pack(pady=(0, 30))

        tk.Label(
            main_container,
            text="Service Port:",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        self.port_var = tk.StringVar(value="7000")
        self.port_entry = tk.Entry(
            main_container,
            textvariable=self.port_var,
            bg="#334155",
            fg="white",
            border=0,
            font=("Segoe UI", 11),
            width=10,
        )
        self.port_entry.pack(anchor="w", pady=(5, 20), ipady=5)

        self.status_circle = tk.Canvas(
            main_container, width=20, height=20, bg="#1e293b", highlightthickness=0
        )
        self.status_circle.pack(pady=10)
        self.circle = self.status_circle.create_oval(2, 2, 18, 18, fill="#ef4444")

        self.status_var = tk.StringVar(value="Service Stopped")
        tk.Label(
            main_container,
            textvariable=self.status_var,
            bg="#1e293b",
            fg="#cbd5e1",
            font=("Segoe UI", 11, "bold"),
        ).pack()

        self.btn_frame = tk.Frame(main_container, bg="#1e293b")
        self.btn_frame.pack(pady=30)

        self.stop_btn = tk.Button(
            self.btn_frame,
            text="STOP SERVICE",
            command=self._stop_service,
            bg="#ef4444",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=15,
            pady=10,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=10)

        self.start_btn = tk.Button(
            self.btn_frame,
            text="START SEARCH SERVICE",
            command=self._start_service,
            bg="#10b981",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            border=0,
            padx=30,
            pady=12,
        )
        self.start_btn.pack(side="left", padx=10)

        self.open_btn = tk.Button(
            self.btn_frame,
            text="OPEN UI IN BROWSER",
            command=self._open_browser,
            bg="#4f46e5",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            border=0,
            padx=20,
            pady=12,
            state="disabled",
        )
        self.open_btn.pack(side="left", padx=10)

        tk.Label(
            main_container,
            text="Service Output:",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 9),
        ).pack(anchor="w")
        self.log_text = tk.Text(
            main_container,
            bg="#0d1117",
            fg="#94a3b8",
            border=0,
            font=("Consolas", 8),
            height=8,
        )
        self.log_text.pack(fill="both", expand=True, pady=5)

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
        self._log(f"Starting search service on http://127.0.0.1:{port}")
        self._set_controls(starting=True)
        self._set_status("Service Starting...", "#f59e0b")

        config = uvicorn.Config(
            search_app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            access_log=False,
        )
        self.server = uvicorn.Server(config)
        self.server_thread = threading.Thread(
            target=self._run_server, name="impact-search-service", daemon=True
        )
        self.server_thread.start()
        threading.Thread(
            target=self._check_health, args=(port,), name="impact-search-health", daemon=True
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
        self._log("Stopping search service...")
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
        self.last_service_url = f"http://127.0.0.1:{self.port_var.get().strip()}/ui"
        self._set_status("Service Running", "#10b981")
        self.start_btn.config(text="SERVICE RUNNING", state="disabled")
        self.stop_btn.config(state="normal")
        self.open_btn.config(state="normal")
        self._log("Search service is ready.")
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
            self._log("Search service stopped.")

    def _set_controls(self, starting=False):
        self.port_entry.config(state="disabled")
        self.start_btn.config(
            text="STARTING..." if starting else "SERVICE RUNNING", state="disabled"
        )
        self.stop_btn.config(state="normal")
        self.open_btn.config(state="disabled")

    def _reset_controls(self):
        self.port_entry.config(state="normal")
        self.start_btn.config(text="START SEARCH SERVICE", state="normal")
        self.stop_btn.config(state="disabled")
        self.open_btn.config(state="disabled")

    def _set_status(self, text, color):
        self.status_var.set(text)
        self.status_circle.itemconfig(self.circle, fill=color)

    def _open_browser(self):
        self.last_service_url = f"http://127.0.0.1:{self.port_var.get().strip()}/ui"
        self._record_history("open_ui")
        webbrowser.open(self.last_service_url)

    def _log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
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
        self._stopping = True
        if self.server:
            self.server.should_exit = True
        if wait and thread and thread.is_alive():
            thread.join(timeout=5)

    def _history_entry(self, action: str) -> dict:
        port = self.port_var.get().strip()
        service_url = self.last_service_url or f"http://127.0.0.1:{port}/ui"
        return {
            "tool_id": self.history_tool_id,
            "tool_label": self.history_tool_label,
            "action": action,
            "summary": f"{action} | port {port}",
            "source_path": "",
            "output_dir": "",
            "report_path": service_url,
            "params": {
                "port": port,
                "service_url": service_url,
            },
        }

    def _record_history(self, action: str) -> None:
        RunHistoryStore.add_entry(self._history_entry(action))

    def apply_history_entry(self, entry: dict) -> bool:
        params = entry.get("params", {})
        port = str(params.get("port", "")).strip() or str(entry.get("port", "")).strip()
        if port:
            self.port_var.set(port)
        service_url = str(params.get("service_url", "")).strip() or str(entry.get("report_path", "")).strip()
        if service_url:
            self.last_service_url = service_url
        return True

    def rerun_history_entry(self, entry: dict) -> bool:
        self.apply_history_entry(entry)
        action = str(entry.get("action", "")).strip()
        if action == "open_ui":
            if not (self.server_thread and self.server_thread.is_alive()):
                self._start_service()
            return True
        self._start_service()
        return True

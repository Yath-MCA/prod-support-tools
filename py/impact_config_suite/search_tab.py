import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import sys
import webbrowser
import threading
import time
import requests

class SearchTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent)
        self.process = None
        self._build_ui()

    def _build_ui(self):
        main_container = tk.Frame(self, bg="#1e293b", padx=30, pady=30)
        main_container.pack(fill="both", expand=True)

        # Header
        tk.Label(main_container, text="DISTRIBUTED SEARCH SERVICE", font=("Segoe UI", 18, "bold"), fg="#10b981", bg="#1e293b").pack(pady=(0, 20))

        # Description
        desc = "The Search Service provides a powerful web interface for searching through XML and HTML configuration files across the entire project root. It uses FastAPI for high performance."
        tk.Label(main_container, text=desc, bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10), wraplength=500, justify="left").pack(pady=(0, 30))

        # Configuration
        tk.Label(main_container, text="Service Port:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10)).pack(anchor="w")
        self.port_var = tk.StringVar(value="7000")
        self.port_entry = tk.Entry(main_container, textvariable=self.port_var, bg="#334155", fg="white", border=0, font=("Segoe UI", 11), width=10)
        self.port_entry.pack(anchor="w", pady=(5, 20), ipady=5)

        # Controls
        self.status_circle = tk.Canvas(main_container, width=20, height=20, bg="#1e293b", highlightthickness=0)
        self.status_circle.pack(pady=10)
        self.circle = self.status_circle.create_oval(2, 2, 18, 18, fill="#ef4444")
        
        self.status_var = tk.StringVar(value="Service Stopped")
        tk.Label(main_container, textvariable=self.status_var, bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 11, "bold")).pack()

        self.btn_frame = tk.Frame(main_container, bg="#1e293b")
        self.btn_frame.pack(pady=30)

        self.start_btn = tk.Button(self.btn_frame, text="▶️ START SEARCH SERVICE", command=self._toggle_service, 
                             bg="#10b981", fg="white", font=("Segoe UI", 12, "bold"), border=0, padx=30, pady=12)
        self.start_btn.pack(side="left", padx=10)

        self.open_btn = tk.Button(self.btn_frame, text="🌐 OPEN UI IN BROWSER", command=self._open_browser, 
                             bg="#4f46e5", fg="white", font=("Segoe UI", 10, "bold"), border=0, padx=20, pady=12, state="disabled")
        self.open_btn.pack(side="left", padx=10)

        # Log output
        tk.Label(main_container, text="Service Output:", bg="#1e293b", fg="#475569", font=("Segoe UI", 9)).pack(anchor="w")
        self.log_text = tk.Text(main_container, bg="#0d1117", fg="#94a3b8", border=0, font=("Consolas", 8), height=8)
        self.log_text.pack(fill="both", expand=True, pady=5)

    def _toggle_service(self):
        if self.process is None:
            self._start_service()
        else:
            self._stop_service()

    def _start_service(self):
        port = self.port_var.get()
        self.start_btn.config(text="Stopping...", state="disabled")
        
        # Determine python executable
        python_exe = sys.executable
        
        # Command to run the search service
        # We need to make sure the working directory is the root so it can find search_service.app
        cmd = [python_exe, "-m", "uvicorn", "search_service.app.app:app", "--host", "127.0.0.1", "--port", str(port)]
        
        cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        try:
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, f"Starting service: {' '.join(cmd)}\n")
            
            self.process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            # Start a thread to read logs
            threading.Thread(target=self._read_logs, daemon=True).start()
            # Start a thread to check health
            threading.Thread(target=self._check_health, daemon=True).start()
            
            self.start_btn.config(text="⏹️ STOP SEARCH SERVICE", state="normal", bg="#ef4444")
            self.status_var.set("Service Starting...")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start service: {e}")
            self.start_btn.config(text="▶️ START SEARCH SERVICE", state="normal", bg="#10b981")
            self.process = None

    def _stop_service(self):
        if self.process:
            self.process.terminate()
            self.process = None
            self.status_circle.itemconfig(self.circle, fill="#ef4444")
            self.status_var.set("Service Stopped")
            self.start_btn.config(text="▶️ START SEARCH SERVICE", bg="#10b981")
            self.open_btn.config(state="disabled")
            self._log("Service terminated.")

    def _read_logs(self):
        if not self.process: return
        for line in iter(self.process.stdout.readline, ''):
            if not self.process: break
            self.log_text.insert(tk.END, line)
            self.log_text.see(tk.END)
        if self.process:
            self._stop_service()

    def _check_health(self):
        port = self.port_var.get()
        url = f"http://127.0.0.1:{port}/ui"
        retries = 10
        while retries > 0 and self.process:
            try:
                # Fast endpoint check (not necessarily /ui but root or similar)
                # Actually let's just try the /ui
                resp = requests.get(f"http://127.0.0.1:{port}", timeout=1)
                if resp.status_code < 500:
                    self.status_circle.itemconfig(self.circle, fill="#10b981")
                    self.status_var.set("Service Running")
                    self.open_btn.config(state="normal")
                    return
            except:
                pass
            time.sleep(1)
            retries -= 1
        
        if self.process:
            self.status_var.set("Service Start Timeout / Error")

    def _open_browser(self):
        port = self.port_var.get()
        webbrowser.open(f"http://127.0.0.1:{port}/ui")

    def _log(self, msg):
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)

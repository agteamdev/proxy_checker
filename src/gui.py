"""
Tkinter GUI for the proxy checker.

Single window, split into two columns via a resizable PanedWindow:
  - Left column ("Process"): settings, start/stop controls, progress bar,
    running log.
  - Right column ("Results"): a live-updating table with columns
    Flag | IP | Port | HTTPS, filled in as proxies are confirmed alive.

Only the standard library is used (tkinter), so no extra GUI dependency
is required beyond `requests` for the networking itself.
"""

import csv
import logging
import queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import config
from .checker import ProxyChecker

log = logging.getLogger(__name__)


class ProcessPanel(ttk.Frame):
    """Left-hand column: settings, controls, progress bar and log."""

    def __init__(self, master, on_start, on_stop):
        super().__init__(master, padding=10)

        settings = ttk.LabelFrame(self, text="Settings")
        settings.pack(fill="x", pady=(0, 10))

        ttk.Label(settings, text="Threads:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.threads_var = tk.IntVar(value=config.DEFAULT_THREADS)
        ttk.Spinbox(settings, from_=1, to=500, textvariable=self.threads_var, width=8).grid(
            row=0, column=1, padx=5, pady=5, sticky="w"
        )

        ttk.Label(settings, text="Timeout (s):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.timeout_var = tk.IntVar(value=config.DEFAULT_TIMEOUT)
        ttk.Spinbox(settings, from_=1, to=60, textvariable=self.timeout_var, width=8).grid(
            row=1, column=1, padx=5, pady=5, sticky="w"
        )

        controls = ttk.Frame(self)
        controls.pack(fill="x", pady=(0, 10))
        self.start_btn = ttk.Button(controls, text="Start", command=on_start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(controls, text="Stop", command=on_stop, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 5))

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status_var, wraplength=280).pack(anchor="w", pady=(0, 10))

        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, state="disabled", wrap="word")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

    def append_log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def set_running(self, running: bool):
        self.start_btn.configure(state="disabled" if running else "normal")
        self.stop_btn.configure(state="normal" if running else "disabled")


class ResultsPanel(ttk.Frame):
    """Right-hand column: live table of proxies confirmed alive."""

    def __init__(self, master):
        super().__init__(master, padding=10)

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 5))
        ttk.Label(header, text="Live proxies", font=("TkDefaultFont", 10, "bold")).pack(side="left")
        self.count_var = tk.StringVar(value="0 found")
        ttk.Label(header, textvariable=self.count_var).pack(side="right")

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = ("flag", "ip", "port", "https")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("flag", text="Flag")
        self.tree.heading("ip", text="IP")
        self.tree.heading("port", text="Port")
        self.tree.heading("https", text="HTTPS")
        self.tree.column("flag", width=50, anchor="center")
        self.tree.column("ip", width=140, anchor="center")
        self.tree.column("port", width=70, anchor="center")
        self.tree.column("https", width=90, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Button(self, text="Export CSV", command=self.export_csv).pack(fill="x", pady=(5, 0))

        self._rows = []  # raw data kept independent of widget state, for export

    def add_row(self, flag: str, ip: str, port: str, https_ok: bool):
        https_text = "HTTPS" if https_ok else "HTTP only"
        self.tree.insert("", "end", values=(flag, ip, port, https_text))
        self._rows.append((flag, ip, port, https_text))
        self.count_var.set(f"{len(self._rows)} found")

    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self._rows.clear()
        self.count_var.set("0 found")

    def export_csv(self):
        if not self._rows:
            messagebox.showinfo("Export", "No results to export yet.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="live_proxies.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Flag", "IP", "Port", "HTTPS"])
            writer.writerows(self._rows)
        messagebox.showinfo("Export", f"Saved {len(self._rows)} proxies to {path}")


class MainWindow(tk.Tk):
    """
    Single application window split into two columns:
    process/controls on the left, live results table on the right.
    """

    POLL_INTERVAL_MS = 100

    def __init__(self):
        super().__init__()
        self.title("Proxy Checker")
        self.geometry("900x520")
        self.minsize(760, 440)

        self.event_queue: "queue.Queue" = queue.Queue()
        self.checker: ProxyChecker | None = None

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        self.process_panel = ProcessPanel(paned, on_start=self.on_start, on_stop=self.on_stop)
        self.results_panel = ResultsPanel(paned)

        paned.add(self.process_panel, weight=1)
        paned.add(self.results_panel, weight=2)

        self.after(self.POLL_INTERVAL_MS, self._poll_queue)

    # -- button handlers --------------------------------------------------

    def on_start(self):
        self.process_panel.set_running(True)
        self.process_panel.progress["value"] = 0
        self.process_panel.status_var.set("Starting...")
        self.results_panel.clear()

        self.checker = ProxyChecker(
            threads=self.process_panel.threads_var.get(),
            timeout=self.process_panel.timeout_var.get(),
        )
        self.checker.start(on_event=self.event_queue.put)

    def on_stop(self):
        if self.checker:
            self.checker.stop()
        self.process_panel.status_var.set("Stopping (finishing in-flight checks)...")
        self.process_panel.stop_btn.configure(state="disabled")

    # -- queue polling (safe cross-thread UI updates) ----------------------

    def _poll_queue(self):
        try:
            while True:
                event = self.event_queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self.after(self.POLL_INTERVAL_MS, self._poll_queue)

    def _handle_event(self, event: dict):
        etype = event["type"]
        if etype == "status":
            self.process_panel.status_var.set(event["text"])
            self.process_panel.append_log(event["text"])
        elif etype == "progress":
            done, total = event["done"], event["total"]
            self.process_panel.progress["maximum"] = total
            self.process_panel.progress["value"] = done
            self.process_panel.status_var.set(f"Checked {done}/{total}")
        elif etype == "result":
            r = event["result"]
            self.results_panel.add_row(r.flag, r.ip, r.port, r.https)
        elif etype == "finished":
            self.process_panel.set_running(False)
            self.process_panel.status_var.set(
                f"Done in {event['elapsed']}s — {event['found']} live proxies found."
            )
            self.process_panel.append_log(
                f"Finished: {event['found']} live proxies saved to {config.RESULTS_CSV}"
            )


def run():
    logging.basicConfig(
        filename=config.LOG_FILE,
        filemode="w",
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.WARNING,
    )
    app = MainWindow()
    app.mainloop()

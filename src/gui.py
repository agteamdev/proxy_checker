"""
Tkinter GUI for the proxy checker.

Single window, split into two columns via a resizable PanedWindow:
  - Left column ("Process"): settings, start/stop controls, progress bar,
    running log.
  - Right column ("Results"): a live-updating, sortable, filterable table
    with a flag icon, row number, country code, IP, port, protocol,
    anonymity level and latency (ms) for every proxy confirmed alive.
    Right-click a row to copy its IP / IP:port / full row to the clipboard.

Only the standard library is used (tkinter), so no extra GUI dependency
is required beyond `requests` (with the `socks` extra) for the networking.
"""

import csv
import logging
import os
import queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import config
from .checker import ProxyChecker

log = logging.getLogger(__name__)

# Path to the app icon, relative to the project root (works both when run
# from source and when bundled by PyInstaller, via sys._MEIPASS).
def _icon_path() -> str:
    import sys
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "assets", "icon_64.png")

# Column ids -> (header text, whether to sort numerically)
COLUMNS = {
    "country": ("Country", False),
    "ip": ("IP", False),
    "port": ("Port", True),
    "protocol": ("Protocol", False),
    "anonymity": ("Anonymity", False),
    "latency": ("Latency (ms)", True),
}


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
    """Right-hand column: sortable/filterable live table of alive proxies."""

    def __init__(self, master):
        super().__init__(master, padding=10)

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 5))
        ttk.Label(header, text="Live proxies", font=("TkDefaultFont", 10, "bold")).pack(side="left")
        self.count_var = tk.StringVar(value="0 found")
        ttk.Label(header, textvariable=self.count_var).pack(side="right")

        # -- filter bar --------------------------------------------------
        filters = ttk.Frame(self)
        filters.pack(fill="x", pady=(0, 5))

        ttk.Label(filters, text="Search IP:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_view())
        ttk.Entry(filters, textvariable=self.search_var, width=16).pack(side="left", padx=(2, 10))

        ttk.Label(filters, text="Protocol:").pack(side="left")
        self.protocol_filter = tk.StringVar(value="All")
        proto_box = ttk.Combobox(
            filters, textvariable=self.protocol_filter, state="readonly", width=8,
            values=["All", "SOCKS4", "SOCKS5"],
        )
        proto_box.pack(side="left", padx=(2, 10))
        proto_box.bind("<<ComboboxSelected>>", lambda *_: self._refresh_view())

        ttk.Label(filters, text="Anonymity:").pack(side="left")
        self.anonymity_filter = tk.StringVar(value="All")
        anon_box = ttk.Combobox(
            filters, textvariable=self.anonymity_filter, state="readonly", width=11,
            values=["All", "Transparent", "Anonymous", "Elite"],
        )
        anon_box.pack(side="left", padx=(2, 0))
        anon_box.bind("<<ComboboxSelected>>", lambda *_: self._refresh_view())

        # -- table ---------------------------------------------------------
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table_frame, columns=list(COLUMNS.keys()), show="tree headings")
        self.tree.heading("#0", text="#")
        self.tree.column("#0", width=60, anchor="center", stretch=False)
        for col_id, (label, _numeric) in COLUMNS.items():
            self.tree.heading(col_id, text=label, command=lambda c=col_id: self._sort_by(c))
        self.tree.column("country", width=70, anchor="center")
        self.tree.column("ip", width=120, anchor="center")
        self.tree.column("port", width=60, anchor="center")
        self.tree.column("protocol", width=70, anchor="center")
        self.tree.column("anonymity", width=90, anchor="center")
        self.tree.column("latency", width=100, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Button-3>", self._show_context_menu)   # Windows/Linux right click
        self.tree.bind("<Button-2>", self._show_context_menu)   # macOS right click

        export_row = ttk.Frame(self)
        export_row.pack(fill="x", pady=(5, 0))
        ttk.Button(export_row, text="Export CSV", command=self.export_csv).pack(side="left", expand=True, fill="x")
        ttk.Button(export_row, text="Export TXT", command=self.export_txt).pack(side="left", expand=True, fill="x", padx=(5, 0))

        self._rows = []          # full dataset, independent of current filter/sort/view
        self._images = []        # keep PhotoImage refs alive (Tkinter would GC them otherwise)
        self._sort_column = None
        self._sort_reverse = False

    # -- data in ------------------------------------------------------------

    def add_row(self, country_code: str, ip: str, port: str, protocol: str,
                anonymity: str, latency_ms: int, flag_png: bytes | None):
        photo = None
        if flag_png:
            try:
                photo = tk.PhotoImage(data=flag_png)
                self._images.append(photo)
            except Exception:  # noqa: BLE001 - bad/unsupported image data, just skip the icon
                photo = None

        self._rows.append({
            "num": len(self._rows) + 1,
            "country": country_code or "??",
            "ip": ip,
            "port": port,
            "protocol": protocol,
            "anonymity": anonymity,
            "latency": latency_ms,
            "photo": photo,
        })
        self.count_var.set(f"{len(self._rows)} found")
        self._refresh_view()

    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self._rows.clear()
        self._images.clear()
        self.count_var.set("0 found")

    # -- filtering / sorting / rendering -------------------------------------

    def _matches_filter(self, row: dict) -> bool:
        search = self.search_var.get().strip()
        if search and search not in row["ip"]:
            return False
        proto = self.protocol_filter.get()
        if proto != "All" and row["protocol"] != proto:
            return False
        anon = self.anonymity_filter.get()
        if anon != "All" and row["anonymity"] != anon:
            return False
        return True

    def _sort_by(self, col_id: str):
        if self._sort_column == col_id:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = col_id
            self._sort_reverse = False
        self._refresh_view()

    def _refresh_view(self):
        self.tree.delete(*self.tree.get_children())
        visible = [r for r in self._rows if self._matches_filter(r)]

        if self._sort_column:
            _label, numeric = COLUMNS[self._sort_column]
            visible.sort(key=lambda r: r[self._sort_column], reverse=self._sort_reverse)

        for row in visible:
            self.tree.insert(
                "", "end",
                text=str(row["num"]),
                image=row["photo"] if row["photo"] else "",
                values=(row["country"], row["ip"], row["port"], row["protocol"],
                        row["anonymity"], row["latency"]),
            )

    # -- right-click copy menu -----------------------------------------------

    def _show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        self.tree.selection_set(row_id)
        values = self.tree.item(row_id, "values")
        country, ip, port, protocol, anonymity, latency = values

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Copy IP", command=lambda: self._copy(ip))
        menu.add_command(label="Copy IP:Port", command=lambda: self._copy(f"{ip}:{port}"))
        menu.add_command(
            label="Copy proxy URL",
            command=lambda: self._copy(f"{protocol.lower()}://{ip}:{port}"),
        )
        menu.add_command(
            label="Copy full row",
            command=lambda: self._copy(
                f"{country}\t{ip}\t{port}\t{protocol}\t{anonymity}\t{latency}"
            ),
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _copy(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)

    # -- export ---------------------------------------------------------------

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
            writer.writerow(["Country", "IP", "Port", "Protocol", "Anonymity", "Latency_ms"])
            for r in self._rows:
                writer.writerow([r["country"], r["ip"], r["port"], r["protocol"], r["anonymity"], r["latency"]])
        messagebox.showinfo("Export", f"Saved {len(self._rows)} proxies to {path}")

    def export_txt(self):
        if not self._rows:
            messagebox.showinfo("Export", "No results to export yet.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="live_proxies.txt",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            for r in self._rows:
                f.write(f"{r['protocol'].lower()}://{r['ip']}:{r['port']}\n")
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
        self.geometry("1020x560")
        self.minsize(820, 460)

        try:
            self._icon_image = tk.PhotoImage(file=_icon_path())
            self.iconphoto(True, self._icon_image)
        except Exception as exc:  # noqa: BLE001 - icon is cosmetic, never block startup
            log.warning("Could not load app icon: %s", exc)

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
            self.results_panel.add_row(
                r.country_code, r.ip, r.port, r.protocol, r.anonymity, r.latency_ms, r.flag_png
            )
        elif etype == "finished":
            self.process_panel.set_running(False)
            self.process_panel.status_var.set(
                f"Done in {event['elapsed']}s — {event['found']} live proxies found."
            )
            self.process_panel.append_log(
                f"Finished: {event['found']} live proxies saved to "
                f"{config.RESULTS_CSV} and {config.RESULTS_TXT}"
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

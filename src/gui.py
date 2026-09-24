"""
Tkinter GUI for the proxy checker - dark theme.

Layout: a header bar (app icon, title, status dot), then two columns via a
PanedWindow: "Process" (settings/controls/progress/log) on the left, and a
live, sortable, filterable results table on the right.

The results table is NOT a ttk.Treeview. Treeview can only color a whole
row's text, not individual cells, which isn't enough to show only the
Anonymity column in color while the rest of the row stays neutral. Instead
the table is built from plain tk.Frame/tk.Label widgets inside a scrollable
canvas, giving full per-cell control (colors, a per-row checkbox, flag
images) at the cost of a bit more code.

Only the standard library is used (tkinter), so no extra GUI dependency is
required beyond `requests` (with the `socks` extra) for the networking.
"""

import csv
import logging
import os
import queue
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import config
from .checker import ProxyChecker

log = logging.getLogger(__name__)


def _icon_path() -> str:
    """
    Path to the app icon, relative to the project root - works both when run
    from source and when bundled by PyInstaller (via sys._MEIPASS).
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "assets", "icon_64.png")


# -- color palette (dark theme) ---------------------------------------------

PALETTE = {
    "bg": "#0b0f17",
    "panel": "#0e1420",
    "card": "#121826",
    "card_alt": "#0f1521",
    "border": "#1f2937",
    "text": "#e5e7eb",
    "muted": "#8b93a7",
    "accent": "#22c55e",
    "accent_dark": "#16a34a",
    "accent_text": "#052e16",
    "input_bg": "#0c111c",
    "row_alt": "#0f1521",
    "danger": "#ef4444",
    "warning": "#f59e0b",
}

ANONYMITY_COLORS = {
    "Elite": PALETTE["accent"],
    "Anonymous": PALETTE["warning"],
    "Transparent": PALETTE["danger"],
}

# (key, header label, pixel width, text anchor)
COLUMN_SPECS = [
    ("check", "", 34, "center"),
    ("num", "#", 40, "center"),
    ("flag", "", 30, "center"),
    ("country", "Country", 64, "center"),
    ("ip", "IP", 130, "w"),
    ("port", "Port", 60, "center"),
    ("protocol", "Protocol", 78, "center"),
    ("anonymity", "Anonymity", 100, "w"),
    ("latency", "Latency (ms)", 110, "center"),
]
ROW_H = 30
HEADER_H = 32


def configure_style(root: tk.Tk) -> ttk.Style:
    """Apply the dark palette to every ttk widget style used in this app."""
    P = PALETTE

    # Tk (not ttk) widgets draw their own "highlight" focus border, separate
    # from ttk styling entirely, that defaults to a light/white rectangle
    # regardless of bg/fg colors. Zeroing it out globally via the resource
    # database is what actually gets rid of the stray white borders around
    # cards, inputs and checkboxes in this dark theme.
    root.option_add("*highlightThickness", 0)
    root.option_add("*highlightBackground", P["panel"])
    root.option_add("*highlightColor", P["accent"])

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=P["panel"], foreground=P["text"], fieldbackground=P["input_bg"])
    style.configure("TFrame", background=P["panel"])
    style.configure("Card.TFrame", background=P["card"])
    style.configure("TLabel", background=P["panel"], foreground=P["text"])
    style.configure("Card.TLabel", background=P["card"], foreground=P["text"])
    style.configure("Muted.TLabel", background=P["panel"], foreground=P["muted"])

    style.configure("TLabelframe", background=P["card"], foreground=P["text"],
                     bordercolor=P["border"], lightcolor=P["border"], darkcolor=P["border"],
                     borderwidth=1, relief="solid")
    style.configure("TLabelframe.Label", background=P["card"], foreground=P["text"])

    style.configure("TButton", background=P["input_bg"], foreground=P["text"],
                     bordercolor=P["border"], focusthickness=0, padding=8, relief="flat")
    style.map("TButton",
              background=[("active", "#1a2333"), ("disabled", "#0c111c")],
              foreground=[("disabled", P["muted"])])

    style.configure("Accent.TButton", background=P["accent"], foreground=P["accent_text"],
                     bordercolor=P["accent"], padding=8, relief="flat")
    style.map("Accent.TButton",
              background=[("active", P["accent_dark"]), ("disabled", "#16321f")],
              foreground=[("disabled", "#5b6b60")])

    style.configure("TSpinbox", fieldbackground=P["input_bg"], background=P["input_bg"],
                     foreground=P["text"], bordercolor=P["border"], arrowcolor=P["text"],
                     lightcolor=P["input_bg"], darkcolor=P["input_bg"], relief="flat")
    style.map("TSpinbox", background=[("readonly", P["input_bg"])],
              fieldbackground=[("readonly", P["input_bg"])],
              arrowcolor=[("disabled", P["muted"])])

    style.configure("TEntry", fieldbackground=P["input_bg"], foreground=P["text"],
                     bordercolor=P["border"], insertcolor=P["text"],
                     lightcolor=P["input_bg"], darkcolor=P["input_bg"])

    style.configure("TCombobox", fieldbackground=P["input_bg"], background=P["input_bg"],
                     foreground=P["text"], bordercolor=P["border"], arrowcolor=P["text"],
                     lightcolor=P["input_bg"], darkcolor=P["input_bg"], relief="flat")
    style.map("TCombobox",
              fieldbackground=[("readonly", P["input_bg"])],
              background=[("readonly", P["input_bg"]), ("active", P["card"])],
              foreground=[("readonly", P["text"])],
              arrowcolor=[("disabled", P["muted"])])
    root.option_add("*TCombobox*Listbox.background", P["input_bg"])
    root.option_add("*TCombobox*Listbox.foreground", P["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", P["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", P["accent_text"])
    root.option_add("*TCombobox*Listbox.borderWidth", 0)
    root.option_add("*TCombobox*Listbox.highlightThickness", 0)

    style.configure("TProgressbar", troughcolor=P["input_bg"], background=P["accent"],
                     bordercolor=P["border"], lightcolor=P["accent"], darkcolor=P["accent"])
    style.configure("TPanedwindow", background=P["bg"])

    for orientation in ("Vertical", "Horizontal"):
        name = f"{orientation}.TScrollbar"
        style.configure(
            name, background=P["border"], troughcolor=P["card"],
            bordercolor=P["card"], arrowcolor=P["muted"],
            lightcolor=P["border"], darkcolor=P["border"], relief="flat", gripcount=0,
        )
        style.map(
            name,
            background=[("active", P["accent"]), ("pressed", P["accent_dark"])],
            arrowcolor=[("active", P["text"])],
        )
    return style


def _fixed(parent, width, height, bg):
    """A Frame with a locked pixel size, used as a table cell container so
    header and data cells always line up regardless of font metrics."""
    f = tk.Frame(parent, width=width, height=height, bg=bg)
    f.pack_propagate(False)
    return f


class Checkbox(tk.Canvas):
    """
    A small custom checkbox drawn entirely with our own colors.

    Classic tk.Checkbutton's indicator square is drawn by the platform's
    native widget rendering and ignores bg/fg overrides on some systems,
    which is exactly what left stray white boxes in the dark theme. Drawing
    it ourselves on a tiny Canvas guarantees it always matches the palette.
    """

    SIZE = 14

    def __init__(self, parent, bg, variable: tk.BooleanVar, command=None):
        super().__init__(parent, width=self.SIZE, height=self.SIZE, bg=bg,
                          highlightthickness=0, bd=0, cursor="hand2")
        self._bg = bg
        self.variable = variable
        self.command = command
        self._trace_id = None
        self.bind("<Button-1>", self._toggle)
        self._bind_variable(variable)
        self._draw()

    def _bind_variable(self, variable):
        if self._trace_id is not None:
            try:
                self.variable.trace_remove("write", self._trace_id)
            except Exception:  # noqa: BLE001 - old var may already be gone
                pass
        self.variable = variable
        self._trace_id = self.variable.trace_add("write", lambda *_: self._draw())

    def rebind(self, variable: tk.BooleanVar, bg: str = None):
        """Point this same widget at a different row's variable/background -
        used when a pooled row is reassigned to show different data, instead
        of creating a brand new Checkbox for every row."""
        if bg is not None and bg != self._bg:
            self._bg = bg
            self.configure(bg=bg)
        self._bind_variable(variable)
        self._draw()

    def _toggle(self, _event=None):
        self.variable.set(not self.variable.get())
        self._draw()
        if self.command:
            self.command()

    def _draw(self):
        self.delete("all")
        pad = 1
        if self.variable.get():
            self.create_rectangle(pad, pad, self.SIZE - pad, self.SIZE - pad,
                                   fill=PALETTE["accent"], outline=PALETTE["accent"])
            self.create_line(3, 7, 6, 10, 11, 4, fill=PALETTE["accent_text"],
                              width=2, capstyle="round", joinstyle="round")
        else:
            self.create_rectangle(pad, pad, self.SIZE - pad, self.SIZE - pad,
                                   fill=self._bg, outline=PALETTE["muted"])

    def refresh(self):
        """Call after the variable was changed from outside this widget."""
        self._draw()


class ProcessPanel(tk.Frame):
    """Left-hand column: settings, controls, progress bar and log."""

    def __init__(self, master, on_start, on_stop):
        super().__init__(master, bg=PALETTE["panel"], padx=14, pady=14)
        P = PALETTE

        settings_card = ttk.Labelframe(self, text=" \u2699  Settings ")
        settings_card.pack(fill="x", pady=(0, 12))
        inner = ttk.Frame(settings_card, style="Card.TFrame")
        inner.pack(fill="x", padx=10, pady=10)

        ttk.Label(inner, text="Threads:", style="Card.TLabel").grid(row=0, column=0, padx=(0, 6), pady=4, sticky="w")
        self.threads_var = tk.IntVar(value=config.DEFAULT_THREADS)
        ttk.Spinbox(inner, from_=1, to=500, textvariable=self.threads_var, width=8).grid(
            row=0, column=1, padx=(0, 16), pady=4, sticky="w"
        )
        ttk.Label(inner, text="Timeout (s):", style="Card.TLabel").grid(row=0, column=2, padx=(0, 6), pady=4, sticky="w")
        self.timeout_var = tk.IntVar(value=config.DEFAULT_TIMEOUT)
        ttk.Spinbox(inner, from_=1, to=60, textvariable=self.timeout_var, width=8).grid(
            row=0, column=3, pady=4, sticky="w"
        )

        ttk.Label(inner, text="Protocols:", style="Card.TLabel").grid(
            row=1, column=0, padx=(0, 6), pady=(10, 4), sticky="w"
        )
        proto_row = ttk.Frame(inner, style="Card.TFrame")
        proto_row.grid(row=1, column=1, columnspan=3, pady=(10, 4), sticky="w")
        self.protocol_vars: dict[str, tk.BooleanVar] = {}
        for key, label in [("http", "HTTP"), ("socks4", "SOCKS4"), ("socks5", "SOCKS5")]:
            var = tk.BooleanVar(value=True)
            self.protocol_vars[key] = var
            item = tk.Frame(proto_row, bg=P["card"])
            item.pack(side="left", padx=(0, 14))
            Checkbox(item, bg=P["card"], variable=var).pack(side="left", padx=(0, 5))
            tk.Label(item, text=label, bg=P["card"], fg=P["text"]).pack(side="left")

        ttk.Label(inner, text="Proxies needed:", style="Card.TLabel").grid(
            row=2, column=0, padx=(0, 6), pady=(6, 0), sticky="w"
        )
        count_row = ttk.Frame(inner, style="Card.TFrame")
        count_row.grid(row=2, column=1, columnspan=3, pady=(6, 0), sticky="w")
        self.target_count_var = tk.IntVar(value=0)
        ttk.Spinbox(count_row, from_=0, to=1000000, textvariable=self.target_count_var, width=8).pack(side="left")
        tk.Label(count_row, text="(0 = unlimited)", bg=P["card"], fg=P["muted"]).pack(side="left", padx=(6, 0))

        controls = ttk.Frame(self)
        controls.pack(fill="x", pady=(0, 12))
        self.start_btn = ttk.Button(controls, text="\u25B8  Start", style="Accent.TButton", command=on_start)
        self.start_btn.pack(side="left", fill="x", expand=True)
        self.stop_btn = ttk.Button(controls, text="\u25A0  Stop", command=on_stop, state="disabled")
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 4))

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel", wraplength=280).pack(
            anchor="w", pady=(0, 12)
        )

        log_card = ttk.Labelframe(self, text=" \u2637  Log ")
        log_card.pack(fill="both", expand=True)
        self.log_text = tk.Text(
            log_card, state="disabled", wrap="word", bg=P["input_bg"], fg=P["text"],
            insertbackground=P["text"], relief="flat", padx=8, pady=6, highlightthickness=0,
            font=("TkFixedFont", 9),
        )
        log_scroll = ttk.Scrollbar(log_card, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        log_scroll.pack(side="right", fill="y", pady=8)

        self.log_text.tag_configure("accent", foreground=P["accent"])
        self.log_text.tag_configure("error", foreground=P["danger"])
        self.log_text.tag_configure("warning", foreground=P["warning"])
        self.log_text.tag_configure("muted", foreground=P["muted"])

    def append_log(self, message: str, level: str = "normal"):
        tag = {"accent": "accent", "error": "error", "warning": "warning", "muted": "muted"}.get(level, "")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n", (tag,) if tag else ())
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def set_running(self, running: bool):
        self.start_btn.configure(state="disabled" if running else "normal")
        self.stop_btn.configure(state="normal" if running else "disabled")


class _PooledRow:
    """
    One reusable set of row widgets, repositioned and refreshed with a
    different data row as the table scrolls, instead of being destroyed and
    recreated. This is what makes scrolling through thousands of results
    fast: only ~20-30 of these ever exist (enough to cover the visible
    viewport), no matter how many rows are in the dataset.
    """

    def __init__(self, table: "ResultsTable"):
        self.table = table
        self.data = None  # the row dict currently shown, or None if unused
        self.bg = PALETTE["card"]

        self.frame = tk.Frame(table.canvas, bg=self.bg)
        self.window_id = table.canvas.create_window(0, 0, window=self.frame, anchor="nw", state="hidden")
        self.frame.bind("<Button-3>", self._on_context)
        self.frame.bind("<Button-2>", self._on_context)

        self.check_widget = None
        self.flag_label = None
        self.cell_labels: dict = {}

        for key, _label, width, anchor in COLUMN_SPECS:
            cell = _fixed(self.frame, width, ROW_H, self.bg)
            cell.pack(side="left")
            cell.bind("<Button-3>", self._on_context)
            cell.bind("<Button-2>", self._on_context)

            if key == "check":
                cb = Checkbox(cell, bg=self.bg, variable=tk.BooleanVar(value=False))
                cb.pack(expand=True)
                self.check_widget = cb
                continue

            if key == "flag":
                lbl = tk.Label(cell, bg=self.bg)
                lbl.pack(expand=True)
                self.flag_label = lbl
            else:
                lbl = tk.Label(cell, bg=self.bg, anchor=anchor,
                                font=("TkDefaultFont", 9, "bold" if key == "anonymity" else "normal"))
                lbl.pack(fill="both", expand=True, padx=6)
                self.cell_labels[key] = lbl
            lbl.bind("<Button-3>", self._on_context)
            lbl.bind("<Button-2>", self._on_context)

    def _on_context(self, event):
        if self.data is not None and self.table.on_context_menu:
            self.table.on_context_menu(event, self.data)

    def set_row(self, row: dict, index: int):
        self.data = row
        bg = PALETTE["card"] if index % 2 == 0 else PALETTE["row_alt"]
        if bg != self.bg:
            self.bg = bg
            self.frame.configure(bg=bg)
            for child in self.frame.winfo_children():
                if not isinstance(child, Checkbox):
                    child.configure(bg=bg)
            for lbl in self.cell_labels.values():
                lbl.configure(bg=bg)
            self.flag_label.configure(bg=bg)

        self.check_widget.rebind(row["check_var"], bg=bg)

        photo = row.get("photo")
        if photo:
            self.flag_label.configure(image=photo)
            self.flag_label.image = photo
        else:
            self.flag_label.configure(image="")
            self.flag_label.image = None

        self.cell_labels["num"].configure(text=str(row["num"]), fg=PALETTE["muted"])
        self.cell_labels["country"].configure(text=row["country"], fg=PALETTE["text"])
        self.cell_labels["ip"].configure(text=row["ip"], fg=PALETTE["text"])
        self.cell_labels["port"].configure(text=str(row["port"]), fg=PALETTE["text"])
        self.cell_labels["protocol"].configure(text=row["protocol"], fg=PALETTE["text"])
        self.cell_labels["anonymity"].configure(
            text=row["anonymity"], fg=ANONYMITY_COLORS.get(row["anonymity"], PALETTE["text"])
        )
        self.cell_labels["latency"].configure(text=str(row["latency"]), fg=PALETTE["text"])

    def move_to(self, y: int, width: int):
        self.table.canvas.coords(self.window_id, 0, y)
        self.table.canvas.itemconfigure(self.window_id, width=width, state="normal")

    def hide(self):
        self.data = None
        self.table.canvas.itemconfigure(self.window_id, state="hidden")


class ResultsTable(tk.Frame):
    """
    Sortable, header-clickable, virtually-scrolled results table.

    It is NOT a ttk.Treeview (which can only color a whole row's text, not
    individual cells - not enough to show only the Anonymity column in
    color) and it does NOT create one set of widgets per data row either -
    with 1000+ results that meant thousands of live Tk widgets and very
    visible stutter while scrolling/filling in. Instead a small fixed pool
    of _PooledRow widget-sets (just enough to cover the visible area) is
    reused and repositioned/refreshed as the table scrolls, so rendering
    cost depends on viewport size, not on how many results were found.
    """

    BUFFER_ROWS = 6  # extra pooled rows above/below the viewport for smooth scrolling

    def __init__(self, master, on_sort):
        super().__init__(master, bg=PALETTE["card"])
        self.on_sort = on_sort
        self.on_context_menu = None
        self.sort_column = None
        self.sort_reverse = False
        self._data: list = []
        self._pool: list[_PooledRow] = []

        header = tk.Frame(self, bg=PALETTE["card_alt"])
        header.pack(fill="x")
        self.select_all_var = tk.BooleanVar(value=False)
        for key, label, width, anchor in COLUMN_SPECS:
            cell = _fixed(header, width, HEADER_H, PALETTE["card_alt"])
            cell.pack(side="left")
            if key == "check":
                Checkbox(cell, bg=PALETTE["card_alt"], variable=self.select_all_var,
                          command=self._on_select_all).pack(expand=True)
            elif key in ("num", "flag"):
                pass
            else:
                lbl = tk.Label(
                    cell, text=label, bg=PALETTE["card_alt"], fg=PALETTE["muted"],
                    font=("TkDefaultFont", 9, "bold"), anchor=anchor, cursor="hand2",
                )
                lbl.pack(fill="both", expand=True, padx=6)
                lbl.bind("<Button-1>", lambda e, k=key: self._sort_by(k))
                cell.bind("<Button-1>", lambda e, k=key: self._sort_by(k))

        tk.Frame(self, bg=PALETTE["border"], height=1).pack(fill="x")

        body_wrap = tk.Frame(self, bg=PALETTE["card"])
        body_wrap.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(body_wrap, bg=PALETTE["card"], highlightthickness=0)
        vscroll = ttk.Scrollbar(body_wrap, orient="vertical", command=self._on_scrollbar)
        self.canvas.configure(yscrollcommand=lambda a, b: (vscroll.set(a, b), self._update_visible()))
        self.canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", lambda e: self._scroll(-1))
        self.canvas.bind_all("<Button-5>", lambda e: self._scroll(1))

        self.empty_label = tk.Label(
            self, text="No live proxies yet\nStart the scan to see results here",
            bg=PALETTE["card"], fg=PALETTE["muted"], font=("TkDefaultFont", 11), justify="center",
        )
        self.empty_label.place(in_=self.canvas, relx=0.5, rely=0.5, anchor="center")

        self.canvas.configure(scrollregion=(0, 0, 0, 1))

    # -- scrolling / windowing ------------------------------------------------

    def _on_scrollbar(self, *args):
        self.canvas.yview(*args)
        self._update_visible()

    def _scroll(self, direction: int):
        self.canvas.yview_scroll(direction, "units")
        self._update_visible()

    def _on_mousewheel(self, event):
        self._scroll(-1 if event.delta > 0 else 1)

    def _on_canvas_configure(self, event):
        if event.width > 10:
            self._ensure_pool_size()
            self._update_visible()

    def _ensure_pool_size(self):
        viewport_h = self.canvas.winfo_height() or 400
        needed = max(12, viewport_h // ROW_H + self.BUFFER_ROWS)
        while len(self._pool) < needed:
            self._pool.append(_PooledRow(self))

    def _update_visible(self):
        canvas_w = self.canvas.winfo_width() or 1
        if not self._data:
            for rw in self._pool:
                rw.hide()
            return
        top_y = max(0, int(self.canvas.canvasy(0)))
        first_index = top_y // ROW_H
        for slot, rw in enumerate(self._pool):
            idx = first_index + slot
            if idx < len(self._data):
                rw.set_row(self._data[idx], idx)
                rw.move_to(idx * ROW_H, canvas_w)
            else:
                rw.hide()

    def _sort_by(self, key):
        if key == self.sort_column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = key
            self.sort_reverse = False
        self.on_sort()

    def _on_select_all(self):
        state = self.select_all_var.get()
        for row in self._data:
            row["check_var"].set(state)

    # -- data in --------------------------------------------------------------

    def clear(self):
        self._data = []
        for rw in self._pool:
            rw.hide()
        self.select_all_var.set(False)
        self.canvas.configure(scrollregion=(0, 0, 0, 1))
        self.canvas.yview_moveto(0)
        self.empty_label.place(in_=self.canvas, relx=0.5, rely=0.5, anchor="center")

    def set_rows(self, rows: list, on_context_menu):
        """Full rebuild of the visible dataset - used after sort/filter changes."""
        self.on_context_menu = on_context_menu
        self._data = rows
        self.canvas.configure(scrollregion=(0, 0, 0, max(len(rows) * ROW_H, 1)))
        self.canvas.yview_moveto(0)
        if rows:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(in_=self.canvas, relx=0.5, rely=0.5, anchor="center")
        self._ensure_pool_size()
        self._update_visible()

    def append_row(self, row: dict, on_context_menu):
        """Fast path used while a scan is running with no sort/filter active:
        add one row to the dataset without rebuilding what's on screen."""
        self.on_context_menu = on_context_menu
        self._data.append(row)
        self.canvas.configure(scrollregion=(0, 0, 0, len(self._data) * ROW_H))
        self.empty_label.place_forget()
        self._ensure_pool_size()

        # Only touch the widget pool if the newly appended row actually
        # falls within the currently visible window. While scrolled to the
        # top during a live scan (the common case), rows appended far below
        # are off-screen and refreshing the pool for them would just be
        # redoing the same already-visible rows over and over for nothing.
        new_index = len(self._data) - 1
        top_y = max(0, int(self.canvas.canvasy(0)))
        first_index = top_y // ROW_H
        if first_index <= new_index < first_index + len(self._pool):
            self._update_visible()

    def selected_rows(self):
        return [row for row in self._data if row["check_var"].get()]


class ResultsPanel(tk.Frame):
    """Right-hand column: header, filters, results table, export buttons."""

    def __init__(self, master):
        super().__init__(master, bg=PALETTE["panel"], padx=14, pady=14)
        P = PALETTE

        header = tk.Frame(self, bg=P["panel"])
        header.pack(fill="x", pady=(0, 8))
        tk.Label(header, text="\u25A3  Live proxies", bg=P["panel"], fg=P["text"],
                 font=("TkDefaultFont", 12, "bold")).pack(side="left")
        self.count_var = tk.StringVar(value="0 found")
        tk.Label(header, textvariable=self.count_var, bg=P["panel"], fg=P["muted"]).pack(side="right")

        filters = tk.Frame(self, bg=P["panel"])
        filters.pack(fill="x", pady=(0, 8))

        tk.Label(filters, text="Search IP:", bg=P["panel"], fg=P["muted"]).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_view())
        tk.Entry(
            filters, textvariable=self.search_var, width=18, bg=P["input_bg"], fg=P["text"],
            insertbackground=P["text"], relief="flat", highlightthickness=1,
            highlightbackground=P["border"], highlightcolor=P["accent"],
        ).pack(side="left", padx=(6, 16), ipady=3)

        tk.Label(filters, text="Protocol:", bg=P["panel"], fg=P["muted"]).pack(side="left")
        self.protocol_filter = tk.StringVar(value="All")
        proto_box = ttk.Combobox(
            filters, textvariable=self.protocol_filter, state="readonly", width=8,
            values=["All", "HTTP", "SOCKS4", "SOCKS5"],
        )
        proto_box.pack(side="left", padx=(6, 16))
        proto_box.bind("<<ComboboxSelected>>", lambda *_: self._refresh_view())

        tk.Label(filters, text="Anonymity:", bg=P["panel"], fg=P["muted"]).pack(side="left")
        self.anonymity_filter = tk.StringVar(value="All")
        anon_box = ttk.Combobox(
            filters, textvariable=self.anonymity_filter, state="readonly", width=11,
            values=["All", "Transparent", "Anonymous", "Elite"],
        )
        anon_box.pack(side="left", padx=(6, 0))
        anon_box.bind("<<ComboboxSelected>>", lambda *_: self._refresh_view())

        table_wrap = tk.Frame(self, bg=P["border"])
        table_wrap.pack(fill="both", expand=True)
        self.table = ResultsTable(table_wrap, on_sort=self._refresh_view)
        self.table.pack(fill="both", expand=True, padx=1, pady=1)

        export_row = tk.Frame(self, bg=P["panel"])
        export_row.pack(fill="x", pady=(10, 0))
        ttk.Button(export_row, text="\u2B07  Export CSV", command=self.export_csv).pack(
            side="left", expand=True, fill="x"
        )
        ttk.Button(export_row, text="\u2B07  Export TXT", command=self.export_txt).pack(
            side="left", expand=True, fill="x", padx=(8, 0)
        )

        self._rows = []
        self._flag_photo_cache: dict[str, tk.PhotoImage] = {}  # one decoded image per country, reused

    # -- data in --------------------------------------------------------------

    def add_row(self, country_code, ip, port, protocol, anonymity, latency_ms, flag_png):
        photo = None
        if flag_png:
            cc = country_code or ""
            photo = self._flag_photo_cache.get(cc)
            if photo is None:
                try:
                    # Decoding a PNG into a Tk image is the actually expensive
                    # part here (not the file size, which is tiny) - do it
                    # once per country and reuse the same PhotoImage for every
                    # row that shares it, instead of once per proxy.
                    photo = tk.PhotoImage(data=flag_png)
                    self._flag_photo_cache[cc] = photo
                except Exception:  # noqa: BLE001 - bad/unsupported image data, just skip the icon
                    photo = None

        row = {
            "num": len(self._rows) + 1,
            "country": country_code or "??",
            "ip": ip,
            "port": port,
            "protocol": protocol,
            "anonymity": anonymity,
            "latency": latency_ms,
            "photo": photo,
            "check_var": tk.BooleanVar(value=False),
        }
        self._rows.append(row)
        self.count_var.set(f"{len(self._rows)} found")

        # Fast path while a scan is running with no sort/filter active: just
        # append one row instead of rebuilding the whole table each time.
        if not self._sort_active() and not self._filter_active():
            self.table.append_row(row, self._show_context_menu)
        else:
            self._refresh_view()

    def clear(self):
        self.table.clear()
        self._rows.clear()
        self._flag_photo_cache.clear()
        self.count_var.set("0 found")
        self.search_var.set("")
        self.protocol_filter.set("All")
        self.anonymity_filter.set("All")
        self.table.sort_column = None
        self.table.sort_reverse = False

    # -- filtering / sorting ----------------------------------------------------

    def _sort_active(self) -> bool:
        return self.table.sort_column is not None

    def _filter_active(self) -> bool:
        return bool(self.search_var.get().strip()) or self.protocol_filter.get() != "All" \
            or self.anonymity_filter.get() != "All"

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

    def _refresh_view(self):
        visible = [r for r in self._rows if self._matches_filter(r)]
        if self.table.sort_column:
            key = self.table.sort_column
            visible.sort(key=lambda r: r[key], reverse=self.table.sort_reverse)
        self.table.set_rows(visible, self._show_context_menu)

    # -- right-click copy menu -----------------------------------------------

    def _show_context_menu(self, event, row):
        P = PALETTE
        menu = tk.Menu(
            self, tearoff=0, bg=P["card"], fg=P["text"],
            activebackground=P["accent"], activeforeground=P["accent_text"],
            relief="flat",
        )
        menu.add_command(label="Copy IP", command=lambda: self._copy(row["ip"]))
        menu.add_command(label="Copy IP:Port", command=lambda: self._copy(f"{row['ip']}:{row['port']}"))
        menu.add_command(
            label="Copy proxy URL",
            command=lambda: self._copy(f"{row['protocol'].lower()}://{row['ip']}:{row['port']}"),
        )
        menu.add_command(
            label="Copy full row",
            command=lambda: self._copy(
                f"{row['country']}\t{row['ip']}\t{row['port']}\t{row['protocol']}\t"
                f"{row['anonymity']}\t{row['latency']}"
            ),
        )
        selected = self.table.selected_rows()
        if len(selected) > 1:
            menu.add_separator()
            menu.add_command(label=f"Copy {len(selected)} selected rows", command=self._copy_selected)
        menu.tk_popup(event.x_root, event.y_root)

    def _copy_selected(self):
        lines = [f"{r['protocol'].lower()}://{r['ip']}:{r['port']}" for r in self.table.selected_rows()]
        self._copy("\n".join(lines))

    def _copy(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)

    # -- export ---------------------------------------------------------------

    def export_csv(self):
        if not self._rows:
            messagebox.showinfo("Export", "No results to export yet.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")], initialfile="live_proxies.csv"
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
            defaultextension=".txt", filetypes=[("Text files", "*.txt")], initialfile="live_proxies.txt"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            for r in self._rows:
                f.write(f"{r['protocol'].lower()}://{r['ip']}:{r['port']}\n")
        messagebox.showinfo("Export", f"Saved {len(self._rows)} proxies to {path}")


class MainWindow(tk.Tk):
    """Application window: header bar, then a two-column paned layout."""

    POLL_INTERVAL_MS = 100

    def __init__(self):
        super().__init__()
        P = PALETTE
        self.configure(bg=P["bg"])
        self.title("Proxy Checker")
        self.geometry("1180x680")
        self.minsize(1000, 560)
        configure_style(self)

        try:
            self._icon_image = tk.PhotoImage(file=_icon_path())
            self.iconphoto(True, self._icon_image)
        except Exception as exc:  # noqa: BLE001 - icon is cosmetic, never block startup
            log.warning("Could not load app icon: %s", exc)
            self._icon_image = None

        self.event_queue: "queue.Queue" = queue.Queue()
        self.checker: ProxyChecker | None = None

        self._build_header()

        body = tk.Frame(self, bg=P["bg"])
        body.pack(fill="both", expand=True)
        paned = ttk.PanedWindow(body, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.process_panel = ProcessPanel(paned, on_start=self.on_start, on_stop=self.on_stop)
        self.results_panel = ResultsPanel(paned)
        paned.add(self.process_panel, weight=1)
        paned.add(self.results_panel, weight=2)

        self._fit_to_screen()
        self.after(self.POLL_INTERVAL_MS, self._poll_queue)

    def _build_header(self):
        P = PALETTE
        header = tk.Frame(self, bg=P["panel"], padx=16, pady=12)
        header.pack(fill="x")
        header.grid_columnconfigure(1, weight=1)

        left_box = tk.Frame(header, bg=P["panel"])
        left_box.grid(row=0, column=0, sticky="w")

        if self._icon_image is not None:
            tk.Label(left_box, image=self._icon_image, bg=P["panel"]).pack(side="left", padx=(0, 10))

        title_box = tk.Frame(left_box, bg=P["panel"])
        title_box.pack(side="left")
        tk.Label(title_box, text="Proxy Checker", bg=P["panel"], fg=P["text"],
                 font=("TkDefaultFont", 14, "bold")).pack(anchor="w")
        tk.Label(title_box, text="Fast \u00b7 Reliable \u00b7 Simple", bg=P["panel"], fg=P["muted"],
                 font=("TkDefaultFont", 9)).pack(anchor="w")

        # Empty spacer column (1) absorbs extra width, so the status box on
        # the right never gets pushed off-screen even in a narrow window.
        status_box = tk.Frame(header, bg=P["panel"])
        status_box.grid(row=0, column=2, sticky="e")
        self.status_dot_label = tk.Label(status_box, text="\u25CF", bg=P["panel"], fg=P["accent"],
                                          font=("TkDefaultFont", 12))
        self.status_dot_label.pack(side="left", padx=(0, 4))
        self.status_text_var = tk.StringVar(value="Ready")
        tk.Label(status_box, textvariable=self.status_text_var, bg=P["panel"], fg=P["text"]).pack(side="left")

        tk.Frame(self, bg=P["border"], height=1).pack(fill="x")

    def _fit_to_screen(self):
        """
        Make sure the window opens fully visible with no manual resize
        needed: use the requested size, but shrink to fit (and center) on
        smaller screens/displays instead of opening partially off-screen.
        """
        self.update_idletasks()
        want_w, want_h = 1180, 680
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(want_w, screen_w - 60)
        h = min(want_h, screen_h - 80)
        x = max(0, (screen_w - w) // 2)
        y = max(0, (screen_h - h) // 3)
        self.geometry(f"{w}x{h}+{x}+{y}")

    # -- button handlers --------------------------------------------------

    def on_start(self):
        protocols = [key for key, var in self.process_panel.protocol_vars.items() if var.get()]
        if not protocols:
            self.process_panel.status_var.set("Select at least one protocol (HTTP/SOCKS4/SOCKS5).")
            self.process_panel.append_log("Cannot start: no protocol selected.", level="error")
            return

        self.process_panel.set_running(True)
        self.process_panel.progress["value"] = 0
        self.process_panel.status_var.set("Starting...")
        self.status_text_var.set("Running")
        self.status_dot_label.configure(fg=PALETTE["warning"])
        self.results_panel.clear()

        self.checker = ProxyChecker(
            threads=self.process_panel.threads_var.get(),
            timeout=self.process_panel.timeout_var.get(),
            protocols=protocols,
            target_count=self.process_panel.target_count_var.get(),
        )
        self.checker.start(on_event=self.event_queue.put)

    def on_stop(self):
        if self.checker:
            self.checker.stop()
        self.process_panel.status_var.set("Stopping (finishing in-flight checks)...")
        self.process_panel.stop_btn.configure(state="disabled")

    # -- queue polling (safe cross-thread UI updates) ----------------------

    def _poll_queue(self):
        # Cap how many events are processed per tick, and never let one bad
        # event kill the polling loop entirely (previously, an uncaught
        # exception here would silently stop all further UI updates for the
        # rest of the run - looking "frozen" even though checking was still
        # progressing in the background).
        processed = 0
        max_per_tick = 500
        try:
            while processed < max_per_tick:
                event = self.event_queue.get_nowait()
                try:
                    self._handle_event(event)
                except Exception:  # noqa: BLE001 - never let a bad event stop the UI loop
                    log.exception("Error handling GUI event: %s", event)
                processed += 1
        except queue.Empty:
            pass
        self.after(self.POLL_INTERVAL_MS, self._poll_queue)

    def _handle_event(self, event: dict):
        etype = event["type"]
        if etype == "status":
            self.process_panel.status_var.set(event["text"])
            text = event["text"]
            if text.startswith("ERROR"):
                level = "error"
            elif text.startswith("WARNING"):
                level = "warning"
            else:
                level = "normal"
            self.process_panel.append_log(text, level=level)
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
            self.status_text_var.set("Ready")
            self.status_dot_label.configure(fg=PALETTE["accent"])
            self.process_panel.status_var.set(
                f"Done in {event['elapsed']}s \u2014 {event['found']} live proxies found."
            )
            self.process_panel.append_log(
                f"Finished: {event['found']} live proxies found. "
                f"Use Export CSV/TXT to save them.",
                level="accent",
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

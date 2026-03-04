from __future__ import annotations

import os
import threading
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from .params_desc import TYKON_DESC, QUANTUM_DESC, build_param_value_table
from .plotting_smith import draw_smith_grid, plot_smith_rlxl_hf_lf
from .tlog_reader import load_tlog
from .p3_analysis import p3_run_analysis, _p3_export_word_report
from .utils import resource_path, read_project_version

class Tlog2ChartP2App(tk.Tk):
    def __init__(self):
        super().__init__()
        try:
            self.iconbitmap(resource_path('smithchart.ico'))
        except Exception:
            pass

        ver = read_project_version()
        self.title(f"tlog2chart_P3 v{ver}")
        self.geometry("1280x760")

        self._smith_data = None  # dict holding plotted point arrays
        self._smith_annot = None  # matplotlib annotation for hover tooltip

        # Dataframes
        self.df_raw: Optional[pd.DataFrame] = None
        self.df: Optional[pd.DataFrame] = None

        self.unit_info: Dict[str, str] = {}
        self.header_params: List[Tuple[str, str]] = []

        # GUI state vars
        self.unit_type_var = tk.StringVar(value="Tykon")
        self.band_var = tk.StringVar(value="All")     # All / HF / LF
        self.file_path_var = tk.StringVar(value="")
        self.fw_var = tk.StringVar(value="")
        self.fpga_var = tk.StringVar(value="")
        self.sn_var = tk.StringVar(value="")
        self.skip_unit_info_var = tk.BooleanVar(value=False)

        # --- Tlog Array paging + column width persistence ---
        self.array_page_size = 2500
        self.array_page_start = 0
        self._array_cols_signature = None
        self._array_col_widths = {}  # {col_name: width}

        # Plot item selection
        self.selected_items: Dict[str, tk.BooleanVar] = {}
        self.available_plot_items: List[str] = []

        # Twin axes references
        self.ax_power_right = None   # Freq/Duty
        self.ax_vbias_right = None   # DCBias

        # Scale settings
        self.scale_mode = "auto"
        self.custom_scale = {
            "x_min": None, "x_max": None,
            "pL_min": None, "pL_max": None,
            "pR_min": None, "pR_max": None,
            "c_min": None, "c_max": None,
            "vL_min": None, "vL_max": None,
            "vR_min": None, "vR_max": None,
        }

        # Smith power threshold (W): filter Smith points by Pfwd >= threshold
        self.smith_pth_var = tk.DoubleVar(value=0.0)
        # ---------------- Graph Tool Modes (Milestone A) ----------------
        self.tool_mode_var = tk.StringVar(value="NONE")  # NONE / ARROW (later: RULER, ANNOTATE, LINE, RECT, CIRCLE)
        # Arrow hover target (manual selection; no auto-pick)
        self.arrow_target_var = tk.StringVar(value="Pfwd")  # default
        self._arrow_target_cb = None  # Combobox widget (created in tool bar)
        self._hover_annot = None  # matplotlib annotation for Arrow hover
        self._hover_marker = None  # marker ring at nearest point
        self._hover_ax = None  # which axes currently owns the hover marker/annotation
        self._plot_series_cache = []  # list of dicts describing plotted series for fast hover

        self._smith_pth_after = None  # debounce handle

        # Build UI
        self._build_top_bar()
        self._build_tabs()
        # --- Tlog Array highlight state ---
        self._array_highlight_items = set()  # set of Treeview item IDs
        self._build_plot_area()

        # Plot init
        self._init_plot()
        self._init_zoom_zone()

        # ---------------- Phase 3 state ----------------
        self.p3_results: Optional[Dict[str, Any]] = None
        self.p3_artifacts_dir: Optional[str] = None

    # -------------------------------------------------------------------------
    # Top Bar (2 rows)
    # -------------------------------------------------------------------------
    def _build_top_bar(self):
        top = ttk.Frame(self, padding=6)
        top.pack(side=tk.TOP, fill=tk.X)

        row1 = ttk.Frame(top)
        row1.pack(side=tk.TOP, fill=tk.X)

        row2 = ttk.Frame(top)
        row2.pack(side=tk.TOP, fill=tk.X, pady=(4, 0))

        # ---------------- Row 1 ----------------
        ttk.Label(row1, text="Unit Type").pack(side=tk.LEFT, padx=(0, 6))
        self.unit_cb = ttk.Combobox(row1, textvariable=self.unit_type_var,
                                    values=["Tykon", "Quantum"], width=10, state="readonly")
        self.unit_cb.pack(side=tk.LEFT, padx=(0, 12))
        self.unit_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_parameter_tab())

        ttk.Label(row1, text="Tlog File Selected").pack(side=tk.LEFT)
        self.file_entry = ttk.Entry(row1, textvariable=self.file_path_var, width=62)
        self.file_entry.pack(side=tk.LEFT, padx=(6, 4))
        ttk.Button(row1, text="📁", width=3, command=self._on_browse).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(row1, text="Select items to plot").pack(side=tk.LEFT, padx=(0, 6))
        self.plot_menu_btn = ttk.Menubutton(row1, text="(select...)")
        self.plot_menu = tk.Menu(self.plot_menu_btn, tearoff=False)
        self.plot_menu_btn["menu"] = self.plot_menu
        self.plot_menu_btn.pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(row1, text="Band Filter").pack(side=tk.LEFT, padx=(0, 6))
        self.band_cb = ttk.Combobox(row1, textvariable=self.band_var,
                                    values=["All", "HF", "LF"], width=6, state="readonly")
        self.band_cb.pack(side=tk.LEFT, padx=(0, 12))
        self.band_cb.bind("<<ComboboxSelected>>", lambda e: self._on_band_changed())

        ttk.Button(row1, text="Clear", command=self._on_clear).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Checkbutton(row1, text="Skip Unit Info", variable=self.skip_unit_info_var)\
            .pack(side=tk.LEFT, padx=(0, 10))

        # ---------------- Row 2 (buttons under Unit Type) ----------------
        ttk.Label(row2, text="Unit FW Ver").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Entry(row2, textvariable=self.fw_var, width=6, state="readonly") \
            .pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(row2, text="Unit FPGA Ver").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Entry(row2, textvariable=self.fpga_var, width=6, state="readonly") \
            .pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(row2, text="Unit SN").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Entry(row2, textvariable=self.sn_var, width=12, state="readonly") \
            .pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(row2, text="Full Scale", command=self._on_full_scale)\
            .pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row2, text="Custom Scale", command=self._on_custom_scale)\
            .pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row2, text="Export Graph", command=self._on_export_graph)\
            .pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row2, text="Stop", command=self.destroy)\
            .pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(row2, text="Analysis", command=self._on_analysis) \
            .pack(side=tk.LEFT, padx=(8, 8))

        self.btn_export_word = ttk.Button(row2, text="Export to Word", command=self._on_export_word, state="disabled")
        self.btn_export_word.pack(side=tk.LEFT, padx=(0, 8))

    # -------------------------------------------------------------------------
    # Tabs
    # -------------------------------------------------------------------------
    def _build_tabs(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.tab_graph = ttk.Frame(self.nb)
        self.tab_params = ttk.Frame(self.nb)
        self.tab_array = ttk.Frame(self.nb)
        self.tab_smith = ttk.Frame(self.nb)

        self.nb.add(self.tab_graph, text="Graph")
        self.nb.add(self.tab_params, text="Parameters")
        self.nb.add(self.tab_array, text="Tlog Array")
        self.nb.add(self.tab_smith, text="Smith Chart")

        # Parameters tab
        self.param_tree = ttk.Treeview(
            self.tab_params,
            columns=("Section", "Param", "Value", "Description"),
            show="headings",
            height=18
        )
        self.param_tree.heading("Section", text="Section")
        self.param_tree.heading("Param", text="Param")
        self.param_tree.heading("Value", text="Value")
        self.param_tree.heading("Description", text="Description")

        self.param_tree.column("Section", width=180, anchor=tk.W)
        self.param_tree.column("Param", width=70, anchor=tk.W)
        self.param_tree.column("Value", width=140, anchor=tk.W)
        self.param_tree.column("Description", width=900, anchor=tk.W)

        param_ysb = ttk.Scrollbar(self.tab_params, orient="vertical", command=self.param_tree.yview)
        self.param_tree.configure(yscrollcommand=param_ysb.set)

        self.param_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        param_ysb.pack(side=tk.RIGHT, fill=tk.Y)

        # Tlog Array tab (paged: 2500 rows per page + scrollbars)
        array_outer = ttk.Frame(self.tab_array)
        array_outer.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # --- Control bar (Prev/Next) ---
        ctrl = ttk.Frame(array_outer, padding=(4, 4))
        ctrl.pack(side=tk.TOP, fill=tk.X)

        self.btn_array_prev = ttk.Button(ctrl, text="◀ Prev 2500", command=self._array_prev_page)
        self.btn_array_prev.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_array_next = ttk.Button(ctrl, text="Next 2500 ▶", command=self._array_next_page)
        self.btn_array_next.pack(side=tk.LEFT, padx=(0, 12))

        self.array_page_label = ttk.Label(ctrl, text="Rows: -")
        self.array_page_label.pack(side=tk.LEFT)

        # Optional: Go to row()
        ttk.Label(ctrl, text="   Go to row():").pack(side=tk.LEFT, padx=(12, 4))
        self.array_goto_var = tk.StringVar(value="")
        self.array_goto_entry = ttk.Entry(ctrl, textvariable=self.array_goto_var, width=10)
        self.array_goto_entry.pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(ctrl, text="Go", command=self._array_goto_row).pack(side=tk.LEFT)

        # --- Treeview frame (with scrollbars) ---
        array_frame = ttk.Frame(array_outer)
        array_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        array_frame.rowconfigure(0, weight=1)
        array_frame.columnconfigure(0, weight=1)

        self.array_tree = ttk.Treeview(array_frame, show="headings")
        # Capture column width changes (user drag)
        self.array_tree.bind("<ButtonRelease-1>", self._on_array_header_release)
        self.array_tree.grid(row=0, column=0, sticky="nsew")

        self.array_ysb = ttk.Scrollbar(array_frame, orient="vertical", command=self.array_tree.yview)
        self.array_ysb.grid(row=0, column=1, sticky="ns")

        self.array_xsb = ttk.Scrollbar(array_frame, orient="horizontal", command=self.array_tree.xview)
        self.array_xsb.grid(row=1, column=0, sticky="ew")

        self.array_tree.configure(yscrollcommand=self.array_ysb.set, xscrollcommand=self.array_xsb.set)

        # Right-click to toggle row highlight
        self.array_tree.bind("<Button-3>", self._on_array_right_click)
        self.array_tree.bind("<Control-Button-3>", lambda e: self._clear_array_highlights())

        self.array_tree.tag_configure("hl", background="#fff2a8")

        # Row highlight style (yellow)
        self.array_tree.tag_configure("hl", background="#fff2a8")

        # ---------------- Smith Chart tab ----------------
        smith_frame = ttk.Frame(self.tab_smith)
        smith_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # two-column layout: chart (left) + info panel (right)
        smith_frame.rowconfigure(0, weight=1)
        smith_frame.columnconfigure(0, weight=1)
        smith_frame.columnconfigure(1, weight=0)
        smith_frame.columnconfigure(2, weight=0)

        left = ttk.Frame(smith_frame)
        left.grid(row=0, column=0, sticky="nsew")

        # vertical red separator
        sep = tk.Frame(smith_frame, width=2, bg="red")
        sep.grid(row=0, column=1, sticky="ns", padx=(6, 6))

        right = ttk.Frame(smith_frame, padding=(6, 6))
        right.grid(row=0, column=2, sticky="ns")

        # --- Smith chart figure/canvas on LEFT ---
        self.smith_fig = Figure(figsize=(7.2, 7.2), dpi=100)
        self.ax_smith = self.smith_fig.add_subplot(111)
        draw_smith_grid(self.ax_smith)
        self.ax_smith.set_title("EVC Zload on Smith Chart (Z0=50Ω)", fontsize=12)

        self.smith_canvas = FigureCanvasTkAgg(self.smith_fig, master=left)
        self.smith_canvas.draw()
        self.smith_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.smith_toolbar = NavigationToolbar2Tk(self.smith_canvas, left)
        self.smith_toolbar.update()

        # --- Info panel on RIGHT ---
        self._build_smith_info_panel(right)

        # connect hover events ONCE
        self._smith_motion_cid = self.smith_canvas.mpl_connect("motion_notify_event", self._on_smith_motion)
        self._smith_leave_cid = self.smith_canvas.mpl_connect("figure_leave_event", self._on_smith_leave)

    def _on_array_header_release(self, event):
        """
        Save current column widths after user resizes columns.
        Triggered after mouse release on header area.
        """
        try:
            cols = self.array_tree["columns"]
            for c in cols:
                self._array_col_widths[c] = int(self.array_tree.column(c, "width"))
        except Exception:
            pass

    def _on_array_right_click(self, event):
        """
        Right-click toggles highlight on the row under cursor.
        Allows multi-row highlights.
        """
        row_id = self.array_tree.identify_row(event.y)
        if not row_id:
            return

        # Toggle highlight tag
        if row_id in self._array_highlight_items:
            self._array_highlight_items.remove(row_id)
            self.array_tree.item(row_id, tags=())
        else:
            self._array_highlight_items.add(row_id)
            self.array_tree.item(row_id, tags=("hl",))

    def _clear_array_highlights(self):
        """Clear all highlighted rows."""
        for row_id in list(self._array_highlight_items):
            try:
                self.array_tree.item(row_id, tags=())
            except Exception:
                pass
        self._array_highlight_items.clear()

    def _build_smith_info_panel(self, parent):
        # StringVars to update on hover
        self.smith_vars = {
            "RL": tk.StringVar(value=""),
            "XL": tk.StringVar(value=""),
            "Gr": tk.StringVar(value=""),
            "Gi": tk.StringVar(value=""),
            "Pfwd": tk.StringVar(value=""),
            "Pref": tk.StringVar(value=""),
            "Time_ms": tk.StringVar(value=""),
            "Row": tk.StringVar(value=""),
            "C1%": tk.StringVar(value=""),
            "C2%": tk.StringVar(value=""),
            "Vpp": tk.StringVar(value=""),
            "Vcap": tk.StringVar(value=""),
            "DCBias": tk.StringVar(value=""),
            "Freq": tk.StringVar(value=""),
            "Duty": tk.StringVar(value=""),
            "Pmode": tk.StringVar(value=""),
            "V": tk.StringVar(value=""),
            "I": tk.StringVar(value=""),
            "Phs": tk.StringVar(value=""),
        }

        def add_group(title, fields, start_row):
            lf = ttk.LabelFrame(parent, text=title, padding=(8, 6))
            lf.grid(row=start_row, column=0, sticky="ew", pady=(0, 8))
            for i, (label, key) in enumerate(fields):
                ttk.Label(lf, text=label, width=7).grid(row=0, column=2 * i, sticky="w", padx=(0, 4))
                e = ttk.Entry(lf, textvariable=self.smith_vars[key], width=10, state="readonly")
                e.grid(row=0, column=2 * i + 1, sticky="w", padx=(0, 10))
            return start_row + 1

        parent.columnconfigure(0, weight=1)

        r = 0
        r = add_group("ZL", [("RL", "RL"), ("XL", "XL")], r)
        r = add_group("Gamma", [("Gr", "Gr"), ("Gi", "Gi")], r)
        r = add_group("Power", [("Pfwd", "Pfwd"), ("Pref", "Pref")], r)
        r = add_group("row()", [("row()", "Row")], r)
        r = add_group("Cap Pos.", [("C1%", "C1%"), ("C2%", "C2%")], r)
        r = add_group("Volt", [("Vpp", "Vpp"), ("Vcap", "Vcap"), ("DCBias", "DCBias")], r)
        r = add_group("Pulse", [("Freq", "Freq"), ("Duty", "Duty"), ("Pmode", "Pmode")], r)
        r = add_group("VI Sensor", [("V", "V"), ("I", "I"), ("Phase", "Phs")], r)
        # --- Power threshold slider (under VI Sensor) ---
        lf_th = ttk.LabelFrame(parent, text="Power threshold", padding=(8, 6))
        lf_th.grid(row=r, column=0, sticky="ew", pady=(0, 8))
        lf_th.columnconfigure(1, weight=1)

        ttk.Label(lf_th, text="0").grid(row=0, column=0, sticky="w")

        # ttk.Scale is smoother than tk.Scale and matches ttk style
        self.smith_pth_scale = ttk.Scale(
            lf_th,
            from_=0, to=2000,
            orient="horizontal",
            variable=self.smith_pth_var,
            command=self._on_smith_threshold_changed  # will be called frequently while dragging
        )
        self.smith_pth_scale.grid(row=0, column=1, sticky="ew", padx=(6, 6))

        ttk.Label(lf_th, text="2000W").grid(row=0, column=2, sticky="e")

        # Optional: show numeric value next to slider
        self.smith_pth_val_label = ttk.Label(lf_th, text="0 W", foreground="gray")
        self.smith_pth_val_label.grid(row=1, column=1, sticky="w", pady=(4, 0))

        # Hover highlight ring (created later after plotting)
        self._smith_hover_marker = None

    def _on_smith_threshold_changed(self, _val=None):
        """
        Called when slider moves. Debounce redraw to avoid heavy repaint.
        ttk.Scale passes _val as string.
        """
        if hasattr(self, "smith_pth_val_label"):
            try:
                self.smith_pth_val_label.config(text=f"{int(float(self.smith_pth_var.get()))} W")
            except Exception:
                pass

        # debounce redraw
        if self._smith_pth_after is not None:
            try:
                self.after_cancel(self._smith_pth_after)
            except Exception:
                pass

        self._smith_pth_after = self.after(120, self._update_smith_chart)

    def _on_tool_mode_changed(self):
        """
        Called when the user switches graph tool mode.
        For now:
          - NONE: hide hover tooltip
          - ARROW: enable hover tooltip
        """
        mode = (self.tool_mode_var.get() or "NONE").upper().strip()
        if mode != "ARROW":
            # Hide hover artists when leaving Arrow mode
            if self._hover_annot is not None:
                try:
                    self._hover_annot.set_visible(False)
                except Exception:
                    pass
            if self._hover_marker is not None:
                try:
                    self._hover_marker.set_visible(False)
                except Exception:
                    pass
            if hasattr(self, "canvas") and self.canvas is not None:
                self.canvas.draw_idle()

    def _fmt(self, val, nd=3):
        try:
            if val is None:
                return ""
            if isinstance(val, str):
                return val
            if isinstance(val, (float, np.floating)) and (np.isnan(val) or np.isinf(val)):
                return ""
            return f"{float(val):.{nd}f}"
        except Exception:
            return ""

    def _clear_smith_panel(self):
        if not hasattr(self, "smith_vars"):
            return
        for v in self.smith_vars.values():
            v.set("")
        if self._smith_hover_marker is not None:
            self._smith_hover_marker.set_visible(False)
        if hasattr(self, "smith_canvas") and self.smith_canvas is not None:
            self.smith_canvas.draw_idle()

    def _on_smith_leave(self, event):
        # mouse left the figure
        self._clear_smith_panel()

    def _on_smith_motion(self, event):
        # Only respond on smith axes
        if event.inaxes != self.ax_smith:
            return

        if not self._smith_data or "sets" not in self._smith_data or self.df is None or self.df.empty:
            return

        best = None  # (dist2, set_dict, point_idx)
        ex = event.xdata
        if ex is None or ey is None:
            return

        # Try Matplotlib's hit-test first (fast enough with 1~2 scatters)
        for s in self._smith_data["sets"]:
            artist = s["artist"]
            ok, hit = artist.contains(event)
            if ok and hit.get("ind") is not None and len(hit["ind"]) > 0:
                j = int(hit["ind"][0])
                dx = s["gx"][j] - ex
                dy = s["gy"][j] - ey
                d2 = dx * dx + dy * dy
                if best is None or d2 < best[0]:
                    best = (d2, s, j)

        # If no hit, clear panel (you can change to "keep last" if you prefer)
        if best is None:
            # keep last values; just hide marker
            if self._smith_hover_marker is not None:
                self._smith_hover_marker.set_visible(False)
                self.smith_canvas.draw_idle()
            return

        _, s, j = best
        # If hover target axis changes, we must recreate artists on that axis.
        target_ax = s["ax"]
        if self._hover_ax is not target_ax:
            # remove old artists (they belong to a different axes)
            if self._hover_annot is not None:
                try:
                    self._hover_annot.remove()
                except Exception:
                    pass
                self._hover_annot = None

            if self._hover_marker is not None:
                try:
                    self._hover_marker.remove()
                except Exception:
                    pass
                self._hover_marker = None

            self._hover_ax = target_ax
        row_i = int(s["row_index"][j])

        # Safely read row (works even if df is filtered)
        try:
            row = self.df.loc[row_i]
        except Exception:
            # fallback: cannot map row
            return

        # Extract RL/XL
        R = pd.to_numeric(row.get("RL", np.nan), errors="coerce")
        X = pd.to_numeric(row.get("XL", np.nan), errors="coerce")

        # Gamma from Z
        try:
            Z = complex(float(R), float(X))
            g = (Z - 50.0) / (Z + 50.0)
            Gr, Gi = np.real(g), np.imag(g)
        except Exception:
            Gr, Gi = np.nan, np.nan

        # Show row() instead of time
        rownum = ""
        if "row()" in self.df.columns:
            try:
                rownum = int(pd.to_numeric(row.get("row()"), errors="coerce"))
            except Exception:
                rownum = ""
        else:
            # fallback: show dataframe index if row() column missing
            rownum = row_i

        # Update panel fields (blank if missing)
        self.smith_vars["RL"].set(self._fmt(R, 2))
        self.smith_vars["XL"].set(self._fmt(X, 2))
        self.smith_vars["Gr"].set(self._fmt(Gr, 4))
        self.smith_vars["Gi"].set(self._fmt(Gi, 4))

        self.smith_vars["Pfwd"].set(self._fmt(pd.to_numeric(row.get("Pfwd", np.nan), errors="coerce"), 2))
        self.smith_vars["Pref"].set(self._fmt(pd.to_numeric(row.get("Pref", np.nan), errors="coerce"), 2))
        self.smith_vars["Row"].set(str(rownum))

        self.smith_vars["C1%"].set(self._fmt(pd.to_numeric(row.get("C1%", np.nan), errors="coerce"), 2))
        self.smith_vars["C2%"].set(self._fmt(pd.to_numeric(row.get("C2%", np.nan), errors="coerce"), 2))

        self.smith_vars["Vpp"].set(self._fmt(pd.to_numeric(row.get("Vpp", np.nan), errors="coerce"), 2))
        self.smith_vars["Vcap"].set(self._fmt(pd.to_numeric(row.get("Vcap", np.nan), errors="coerce"), 2))
        self.smith_vars["DCBias"].set(self._fmt(pd.to_numeric(row.get("DCBias", np.nan), errors="coerce"), 2))

        self.smith_vars["Freq"].set(self._fmt(pd.to_numeric(row.get("Freq", np.nan), errors="coerce"), 3))
        self.smith_vars["Duty"].set(self._fmt(pd.to_numeric(row.get("Duty", np.nan), errors="coerce"), 3))
        pm = int(pd.to_numeric(row.get("Pmode", 0), errors="coerce") or 0)
        self.smith_vars["Pmode"].set("Pulse" if pm == 1 else "CW")

        self.smith_vars["V"].set(self._fmt(pd.to_numeric(row.get("V", np.nan), errors="coerce"), 2))
        self.smith_vars["I"].set(self._fmt(pd.to_numeric(row.get("I", np.nan), errors="coerce"), 3))
        self.smith_vars["Phs"].set(self._fmt(pd.to_numeric(row.get("Phs", np.nan), errors="coerce"), 2))

        # Hover highlight ring
        if self._smith_hover_marker is None:
            self._smith_hover_marker = self.ax_smith.scatter(
                [], [], s=140, facecolors="none", edgecolors="red", linewidths=1.6, zorder=6
            )

        self._smith_hover_marker.set_offsets([[s["gx"][j], s["gy"][j]]])
        self._smith_hover_marker.set_visible(True)

        self.smith_canvas.draw_idle()

    def _array_prev_page(self):
        df = self.df if (self.df is not None and not self.df.empty) else self.df_raw
        if df is None or df.empty:
            return
        self.array_page_start = max(0, self.array_page_start - self.array_page_size)
        self._refresh_array_tab()

    def _array_next_page(self):
        df = self.df if (self.df is not None and not self.df.empty) else self.df_raw
        if df is None or df.empty:
            return
        total = len(df)
        self.array_page_start = min(max(0, total - 1), self.array_page_start + self.array_page_size)
        self._refresh_array_tab()

    def _array_goto_row(self):
        """
        Go to a specific row() (1-based as you created), not DataFrame index.
        """
        df = self.df if (self.df is not None and not self.df.empty) else self.df_raw
        if df is None or df.empty:
            return

        s = (self.array_goto_var.get() or "").strip()
        if not s:
            return

        try:
            rownum = int(float(s))
        except Exception:
            messagebox.showwarning("Go to row()", f"Invalid row(): {s}")
            return

        if rownum < 1:
            rownum = 1
        if rownum > len(df):
            rownum = len(df)

        # row() is 1-based, page_start is 0-based index
        idx0 = rownum - 1
        self.array_page_start = (idx0 // self.array_page_size) * self.array_page_size
        self._refresh_array_tab()

        # highlight the row inside current page
        within = idx0 - self.array_page_start
        children = self.array_tree.get_children()
        if 0 <= within < len(children):
            item = children[within]
            self.array_tree.selection_set(item)
            self.array_tree.focus(item)
            self.array_tree.see(item)

    def _build_plot_area(self):
        # -------- Graph Tools toolbar (Milestone A) --------
        tool_bar = ttk.Frame(self.tab_graph, padding=(6, 4))
        tool_bar.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(tool_bar, text="Tools:").pack(side=tk.LEFT, padx=(0, 8))

        # Use radiobuttons so only one tool is active at a time (JMP style)
        ttk.Radiobutton(tool_bar, text="None", value="NONE",
                        variable=self.tool_mode_var,
                        command=self._on_tool_mode_changed).pack(side=tk.LEFT)

        ttk.Radiobutton(tool_bar, text="Arrow", value="ARROW",
                        variable=self.tool_mode_var,
                        command=self._on_tool_mode_changed).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(tool_bar, text="  Hover Item:").pack(side=tk.LEFT, padx=(12, 4))

        self._arrow_target_cb = ttk.Combobox(
            tool_bar,
            textvariable=self.arrow_target_var,
            values=["Pfwd"],  # will be refreshed after plotting
            width=10,
            state="readonly"
        )
        self._arrow_target_cb.pack(side=tk.LEFT)

        # Future buttons placeholders (not active yet)
        ttk.Label(tool_bar, text="|  (Ruler / Annotate / Line / Shape coming next)",
                  foreground="gray").pack(side=tk.LEFT, padx=(12, 0))

        self.plot_frame = ttk.Frame(self.tab_graph)
        self.plot_frame.pack(fill=tk.BOTH, expand=True)

    # -------------------------------------------------------------------------
    # Plot Initialization
    # -------------------------------------------------------------------------
    def _init_plot(self):
        self.fig = Figure(figsize=(12, 6), dpi=100)
        gs = self.fig.add_gridspec(3, 1, height_ratios=[2.0, 1.2, 1.6], hspace=0.10)

        self.ax_power = self.fig.add_subplot(gs[0, 0])
        self.ax_caps = self.fig.add_subplot(gs[1, 0], sharex=self.ax_power)
        self.ax_vbias = self.fig.add_subplot(gs[2, 0], sharex=self.ax_power)
        self.axes = [self.ax_power, self.ax_caps, self.ax_vbias]

        self.ax_power.set_ylabel("Power (W)")
        self.ax_caps.set_ylabel("Caps (%)")
        self.ax_vbias.set_ylabel("V / Bias")
        self.ax_vbias.set_xlabel("t(ms)")

        for ax in self.axes:
            ax.grid(True, alpha=0.3)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        self.toolbar.update()

        # Events (zoom box)
        self.canvas.mpl_connect("motion_notify_event", self._on_mpl_motion)
        self.canvas.mpl_connect("button_press_event", self._on_mpl_press)
        self.canvas.mpl_connect("button_release_event", self._on_mpl_release)

    # -------------------------------------------------------------------------
    # Zoom(Drag) Zone — X-axis only (works with twinx overlays)
    # -------------------------------------------------------------------------
    def _init_zoom_zone(self):
        self.zoom_active = False
        self.zoom_last_y = None

        self.zoom_rect_axes = (0.93, 0.05, 0.06, 0.25)  # x,y,w,h in AXES coords

        # remove old patch/text if present
        if hasattr(self, "zoom_patch") and self.zoom_patch is not None:
            try:
                self.zoom_patch.remove()
            except Exception:
                pass
        if hasattr(self, "zoom_text") and self.zoom_text is not None:
            try:
                self.zoom_text.remove()
            except Exception:
                pass

        x, y, w, h = self.zoom_rect_axes
        self.zoom_patch = Rectangle((x, y), w, h, transform=self.ax_power.transAxes,
                                    facecolor="#ffeeee", edgecolor="red",
                                    linewidth=1.2, alpha=0.35)
        self.ax_power.add_patch(self.zoom_patch)
        self.zoom_text = self.ax_power.text(x + w / 2, y + h / 2, "ZOOM\n(Drag)",
                                            transform=self.ax_power.transAxes,
                                            ha="center", va="center",
                                            fontsize=9, color="red")

    def _event_in_zoom_zone(self, event) -> bool:
        """
        Accept events from ax_power or its twinx (ax_power_right) because twinx overlays
        can become event.inaxes.
        Always calculate coordinates in ax_power.transAxes.
        """
        valid_axes = {self.ax_power, getattr(self, "ax_power_right", None)}
        valid_axes.discard(None)

        if event.inaxes not in valid_axes:
            return False
        if event.x is None or event.y is None:
            return False

        inv = self.ax_power.transAxes.inverted()
        xa, ya = inv.transform((event.x, event.y))

        x, y, w, h = self.zoom_rect_axes
        return (x <= xa <= x + w) and (y <= ya <= y + h)

    def _on_mpl_motion(self, event):
        in_zone = self._event_in_zoom_zone(event)
        self.canvas.get_tk_widget().configure(cursor="hand2" if in_zone else "")
        # -------- Arrow Hover (Milestone B) --------
        if (self.tool_mode_var.get() or "NONE").upper().strip() == "ARROW":
            self._arrow_hover_update(event)
        if self.zoom_active and self.zoom_last_y is not None and event.y is not None:
            dy = event.y - self.zoom_last_y
            if abs(dy) >= 3:
                scale = 0.90 if dy > 0 else 1.10
                self._zoom_x(scale)
                self.zoom_last_y = event.y
                self.canvas.draw_idle()

    def _on_mpl_press(self, event):
        if event.button != 1:
            return
        if self._event_in_zoom_zone(event):
            self.zoom_active = True
            self.zoom_last_y = event.y

    def _on_mpl_release(self, event):
        self.zoom_active = False
        self.zoom_last_y = None

    def _zoom_x(self, scale: float):
        x0, x1 = self.ax_power.get_xlim()
        xc = (x0 + x1) / 2.0
        xr = (x1 - x0) * scale / 2.0
        new_xlim = (xc - xr, xc + xr)

        for ax in self.axes:
            ax.set_xlim(*new_xlim)
        if self.ax_power_right is not None:
            self.ax_power_right.set_xlim(*new_xlim)
        if self.ax_vbias_right is not None:
            self.ax_vbias_right.set_xlim(*new_xlim)

    def _arrow_hover_update(self, event):
        """Arrow tool: snap to nearest series point on the Graph tab."""
        if self.df is None or self.df.empty:
            return

        if event.inaxes is None or event.xdata is None or event.ydata is None:
            # hide when leaving axes
            if self._hover_annot is not None:
                try:
                    self._hover_annot.set_visible(False)
                except Exception:
                    pass
            if self._hover_marker is not None:
                try:
                    self._hover_marker.set_visible(False)
                except Exception:
                    pass
            self.canvas.draw_idle()
            return

        ex, ey = float(event.xdata), float(event.ydata)

        # Which series are eligible?
        # Treat twinx overlays as one hover region
        if event.inaxes in {self.ax_power, getattr(self, "ax_power_right", None)}:
            group_axes = {self.ax_power, getattr(self, "ax_power_right", None)}
        elif event.inaxes in {self.ax_vbias, getattr(self, "ax_vbias_right", None)}:
            group_axes = {self.ax_vbias, getattr(self, "ax_vbias_right", None)}
        else:
            group_axes = {event.inaxes}
        group_axes.discard(None)

        candidates = [s for s in self._plot_series_cache if s["ax"] in group_axes]

        # Ignore right-axis series for Arrow hover (keep them plotted, but no red circle)
        deny_labels = {"Freq", "Duty", "Pmode"}
        candidates = [s for s in candidates if s.get("label") not in deny_labels]
        # ---- Arrow hover: ignore right-axis series on Power plot ----
        deny_labels = {"Freq", "Duty", "Pmode"}
        candidates = [s for s in candidates if s.get("label") not in deny_labels]
        if not candidates:
            # Allow hover even if event.inaxes is twinx overlay by scanning all
            candidates = list(self._plot_series_cache)

        # Optional: respect manual dropdown selection (if present)
        target_label = None
        if hasattr(self, "arrow_target_var"):
            t = (self.arrow_target_var.get() or "").strip()
            if t:
                target_label = t
        if target_label:
            candidates2 = [s for s in candidates if s["label"] == target_label]
            if candidates2:
                candidates = candidates2

        best = None  # (score, s_dict, idx)
        for s in candidates:
            x = s["x"]
            y = s["y"]
            if x.size < 2:
                continue

            # nearest index by x (fast)
            i = int(np.searchsorted(x, ex))
            if i <= 0:
                idxs = [0]
            elif i >= x.size:
                idxs = [x.size - 1]
            else:
                idxs = [i - 1, i]

            # normalize dy by axis y-range so dx/dy comparable
            try:
                y0, y1 = s["ax"].get_ylim()
                yr = abs(y1 - y0) if abs(y1 - y0) > 1e-12 else 1.0
            except Exception:
                yr = 1.0

            for j in idxs:
                xv = x[j]
                yv = y[j]
                if not np.isfinite(xv) or not np.isfinite(yv):
                    continue
                dx = ex - float(xv)
                dy = (ey - float(yv)) / yr
                score = dx * dx + dy * dy
                if best is None or score < best[0]:
                    best = (score, s, j)

        if best is None:
            if self._hover_annot is not None:
                self._hover_annot.set_visible(False)
            if self._hover_marker is not None:
                self._hover_marker.set_visible(False)
            self.canvas.draw_idle()
            return

        _, s, j = best
        target_ax = s["ax"]

        # If hover target axis changes, recreate artists on that axis
        if self._hover_ax is not target_ax:
            if self._hover_annot is not None:
                try:
                    self._hover_annot.remove()
                except Exception:
                    pass
                self._hover_annot = None

            if self._hover_marker is not None:
                try:
                    self._hover_marker.remove()
                except Exception:
                    pass
                self._hover_marker = None

            self._hover_ax = target_ax

        xv = float(s["x"][j])
        yv = float(s["y"][j])
        label = s["label"]

        # row() mapping: j is index into current df used for plotting
        try:
            rownum = int(pd.to_numeric(self.df["row()"].iloc[j], errors="coerce"))
        except Exception:
            rownum = j + 1

        # Create annotation on correct axis
        if self._hover_annot is None:
            self._hover_annot = target_ax.annotate(
                "",
                xy=(xv, yv),
                xytext=(12, 12),
                textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9),
                arrowprops=dict(arrowstyle="->", color="gray", lw=1.0),
            )

        txt = f"{label}\nrow(): {rownum}\nt(s): {xv:.3f}\n{label}: {yv:.3f}"
        self._hover_annot.set_text(txt)
        self._hover_annot.xy = (xv, yv)
        self._hover_annot.set_visible(True)

        # Red circle marker on correct axis
        if self._hover_marker is None:
            self._hover_marker = target_ax.scatter(
                [xv], [yv],
                s=120, facecolors="none", edgecolors="red", linewidths=1.6, zorder=10
            )
        else:
            try:
                self._hover_marker.set_offsets([[xv, yv]])
                self._hover_marker.set_visible(True)
            except Exception:
                pass

        self.canvas.draw_idle()

    # -------------------------------------------------------------------------
    # Band Filter
    # -------------------------------------------------------------------------
    def _apply_band_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        band = (self.band_var.get() or "All").upper().strip()
        if band == "ALL":
            return df

        # Quantum: MN column is HF/LF
        if "MN" in df.columns:
            mn = df["MN"].astype(str).str.upper().str.strip()
            return df.loc[mn == band].copy()

        # Tykon fallback: use Freq threshold if meaningful
        if "Freq" in df.columns:
            freq = pd.to_numeric(df["Freq"], errors="coerce")
            if freq.notna().sum() == 0 or (freq.fillna(0) == 0).mean() > 0.95:
                return df  # cannot classify reliably
            med = float(freq.dropna().median())
            freq_mhz = (freq / 1e6) if med > 1000 else freq
            is_hf = freq_mhz >= 1.0
            if band == "HF":
                return df.loc[is_hf].copy()
            if band == "LF":
                return df.loc[~is_hf].copy()

        return df

    def _on_band_changed(self):
        if self.df_raw is None:
            return
        self.df = self._apply_band_filter(self.df_raw)
        self._update_plot()
        self._refresh_array_tab(max_rows=2500)
        self._update_smith_chart()

    # -------------------------------------------------------------------------
    # Full Scale + Custom Scale (JMP-like)
    # -------------------------------------------------------------------------
    def _on_full_scale(self):
        self.scale_mode = "auto"
        self._reset_full_scale()

    def _reset_full_scale(self):
        if self.df is None or self.df.empty or "t(s)" not in self.df.columns:
            return
        x = pd.to_numeric(self.df["t(s)"], errors="coerce").dropna()
        if x.empty:
            return
        xmin, xmax = float(x.min()), float(x.max())
        if xmin == xmax:
            xmin -= 0.5
            xmax += 0.5

        for ax in self.axes:
            ax.set_xlim(xmin, xmax)
        if self.ax_power_right is not None:
            self.ax_power_right.set_xlim(xmin, xmax)
        if self.ax_vbias_right is not None:
            self.ax_vbias_right.set_xlim(xmin, xmax)

        for ax in self.axes:
            ax.relim()
            ax.autoscale_view(scalex=False, scaley=True)

        if self.ax_power_right is not None:
            self.ax_power_right.relim()
            self.ax_power_right.autoscale_view(scalex=False, scaley=True)

        if self.ax_vbias_right is not None:
            self.ax_vbias_right.relim()
            self.ax_vbias_right.autoscale_view(scalex=False, scaley=True)

        self._init_zoom_zone()
        self.canvas.draw_idle()

    def _on_custom_scale(self):
        self._open_custom_scale_dialog()

    # ---------------- Smith chart update ----------------
    def _update_smith_chart(self):
        if not hasattr(self, "ax_smith") or self.ax_smith is None:
            return
        if not hasattr(self, "smith_canvas") or self.smith_canvas is None:
            return

        thr = 0.0
        if hasattr(self, "smith_pth_var"):
            try:
                thr = float(self.smith_pth_var.get())
            except Exception:
                thr = 0.0

        self.ax_smith.clear()
        self._smith_data = plot_smith_rlxl_hf_lf(
            self.ax_smith,
            self.df,
            z0=50.0,
            max_points=8000,
            pfwd_threshold=thr,
            title="EVC Zload on Smith Chart (Z0=50Ω)"
        )
        self._smith_hover_marker = None

        # If threshold filtering hides everything, clear the panel values too
        if hasattr(self, "smith_vars"):
            self._clear_smith_panel()

        self.smith_canvas.draw_idle()

    def _open_custom_scale_dialog(self):
        if hasattr(self, "_custom_scale_win") and self._custom_scale_win.winfo_exists():
            self._custom_scale_win.lift()
            self._custom_scale_win.focus_force()
            return

        win = tk.Toplevel(self)
        win.title("Custom Scale (JMP-style)")
        win.geometry("520x360")
        win.resizable(False, False)
        self._custom_scale_win = win

        def make_row(r, label, key_min, key_max):
            ttk.Label(win, text=label).grid(row=r, column=0, sticky="w", padx=10, pady=6)
            e_min = ttk.Entry(win, width=12)
            e_max = ttk.Entry(win, width=12)
            e_min.grid(row=r, column=1, padx=6)
            e_max.grid(row=r, column=2, padx=6)

            vmin = self.custom_scale.get(key_min)
            vmax = self.custom_scale.get(key_max)
            if vmin is not None:
                e_min.insert(0, str(vmin))
            if vmax is not None:
                e_max.insert(0, str(vmax))
            return e_min, e_max

        ttk.Label(win, text="Leave blank to keep auto/current scale.", foreground="gray")\
            .grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 4))
        ttk.Label(win, text="Min").grid(row=1, column=1)
        ttk.Label(win, text="Max").grid(row=1, column=2)

        row = 2
        x_min_e, x_max_e = make_row(row, "X axis: t(s)", "x_min", "x_max"); row += 1
        pL_min_e, pL_max_e = make_row(row, "Power Left (Pfwd/Pref/SetPt)", "pL_min", "pL_max"); row += 1
        pR_min_e, pR_max_e = make_row(row, "Power Right (Freq/Duty)", "pR_min", "pR_max"); row += 1
        c_min_e, c_max_e = make_row(row, "Caps (%) (C1/C2)", "c_min", "c_max"); row += 1
        vL_min_e, vL_max_e = make_row(row, "V/Bias Left (Vpp/Vcap/HVDC)", "vL_min", "vL_max"); row += 1
        vR_min_e, vR_max_e = make_row(row, "V/Bias Right (DCBias)", "vR_min", "vR_max"); row += 1

        def parse_entry(e):
            s = e.get().strip()
            if s == "":
                return None
            try:
                return float(s)
            except ValueError:
                raise ValueError(f"Invalid number: '{s}'")

        def on_apply(save_default=False):
            try:
                self.custom_scale["x_min"] = parse_entry(x_min_e)
                self.custom_scale["x_max"] = parse_entry(x_max_e)
                self.custom_scale["pL_min"] = parse_entry(pL_min_e)
                self.custom_scale["pL_max"] = parse_entry(pL_max_e)
                self.custom_scale["pR_min"] = parse_entry(pR_min_e)
                self.custom_scale["pR_max"] = parse_entry(pR_max_e)
                self.custom_scale["c_min"] = parse_entry(c_min_e)
                self.custom_scale["c_max"] = parse_entry(c_max_e)
                self.custom_scale["vL_min"] = parse_entry(vL_min_e)
                self.custom_scale["vL_max"] = parse_entry(vL_max_e)
                self.custom_scale["vR_min"] = parse_entry(vR_min_e)
                self.custom_scale["vR_max"] = parse_entry(vR_max_e)
            except Exception as e:
                messagebox.showerror("Custom Scale", str(e))
                return

            self.scale_mode = "custom"
            self._apply_custom_scale()
            if save_default:
                messagebox.showinfo("Custom Scale", "Saved as default for this session.")

        btn_frame = ttk.Frame(win)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=14)

        ttk.Button(btn_frame, text="Apply", command=lambda: on_apply(False)).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Save as Default", command=lambda: on_apply(True)).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Close", command=win.destroy).pack(side=tk.LEFT, padx=8)

    def _apply_custom_scale(self):
        if self.df is None or self.df.empty:
            return

        # X range
        x_min = self.custom_scale.get("x_min")
        x_max = self.custom_scale.get("x_max")
        if x_min is not None and x_max is not None and x_min != x_max:
            for ax in self.axes:
                ax.set_xlim(x_min, x_max)
            if self.ax_power_right is not None:
                self.ax_power_right.set_xlim(x_min, x_max)
            if self.ax_vbias_right is not None:
                self.ax_vbias_right.set_xlim(x_min, x_max)

        def set_ylim(ax, ymin, ymax):
            if ax is None:
                return
            if ymin is not None and ymax is not None and ymin != ymax:
                ax.set_ylim(ymin, ymax)

        set_ylim(self.ax_power, self.custom_scale.get("pL_min"), self.custom_scale.get("pL_max"))
        set_ylim(self.ax_power_right, self.custom_scale.get("pR_min"), self.custom_scale.get("pR_max"))
        set_ylim(self.ax_caps, self.custom_scale.get("c_min"), self.custom_scale.get("c_max"))
        set_ylim(self.ax_vbias, self.custom_scale.get("vL_min"), self.custom_scale.get("vL_max"))
        set_ylim(self.ax_vbias_right, self.custom_scale.get("vR_min"), self.custom_scale.get("vR_max"))

        self._init_zoom_zone()
        self.canvas.draw_idle()

    # -------------------------------------------------------------------------
    # File Load / UI actions
    # -------------------------------------------------------------------------
    def _on_browse(self):
        path = filedialog.askopenfilename(
            title="Select tlog file",
            filetypes=[("tlog text", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return
        self.file_path_var.set(path)
        self._load_and_plot_async(path)

    def _load_and_plot_async(self, path: str):
        # Show status in plot area
        self._clear_plot_axes(keep_zoom=True)
        self.ax_power.text(
            0.5, 0.5,
            "Loading & parsing tlog...\nPlease wait.",
            transform=self.ax_power.transAxes,
            ha="center", va="center", fontsize=12
        )
        self.canvas.draw_idle()

        def worker():
            try:
                df, unit_info, header_params = load_tlog(path)

                # Schedule UI update
                self.after(0, lambda d=df, u=unit_info, h=header_params: self._on_loaded(d, u, h))

            except Exception as e:
                import traceback
                tb = traceback.format_exc()

                # IMPORTANT: capture message before leaving except block (Python 3.13 clears 'e')
                msg = str(e)
                self.after(0, lambda m=msg: messagebox.showerror("Error", m))

        threading.Thread(target=worker, daemon=True).start()

    def _on_loaded(self, df: pd.DataFrame, unit_info: Dict[str, str], header_params: List[Tuple[str, str]]):
        self.band_var.set("All")
        self.df = self._apply_band_filter(df)
        self.unit_info = unit_info
        self.header_params = header_params

        ut = (unit_info.get("UnitType", "") or "").lower()
        if "quantum" in ut:
            self.unit_type_var.set("Quantum")
        elif "tykon" in ut:
            self.unit_type_var.set("Tykon")

        if not self.skip_unit_info_var.get():
            self.fw_var.set(unit_info.get("FW", ""))
            self.fpga_var.set(unit_info.get("FPGA", ""))
            self.sn_var.set(unit_info.get("SN", ""))

        self.df_raw = df
        self.df = self._apply_band_filter(df)

        self._refresh_plot_item_menu()
        self._refresh_parameter_tab()
        self._refresh_array_tab(max_rows=2500)

        defaults = []
        for c in ["Pfwd", "Pref", "SetPt", "Freq", "Duty", "C1%", "C2%", "Vpp", "DCBias"]:
            if self.df is not None and c in self.df.columns:
                defaults.append(c)

        for k, v in self.selected_items.items():
            v.set(k in defaults)

        self._update_plot()
        self._update_smith_chart()

        # reset Phase 3 results because df changed
        self.p3_results = None
        if hasattr(self, "btn_export_word"):
            self.btn_export_word.config(state="disabled")

    def _refresh_plot_item_menu(self):
        if self.df_raw is None:
            return

        df = self.df_raw
        candidates = []
        for c in df.columns:
            if c in ("row()", "time(s)", "time(ms)", "time0(s)", "t(s)"):
                continue
            s = df[c]
            if pd.api.types.is_numeric_dtype(s):
                candidates.append(c)
            else:
                samp = pd.to_numeric(s.head(200), errors="coerce")
                if samp.notna().sum() > 50:
                    candidates.append(c)

        priority = ["MN", "Pfwd", "Pref", "SetPt", "Freq", "Duty", "Pmode", "C1%", "C2%", "Vpp", "Vcap", "HVDC", "DCBias"]
        candidates = sorted(set(candidates), key=lambda x: (0, priority.index(x)) if x in priority else (1, x))
        self.available_plot_items = candidates

        self.plot_menu.delete(0, tk.END)
        self.selected_items.clear()

        def set_all(val: bool):
            for vv in self.selected_items.values():
                vv.set(val)
            self._update_plot()

        self.plot_menu.add_command(label="Select All", command=lambda: set_all(True))
        self.plot_menu.add_command(label="Select None", command=lambda: set_all(False))
        self.plot_menu.add_separator()

        for c in self.available_plot_items:
            var = tk.BooleanVar(value=False)
            self.selected_items[c] = var
            self.plot_menu.add_checkbutton(label=c, variable=var, command=self._update_plot)

        self._update_plot_menu_text()

    def _update_plot_menu_text(self):
        sel = [k for k, v in self.selected_items.items() if v.get()]
        if not sel:
            self.plot_menu_btn.config(text="(select...)")
        elif len(sel) <= 3:
            self.plot_menu_btn.config(text=", ".join(sel))
        else:
            self.plot_menu_btn.config(text=f"{sel[0]}, {sel[1]}, {sel[2]} +{len(sel)-3}")

    def _update_arrow_target_choices(self, sel):
        """
        Update Arrow hover dropdown choices based on currently selected plot items.
        Only numeric/meaningful items are shown.
        """
        if self._arrow_target_cb is None:
            return

        # If nothing selected, keep current but do not change list
        if not sel:
            return

        # Prefer power items first if they exist
        prefer_order = ["Pfwd", "Pref", "SetPt", "Pdel", "Freq", "Duty", "Pmode"]
        ordered = [x for x in prefer_order if x in sel] + [x for x in sel if x not in prefer_order]

        # Update dropdown list
        self._arrow_target_cb["values"] = ordered

        # If current selection is not in list, set a sensible default
        cur = (self.arrow_target_var.get() or "").strip()
        if cur not in ordered:
            self.arrow_target_var.set(ordered[0])

    def _refresh_parameter_tab(self):
        for item in self.param_tree.get_children():
            self.param_tree.delete(item)

        if not self.header_params:
            return

        param_rows = build_param_value_table(self.header_params)
        unit = self.unit_type_var.get().strip()
        desc_map = TYKON_DESC if unit == "Tykon" else QUANTUM_DESC

        def find_desc(sec: str, pid: int) -> str:
            if sec in desc_map and pid in desc_map[sec]:
                return desc_map[sec][pid]
            for sname, inner in desc_map.items():
                if pid in inner:
                    return inner[pid]
            return ""

        for sec, pid, val in param_rows:
            d = find_desc(sec, pid)
            self.param_tree.insert("", tk.END, values=(sec, pid, val, d))

    def _refresh_array_tab(self, max_rows: Optional[int] = None):
        # Pick df to display
        df = self.df if (self.df is not None and not self.df.empty) else self.df_raw
        if df is None or df.empty:
            for item in self.array_tree.get_children():
                self.array_tree.delete(item)
            if hasattr(self, "array_page_label"):
                self.array_page_label.config(text="Rows: -")
            return

        # Page size + clamp
        page_size = int(max_rows) if max_rows is not None else int(getattr(self, "array_page_size", 2500))
        total = int(len(df))

        start = int(getattr(self, "array_page_start", 0))
        if start < 0:
            start = 0
        if start >= total:
            start = max(0, total - page_size)
        self.array_page_start = start

        end = min(start + page_size, total)

        # --- Clear rows only (do not rebuild columns every time) ---
        for item in self.array_tree.get_children():
            self.array_tree.delete(item)

        cols = list(df.columns)
        sig = tuple(cols)

        # --- Configure columns ONLY if changed (new file / different df columns) ---
        if self._array_cols_signature != sig:
            self._array_cols_signature = sig
            self.array_tree["columns"] = cols

            # If no saved widths yet for this signature, create a reasonable default
            # Use 90 as fallback, but keep known important columns wider
            default_widths = {}
            for c in cols:
                if c in ("sec,_ms.", "sec,_ms", "Faults"):
                    default_widths[c] = 100
                elif c in ("Pls", "MN", "Stat", "RF:UC", "RF:S", "RF:UC-S"):
                    default_widths[c] = 40
                else:
                    default_widths[c] = 50

            # Reset saved widths dict for new signature (optional)
            # Keep any existing saved widths that match column names
            for c in cols:
                if c not in self._array_col_widths:
                    self._array_col_widths[c] = default_widths.get(c, 90)

            for c in cols:
                self.array_tree.heading(c, text=c)
                w = int(self._array_col_widths.get(c, default_widths.get(c, 90)))
                self.array_tree.column(c, width=w, minwidth=40, anchor=tk.W, stretch=False)

        else:
            # Signature same: just re-apply saved widths (keeps user drag widths)
            for c in cols:
                if c in self._array_col_widths:
                    self.array_tree.column(c, width=int(self._array_col_widths[c]), stretch=False)

        # --- Insert rows for current page ---
        page_df = df.iloc[start:end]
        for _, row_s in page_df.iterrows():
            row = []
            for col, val in zip(df.columns, row_s.tolist()):
                if col == "Pdel":
                    try:
                        row.append(f"{float(val):.1f}")
                    except Exception:
                        row.append("")
                else:
                    if isinstance(val, float) and pd.isna(val):
                        row.append("")
                    else:
                        row.append(val)

            self.array_tree.insert("", tk.END, values=row)

        # Label + buttons
        if hasattr(self, "array_page_label"):
            self.array_page_label.config(text=f"Rows {start + 1}–{end} / {total}")

        if hasattr(self, "btn_array_prev"):
            self.btn_array_prev.config(state=("normal" if start > 0 else "disabled"))
        if hasattr(self, "btn_array_next"):
            self.btn_array_next.config(state=("normal" if end < total else "disabled"))

    # -------------------------------------------------------------------------
    # Plot update
    # -------------------------------------------------------------------------
    def _rebuild_plot_series_cache(self, x_series):
        """Cache plotted lines for fast Arrow hover (Graph tab)."""
        self._plot_series_cache = []
        if self.df is None or self.df.empty:
            return

        try:
            x = np.asarray(pd.to_numeric(x_series, errors="coerce"), dtype=float)
        except Exception:
            return

        def add_line(ax, line_artist):
            if line_artist is None or (not line_artist.get_visible()):
                return
            label = line_artist.get_label()
            try:
                y = np.asarray(line_artist.get_ydata(), dtype=float)
            except Exception:
                return
            if len(y) != len(x):
                return

            self._plot_series_cache.append({
                "ax": ax,
                "label": label,
                "x": x,
                "y": y,
            })

        axes_to_scan = [self.ax_power, self.ax_caps, self.ax_vbias]
        if getattr(self, "ax_power_right", None) is not None:
            axes_to_scan.append(self.ax_power_right)
        if getattr(self, "ax_vbias_right", None) is not None:
            axes_to_scan.append(self.ax_vbias_right)

        for ax in axes_to_scan:
            try:
                for ln in ax.get_lines():
                    add_line(ax, ln)
            except Exception:
                pass

        # Refresh Arrow dropdown list (if you added one)
        if hasattr(self, "_arrow_target_cb") and hasattr(self, "arrow_target_var"):
            deny_labels = {"Freq", "Duty", "Pmode"}
            items = [x for x in sorted({s["label"] for s in self._plot_series_cache}) if x not in deny_labels]
            if items:
                self._arrow_target_cb["values"] = items
                if (self.arrow_target_var.get() or "").strip() not in items:
                    self.arrow_target_var.set(items[0])

    def _clear_plot_axes(self, keep_zoom: bool = True):
        # Remove twin axes
        if self.ax_vbias_right is not None:
            try:
                self.fig.delaxes(self.ax_vbias_right)
            except Exception:
                pass
            self.ax_vbias_right = None

        if self.ax_power_right is not None:
            try:
                self.fig.delaxes(self.ax_power_right)
            except Exception:
                pass
            self.ax_power_right = None

        for ax in self.axes:
            ax.clear()
            ax.grid(True, alpha=0.3)

        self.ax_power.set_ylabel("Power (W)")
        self.ax_caps.set_ylabel("Caps (%)")
        self.ax_vbias.set_ylabel("Vpp/Vcap")
        self.ax_vbias.set_xlabel("t(ms)")

        if keep_zoom:
            self._init_zoom_zone()

    def _update_plot(self):
        if self.df is None:
            return

        self._update_plot_menu_text()

        if self.df.empty:
            self._clear_plot_axes(keep_zoom=True)
            self.ax_power.text(0.5, 0.5, f"No data after Band Filter = {self.band_var.get()}",
                               transform=self.ax_power.transAxes, ha="center", va="center", fontsize=12)
            # Build hover cache for Arrow tool
            self._rebuild_plot_series_cache(x)
            self.canvas.draw_idle()
            return

        df = self.df
        if "t(s)" not in df.columns:
            messagebox.showerror("Error", "Missing 't(s)' column.")
            return

        x = pd.to_numeric(df["t(s)"], errors="coerce")
        sel = [k for k, v in self.selected_items.items() if v.get()]
        self._update_arrow_target_choices(sel)
        self._clear_plot_axes(keep_zoom=False)

        if not sel:
            self.ax_power.text(0.5, 0.5, "Select items to plot",
                               transform=self.ax_power.transAxes, ha="center", va="center", fontsize=12)
            self._init_zoom_zone()
            self.canvas.draw_idle()
            return

        # Grouping sets
        power_left_set = {"Pfwd", "Pref", "SetPt", "Pdel"}
        power_right_set = {"Freq", "Duty", "Pmode"}         # <-- your request
        caps_set = {"C1%", "C2%"}
        vbias_left_set = {"Vpp", "Vcap", "DcV", "HVDC", "Ibias"}
        vbias_right_set = {"DCBias"}

        def group_of(col: str) -> str:
            if col in power_right_set:
                return "power_right"
            if col in power_left_set:
                return "power"
            if col in caps_set:
                return "caps"
            if col in vbias_left_set or col in vbias_right_set:
                return "vbias"
            # fallback by name
            c = col.lower()
            if c in ("freq", "duty"):
                return "power_right"
            if "pfwd" in c or "pref" in c or "setpt" in c or "pdel" in c:
                return "power"
            if "c1" in c or "c2" in c:
                return "caps"
            if "vpp" in c or "vcap" in c or "hvdc" in c or "dcv" in c or "dcbias" in c:
                return "vbias"
            return "power"

        # Create twin axes only if needed
        need_power_right = any(group_of(c) == "power_right" for c in sel)
        if need_power_right:
            self.ax_power_right = self.ax_power.twinx()
            self.ax_power_right.set_ylabel("Freq / Duty / Pmode")

        need_vbias_right = any(c in vbias_right_set for c in sel)
        if need_vbias_right:
            self.ax_vbias_right = self.ax_vbias.twinx()
            self.ax_vbias_right.set_ylabel("DCBias")

        h_power_l, h_power_r, h_caps, h_vl, h_vr = [], [], [], [], []

        for col in sel:
            if col not in df.columns:
                continue

            y = pd.to_numeric(df[col], errors="coerce")
            g = group_of(col)

            if g == "power":
                ln, = self.ax_power.plot(x, y, linewidth=1.0, label=col)
                h_power_l.append(ln)

            elif g == "power_right":
                if self.ax_power_right is None:
                    self.ax_power_right = self.ax_power.twinx()
                    self.ax_power_right.set_ylabel("Freq / Duty / Pmode")

                if col == "Pmode":
                    ln, = self.ax_power_right.step(x, y, where="post",
                                                   linewidth=1.2, label=col, color="black")
                else:
                    ln, = self.ax_power_right.plot(x, y, linewidth=1.0, label=col, linestyle="--")

                h_power_r.append(ln)

            elif g == "caps":
                ln, = self.ax_caps.plot(x, y, linewidth=1.0, label=col)
                h_caps.append(ln)

            else:  # vbias
                if self.ax_vbias_right is not None and col in vbias_right_set:
                    ln, = self.ax_vbias_right.plot(x, y, linewidth=1.0, label=col, color="tab:red")
                    h_vr.append(ln)
                else:
                    ln, = self.ax_vbias.plot(x, y, linewidth=1.0, label=col)
                    h_vl.append(ln)

        title = os.path.basename(self.file_path_var.get()) or "tlog"
        self.ax_power.set_title(title)

        # Legends
        if h_power_l or h_power_r:
            handles = h_power_l + h_power_r
            labels = [h.get_label() for h in handles]
            self.ax_power.legend(handles, labels, loc="upper left", fontsize=9)

        if h_caps:
            self.ax_caps.legend(loc="upper left", fontsize=9)

        if h_vl or h_vr:
            handles = h_vl + h_vr
            labels = [h.get_label() for h in handles]
            self.ax_vbias.legend(handles, labels, loc="upper left", fontsize=9)

        self._init_zoom_zone()

        # If custom scale mode, re-apply custom limits after plotting
        if self.scale_mode == "custom":
            self._apply_custom_scale()
        # Build hover cache for Arrow tool (Milestone B)
        self._rebuild_plot_series_cache(x)
        self._rebuild_plot_series_cache(x)
        self.canvas.draw_idle()

    # -------------------------------------------------------------------------
    # Buttons
    # -------------------------------------------------------------------------
    def _on_clear(self):
        for v in self.selected_items.values():
            v.set(False)
        self._update_plot_menu_text()

        self._clear_plot_axes(keep_zoom=True)
        self.ax_power.text(0.5, 0.5, "Cleared",
                           transform=self.ax_power.transAxes, ha="center", va="center", fontsize=12)
        self.canvas.draw_idle()

        self.p3_results = None
        if hasattr(self, "btn_export_word"):
            self.btn_export_word.config(state="disabled")

    def _on_export_graph(self):
        if self.df is None:
            messagebox.showinfo("Export", "No plot to export yet.")
            return

        # Build default filename: UnitType + SN + yyyymmdd
        unit_type = (self.unit_type_var.get() or "Unit").strip().replace(" ", "")
        sn = (self.sn_var.get() or "SN").strip().replace(" ", "")
        date_code = __import__("datetime").datetime.now().strftime("%Y%m%d")

        default_name = f"{unit_type}_{sn}_{date_code}.jpg"

        path = filedialog.asksaveasfilename(
            title="Export graph",
            defaultextension=".jpg",
            initialfile=default_name,
            filetypes=[("JPG", "*.jpg"), ("PNG", "*.png"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            self.fig.savefig(path, dpi=200)
            messagebox.showinfo("Export", f"Saved:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _on_analysis(self):
        if self.df is None or self.df.empty:
            messagebox.showwarning("Analysis", "No tlog loaded.")
            return

        # Reset previous analysis
        self.p3_results = None
        self.btn_export_word.config(state="disabled")

        unit_type = (self.unit_type_var.get() or "").strip()
        tlog_path = self.file_path_var.get().strip()
        base_dir = os.path.dirname(tlog_path) if tlog_path else os.getcwd()
        self.p3_artifacts_dir = os.path.join(base_dir, "p3_artifacts")

        # Show quick status
        messagebox.showinfo("Analysis", "Phase 3 analysis started. Please wait...")

        def worker():
            try:
                # Defaults per your requirement
                results = p3_run_analysis(
                    self.df,
                    unit_type=unit_type,
                    artifacts_dir=self.p3_artifacts_dir,
                    active_thr_w=3.0,
                    tol_pct=2.0,  # adjustable later
                    settle_ms=6.0,  # adjustable later
                    pref_ratio=0.01,
                    mask_ms=3.0,
                    fmin_khz=0.01,
                    fmax_khz=50.0,
                    dmin_pct=10.0,
                    dmax_pct=90.0
                )
                self.after(0, lambda r=results: self._on_analysis_done(r))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda m=msg: messagebox.showerror("Analysis failed", m))

        threading.Thread(target=worker, daemon=True).start()

    def _on_analysis_done(self, results: Dict[str, Any]):
        self.p3_results = results
        self.btn_export_word.config(state="normal")

        s4 = results.get("step4_forward", {})
        s5 = results.get("step5_reflect", {})
        pa = results.get("pulse_alarm", {})

        msg = []
        msg.append(f"Done. Cycles detected: {results.get('cycle_count', 0)}")

        if s4.get("available"):
            msg.append(f"Step 4 (Pfwd vs setpoint) flagged cycles: {len(s4.get('trouble_cases', []))}")
            msg.append(f"  Setpoint col: {s4.get('setpoint_col')}")
        else:
            msg.append(f"Step 4 skipped: {s4.get('reason', '')}")

        if s5.get("available"):
            msg.append(f"Step 5 (Pref high) flagged cycles: {len(s5.get('trouble_cases', []))}")
        else:
            msg.append(f"Step 5 unavailable: {s5.get('reason', '')}")

        if pa.get("available"):
            msg.append(f"Pulse mode range alarms: {len(pa.get('alarms', []))}")

        messagebox.showinfo("Analysis Summary", "\n".join(msg))

    def _on_export_word(self):
        if not self.p3_results:
            messagebox.showwarning("Export", "Please run Analysis first.")
            return

        tlog_path = self.file_path_var.get().strip()
        tlog_filename = os.path.basename(tlog_path) if tlog_path else "tlog"

        default_name = f"{(self.unit_type_var.get() or 'Unit').strip()}_{(self.sn_var.get() or 'SN').strip()}_{datetime.now().strftime('%Y%m%d_%H%M')}_P3_Report.docx"
        out_path = filedialog.asksaveasfilename(
            title="Save Phase 3 report",
            defaultextension=".docx",
            initialfile=default_name,
            filetypes=[("Word document", "*.docx")]
        )
        if not out_path:
            return

        try:
            r = self.p3_results
            _p3_export_word_report(
                out_docx=out_path,
                unit_type=r.get("unit_type", self.unit_type_var.get()),
                tlog_filename=tlog_filename,
                artifacts=r.get("artifacts", {}),
                cycles=r.get("cycles", []),
                step4=r.get("step4_forward", {}),
                step5=r.get("step5_reflect", {}),
                pulse_alarm=r.get("pulse_alarm", {}),
                settings=r.get("settings", {}),
                step3_metrics=r.get("step3_metrics",[]),
                unit_fw=self.fw_var.get(),
                unit_fpga=self.fpga_var.get(),
                unit_sn=self.sn_var.get()
            )
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            messagebox.showerror("Export failed", str(e))
            return

        messagebox.showinfo("Export", f"Report saved:\n{out_path}")

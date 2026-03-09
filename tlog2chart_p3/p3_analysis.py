from __future__ import annotations
from .version import APP_NAME, APP_VERSION
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from .utils import read_project_version

# =============================================================================
# -------------------------- Phase 3 Basic Analysis Engine ---------------------
# =============================================================================
def _p3_get_graph_time_ms(df: pd.DataFrame) -> np.ndarray:
    """
    Return the ms timebase that matches what the Graph tab displays.
    Priority:
      1) time(ms) if present (already in ms)
      2) t(s) * 1000
      3) time(s) * 1000
      4) fallback to existing _p3_get_t_ms(df)
    """
    if df is None or df.empty:
        return np.array([], dtype=float)

    if "time(ms)" in df.columns:
        return pd.to_numeric(df["time(ms)"], errors="coerce").to_numpy(dtype=float)

    if "t(s)" in df.columns:
        return pd.to_numeric(df["t(s)"], errors="coerce").to_numpy(dtype=float) * 1000.0

    if "time(s)" in df.columns:
        return pd.to_numeric(df["time(s)"], errors="coerce").to_numpy(dtype=float) * 1000.0

    # fallback (your existing implementation)
    return _p3_get_t_ms(df)

def _p3_get_t_ms(df: pd.DataFrame) -> np.ndarray:
    """
    Use continuous time from t(s) if available, convert to ms.
    Fallback to time(s)+time(ms). Final fallback: row index.
    """
    if df is None or df.empty:
        return np.array([], dtype=float)

    if "t(s)" in df.columns:
        t_s = pd.to_numeric(df["t(s)"], errors="coerce").ffill().fillna(0.0)
        return (t_s.to_numpy(dtype=float) * 1000.0)

    if "time(s)" in df.columns and "time(ms)" in df.columns:
        ts = pd.to_numeric(df["time(s)"], errors="coerce").ffill().fillna(0.0).to_numpy(dtype=float)
        tms = pd.to_numeric(df["time(ms)"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        base = ts[0] if len(ts) else 0.0
        return ((ts - base) * 1000.0 + tms)

    # last resort
    return np.arange(len(df), dtype=float)

def _p3_get_last_zoom_window(
    df: pd.DataFrame,
    active_thr_w: float = 3.0,
    zoom_factor: float = 100.0,
    pad_after: float = 0.05
):
    """
    Return (mask, x0, x1, anchor_idx) for Step 2:
      - anchor on last index where Pfwd > active_thr_w (if none, last row)
      - window width = full_span / zoom_factor
      - x0 = t_anchor - window
      - x1 = t_anchor + window*pad_after
    """
    t = _p3_get_t_ms(df)
    if t.size == 0:
        return None, None, None, None

    full_span = float(t[-1] - t[0])
    if full_span <= 0:
        anchor_idx = len(df) - 1
        return np.ones(len(df), dtype=bool), float(t[0]), float(t[-1]), anchor_idx

    win = full_span / float(zoom_factor)

    pfwd = pd.to_numeric(df.get("Pfwd", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
    idx = np.where(pfwd > active_thr_w)[0]
    anchor_idx = int(idx[-1]) if len(idx) else (len(df) - 1)

    t_last = float(t[anchor_idx])
    x0 = max(float(t[0]), t_last - win)
    x1 = min(float(t[-1]), t_last + win * float(pad_after))

    mask = (t >= x0) & (t <= x1)
    if not mask.any():
        n = min(500, len(df))
        mask = np.zeros(len(df), dtype=bool)
        mask[-n:] = True
        x0 = float(t[-n])
        x1 = float(t[-1])

    return mask, x0, x1, anchor_idx

def _p3_pick_rfuc_column(df: pd.DataFrame) -> str:
    """
    Your header normalizer splits 'RF:UC-S' into 'RF:UC' and 'RF:S'.
    Prefer 'RF:UC'. Fall back to raw names if needed.
    """
    for c in ("RF:UC", "Rf:UC", "RF:UC-S", "Rf:UC-S"):
        if c in df.columns:
            return c
    return ""

def _p3_detect_cycles_from_rf_status(df: pd.DataFrame, rf_col: str = "RF") -> List[Dict[str, float]]:
    """
    Detect RF ON/OFF cycles from a status column (Chronos 2.0 uses 'RF'). [1](https://oneasm-my.sharepoint.com/personal/victor_huang_asm_com/Documents/Microsoft%20Copilot%20Chat%20Files/02-Tykon1213-EDCM_EvalWoDepo_RF50ms_10000Cyc%20-%20Copy.txt)
    Assumes values like Y/N (or ON/OFF).
    Returns cycles with start_idx/end_idx (row indices).
    """
    s = df[rf_col].astype(str).fillna("").str.strip()

    # Treat these as ON
    on = s.isin(["Y", "1", "ON", "On", "TRUE", "True"])

    cycles: List[Dict[str, float]] = []
    in_on = False
    start = None

    for idx, is_on in enumerate(on.to_numpy()):
        if (not in_on) and is_on:
            in_on = True
            start = idx
        elif in_on and (not is_on):
            end = idx - 1
            if start is not None and end >= start:
                cycles.append({"start_idx": float(start), "end_idx": float(end)})
            in_on = False
            start = None

    # file ends while still ON
    if in_on and start is not None:
        end = len(df) - 1
        if end >= start:
            cycles.append({"start_idx": float(start), "end_idx": float(end)})

    return cycles


def _p3_detect_cycles_from_rfuc(df: pd.DataFrame) -> List[Dict[str, float]]:
    """
    Detect RF ON/OFF cycles using RF:UC:
      '*' = RF ON
      '-' = RF OFF

    Returns list of cycles with start_idx/end_idx and timing.
    """
    if df is None or df.empty:
        return []

    col = _p3_pick_rfuc_column(df)
    if not col:
        return []

    t = _p3_get_t_ms(df)  # ms
    uc = df[col].astype(str).str.strip()

    on = uc.eq("*").to_numpy(dtype=bool)

    # edges
    edges = np.diff(on.astype(int), prepend=int(on[0]))
    rise = np.where(edges == 1)[0]
    fall = np.where(edges == -1)[0] - 1  # inclusive end

    if on[0] and (len(rise) == 0 or rise[0] != 0):
        rise = np.insert(rise, 0, 0)

    if on[-1]:
        if len(fall) == 0 or fall[-1] < rise[-1]:
            fall = np.append(fall, len(on) - 1)

    cycles = []
    for s, e in zip(rise, fall):
        if e <= s:
            continue
        cycles.append({
            "start_idx": int(s),
            "end_idx": int(e),
            "start_t_ms": float(t[s]),
            "end_t_ms": float(t[e]),
            "duration_ms": float(t[e] - t[s])
        })

    return cycles

def _p3_calc_first6_cycle_metrics_rfuc(
    df: pd.DataFrame,
    cycles: List[Dict[str, float]],
    unit_type: str,
    settle_ms: float = 6.0
) -> List[Dict[str, object]]:
    if df is None or df.empty or not cycles:
        return []

    t = _p3_get_t_ms(df)  # ms
    pfwd_all = pd.to_numeric(df.get("Pfwd", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)

    # setpoint column (Tykon usually has SetPt; sometimes Pset)
    sp_col = None
    if (unit_type or "").strip().lower() == "tykon":
        if "SetPt" in df.columns:
            sp_col = "SetPt"
        elif "Pset" in df.columns:
            sp_col = "Pset"

    pmode_all = None
    if "Pmode" in df.columns:
        pmode_all = pd.to_numeric(df["Pmode"], errors="coerce").fillna(0).astype(int).to_numpy()

    freq_all = pd.to_numeric(df["Freq"], errors="coerce").to_numpy(dtype=float) if "Freq" in df.columns else None
    duty_all = pd.to_numeric(df["Duty"], errors="coerce").to_numpy(dtype=float) if "Duty" in df.columns else None

    out = []
    first6 = cycles[:6]
    prev_end_t = None

    for i, c in enumerate(first6, start=1):
        s = int(c["start_idx"])
        e = int(c["end_idx"])
        ts = float(t[s])
        te = float(t[e])
        on_time = max(0.0, te - ts)

        # idle time before this cycle
        idle_time = None if prev_end_t is None else max(0.0, ts - prev_end_t)
        prev_end_t = te

        seg_pfwd = pfwd_all[s:e+1]
        seg_t = t[s:e+1]

        # setpoint (Tykon)
        setpoint = None
        if sp_col is not None:
            seg_sp = pd.to_numeric(df[sp_col].iloc[s:e+1], errors="coerce").dropna()
            if len(seg_sp) > 0:
                setpoint = float(seg_sp.median())

        # settle window end
        settle_end_t = ts + float(settle_ms)
        settle_end_idx = int(np.searchsorted(t, settle_end_t, side="right") - 1)
        settle_end_idx = int(np.clip(settle_end_idx, s, e))

        ss_seg = pfwd_all[settle_end_idx:e+1] if settle_end_idx < e else pfwd_all[s:e+1]
        pfwd_steady = float(np.nanmean(ss_seg)) if len(ss_seg) else float(np.nanmean(seg_pfwd))

        # target for rise/overshoot reference
        target = setpoint if (setpoint is not None and setpoint > 0) else pfwd_steady

        # overshoot
        pfwd_peak = float(np.nanmax(seg_pfwd)) if len(seg_pfwd) else float("nan")
        overshoot_w = float(pfwd_peak - target) if (target is not None and np.isfinite(pfwd_peak)) else None
        overshoot_pct = (100.0 * overshoot_w / target) if (overshoot_w is not None and target and target > 0) else None

        # Rise time = time to reach 95% of target (your choice C)
        rise_to_95 = None
        if target is not None and target > 0 and len(seg_pfwd) >= 2:
            th95 = 0.95 * target
            idx95 = np.where(seg_pfwd >= th95)[0]
            if len(idx95) > 0:
                j95 = int(idx95[0])
                rise_to_95 = float(seg_t[j95] - seg_t[0])

        # Mode from Pmode within ON window
        mode = "CW"
        freq_med = None
        duty_med = None
        if pmode_all is not None:
            seg_pm = pmode_all[s:e+1]
            if np.any(seg_pm == 1):
                mode = "Pulse"
                if freq_all is not None:
                    fv = freq_all[s:e+1]
                    fv = fv[np.isfinite(fv)]
                    if fv.size > 0:
                        freq_med = float(np.median(fv))
                if duty_all is not None:
                    dv = duty_all[s:e+1]
                    dv = dv[np.isfinite(dv)]
                    if dv.size > 0:
                        duty_med = float(np.median(dv))

        start_row = int(df.iloc[s].get("row()", s+1)) if "row()" in df.columns else s+1

        out.append({
            "cycle": i,
            "start_row": start_row,
            "setpoint_w": setpoint,
            "pfwd_steady_w": pfwd_steady,
            "pfwd_peak_w": pfwd_peak,
            "overshoot_w": overshoot_w,
            "overshoot_pct": overshoot_pct,
            "rise_to_95_ms": rise_to_95,
            "rf_on_ms": on_time,
            "idle_before_ms": idle_time,
            "mode": mode,
            "freq_khz_med": freq_med,
            "duty_pct_med": duty_med
        })

    return out

def _p3_detect_cycles(df: pd.DataFrame,
                     pfwd_threshold_w: float = 3.0,
                     min_on_ms: float = 0.5,
                     min_off_ms: float = 0.5) -> List[Dict[str, float]]:
    """
    Detect RF ON cycles using Pfwd threshold.
    Returns list of cycles dict with indices and timing.
    """
    if df is None or df.empty or "Pfwd" not in df.columns:
        return []

    t = _p3_get_t_ms(df)
    pfwd = pd.to_numeric(df["Pfwd"], errors="coerce").fillna(0.0).to_numpy(dtype=float)

    on = pfwd > pfwd_threshold_w
    if len(on) == 0:
        return []

    edges = np.diff(on.astype(int), prepend=int(on[0]))
    rise = np.where(edges == 1)[0]
    fall = np.where(edges == -1)[0] - 1

    if on[0] and (len(rise) == 0 or rise[0] != 0):
        rise = np.insert(rise, 0, 0)
    if on[-1]:
        if len(fall) == 0 or fall[-1] < rise[-1]:
            fall = np.append(fall, len(on) - 1)

    cycles = []
    for s, e in zip(rise, fall):
        if e <= s:
            continue
        dur = float(t[e] - t[s])
        if dur < min_on_ms:
            continue
        cycles.append({
            "start_idx": int(s),
            "end_idx": int(e),
            "start_t_ms": float(t[s]),
            "end_t_ms": float(t[e]),
            "duration_ms": dur
        })

    # merge cycles if off gap too short (noise)
    merged = []
    for c in cycles:
        if not merged:
            merged.append(c)
            continue
        prev = merged[-1]
        off_gap = c["start_t_ms"] - prev["end_t_ms"]
        if off_gap < min_off_ms:
            prev["end_idx"] = c["end_idx"]
            prev["end_t_ms"] = c["end_t_ms"]
            prev["duration_ms"] = prev["end_t_ms"] - prev["start_t_ms"]
        else:
            merged.append(c)

    return merged

def _p3_pick_setpoint_col(df: pd.DataFrame) -> Optional[str]:
    # Prefer SetPt, then Pset (if exists)
    if "SetPt" in df.columns:
        return "SetPt"
    if "Pset" in df.columns:
        return "Pset"
    return None


def _p3_calc_first6_cycle_metrics_rfuc(
    df: pd.DataFrame,
    cycles_uc: List[Dict[str, float]],
    unit_type: str,
    settle_ms: float = 6.0
) -> List[Dict[str, object]]:
    """
    Step 3 metrics for first 6 RF cycles based on RF:UC.
    Rise time = time to reach 95% of SetPt (always) when SetPt exists.
    """
    if df is None or df.empty or not cycles_uc:
        return []

    t = _p3_get_t_ms(df)  # ms
    pfwd_all = pd.to_numeric(df.get("Pfwd", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)

    sp_col = _p3_pick_setpoint_col(df)

    pmode_all = None
    if "Pmode" in df.columns:
        pmode_all = pd.to_numeric(df["Pmode"], errors="coerce").fillna(0).astype(int).to_numpy()

    freq_all = pd.to_numeric(df["Freq"], errors="coerce").to_numpy(dtype=float) if "Freq" in df.columns else None
    duty_all = pd.to_numeric(df["Duty"], errors="coerce").to_numpy(dtype=float) if "Duty" in df.columns else None

    out = []
    prev_end_t = None

    for i, c in enumerate(cycles_uc, start=1):
        s = int(c["start_idx"])
        e = int(c["end_idx"])
        ts = float(t[s])
        te = float(t[e])
        rf_on_ms = max(0.0, te - ts)

        idle_before_ms = None if prev_end_t is None else max(0.0, ts - prev_end_t)
        prev_end_t = te

        seg_pfwd = pfwd_all[s:e+1]
        seg_t = t[s:e+1]

        # --- Setpoint target: "SetPt always" (use SetPt as reference whenever available)
        setpoint_w = None
        if sp_col is not None:
            sp_seg = pd.to_numeric(df[sp_col].iloc[s:e+1], errors="coerce").dropna()
            if len(sp_seg) > 0:
                # "SetPt always": use the SetPt value during the cycle.
                # If SetPt is constant, median == constant. If not, median is robust.
                setpoint_w = float(sp_seg.median())

        # --- steady Pfwd mean after settle
        settle_end_t = ts + float(settle_ms)
        settle_end_idx = int(np.searchsorted(t, settle_end_t, side="right") - 1)
        settle_end_idx = int(np.clip(settle_end_idx, s, e))

        ss_seg = pfwd_all[settle_end_idx:e+1] if settle_end_idx < e else pfwd_all[s:e+1]
        pfwd_steady_w = float(np.nanmean(ss_seg)) if len(ss_seg) else float(np.nanmean(seg_pfwd))

        # target for overshoot/rise:
        # - If SetPt exists: always use SetPt
        # - Else (Quantum): use steady Pfwd as fallback
        target = setpoint_w if (setpoint_w is not None and setpoint_w > 0) else pfwd_steady_w

        # --- overshoot peak relative to target
        pfwd_peak_w = float(np.nanmax(seg_pfwd)) if len(seg_pfwd) else float("nan")
        overshoot_w = float(pfwd_peak_w - target) if np.isfinite(pfwd_peak_w) else None
        overshoot_pct = (100.0 * overshoot_w / target) if (overshoot_w is not None and target > 0) else None

        # --- rise time: to reach 95% of SetPt (your choice C)
        rise_to_95_ms = None
        if target is not None and target > 0 and len(seg_pfwd) >= 2:
            th95 = 0.95 * target
            idx95 = np.where(seg_pfwd >= th95)[0]
            if len(idx95) > 0:
                j95 = int(idx95[0])
                rise_to_95_ms = float(seg_t[j95] - seg_t[0])

        # --- CW vs Pulse from Pmode within ON
        mode = "CW"
        freq_khz_med = None
        duty_pct_med = None
        if pmode_all is not None:
            seg_pm = pmode_all[s:e+1]
            if np.any(seg_pm == 1):
                mode = "Pulse"
                if freq_all is not None:
                    fv = freq_all[s:e+1]
                    fv = fv[np.isfinite(fv)]
                    if fv.size > 0:
                        freq_khz_med = float(np.median(fv))
                if duty_all is not None:
                    dv = duty_all[s:e+1]
                    dv = dv[np.isfinite(dv)]
                    if dv.size > 0:
                        duty_pct_med = float(np.median(dv))

        start_row = int(df.iloc[s].get("row()", s+1)) if "row()" in df.columns else s+1

        out.append({
            "cycle": i,
            "start_row": start_row,
            "setpoint_w": setpoint_w,
            "pfwd_steady_w": pfwd_steady_w,
            "pfwd_peak_w": pfwd_peak_w,
            "overshoot_w": overshoot_w,
            "overshoot_pct": overshoot_pct,
            "rise_to_95_ms": rise_to_95_ms,
            "rf_on_ms": rf_on_ms,
            "idle_before_ms": idle_before_ms,
            "mode": mode,
            "freq_khz_med": freq_khz_med,
            "duty_pct_med": duty_pct_med
        })

    return out

def _p3_plot_power_png(df: pd.DataFrame,
                       out_png: str,
                       title: str,
                       use_active_only: bool = False,
                       active_pfwd_threshold_w: float = 3.0,
                       idx_range: Optional[Tuple[int, int]] = None,
                       dpi: int = 180,
                       include_pdel: bool = True  # <-- ADD THIS
                       ) -> None:
    """
    Create report plot (Pfwd/Pref/Pdel and optionally Pset if available) as PNG.
    If use_active_only=True, filter rows where Pfwd > threshold (compress idle time).
    If idx_range is provided, slice original df by index range (keeps time axis).
    """
    if df is None or df.empty:
        return

    dfp = df.copy()

    if idx_range is not None:
        s, e = idx_range
        dfp = dfp.iloc[s:e + 1].copy()

    if use_active_only and "Pfwd" in dfp.columns:
        pf = pd.to_numeric(dfp["Pfwd"], errors="coerce").fillna(0.0)
        dfp = dfp.loc[pf > active_pfwd_threshold_w].copy()
        if dfp.empty:
            # fallback to original if active filter wipes out everything
            dfp = df.iloc[idx_range[0]:idx_range[1] + 1].copy() if idx_range else df.copy()

    t = _p3_get_t_ms(dfp)

    pfwd = pd.to_numeric(dfp.get("Pfwd", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
    pref = pd.to_numeric(dfp.get("Pref", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
    pdel = pfwd - pref

    pset_col = _p3_pick_setpoint_col(dfp)
    pset = None
    if pset_col:
        pset = pd.to_numeric(dfp.get(pset_col, np.nan), errors="coerce").to_numpy(dtype=float)

    fig = Figure(figsize=(10.8, 4.2), dpi=dpi)
    ax = fig.add_subplot(111)

    ax.plot(t, pfwd, label="Pfwd (W)", linewidth=1.2)
    ax.plot(t, pref, label="Pref (W)", linewidth=1.2)
    if include_pdel:
        ax.plot(t, pdel, label="Pdel (W)", linewidth=1.2)
    if pset is not None and np.isfinite(pset).any():
        ax.plot(t, pset, label=f"{pset_col} (W)", linewidth=1.2, linestyle="--")

    ax.set_title(title)
    ax.set_xlabel("t (ms)")
    ax.ticklabel_format(style="plain", axis="x", useOffset=False)
    ax.set_ylabel("Power (W)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_png, dpi=dpi)
    plt.close(fig)

def _p3_step4_forward_vs_setpoint(df: pd.DataFrame,
                                 unit_type: str,
                                 cycles: List[Dict[str, float]],
                                 tol_pct: float = 2.0,
                                 settle_ms: float = 6.0) -> Dict[str, Any]:
    """
    Step 4: Only for Tykon and only if Pset/SetPt exists.
    For each cycle:
      - must reach within +/- tol_pct of setpoint within settle_ms after RF ON
      - steady mean after settle window must not be below setpoint - tol
    """
    if df is None or df.empty:
        return {"available": False, "reason": "No data"}

    if (unit_type or "").strip().lower() != "tykon":
        return {"available": False, "reason": "Quantum: no setpoint, skip Step 4"}

    sp_col = _p3_pick_setpoint_col(df)
    if sp_col is None:
        return {"available": False, "reason": "Missing Pset/SetPt, skip Step 4"}

    t = _p3_get_t_ms(df)
    pfwd = pd.to_numeric(df.get("Pfwd", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
    pset = pd.to_numeric(df.get(sp_col, np.nan), errors="coerce").ffill().fillna(0.0).to_numpy(dtype=float)

    trouble = []
    for k, c in enumerate(cycles):
        s = int(c["start_idx"])
        e = int(c["end_idx"])
        ts = float(t[s])

        settle_end_t = ts + float(settle_ms)
        settle_end_idx = int(np.searchsorted(t, settle_end_t, side="right") - 1)
        settle_end_idx = int(np.clip(settle_end_idx, s, e))

        sp = float(np.nanmedian(pset[s:e + 1]))
        tol = abs(sp) * (tol_pct / 100.0)

        seg = pfwd[s:e + 1]
        in_band = np.where(np.abs(seg - sp) <= tol)[0]
        reach_idx = (s + int(in_band[0])) if len(in_band) else None
        reached = (reach_idx is not None) and (t[reach_idx] <= settle_end_t)

        ss = pfwd[settle_end_idx:e + 1] if settle_end_idx < e else pfwd[s:e + 1]
        ss_mean = float(np.nanmean(ss)) if len(ss) else float(np.nanmean(seg))

        flags = []
        if not reached:
            flags.append(f"Slow settling (> {settle_ms:.1f} ms to reach ±{tol_pct:.1f}%)")
        if ss_mean < (sp - tol):
            flags.append(f"Low Pfwd vs {sp_col} (mean {ss_mean:.2f} W, {sp_col} {sp:.2f} W)")

        if flags:
            trouble.append({
                "cycle": k + 1,
                "start_row": int(df.iloc[s].get("row()", s + 1)) if "row()" in df.columns else s + 1,
                "start_idx": s,
                "start_t_ms": ts,
                "setpoint_col": sp_col,
                "setpoint_w": sp,
                "steady_mean_w": ss_mean,
                "flags": "; ".join(flags),
            })

    return {
        "available": True,
        "setpoint_col": sp_col,
        "tol_pct": float(tol_pct),
        "settle_ms": float(settle_ms),
        "trouble_cases": trouble
    }


def _p3_step5_reflect(df: pd.DataFrame,
                      cycles: List[Dict[str, float]],
                      ratio_limit: float = 0.01,
                      mask_ms: float = 3.0) -> Dict[str, Any]:
    """
    Step 5: report Pref > ratio_limit * Pfwd.
    Mask first mask_ms after RF ON to avoid plasma strike transient.
    """
    if df is None or df.empty:
        return {"available": False, "reason": "No data"}
    if "Pfwd" not in df.columns or "Pref" not in df.columns:
        return {"available": False, "reason": "Missing Pfwd or Pref"}

    t = _p3_get_t_ms(df)
    pfwd = pd.to_numeric(df["Pfwd"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    pref = pd.to_numeric(df["Pref"], errors="coerce").fillna(0.0).to_numpy(dtype=float)

    trouble = []
    for k, c in enumerate(cycles):
        s = int(c["start_idx"])
        e = int(c["end_idx"])
        ts = float(t[s])

        mask_end_t = ts + float(mask_ms)
        mask_end_idx = int(np.searchsorted(t, mask_end_t, side="right") - 1)
        mask_end_idx = int(np.clip(mask_end_idx, s, e))

        seg_pfwd = pfwd[mask_end_idx:e + 1]
        seg_pref = pref[mask_end_idx:e + 1]
        if len(seg_pfwd) == 0:
            continue

        limit = float(ratio_limit) * np.maximum(seg_pfwd, 1e-12)
        bad = np.where(seg_pref > limit)[0]
        if len(bad) == 0:
            continue

        first_bad = mask_end_idx + int(bad[0])
        worst = mask_end_idx + int(np.argmax(seg_pref / np.maximum(seg_pfwd, 1e-12)))

        trouble.append({
            "cycle": k + 1,
            "start_row": int(df.iloc[s].get("row()", s + 1)) if "row()" in df.columns else s + 1,
            "first_bad_row": int(df.iloc[first_bad].get("row()", first_bad + 1)) if "row()" in df.columns else first_bad + 1,
            "worst_row": int(df.iloc[worst].get("row()", worst + 1)) if "row()" in df.columns else worst + 1,
            "worst_pref_w": float(pref[worst]),
            "worst_pfwd_w": float(pfwd[worst]),
            "ratio_pct": float(100.0 * pref[worst] / pfwd[worst]) if pfwd[worst] > 0 else float("inf"),
        })

    return {
        "available": True,
        "ratio_limit": float(ratio_limit),
        "mask_ms": float(mask_ms),
        "trouble_cases": trouble
    }


def _p3_pulse_mode_range_alarm(df: pd.DataFrame,
                              freq_khz_min: float = 0.01,
                              freq_khz_max: float = 50.0,
                              duty_min: float = 10.0,
                              duty_max: float = 90.0) -> Dict[str, Any]:
    """
    Pulse mode alarm:
      - only check rows where Pmode == 1
      - Freq in kHz must be within [0.01, 50]
      - Duty (%) must be within [10, 90]
    """
    if df is None or df.empty:
        return {"available": False, "reason": "No data"}
    if "Pmode" not in df.columns:
        return {"available": False, "reason": "Missing Pmode"}

    pmode = pd.to_numeric(df["Pmode"], errors="coerce").fillna(0).astype(int).to_numpy()
    pulse_rows = np.where(pmode == 1)[0]

    # Defensive: if Pls exists, exclude rows where 2nd char is 'C'
    if "Pls" in df.columns and len(pulse_rows) > 0:
        pls0 = df["Pls"].astype(str).str.strip()
        ch1 = pls0.str.slice(1, 2).to_numpy()
        pulse_rows = pulse_rows[ch1[pulse_rows] != "C"]

    if len(pulse_rows) == 0:
        return {"available": True, "pulse_mode_rows": 0, "alarms": []}

    alarms = []

    if "Freq" in df.columns:
        freq = pd.to_numeric(df["Freq"], errors="coerce").to_numpy(dtype=float)
        bad = pulse_rows[(freq[pulse_rows] < freq_khz_min) | (freq[pulse_rows] > freq_khz_max)]
        for i in bad[:5000]:
            rownum = int(df.iloc[i].get("row()", i + 1)) if "row()" in df.columns else i + 1
            alarms.append({"row": rownum, "type": "PulseFreqOutOfRange", "value": float(freq[i]), "unit": "kHz"})
    else:
        alarms.append({"row": None, "type": "PulseFreqMissing", "value": None, "unit": "kHz"})

    if "Duty" in df.columns:
        duty = pd.to_numeric(df["Duty"], errors="coerce").to_numpy(dtype=float)
        bad = pulse_rows[(duty[pulse_rows] < duty_min) | (duty[pulse_rows] > duty_max)]
        for i in bad[:5000]:
            rownum = int(df.iloc[i].get("row()", i + 1)) if "row()" in df.columns else i + 1
            alarms.append({"row": rownum, "type": "DutyOutOfRange", "value": float(duty[i]), "unit": "%"})
    else:
        alarms.append({"row": None, "type": "DutyMissing", "value": None, "unit": "%"})

    return {
        "available": True,
        "pulse_mode_rows": int(len(pulse_rows)),
        "alarms": alarms,
        "freq_range_khz": (float(freq_khz_min), float(freq_khz_max)),
        "duty_range_pct": (float(duty_min), float(duty_max)),
    }

def _set_table_font_size(table, size_pt: float):
    """Set font size (pt) for all runs in a python-docx table."""
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(size_pt)

def _p3_export_word_report(
        out_docx,
        unit_type,
        tlog_filename,
        artifacts,
        cycles,
        step4,
        step5,
        pulse_alarm,
        settings,
        step3_metrics=None,
        unit_fw="",
        unit_fpga="",
        unit_sn=""
):
    """
    Write Word report with 3 plots + analysis tables.
    """
    doc = Document()
    # Title block (basic info)
    doc.add_heading("tlog2chart Phase 3 Basic Analysis Report", level=0)
    p = doc.add_paragraph()
    p.add_run(f"File: {tlog_filename}\n")
    p.add_run(f"Unit Type: {unit_type}\n")
    p.add_run(f"Unit FW Ver: {unit_fw}\n")
    p.add_run(f"Unit FPGA Ver: {unit_fpga}\n")
    p.add_run(f"Unit SN: {unit_sn}\n")
    tool_ver = read_project_version()
    p.add_run(f"Tool: {APP_NAME} v{APP_VERSION}\n")
    p.add_run(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph("")

    # Settings summary
    doc.add_heading("Analysis Settings", level=1)
    doc.add_paragraph(
        f"- Active threshold: Pfwd > {settings['active_thr']:.2f} W\n"
        f"- Step4 tolerance: ±{settings['tol_pct']:.1f}%  | settle time: {settings['settle_ms']:.1f} ms (Tykon only)\n"
        f"- Step5 reflect rule: Pref > {settings['pref_ratio']*100:.2f}% of Pfwd  | mask first {settings['mask_ms']:.1f} ms\n"
        f"- Pulse mode range: Freq {settings['fmin']:.2f}–{settings['fmax']:.2f} kHz, Duty {settings['dmin']:.1f}–{settings['dmax']:.1f}%"
    )

    def add_fig(png_path: str, caption: str):
        if png_path and os.path.exists(png_path):
            doc.add_picture(png_path, width=Inches(6.6))
            p = doc.add_paragraph(caption)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Step 1-3 figures
    doc.add_heading("Step 1 — Full Scale Overview", level=1)
    doc.add_paragraph("Full plot of Pfwd/Pref/Pdel across the entire tlog.")
    add_fig(artifacts.get("step1_full", ""), "Figure 1. Full-scale power overview.")

    doc.add_heading("Step 2 — Zoom In to last RF event with 100x smaller time span than Step 1, improving resolution around the last power event.", level=1)
    doc.add_paragraph(
        "This plot zooms into the time window around the last RF event. "
        "The X-axis time span is 100× smaller than Step 1 to improve resolution near the last power activity."
    )
    add_fig(artifacts.get("step2_active", ""), "Figure 2. Active-area power plot (idle removed).")

#    doc.add_heading("Step 3 — First 6 RF Cycles", level=1)
    # Step 3 title (Task G - time range)
    if settings.get("step3_range_s") is not None:
        t0, t1 = settings["step3_range_s"]
        title3 = f"Step 3 — Customize time range analysis ({t0:.1f}–{t1:.1f} s)"
    else:
        title3 = "Step 3 — First 6 RF Cycles"
    doc.add_heading(title3, level=1)
    add_fig(artifacts.get("step3_first6", ""), "Figure 3. User assigned time range RF cycles.")

    metrics = step3_metrics or []
    if metrics:
        doc.add_paragraph("Step 3 cycle metrics (base on RF on/off signal):")

        table = doc.add_table(rows=1, cols=11)
        hdr = table.rows[0].cells
        hdr[0].text = "Cycle"
        hdr[1].text = "Start row()"
        hdr[2].text = "SetPt (W)"
        hdr[3].text = "Pfwd steady (W)"
        hdr[4].text = "Pfwd peak (W)"
        hdr[5].text = "Overshoot (W)"
        hdr[6].text = "Overshoot (%)"
        hdr[7].text = "Rise to 95% (ms)"
        hdr[8].text = "RF ON (ms)"
        hdr[9].text = "Idle before (ms)"
        hdr[10].text = "Mode / Freq / Duty"

        for m in metrics:
            row = table.add_row().cells
            row[0].text = str(m["cycle"])
            row[1].text = str(m["start_row"])
            row[2].text = "" if m["setpoint_w"] is None else f"{m['setpoint_w']:.1f}"
            row[3].text = f"{m['pfwd_steady_w']:.1f}"
            row[4].text = f"{m['pfwd_peak_w']:.1f}"
            row[5].text = "" if m["overshoot_w"] is None else f"{m['overshoot_w']:.1f}"
            row[6].text = "" if m["overshoot_pct"] is None else f"{m['overshoot_pct']:.2f}"
            row[7].text = "" if m["rise_to_95_ms"] is None else f"{m['rise_to_95_ms']:.3f}"
            row[8].text = f"{m['rf_on_ms']:.3f}"
            row[9].text = "N/A" if m["idle_before_ms"] is None else f"{m['idle_before_ms']:.3f}"

            mode = m["mode"]
            extra = mode
            if mode == "Pulse":
                if m["freq_khz_med"] is not None:
                    extra += f", F={m['freq_khz_med']:.3f}kHz"
                if m["duty_pct_med"] is not None:
                    extra += f", D={m['duty_pct_med']:.1f}%"
            row[10].text = extra
        # ✅ shrink Step‑3 table font size to 8
        _set_table_font_size(table, 8)
    doc.add_paragraph(
        f"Detected RF cycles: {len(cycles)}. The plot shows user assigned time range."
    )

    # Step 4 table (Tykon only)
    doc.add_heading("Step 4 — Forward Power vs Setpoint (Tykon only)", level=1)
    if step4.get("available"):
        trouble = step4.get("trouble_cases", [])
        doc.add_paragraph(
            f"Setpoint column: {step4.get('setpoint_col')}. "
            f"Rule: Pfwd must reach ±{step4['tol_pct']:.1f}% of setpoint within {step4['settle_ms']:.1f} ms after RF ON. "
            "Steady-state mean after settle window must not be low beyond tolerance."
        )
        doc.add_paragraph(f"Flagged cycles: {len(trouble)}")
        if trouble:
            table = doc.add_table(rows=1, cols=6)
            hdr = table.rows[0].cells
            hdr[0].text = "Cycle"
            hdr[1].text = "Start row()"
            hdr[2].text = "Start t(ms)"
            hdr[3].text = "Setpoint (W)"
            hdr[4].text = "Steady Pfwd mean (W)"
            hdr[5].text = "Flags"
            for r in trouble[:200]:
                row = table.add_row().cells
                row[0].text = str(r["cycle"])
                row[1].text = str(r["start_row"])
                row[2].text = f"{r['start_t_ms']:.3f}"
                row[3].text = f"{r['setpoint_w']:.2f}"
                row[4].text = f"{r['steady_mean_w']:.2f}"
                row[5].text = r["flags"]
            doc.add_paragraph("Note: table capped at 200 rows for readability.")
    else:
        doc.add_paragraph(step4.get("reason", "Skipped"))

    # Step 5 table
    doc.add_heading("Step 5 — Reflected Power (Pref high)", level=1)
    if step5.get("available"):
        trouble = step5.get("trouble_cases", [])
        doc.add_paragraph(
            f"Rule: Pref > {step5['ratio_limit']*100:.2f}% of Pfwd after masking the first {step5['mask_ms']:.1f} ms."
        )
        doc.add_paragraph(f"Flagged cycles: {len(trouble)}")
        if trouble:
            table = doc.add_table(rows=1, cols=6)
            hdr = table.rows[0].cells
            hdr[0].text = "Cycle"
            hdr[1].text = "Start row()"
            hdr[2].text = "First bad row()"
            hdr[3].text = "Worst row()"
            hdr[4].text = "Worst Pref (W)"
            hdr[5].text = "Worst Pref/Pfwd (%)"
            for r in trouble[:200]:
                row = table.add_row().cells
                row[0].text = str(r["cycle"])
                row[1].text = str(r["start_row"])
                row[2].text = str(r["first_bad_row"])
                row[3].text = str(r["worst_row"])
                row[4].text = f"{r['worst_pref_w']:.2f}"
                row[5].text = f"{r['ratio_pct']:.2f}"
            doc.add_paragraph("Note: table capped at 200 rows.")
    else:
        doc.add_paragraph(step5.get("reason", "Unavailable"))

    # Pulse alarms
    doc.add_heading("Pulse Mode Range Alarms", level=1)
    if pulse_alarm.get("available"):
        alarms = pulse_alarm.get("alarms", [])
        doc.add_paragraph(f"Pulse-mode rows: {pulse_alarm.get('pulse_mode_rows', 0)}")
        doc.add_paragraph(f"Alarms: {len(alarms)}")
        if alarms:
            table = doc.add_table(rows=1, cols=4)
            hdr = table.rows[0].cells
            hdr[0].text = "Row()"
            hdr[1].text = "Type"
            hdr[2].text = "Value"
            hdr[3].text = "Unit"
            for a in alarms[:200]:
                row = table.add_row().cells
                row[0].text = "" if a["row"] is None else str(a["row"])
                row[1].text = str(a["type"])
                row[2].text = "" if a["value"] is None else f"{a['value']:.3f}"
                row[3].text = str(a["unit"])
            doc.add_paragraph("Note: table capped at 200 rows.")
    else:
        doc.add_paragraph(pulse_alarm.get("reason", "Unavailable"))

    os.makedirs(os.path.dirname(out_docx) or ".", exist_ok=True)
    doc.save(out_docx)

def p3_run_analysis(
    df: pd.DataFrame,
    unit_type: str,
    artifacts_dir: str,
    active_thr_w: float = 3.0,
    tol_pct: float = 2.0,
    settle_ms: float = 6.0,
    pref_ratio: float = 0.01,
    mask_ms: float = 3.0,
    fmin_khz: float = 0.01,
    fmax_khz: float = 50.0,
    dmin_pct: float = 10.0,
    dmax_pct: float = 90.0,
    step3_range_s: Optional[Tuple[float, float]] = None,
) -> Dict[str, Any]:
    """
    Orchestrate Step1-8.
    Returns dict with artifacts + findings.
    """
    os.makedirs(artifacts_dir, exist_ok=True)

    # cycles for Step 4/5 etc. (Pfwd threshold based)
    cycles = _p3_detect_cycles(df, pfwd_threshold_w=active_thr_w)

    # 1) detect cycles using legacy RFUC (Tykon/Quantum)
    cycles_uc = []
    try:
        cycles_uc = _p3_detect_cycles_from_rfuc(df)
    except Exception:
        cycles_uc = []

    # 2) fallback cycles for Chronos 2.0 using RF status column
    cycles_status = []
    if (not cycles_uc) and ("RF" in df.columns):
        cycles_status = _p3_detect_cycles_from_rf_status(df, rf_col="RF")

    # 3) choose which cycles list to use for metrics
    cycles_for_metrics = cycles_uc if cycles_uc else cycles_status

    # 4) compute step 3 metrics table
    step3_metrics = _p3_calc_first6_cycle_metrics_rfuc(
        df,
        cycles_uc=cycles_for_metrics,
        unit_type=unit_type,
        settle_ms=settle_ms
    )

    # cycles for Step 3 (RF:UC based)
    cycles_uc = _p3_detect_cycles_from_rfuc(df)
    # --- Task I-06: Chronos 2.0 fallback ---
    # Chronos 2.0 uses RF status column 'RF' for ON/OFF. [1](https://oneasm-my.sharepoint.com/personal/victor_huang_asm_com/Documents/Microsoft%20Copilot%20Chat%20Files/02-Tykon1213-EDCM_EvalWoDepo_RF50ms_10000Cyc%20-%20Copy.txt)
    cycles_status = []
    if (not cycles_uc) and ("RF" in df.columns):
        cycles_status = _p3_detect_cycles_from_rf_status(df, rf_col="RF")
    # Select cycles for Step 3 metrics
    selected_cycles_uc = cycles_uc[:6]  # default

    if step3_range_s is not None and len(cycles_uc) > 0:
        t0_s, t1_s = step3_range_s
        t_s_all = pd.to_numeric(df["t(s)"], errors="coerce").to_numpy(dtype=float)

        tmp = []
        for c in cycles_uc:
            s_idx = int(c["start_idx"])
            e_idx = int(c["end_idx"])
            if 0 <= s_idx < len(t_s_all) and 0 <= e_idx < len(t_s_all):
                cs = float(t_s_all[s_idx])
                ce = float(t_s_all[e_idx])
                # overlap rule
                if (ce >= t0_s) and (cs <= t1_s):
                    tmp.append(c)

        if tmp:
            selected_cycles_uc = tmp
    first6_range = None

    # ---------------- Step 1: full ----------------
    png1 = os.path.join(artifacts_dir, "step1_full.png")
    _p3_plot_power_png(df, png1, "Step 1: Full-scale overview", use_active_only=False, dpi=180)

    # ---------------- Step 2: zoom near last power point ----------------
    png2 = os.path.join(artifacts_dir, "step2_zoom_last.png")

    mask, x0, x1, anchor_idx = _p3_get_last_zoom_window(
        df, active_thr_w=active_thr_w, zoom_factor=100.0, pad_after=0.05
    )

    df_zoom = df.loc[mask].copy() if mask is not None else df.copy()

    title2 = "Step 2: Zoom near last power point"
    if x0 is not None and x1 is not None:
        title2 = f"Step 2: Zoom near last power point (full/100) [{x0:.1f} - {x1:.1f} ms]"

    _p3_plot_power_png(
        df_zoom,
        png2,
        title=title2,
        use_active_only=False,
        dpi=180,
        include_pdel=False   # <-- Ste
    )

    # # ---------------- Step 3: first 6 RF cycles (RF:UC) ----------------
    # png3 = os.path.join(artifacts_dir, "step3_first6.png")
    # first6_range = None
    #
    # if len(cycles_uc) > 0:
    #     first = cycles_uc[:6]
    #     s = int(first[0]["start_idx"])
    #     e = int(first[-1]["end_idx"])
    #     first6_range = (s, e)
    #     _p3_plot_power_png(
    #         df,
    #         png3,
    #         "Step 3: First 6 RF cycles (RF:UC based)",
    #         idx_range=(s, e),
    #         dpi=180
    #     )
    # else:
    #     _p3_plot_power_png(
    #         df,
    #         png3,
    #         "Step 3: No RF:UC cycles detected",
    #         use_active_only=False,
    #         dpi=180
    #     )

    # ---------------- Step 3 figure (png3) ----------------
    png3 = ""

    df_step3 = None
    title3_plot = "Step 3: First 6 RF cycles"

    # If user provided time-range override (seconds), slice by Graph timebase df['t(s)']
    if step3_range_s is not None:
        t0_s, t1_s = step3_range_s
        title3_plot = f"Step 3: RF cycles (Custom time window: {t0_s:.1f}-{t1_s:.1f} s)"

        if "t(s)" in df.columns:
            t_s = pd.to_numeric(df["t(s)"], errors="coerce").to_numpy(dtype=float)
            mask3 = (t_s >= t0_s) & (t_s <= t1_s)
            df_step3 = df.loc[mask3].copy()

    else:
        # Default behavior (no override): keep whatever you already do for default Step 3
        # If you have first6_range computed, keep it; otherwise skip default plot for now.
        if "first6_range" in locals() and first6_range is not None:
            s, e = first6_range
            s = max(0, int(s))
            e = min(int(e), len(df) - 1)
            if e >= s:
                df_step3 = df.iloc[s:e + 1].copy()

    # Generate Step 3 figure if there is data
    if df_step3 is not None and not df_step3.empty:
        png3 = os.path.join(artifacts_dir, "step3_first6.png")  # keep compatibility key
        _p3_plot_power_png(
            df_step3,
            png3,
            title=title3_plot,
            use_active_only=False,
            dpi=180,
            include_pdel=False
        )

    # Step 3 metrics
    cycles_for_metrics = cycles_uc if cycles_uc else cycles_status

    step3_metrics = _p3_calc_first6_cycle_metrics_rfuc(
        df,
        cycles_uc=cycles_for_metrics,
        unit_type=unit_type,
        settle_ms=settle_ms
    )

    # ---------------- Step 4/5/6... ----------------
    step4 = _p3_step4_forward_vs_setpoint(df, unit_type, cycles, tol_pct=tol_pct, settle_ms=settle_ms)
    step5 = _p3_step5_reflect(df, cycles, ratio_limit=pref_ratio, mask_ms=mask_ms)
    pulse_alarm = _p3_pulse_mode_range_alarm(
        df,
        freq_khz_min=fmin_khz,
        freq_khz_max=fmax_khz,
        duty_min=dmin_pct,
        duty_max=dmax_pct
    )

    # ---------------- Return dict ----------------
    return {
        "unit_type": unit_type,
        "cycle_count": len(cycles),
        "cycles": cycles,
        "cycles_uc": cycles_uc,               # optional: keep for debugging
        "first6_range": first6_range,
        "artifacts": {
            "step1_full": png1,
            "step2_active": png2,             # keep the key name if your Word export expects this
            "step3_first6": png3
        },
        "step3_metrics": step3_metrics,        # <-- NEW: add Step 3 info here
        "step4_forward": step4,
        "step5_reflect": step5,
        "pulse_alarm": pulse_alarm,
        "settings": {
            "active_thr": float(active_thr_w),
            "tol_pct": float(tol_pct),
            "settle_ms": float(settle_ms),
            "pref_ratio": float(pref_ratio),
            "mask_ms": float(mask_ms),
            "fmin": float(fmin_khz),
            "fmax": float(fmax_khz),
            "dmin": float(dmin_pct),
            "dmax": float(dmax_pct),
            "step3_range_s": step3_range_s,
        }
    }

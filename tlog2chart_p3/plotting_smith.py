from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

# =============================================================================
# ----------------------------- Smith Chart helpers ----------------------------
# =============================================================================

def _z_to_gamma(z: np.ndarray, z0: float = 50.0) -> np.ndarray:
    z0 = float(z0)
    return (z - z0) / (z + z0)

def _circle_xy(cx, cy, r, n=400):
    th = np.linspace(0, 2*np.pi, n)
    return cx + r*np.cos(th), cy + r*np.sin(th)

def draw_smith_grid(ax, grid_color="#B0B0B0", lw=0.8, alpha=0.45):
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-1.05, 1.05)
    ax.axis("off")

    # Outer unit circle
    x, y = _circle_xy(0, 0, 1.0)
    ax.plot(x, y, color="black", lw=1.3)

    # Constant resistance circles (normalized r)
    r_list = [0, 0.2, 0.5, 1, 2, 5]
    for r in r_list:
        c = (r / (r + 1), 0.0)
        rad = 1 / (r + 1)
        x, y = _circle_xy(c[0], c[1], rad)
        ax.plot(x, y, color=grid_color, lw=lw, alpha=alpha)

    # Constant reactance arcs (normalized x)
    x_list = [0.2, 0.5, 1, 2, 5]
    for xval in x_list:
        for sign in (+1, -1):
            xnorm = sign * xval
            cx, cy = 1.0, 1.0 / xnorm
            rad = abs(1.0 / xnorm)
            xc, yc = _circle_xy(cx, cy, rad)
            mask = (xc ** 2 + yc ** 2) <= 1.0001
            ax.plot(xc[mask], yc[mask], color=grid_color, lw=lw, alpha=alpha)

    ax.plot([-1, 1], [0, 0], color=grid_color, lw=lw, alpha=alpha)

def plot_smith_rlxl_hf_lf(
        ax,
        df: Optional[pd.DataFrame],
        z0=50.0,
        max_points=8000,
        pfwd_threshold: float = 0.0,
        title="EVC Zload on Smith Chart (Z0=50Ω)"
):
    """
    Draw smith grid + scatter points.
    Filter points with Pfwd < pfwd_threshold.
    Returns dict for hover:
      { "sets": [ {label, artist, row_index, R, X, gx, gy}, ... ] }
    """
    draw_smith_grid(ax)
    ax.set_title(title, fontsize=12)

    if pfwd_threshold and pfwd_threshold > 0:
        ax.text(0.02, 0.98, f"Pfwd ≥ {int(pfwd_threshold)} W",
                transform=ax.transAxes, ha="left", va="top",
                fontsize=10, color="gray")

    ret = {"sets": []}

    if df is None or df.empty:
        ax.text(0, 0, "No data loaded", ha="center", va="center", fontsize=12)
        return ret

    if "RL" not in df.columns or "XL" not in df.columns:
        ax.text(0, 0, "RL/XL columns not found", ha="center", va="center", fontsize=12)
        return ret

    def _plot_one(label, subdf, color):
        # Filter by forward power threshold if Pfwd exists
        if "Pfwd" in subdf.columns and pfwd_threshold > 0:
            pf = pd.to_numeric(subdf["Pfwd"], errors="coerce")
            subdf = subdf.loc[pf >= pfwd_threshold]
            if subdf.empty:
                return False

        R0 = pd.to_numeric(subdf["RL"], errors="coerce").to_numpy()
        X0 = pd.to_numeric(subdf["XL"], errors="coerce").to_numpy()
        idx0 = subdf.index.to_numpy()

        good = np.isfinite(R0) & np.isfinite(X0)
        R0, X0, idx0 = R0[good], X0[good], idx0[good]
        if R0.size == 0:
            return False

        if R0.size > max_points:
            take = np.linspace(0, R0.size - 1, max_points).astype(int)
            R0, X0, idx0 = R0[take], X0[take], idx0[take]

        Z = R0 + 1j * X0
        G = _z_to_gamma(Z, z0=z0)
        gx, gy = np.real(G), np.imag(G)

        sc = ax.scatter(gx, gy, s=10, c=color, alpha=0.85,
                        label=f"{label} points", picker=5)

        # Start/end markers
        ax.scatter([gx[0]], [gy[0]], s=90, c=color, marker="o",
                   edgecolors="black", linewidths=0.6, label=f"{label} start")
        ax.scatter([gx[-1]], [gy[-1]], s=90, c=color, marker="X", label=f"{label} end")

        ret["sets"].append({
            "label": label,
            "artist": sc,
            "row_index": idx0,
            "R": R0, "X": X0,
            "gx": gx, "gy": gy
        })
        return True

    if "MN" in df.columns:
        mn = df["MN"].astype(str).str.upper().str.strip()
        df_hf = df.loc[mn == "HF"]
        df_lf = df.loc[mn == "LF"]

        has_any = False
        if not df_hf.empty:
            has_any |= _plot_one("HF", df_hf, "#1f77b4")
        if not df_lf.empty:
            has_any |= _plot_one("LF", df_lf, "#ff7f0e")

        if not has_any:
            ax.text(0, 0, "No points above threshold", ha="center", va="center", fontsize=12)
            return ret

        ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
        return ret

        ok = _plot_one("All", df, "#d62728")
        if not ok:
            ax.text(0, 0, "No points above threshold", ha="center", va="center", fontsize=12)
            return ret

        ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
        return ret

    _plot_one("All", df, "#d62728")
    ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
    return ret

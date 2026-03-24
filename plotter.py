"""Chart generation for EVC tlog data."""

import os
from collections import defaultdict
from datetime import datetime
from typing import List, Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive backend; override before pyplot import
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from tlog_parser import TlogFile, TlogRecord


# Default figure dimensions
_FIG_W = 12
_FIG_H = 5


def plot_tlog(
    tlog: TlogFile,
    output_dir: str = ".",
    show: bool = False,
) -> List[str]:
    """Generate all standard charts for *tlog* and save them to *output_dir*.

    Parameters
    ----------
    tlog:
        Parsed :class:`~parser.TlogFile` object.
    output_dir:
        Directory where PNG files are written.  Created if it does not exist.
    show:
        When ``True`` the charts are also displayed interactively (requires a
        display / GUI environment).

    Returns
    -------
    list[str]
        Paths of all generated PNG files.
    """
    os.makedirs(output_dir, exist_ok=True)
    records = tlog.records

    if not records:
        print("No charging records found in tlog – nothing to plot.")
        return []

    generated: List[str] = []

    def _save(fig: plt.Figure, name: str) -> str:
        path = os.path.join(output_dir, name)
        fig.savefig(path, bbox_inches="tight", dpi=150)
        if show:
            plt.show()
        plt.close(fig)
        generated.append(path)
        return path

    sn_label = f"  [SN: {tlog.metadata.serial_number}]" if tlog.metadata.serial_number else ""
    base_title = f"EVC Tlog{sn_label}"

    # ------------------------------------------------------------------ #
    # 1. Energy per session (bar chart)                                   #
    # ------------------------------------------------------------------ #
    fig, ax = plt.subplots(figsize=(_FIG_W, _FIG_H))
    indices = [r.index for r in records]
    energies = [r.energy_kwh for r in records]
    colors = ["#d62728" if r.fault != "0000" else "#1f77b4" for r in records]
    ax.bar(indices, energies, color=colors, width=0.7)
    ax.set_xlabel("Session Index")
    ax.set_ylabel("Energy (kWh)")
    ax.set_title(f"{base_title} – Energy per Session")
    ax.set_xticks(indices)
    _add_fault_legend(ax)
    fig.tight_layout()
    _save(fig, "energy_per_session.png")

    # ------------------------------------------------------------------ #
    # 2. Session duration per session (bar chart)                         #
    # ------------------------------------------------------------------ #
    fig, ax = plt.subplots(figsize=(_FIG_W, _FIG_H))
    durations = [r.duration_min for r in records]
    ax.bar(indices, durations, color=colors, width=0.7)
    ax.set_xlabel("Session Index")
    ax.set_ylabel("Duration (min)")
    ax.set_title(f"{base_title} – Session Duration")
    ax.set_xticks(indices)
    _add_fault_legend(ax)
    fig.tight_layout()
    _save(fig, "duration_per_session.png")

    # ------------------------------------------------------------------ #
    # 3. Energy over time (scatter / line) – requires valid start_dt      #
    # ------------------------------------------------------------------ #
    timed = [r for r in records if r.start_dt is not None]
    if timed:
        fig, ax = plt.subplots(figsize=(_FIG_W, _FIG_H))
        times = [r.start_dt for r in timed]
        energies_t = [r.energy_kwh for r in timed]
        colors_t = ["#d62728" if r.fault != "0000" else "#1f77b4" for r in timed]
        ax.scatter(times, energies_t, c=colors_t, s=60, zorder=3)
        ax.plot(times, energies_t, color="#aec7e8", linewidth=1, zorder=2)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        fig.autofmt_xdate(rotation=30)
        ax.set_xlabel("Session Start Time")
        ax.set_ylabel("Energy (kWh)")
        ax.set_title(f"{base_title} – Energy over Time")
        _add_fault_legend(ax)
        fig.tight_layout()
        _save(fig, "energy_over_time.png")

        # ---------------------------------------------------------------- #
        # 4. Cumulative energy over time                                   #
        # ---------------------------------------------------------------- #
        fig, ax = plt.subplots(figsize=(_FIG_W, _FIG_H))
        cumulative = []
        total = 0.0
        for r in timed:
            total += r.energy_kwh
            cumulative.append(total)
        ax.step(times, cumulative, where="post", color="#2ca02c", linewidth=2)
        ax.fill_between(times, cumulative, step="post", alpha=0.15, color="#2ca02c")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        fig.autofmt_xdate(rotation=30)
        ax.set_xlabel("Session Start Time")
        ax.set_ylabel("Cumulative Energy (kWh)")
        ax.set_title(f"{base_title} – Cumulative Energy")
        fig.tight_layout()
        _save(fig, "cumulative_energy.png")

        # ---------------------------------------------------------------- #
        # 5. Daily energy totals (bar chart)                               #
        # ---------------------------------------------------------------- #
        daily: defaultdict = defaultdict(float)
        for r in timed:
            day = r.start_dt.date()  # type: ignore[union-attr]
            daily[day] += r.energy_kwh
        if len(daily) > 1:
            days = sorted(daily.keys())
            day_energies = [daily[d] for d in days]
            fig, ax = plt.subplots(figsize=(_FIG_W, _FIG_H))
            ax.bar(range(len(days)), day_energies, color="#ff7f0e")
            ax.set_xticks(range(len(days)))
            ax.set_xticklabels([d.strftime("%m/%d") for d in days], rotation=30)
            ax.set_xlabel("Date")
            ax.set_ylabel("Total Energy (kWh)")
            ax.set_title(f"{base_title} – Daily Energy Total")
            fig.tight_layout()
            _save(fig, "daily_energy.png")

    return generated


# --------------------------------------------------------------------------- #
# Internal helpers                                                              #
# --------------------------------------------------------------------------- #

def _add_fault_legend(ax: plt.Axes) -> None:
    """Add a small legend distinguishing normal and faulted sessions."""
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#1f77b4", label="Normal"),
        Patch(facecolor="#d62728", label="Fault"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=8)

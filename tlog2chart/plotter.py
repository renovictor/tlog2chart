"""Chart generation from parsed EVC tlog data."""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use("Agg")  # Non-interactive backend suitable for scripts

# Human-readable labels: (message_type, field_name) -> label string.
# A plain field_name key (without message type) is used as a fallback.
_FIELD_LABELS: Dict[Tuple[str, str] | str, str] = {
    # BATTERY_STATUS
    ("BATTERY_STATUS", "voltage_battery"): "Voltage (mV)",
    ("BATTERY_STATUS", "current_battery"): "Current (cA)",
    ("BATTERY_STATUS", "battery_remaining"): "Remaining (%)",
    ("BATTERY_STATUS", "temperature"): "Temperature (cdegC)",
    # SYS_STATUS
    ("SYS_STATUS", "voltage_battery"): "Voltage (mV)",
    ("SYS_STATUS", "current_battery"): "Current (cA)",
    # VFR_HUD
    ("VFR_HUD", "airspeed"): "Airspeed (m/s)",
    ("VFR_HUD", "groundspeed"): "Ground Speed (m/s)",
    ("VFR_HUD", "alt"): "Altitude (m)",
    ("VFR_HUD", "climb"): "Climb Rate (m/s)",
    ("VFR_HUD", "throttle"): "Throttle (%)",
    ("VFR_HUD", "heading"): "Heading (deg)",
    # ATTITUDE
    ("ATTITUDE", "roll"): "Roll (rad)",
    ("ATTITUDE", "pitch"): "Pitch (rad)",
    ("ATTITUDE", "yaw"): "Yaw (rad)",
    ("ATTITUDE", "rollspeed"): "Roll Rate (rad/s)",
    ("ATTITUDE", "pitchspeed"): "Pitch Rate (rad/s)",
    ("ATTITUDE", "yawspeed"): "Yaw Rate (rad/s)",
    # GPS_RAW_INT
    ("GPS_RAW_INT", "lat"): "Latitude (degE7)",
    ("GPS_RAW_INT", "lon"): "Longitude (degE7)",
    ("GPS_RAW_INT", "alt"): "Altitude (mm)",
    ("GPS_RAW_INT", "vel"): "Speed (cm/s)",
    ("GPS_RAW_INT", "satellites_visible"): "Satellites",
    # GLOBAL_POSITION_INT
    ("GLOBAL_POSITION_INT", "relative_alt"): "Relative Altitude (mm)",
    ("GLOBAL_POSITION_INT", "vx"): "Velocity X (cm/s)",
    ("GLOBAL_POSITION_INT", "vy"): "Velocity Y (cm/s)",
    ("GLOBAL_POSITION_INT", "vz"): "Velocity Z (cm/s)",
}

# Default fields to plot per message type (ordered)
_DEFAULT_PLOT_FIELDS: Dict[str, List[str]] = {
    "BATTERY_STATUS": ["voltage_battery", "current_battery", "battery_remaining"],
    "SYS_STATUS": ["voltage_battery", "current_battery"],
    "VFR_HUD": ["airspeed", "groundspeed", "alt", "throttle", "climb"],
    "ATTITUDE": ["roll", "pitch", "yaw"],
    "GPS_RAW_INT": ["alt", "vel", "satellites_visible"],
    "GLOBAL_POSITION_INT": ["relative_alt", "vx", "vy", "vz"],
}


class TlogPlotter:
    """Create charts from EVC tlog DataFrames produced by :class:`~tlog2chart.parser.TlogParser`.

    Parameters
    ----------
    data:
        Mapping of ``{message_type: DataFrame}`` as returned by
        :meth:`~tlog2chart.parser.TlogParser.parse`.
    """

    def __init__(self, data: Dict[str, pd.DataFrame]) -> None:
        self.data = data

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plot(
        self,
        message_types: Optional[Sequence[str]] = None,
        output: Optional[str] = None,
        show: bool = False,
    ) -> List[plt.Figure]:
        """Generate one figure per message type.

        Parameters
        ----------
        message_types:
            Subset of message types to plot.  Defaults to all available types.
        output:
            Directory or file path for saving charts.  When a directory is
            given each message type is saved as ``<output>/<MessageType>.png``.
            When a file path is given (only valid for a single message type)
            the chart is written directly to that path.  If *None* charts are
            not saved automatically.
        show:
            If *True* call :func:`matplotlib.pyplot.show` after generating all
            figures (useful in interactive environments).

        Returns
        -------
        list of Figure
        """
        types_to_plot = list(message_types or self.data.keys())
        figures: List[plt.Figure] = []

        for msg_type in types_to_plot:
            if msg_type not in self.data:
                continue
            df = self.data[msg_type]
            fields = self._fields_for(msg_type, df)
            if not fields:
                continue
            fig = self._make_figure(msg_type, df, fields)
            figures.append(fig)
            if output:
                self._save(fig, msg_type, output, len(types_to_plot))

        if show:
            plt.show()

        return figures

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fields_for(msg_type: str, df: pd.DataFrame) -> List[str]:
        """Return ordered list of fields to plot for *msg_type*."""
        preferred = _DEFAULT_PLOT_FIELDS.get(msg_type, [])
        available = [f for f in preferred if f in df.columns]
        if available:
            return available
        # Fall back: plot all numeric columns except timestamp
        return [
            c for c in df.select_dtypes(include="number").columns
            if c != "timestamp"
        ]

    @staticmethod
    def _field_label(field: str, msg_type: str = "") -> str:
        return _FIELD_LABELS.get((msg_type, field), _FIELD_LABELS.get(field, field))

    @staticmethod
    def _make_figure(
        msg_type: str,
        df: pd.DataFrame,
        fields: List[str],
    ) -> plt.Figure:
        """Build a figure with one subplot per field."""
        n = len(fields)
        fig, axes = plt.subplots(n, 1, figsize=(12, 3 * n), sharex=True)
        if n == 1:
            axes = [axes]

        time_col = df["timestamp"] - df["timestamp"].iloc[0]  # seconds from start

        for ax, field in zip(axes, fields):
            ax.plot(time_col, df[field], linewidth=1.0)
            ax.set_ylabel(TlogPlotter._field_label(field, msg_type), fontsize=9)
            ax.grid(True, linestyle="--", alpha=0.5)

        axes[-1].set_xlabel("Time (s)")
        fig.suptitle(msg_type, fontsize=12, fontweight="bold")
        fig.tight_layout()
        return fig

    @staticmethod
    def _save(fig: plt.Figure, msg_type: str, output: str, n_types: int) -> None:
        """Save *fig* to *output* (directory or file path).

        When *n_types* > 1, or when *output* has no file extension (i.e. it
        looks like a directory name), charts are stored inside *output* as
        ``<output>/<MessageType>.png``.  Otherwise *output* is used directly
        as the destination file path.
        """
        _, ext = os.path.splitext(output)
        is_dir_target = n_types > 1 or os.path.isdir(output) or not ext
        if is_dir_target:
            os.makedirs(output, exist_ok=True)
            path = os.path.join(output, f"{msg_type}.png")
        else:
            os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
            path = output
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

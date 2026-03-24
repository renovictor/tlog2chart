"""Tests for tlog2chart.plotter."""

from __future__ import annotations

import struct
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import pytest

from tlog2chart.plotter import TlogPlotter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vfr_hud_df(n: int = 10) -> pd.DataFrame:
    """Return a synthetic VFR_HUD DataFrame."""
    return pd.DataFrame(
        {
            "timestamp": [1_700_000_000.0 + i for i in range(n)],
            "airspeed": [10.0 + i for i in range(n)],
            "groundspeed": [9.0 + i for i in range(n)],
            "alt": [100.0 + i for i in range(n)],
            "throttle": [50] * n,
            "climb": [0.5] * n,
        }
    )


def _make_attitude_df(n: int = 10) -> pd.DataFrame:
    """Return a synthetic ATTITUDE DataFrame."""
    return pd.DataFrame(
        {
            "timestamp": [1_700_000_000.0 + i * 0.1 for i in range(n)],
            "roll": [0.01 * i for i in range(n)],
            "pitch": [0.005 * i for i in range(n)],
            "yaw": [0.02 * i for i in range(n)],
        }
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTlogPlotterInit:
    def test_init_stores_data(self):
        data = {"VFR_HUD": _make_vfr_hud_df()}
        plotter = TlogPlotter(data)
        assert plotter.data is data


class TestTlogPlotterPlot:
    def test_returns_list_of_figures(self):
        data = {"VFR_HUD": _make_vfr_hud_df()}
        plotter = TlogPlotter(data)
        figs = plotter.plot()
        assert isinstance(figs, list)
        assert len(figs) == 1
        assert isinstance(figs[0], plt.Figure)
        plt.close("all")

    def test_figure_per_message_type(self):
        data = {"VFR_HUD": _make_vfr_hud_df(), "ATTITUDE": _make_attitude_df()}
        plotter = TlogPlotter(data)
        figs = plotter.plot()
        assert len(figs) == 2
        plt.close("all")

    def test_subset_message_types(self):
        data = {"VFR_HUD": _make_vfr_hud_df(), "ATTITUDE": _make_attitude_df()}
        plotter = TlogPlotter(data)
        figs = plotter.plot(message_types=["VFR_HUD"])
        assert len(figs) == 1
        plt.close("all")

    def test_unknown_message_type_skipped(self):
        data = {"VFR_HUD": _make_vfr_hud_df()}
        plotter = TlogPlotter(data)
        figs = plotter.plot(message_types=["NONEXISTENT"])
        assert figs == []
        plt.close("all")

    def test_saves_png_to_directory(self, tmp_path):
        data = {"VFR_HUD": _make_vfr_hud_df()}
        plotter = TlogPlotter(data)
        out_dir = str(tmp_path / "charts")
        plotter.plot(output=out_dir)
        assert (tmp_path / "charts" / "VFR_HUD.png").exists()

    def test_saves_multiple_charts(self, tmp_path):
        data = {"VFR_HUD": _make_vfr_hud_df(), "ATTITUDE": _make_attitude_df()}
        plotter = TlogPlotter(data)
        out_dir = str(tmp_path / "charts")
        plotter.plot(output=out_dir)
        assert (tmp_path / "charts" / "VFR_HUD.png").exists()
        assert (tmp_path / "charts" / "ATTITUDE.png").exists()

    def test_saves_single_chart_to_file(self, tmp_path):
        data = {"VFR_HUD": _make_vfr_hud_df()}
        plotter = TlogPlotter(data)
        out_file = str(tmp_path / "output.png")
        plotter.plot(message_types=["VFR_HUD"], output=out_file)
        assert (tmp_path / "output.png").exists()

    def test_figure_has_correct_title(self):
        data = {"VFR_HUD": _make_vfr_hud_df()}
        plotter = TlogPlotter(data)
        figs = plotter.plot()
        title = figs[0]._suptitle.get_text()
        assert title == "VFR_HUD"
        plt.close("all")

    def test_figure_subplots_count_matches_fields(self):
        data = {"ATTITUDE": _make_attitude_df()}
        plotter = TlogPlotter(data)
        figs = plotter.plot()
        # ATTITUDE default fields: roll, pitch, yaw = 3 subplots
        axes = figs[0].get_axes()
        assert len(axes) == 3
        plt.close("all")

    def test_empty_data_returns_no_figures(self):
        plotter = TlogPlotter({})
        figs = plotter.plot()
        assert figs == []

    def test_dataframe_missing_fields_falls_back(self):
        """When preferred fields are absent, fall back to all numeric columns."""
        data = {"VFR_HUD": pd.DataFrame({"timestamp": [1.0, 2.0], "custom_field": [3.0, 4.0]})}
        plotter = TlogPlotter(data)
        figs = plotter.plot()
        assert len(figs) == 1
        plt.close("all")

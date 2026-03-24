"""Tests for the tlog2chart CLI (__main__)."""

from __future__ import annotations

import struct

import pytest

from tlog2chart.__main__ import main


# ---------------------------------------------------------------------------
# Helpers (duplicated from test_parser.py for self-contained test module)
# ---------------------------------------------------------------------------


def _write_tlog(path: str, messages: list) -> None:
    with open(path, "wb") as f:
        for ts_sec, packet_bytes in messages:
            ts_usec = int(ts_sec * 1_000_000)
            f.write(struct.pack(">Q", ts_usec))
            f.write(packet_bytes)


def _vfr_hud_packet(airspeed: float, groundspeed: float, alt: float) -> bytes:
    from pymavlink.dialects.v20 import ardupilotmega as mavlink2

    mav = mavlink2.MAVLink(None, srcSystem=1, srcComponent=1)
    msg = mavlink2.MAVLink_vfr_hud_message(
        airspeed=float(airspeed),
        groundspeed=float(groundspeed),
        heading=90,
        throttle=50,
        alt=float(alt),
        climb=0.5,
    )
    return msg.pack(mav)


@pytest.fixture()
def sample_tlog(tmp_path):
    tlog_path = str(tmp_path / "sample.tlog")
    messages = [
        (1_700_000_000.0 + i, _vfr_hud_packet(10.0 + i, 9.0 + i, 100.0 + i))
        for i in range(5)
    ]
    _write_tlog(tlog_path, messages)
    return tlog_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMainCLI:
    def test_missing_file_returns_error(self, tmp_path):
        rc = main([str(tmp_path / "ghost.tlog")])
        assert rc == 1

    def test_successful_run_returns_zero(self, sample_tlog, tmp_path):
        out_dir = str(tmp_path / "charts")
        rc = main([sample_tlog, "-o", out_dir, "-m", "VFR_HUD"])
        assert rc == 0

    def test_chart_files_created(self, sample_tlog, tmp_path):
        out_dir = str(tmp_path / "charts")
        main([sample_tlog, "-o", out_dir, "-m", "VFR_HUD"])
        chart = tmp_path / "charts" / "VFR_HUD.png"
        assert chart.exists()

    def test_list_messages_flag(self, sample_tlog, capsys):
        rc = main([sample_tlog, "--list-messages", "-m", "VFR_HUD"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "VFR_HUD" in captured.out

    def test_no_matching_messages_returns_error(self, sample_tlog, tmp_path):
        out_dir = str(tmp_path / "charts")
        rc = main([sample_tlog, "-o", out_dir, "-m", "NONEXISTENT_MSG_TYPE"])
        assert rc == 1

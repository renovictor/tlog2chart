"""Tests for tlog2chart.parser."""

from __future__ import annotations

import os
import struct
import tempfile
import time

import pytest

from tlog2chart.parser import TlogParser, DEFAULT_MESSAGE_TYPES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_tlog(path: str, messages: list) -> None:
    """Write a list of (timestamp_sec, mavlink_packet_bytes) tuples to *path*."""
    with open(path, "wb") as f:
        for ts_sec, packet_bytes in messages:
            ts_usec = int(ts_sec * 1_000_000)
            f.write(struct.pack(">Q", ts_usec))
            f.write(packet_bytes)


def _vfr_hud_packet(airspeed: float, groundspeed: float, alt: float, throttle: int = 50) -> bytes:
    """Return a packed MAVLink VFR_HUD message."""
    from pymavlink.dialects.v20 import ardupilotmega as mavlink2

    mav = mavlink2.MAVLink(None, srcSystem=1, srcComponent=1)
    msg = mavlink2.MAVLink_vfr_hud_message(
        airspeed=float(airspeed),
        groundspeed=float(groundspeed),
        heading=90,
        throttle=int(throttle),
        alt=float(alt),
        climb=0.5,
    )
    return msg.pack(mav)


def _attitude_packet(roll: float, pitch: float, yaw: float) -> bytes:
    """Return a packed MAVLink ATTITUDE message."""
    from pymavlink.dialects.v20 import ardupilotmega as mavlink2

    mav = mavlink2.MAVLink(None, srcSystem=1, srcComponent=1)
    msg = mavlink2.MAVLink_attitude_message(
        time_boot_ms=0,
        roll=float(roll),
        pitch=float(pitch),
        yaw=float(yaw),
        rollspeed=0.0,
        pitchspeed=0.0,
        yawspeed=0.0,
    )
    return msg.pack(mav)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_tlog(tmp_path):
    """Return path to a temporary tlog file with VFR_HUD and ATTITUDE messages."""
    tlog_path = str(tmp_path / "sample.tlog")
    base_ts = 1_700_000_000.0  # fixed base timestamp
    messages = []
    for i in range(5):
        ts = base_ts + i
        messages.append((ts, _vfr_hud_packet(airspeed=10.0 + i, groundspeed=9.0 + i, alt=100.0 + i)))
        messages.append((ts + 0.1, _attitude_packet(roll=0.1 * i, pitch=0.05 * i, yaw=0.2 * i)))
    _write_tlog(tlog_path, messages)
    return tlog_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTlogParserInit:
    def test_raises_for_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="tlog file not found"):
            TlogParser(str(tmp_path / "nonexistent.tlog"))

    def test_default_message_types(self, sample_tlog):
        parser = TlogParser(sample_tlog)
        assert parser.message_types == list(DEFAULT_MESSAGE_TYPES)

    def test_custom_message_types(self, sample_tlog):
        parser = TlogParser(sample_tlog, message_types=["VFR_HUD"])
        assert parser.message_types == ["VFR_HUD"]

    def test_data_empty_before_parse(self, sample_tlog):
        parser = TlogParser(sample_tlog)
        assert parser.data == {}


class TestTlogParserParse:
    def test_parse_returns_dict(self, sample_tlog):
        parser = TlogParser(sample_tlog, message_types=["VFR_HUD", "ATTITUDE"])
        result = parser.parse()
        assert isinstance(result, dict)

    def test_vfr_hud_records_count(self, sample_tlog):
        parser = TlogParser(sample_tlog, message_types=["VFR_HUD"])
        data = parser.parse()
        assert "VFR_HUD" in data
        assert len(data["VFR_HUD"]) == 5

    def test_attitude_records_count(self, sample_tlog):
        parser = TlogParser(sample_tlog, message_types=["ATTITUDE"])
        data = parser.parse()
        assert "ATTITUDE" in data
        assert len(data["ATTITUDE"]) == 5

    def test_dataframe_has_timestamp_column(self, sample_tlog):
        parser = TlogParser(sample_tlog, message_types=["VFR_HUD"])
        data = parser.parse()
        assert "timestamp" in data["VFR_HUD"].columns

    def test_dataframe_has_expected_fields(self, sample_tlog):
        parser = TlogParser(sample_tlog, message_types=["VFR_HUD"])
        data = parser.parse()
        df = data["VFR_HUD"]
        for col in ("airspeed", "groundspeed", "alt"):
            assert col in df.columns, f"Missing column: {col}"

    def test_airspeed_values(self, sample_tlog):
        parser = TlogParser(sample_tlog, message_types=["VFR_HUD"])
        data = parser.parse()
        airspeeds = sorted(data["VFR_HUD"]["airspeed"].tolist())
        assert airspeeds == pytest.approx([10.0, 11.0, 12.0, 13.0, 14.0], abs=1e-3)

    def test_timestamps_are_increasing(self, sample_tlog):
        parser = TlogParser(sample_tlog, message_types=["VFR_HUD"])
        data = parser.parse()
        ts = data["VFR_HUD"]["timestamp"].tolist()
        assert ts == sorted(ts)

    def test_unknown_message_type_not_in_result(self, sample_tlog):
        parser = TlogParser(sample_tlog, message_types=["NONEXISTENT_MSG"])
        data = parser.parse()
        assert "NONEXISTENT_MSG" not in data

    def test_data_property_after_parse(self, sample_tlog):
        parser = TlogParser(sample_tlog, message_types=["VFR_HUD"])
        data = parser.parse()
        assert parser.data is data

    def test_available_message_types(self, sample_tlog):
        parser = TlogParser(sample_tlog, message_types=["VFR_HUD", "ATTITUDE"])
        parser.parse()
        types = parser.available_message_types()
        assert set(types) == {"VFR_HUD", "ATTITUDE"}

    def test_multiple_types_parsed_together(self, sample_tlog):
        parser = TlogParser(sample_tlog, message_types=["VFR_HUD", "ATTITUDE"])
        data = parser.parse()
        assert "VFR_HUD" in data
        assert "ATTITUDE" in data

"""Tests for the EVC tlog parser."""

import sys
import os
import textwrap
import tempfile
import pytest

# Ensure the project root is on the path so the modules can be imported
# (conftest.py also inserts the root path, but this makes the file self-contained)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import tlog_parser
from tlog_parser import TlogFile, TlogMetadata, TlogRecord


SAMPLE_TLOG = textwrap.dedent("""\
    // collect_tlog_2.0
    // Set-Top Box uptime_start: 0
    // tlog start time : 20240115-080000
    tlog
    Idx  Date(MM/DD/YY)  StartTime  StopTime  Duration(m)  Energy(kWh)  Fault  User
    001  01/15/24        08:00:00   09:03:12  063          07.214       0000   RFID:1001
    002  01/15/24        09:45:31   10:52:44  067          07.856       0000   RFID:1002
    003  01/16/24        11:10:00   12:40:15  090          10.531       0001   RFID:1003
    Printed from SN: 53300201
    // Set-Top Box uptime_end: 300
    // tlog took(min): 5.00
    // tlog end time : 20240115-080500
""")

EMPTY_TLOG = textwrap.dedent("""\
    // collect_tlog_2.0
    // Set-Top Box uptime_start: 100
    // tlog start time : 20240115-090000
    tlog
    The log is empty
    // Set-Top Box uptime_end: 110
    // tlog took(min): 0.17
    // tlog end time : 20240115-090010
""")


def _write_temp(content: str) -> str:
    """Write *content* to a temporary file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="tlog_test_")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


# --------------------------------------------------------------------------- #
# Metadata parsing                                                             #
# --------------------------------------------------------------------------- #

class TestMetadataParsing:
    def setup_method(self):
        path = _write_temp(SAMPLE_TLOG)
        self.tlog: TlogFile = tlog_parser.parse_file(path)
        os.unlink(path)

    def test_version(self):
        assert self.tlog.metadata.version == "2.0"

    def test_uptime_start(self):
        assert self.tlog.metadata.uptime_start_sec == 0

    def test_uptime_end(self):
        assert self.tlog.metadata.uptime_end_sec == 300

    def test_tlog_start_time(self):
        assert self.tlog.metadata.tlog_start_time == "20240115-080000"

    def test_tlog_end_time(self):
        assert self.tlog.metadata.tlog_end_time == "20240115-080500"

    def test_tlog_duration(self):
        assert self.tlog.metadata.tlog_duration_min == pytest.approx(5.0)

    def test_serial_number(self):
        assert self.tlog.metadata.serial_number == "53300201"


# --------------------------------------------------------------------------- #
# Record parsing                                                               #
# --------------------------------------------------------------------------- #

class TestRecordParsing:
    def setup_method(self):
        path = _write_temp(SAMPLE_TLOG)
        self.tlog: TlogFile = tlog_parser.parse_file(path)
        os.unlink(path)

    def test_record_count(self):
        assert len(self.tlog.records) == 3

    def test_first_record_index(self):
        assert self.tlog.records[0].index == 1

    def test_first_record_date(self):
        assert self.tlog.records[0].date == "01/15/24"

    def test_first_record_start_time(self):
        assert self.tlog.records[0].start_time == "08:00:00"

    def test_first_record_stop_time(self):
        assert self.tlog.records[0].stop_time == "09:03:12"

    def test_first_record_duration(self):
        assert self.tlog.records[0].duration_min == pytest.approx(63.0)

    def test_first_record_energy(self):
        assert self.tlog.records[0].energy_kwh == pytest.approx(7.214)

    def test_first_record_fault(self):
        assert self.tlog.records[0].fault == "0000"

    def test_first_record_user(self):
        assert self.tlog.records[0].user == "RFID:1001"

    def test_faulted_record(self):
        assert self.tlog.records[2].fault == "0001"

    def test_start_dt_parsed(self):
        from datetime import datetime
        assert self.tlog.records[0].start_dt == datetime(2024, 1, 15, 8, 0, 0)


# --------------------------------------------------------------------------- #
# Empty tlog                                                                   #
# --------------------------------------------------------------------------- #

class TestEmptyTlog:
    def setup_method(self):
        path = _write_temp(EMPTY_TLOG)
        self.tlog: TlogFile = tlog_parser.parse_file(path)
        os.unlink(path)

    def test_no_records(self):
        assert len(self.tlog.records) == 0

    def test_version_still_parsed(self):
        assert self.tlog.metadata.version == "2.0"

    def test_uptime_start(self):
        assert self.tlog.metadata.uptime_start_sec == 100


# --------------------------------------------------------------------------- #
# Sample file round-trip                                                       #
# --------------------------------------------------------------------------- #

class TestSampleFile:
    def test_sample_file_parses(self):
        sample_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "sample_data", "sample_tlog.txt"
        )
        tlog = tlog_parser.parse_file(sample_path)
        assert len(tlog.records) == 20
        assert tlog.metadata.serial_number == "53300201"
        total_energy = sum(r.energy_kwh for r in tlog.records)
        assert total_energy == pytest.approx(179.241, abs=0.01)

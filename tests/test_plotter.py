"""Tests for the EVC tlog plotter."""

import os
import sys
import textwrap
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import tlog_parser
import plotter


SAMPLE_TLOG = textwrap.dedent("""\
    // collect_tlog_2.0
    // Set-Top Box uptime_start: 0
    // tlog start time : 20240115-080000
    tlog
    Idx  Date(MM/DD/YY)  StartTime  StopTime  Duration(m)  Energy(kWh)  Fault  User
    001  01/15/24        08:00:00   09:03:12  063          07.214       0000   RFID:1001
    002  01/15/24        09:45:31   10:52:44  067          07.856       0000   RFID:1002
    003  01/16/24        11:10:00   12:40:15  090          10.531       0001   RFID:1003
    004  01/17/24        14:00:00   14:45:00  045          05.250       0000   RFID:1002
    Printed from SN: 53300201
    // tlog end time : 20240115-080500
""")


def _write_temp(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="tlog_test_")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


class TestPlotter:
    def setup_method(self):
        tlog_path = _write_temp(SAMPLE_TLOG)
        self.tlog = tlog_parser.parse_file(tlog_path)
        os.unlink(tlog_path)
        self.out_dir = tempfile.mkdtemp(prefix="tlog2chart_test_")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.out_dir, ignore_errors=True)

    def test_generates_files(self):
        generated = plotter.plot_tlog(self.tlog, output_dir=self.out_dir)
        assert len(generated) > 0
        for path in generated:
            assert os.path.isfile(path), f"Missing: {path}"

    def test_energy_per_session_created(self):
        plotter.plot_tlog(self.tlog, output_dir=self.out_dir)
        assert os.path.isfile(os.path.join(self.out_dir, "energy_per_session.png"))

    def test_duration_per_session_created(self):
        plotter.plot_tlog(self.tlog, output_dir=self.out_dir)
        assert os.path.isfile(os.path.join(self.out_dir, "duration_per_session.png"))

    def test_energy_over_time_created(self):
        plotter.plot_tlog(self.tlog, output_dir=self.out_dir)
        assert os.path.isfile(os.path.join(self.out_dir, "energy_over_time.png"))

    def test_cumulative_energy_created(self):
        plotter.plot_tlog(self.tlog, output_dir=self.out_dir)
        assert os.path.isfile(os.path.join(self.out_dir, "cumulative_energy.png"))

    def test_daily_energy_created(self):
        plotter.plot_tlog(self.tlog, output_dir=self.out_dir)
        assert os.path.isfile(os.path.join(self.out_dir, "daily_energy.png"))

    def test_empty_tlog_returns_empty_list(self):
        from tlog_parser import TlogFile, TlogMetadata
        empty = TlogFile(
            path="",
            metadata=TlogMetadata(),
            records=[],
            raw_header_lines=[],
            raw_data_lines=[],
        )
        generated = plotter.plot_tlog(empty, output_dir=self.out_dir)
        assert generated == []

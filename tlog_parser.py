"""Parser for EVC tlog files produced by the RF Data Logger."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


# Markers written by the RF Data Logger (collect_tlog_2.0 format)
_COMMENT_PREFIX = "//"
_TLOG_END_TOKENS = ("Printed from", "The log is empty")
_HEADER_VERSION_RE = re.compile(r"//\s*collect_tlog_(\S+)")

# Column headers expected in the device data section
_DATA_HEADER_KEYWORDS = ("Idx", "idx", "SEQ", "Seq")


@dataclass
class TlogMetadata:
    """Metadata extracted from the collect_tlog_2.0 comment header."""

    version: str = ""
    uptime_start_sec: Optional[int] = None
    uptime_end_sec: Optional[int] = None
    tlog_start_time: Optional[str] = None
    tlog_end_time: Optional[str] = None
    tlog_duration_min: Optional[float] = None
    serial_number: Optional[str] = None


@dataclass
class TlogRecord:
    """A single charging-session record from the tlog data table."""

    index: int
    date: str                           # MM/DD/YY as stored in the log
    start_time: str                     # HH:MM:SS
    stop_time: str                      # HH:MM:SS
    duration_min: float
    energy_kwh: float
    fault: str
    user: str
    # Derived
    start_dt: Optional[datetime] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.start_dt is None:
            try:
                self.start_dt = datetime.strptime(
                    f"{self.date} {self.start_time}", "%m/%d/%y %H:%M:%S"
                )
            except ValueError:
                self.start_dt = None


@dataclass
class TlogFile:
    """Parsed contents of a single EVC tlog file."""

    path: str
    metadata: TlogMetadata
    records: List[TlogRecord]
    raw_header_lines: List[str]
    raw_data_lines: List[str]


def parse_file(path: str) -> TlogFile:
    """Parse an EVC tlog file and return a :class:`TlogFile`.

    Parameters
    ----------
    path:
        Filesystem path to the tlog text file.

    Returns
    -------
    TlogFile
        Parsed metadata and list of :class:`TlogRecord` objects.
    """
    with open(path, encoding="utf-8", errors="ignore") as fh:
        lines = fh.readlines()

    metadata = TlogMetadata()
    raw_header: List[str] = []
    raw_data: List[str] = []
    records: List[TlogRecord] = []

    in_data_section = False
    col_header_parsed = False

    for raw_line in lines:
        line = raw_line.rstrip("\r\n")

        # ------------------------------------------------------------------ #
        # Comment / metadata lines (prefixed with "//")                       #
        # ------------------------------------------------------------------ #
        if line.startswith(_COMMENT_PREFIX):
            raw_header.append(line)
            m = _HEADER_VERSION_RE.match(line)
            if m:
                metadata.version = m.group(1)
                continue

            lower = line.lower()
            if "uptime_start" in lower:
                val = _extract_int_after_colon(line)
                if val is not None:
                    metadata.uptime_start_sec = val
            elif "uptime_end" in lower:
                val = _extract_int_after_colon(line)
                if val is not None:
                    metadata.uptime_end_sec = val
            elif "tlog start time" in lower:
                metadata.tlog_start_time = line.split(":", 1)[1].strip()
            elif "tlog end time" in lower:
                metadata.tlog_end_time = line.split(":", 1)[1].strip()
            elif "tlog took" in lower:
                val_f = _extract_float_after_colon(line)
                if val_f is not None:
                    metadata.tlog_duration_min = val_f
            continue

        # ------------------------------------------------------------------ #
        # Device-output end markers                                            #
        # ------------------------------------------------------------------ #
        if any(line.startswith(tok) for tok in _TLOG_END_TOKENS):
            if "Printed from" in line and "SN:" in line:
                metadata.serial_number = line.split("SN:", 1)[1].strip()
            raw_data.append(line)
            in_data_section = False
            continue

        # ------------------------------------------------------------------ #
        # Skip the "tlog" echo line (the device echoes the command)           #
        # ------------------------------------------------------------------ #
        if line.strip() == "tlog":
            in_data_section = True
            continue

        # ------------------------------------------------------------------ #
        # Column header row                                                   #
        # ------------------------------------------------------------------ #
        if not col_header_parsed and any(kw in line for kw in _DATA_HEADER_KEYWORDS):
            col_header_parsed = True
            in_data_section = True
            raw_data.append(line)
            continue

        # ------------------------------------------------------------------ #
        # Data rows                                                           #
        # ------------------------------------------------------------------ #
        if in_data_section and line.strip():
            raw_data.append(line)
            record = _parse_data_line(line)
            if record is not None:
                records.append(record)

    return TlogFile(
        path=path,
        metadata=metadata,
        records=records,
        raw_header_lines=raw_header,
        raw_data_lines=raw_data,
    )


# --------------------------------------------------------------------------- #
# Internal helpers                                                              #
# --------------------------------------------------------------------------- #

def _extract_int_after_colon(line: str) -> Optional[int]:
    if ":" not in line:
        return None
    try:
        return int(line.split(":")[-1].strip())
    except ValueError:
        return None


def _extract_float_after_colon(line: str) -> Optional[float]:
    if ":" not in line:
        return None
    try:
        return float(line.split(":")[-1].strip())
    except ValueError:
        return None


def _parse_data_line(line: str) -> Optional[TlogRecord]:
    """Attempt to parse a whitespace-delimited data row.

    Expected column order (produced by the Tykon EVC tlog command):
        Idx  Date(MM/DD/YY)  StartTime  StopTime  Duration(m)  Energy(kWh)  Fault  User

    Returns ``None`` if the line cannot be parsed.
    """
    parts = line.split()
    if len(parts) < 7:
        return None

    try:
        idx = int(parts[0])
    except ValueError:
        return None

    try:
        date = parts[1]    # MM/DD/YY
        start_time = parts[2]
        stop_time = parts[3]
        duration_min = float(parts[4])
        energy_kwh = float(parts[5])
        fault = parts[6]
        user = parts[7] if len(parts) > 7 else ""
    except (ValueError, IndexError):
        return None

    return TlogRecord(
        index=idx,
        date=date,
        start_time=start_time,
        stop_time=stop_time,
        duration_min=duration_min,
        energy_kwh=energy_kwh,
        fault=fault,
        user=user,
    )

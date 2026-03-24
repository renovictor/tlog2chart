"""Parser for MAVLink telemetry log (.tlog) files."""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Dict, List, Optional

import pandas as pd
from pymavlink import mavutil


# Message types relevant to EVC (Electric Vehicle Controller) telemetry
DEFAULT_MESSAGE_TYPES = [
    "BATTERY_STATUS",
    "SYS_STATUS",
    "VFR_HUD",
    "GPS_RAW_INT",
    "ATTITUDE",
    "GLOBAL_POSITION_INT",
]


class TlogParser:
    """Parse a MAVLink .tlog file and extract telemetry data as DataFrames.

    Parameters
    ----------
    filepath:
        Path to the ``.tlog`` file to parse.
    message_types:
        List of MAVLink message type names to extract.  Defaults to
        :data:`DEFAULT_MESSAGE_TYPES`.
    """

    def __init__(
        self,
        filepath: str,
        message_types: Optional[List[str]] = None,
    ) -> None:
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"tlog file not found: {filepath}")
        self.filepath = filepath
        self.message_types = list(message_types or DEFAULT_MESSAGE_TYPES)
        self._data: Dict[str, pd.DataFrame] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self) -> Dict[str, pd.DataFrame]:
        """Parse the tlog file and return a mapping of message type to DataFrame.

        Each DataFrame has a ``timestamp`` column (seconds since epoch) plus
        one column per numeric field found in that message type.

        Returns
        -------
        dict
            ``{message_type: DataFrame}``
        """
        raw: Dict[str, List[dict]] = defaultdict(list)

        mlog = mavutil.mavlink_connection(self.filepath)
        try:
            while True:
                msg = mlog.recv_match(
                    type=self.message_types,
                    blocking=False,
                )
                if msg is None:
                    break
                msg_type = msg.get_type()
                row = self._extract_row(msg)
                if row:
                    raw[msg_type].append(row)
        finally:
            mlog.close()

        self._data = {
            msg_type: pd.DataFrame(rows)
            for msg_type, rows in raw.items()
            if rows
        }
        return self._data

    @property
    def data(self) -> Dict[str, pd.DataFrame]:
        """Return last parsed data, or an empty dict if :meth:`parse` has not been called."""
        return self._data

    def available_message_types(self) -> List[str]:
        """Return the message types that were actually found in the file."""
        return list(self._data.keys())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_row(msg) -> Optional[dict]:
        """Extract a flat dict of numeric fields plus timestamp from *msg*."""
        fieldnames = getattr(msg, "fieldnames", [])
        if not fieldnames:
            return None

        row: dict = {}

        # Prefer _timestamp attribute set by pymavlink when reading tlogs
        ts = getattr(msg, "_timestamp", None)
        if ts is not None:
            row["timestamp"] = float(ts)

        for field in fieldnames:
            value = getattr(msg, field, None)
            if isinstance(value, (int, float)):
                row[field] = value

        # Require at least a timestamp and one data field
        if "timestamp" not in row or len(row) < 2:
            return None

        return row

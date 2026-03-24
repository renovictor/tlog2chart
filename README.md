# tlog2chart

Convert EVC (Electric Vehicle Charger) tlog files into charts.

EVC tlog files are transaction logs downloaded from Tykon EV Charger units via
the `RF Data Logger` tool.  Each file starts with a `// collect_tlog_2.0`
header and contains one row per charging session.

## Requirements

```
pip install -r requirements.txt
```

## Usage

```
python tlog2chart.py <tlog_file> [<tlog_file> ...] [-o OUTPUT_DIR] [--show]
```

### Examples

```bash
# Plot a single tlog file (charts saved next to the file):
python tlog2chart.py sample_data/sample_tlog.txt

# Specify output directory:
python tlog2chart.py logs/001_53300201_20240115-080000_tlog.txt -o charts/

# Plot all tlog files in a folder:
python tlog2chart.py logs/*_tlog.txt -o charts/
```

## Generated charts

| File | Description |
|------|-------------|
| `energy_per_session.png` | Energy (kWh) delivered per session (faults highlighted in red) |
| `duration_per_session.png` | Session duration (minutes) per session |
| `energy_over_time.png` | Energy scatter/line plot over calendar time |
| `cumulative_energy.png` | Cumulative energy delivered over time |
| `daily_energy.png` | Daily energy totals (only when log spans ≥ 2 days) |

## Tlog file format

The tool expects tlog files in the `collect_tlog_2.0` format produced by the
RF Data Logger:

```
// collect_tlog_2.0
// Set-Top Box uptime_start: 0
// tlog start time : 20240115-080000
tlog
Idx  Date(MM/DD/YY)  StartTime  StopTime  Duration(m)  Energy(kWh)  Fault  User
001  01/15/24        08:00:00   09:03:12  063          07.214       0000   RFID:1001
...
Printed from SN: 53300201
// tlog end time : 20240115-080500
```

## Running tests

```
python -m pytest tests/ -v
```
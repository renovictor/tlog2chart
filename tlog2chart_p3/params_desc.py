from __future__ import annotations

import re
from typing import Dict, List, Tuple

# =============================================================================
# ----------------------------- Parameter descriptions -------------------------
# =============================================================================

# NOTE:
# Descriptions are used in Parameters tab. Values are extracted from tlog header.
# For v3.4 we keep mapping best-effort; missing items will show blank description.

TYKON_DESC_TEXT = r"""
# General Parameters
2  User Control Input Source. --> 0-ECAT, 1-HW, Six 0/1 digits [MANUAL RF_ON, PLS_EN, C1_SET, C2_SET, PFWD_SET]
3  Misc Options --> 0-Disable, 1-Enable. Two 0/1 digits [PULSE_WIDTH_FAULT_ENABLE, PULSE_FAULT_ENABLE]
4  FPGA Diagnostic Vector Select (0..15)
6  P/S Fault Monitor (0/1)
7  Default TLog Mode 0/1/2 (some/all/rf)
8  DeviceNet communication timeout (0=disable)
9  Disable Devicenet (0=DNet Enabled, 1=DNet Disabled)
10 DeviceNet MAC ID
11 DeviceNet baud rate
12 ECAT Product Code (HEX)
13 ADC Speed
14 VIP Sampling start (%)
15 VIP Sampling stop (%)
16 VIP Sampling start (us)
17 VIP Sampling length (us)
18 VIP Sampling start from end (us)
19 VIP Sampling start mode (0=% 1=us 2=us from end)
20 VIP Sampling end mode (0=% 1=us len)
21 Ignore Fans xyz (000-111)
22 Interlocks monitor/ignore
23 Cap Dead Time [us]
24 Interface Board Rev
25 P/S Vin Fault Low Limit [V]
26 P/S Vin Fault High Limit [V]
27 DCBias AutoRng low->high [V]
28 DCBias AutoRng high->low [V]
29 Allow HVDC rise time [ms]
30 HVDC Fault High Limit [V]
31 Amb Temp threshold cumulative log [deg]
32 Cap map selection
33 MinSample count for matching
34 Cap Switching Time [us]
35 Analog cap preset noise threshold [%]
37 RF off detection time [ms]
38 Startup Mode (0 user / 1 factory)
39 Control loops per ms
40 Local/bench mode selection
41 Local mode CW hold time [ms]
42 Local mode VDC abs threshold
43 Local mode VDC monitoring delay [ms]
44 Use local params for remote mode (0/1)
45 Data collection algorithm selection
46 Wait after PDAC change [us]
47 Gamma correction factor for PDAC Adj
48 Phase offset for PDAC Adj [deg]
49 Max correction counts for PDAC
50 Fan fault hold time [ms]
51 Fan1 PWM
52 Fan1 RPM fault threshold
53 Fan1 RPM clear threshold
54 Fan2 PWM
55 Fan2 RPM fault threshold
56 Fan2 RPM clear threshold
57 Fan3 PWM
58 Fan3 RPM fault threshold
59 Fan3 RPM clear threshold
60 Use Gen VIP for power ctrl in pulse mode (0/1)
61 SetPt threshold switch DC rail [W]
62 Apply cal table constant PDAC threshold [W]
63 C1 hold offset [%]
64 C2 hold offset [%]
65 Hold/jump DAC during startup mode
66 DCRail voltage for SetPt > param61 [V]
67 DCRail voltage for SetPt <= param61 [V]
68 DC rail control mode (0 fixed / 1 dynamic)
69 Apply setPt % correction for striking
70 Average power setPt from analog port
71 Hold CW match position in low power pulse mode

# Match Parameters
104 Max Vcap raw limit [V]
105 Max Vcap avg limit [V]
107 Delay after reaching match (steps)
109 Delay after losing match (steps)
111 Max Vcap cumulative log [V]
112 Max Vcap [V]
113 HVDC low -> shutdown PS [V]
114 HVDC low -> pause matching [V]
115 HVDC high -> resume matching [V]
116 HVDC target at power up [V]
120 Gamma correction angle [deg]
121 |Z| multiplicative correction
122 |Z| additive correction
123 Phase multiplicative correction
124 Phase additive correction
125 Vpp DAC average log2(samples)
126 Vpp correction factor
127 RF frequency [MHz]
132 Dual restart enable mode
133 Max cap movement fine steps
139 VIP sensor settling time [us]
140 VPP sensor settling time [us]
144 Cap toggle limiting interval [ms]
145 Max cap toggles within interval
146 If RF off, Vpp must exceed to report [V]
150 Hunting algorithm enable
151 Hunting algorithm selection
152 |Gamma| threshold hunting vs table match
159 Alg1 target |Zin|
160 Alg1 target |Xin|
161-169 Pref/Gamma thresholds

# Generator Parameters
300 Max power [W]
305 Nominal DC voltage limit for DCPS [V]
307 Nominal DC current limit [A]
315 RF ramp rate [W/s]
345 Max PA temp [C]
"""

QUANTUM_DESC_TEXT = r"""
# General Parameters
1  Maximum Ambient temperature
2  User Control Input Src (HF/LF control bits)
3  Misc Options (pulse fault enables)
4  FPGA Diagnostic vector select
6  Monitor PS voltages for fault generation
7  Default TLog Mode
8  DeviceNet communication timeout
9  Disable Devicenet
10 DeviceNet MAC ID
11 DeviceNet baud rate
13 Min sample count
20 Fan fault hold time
21 Ignore fans
22 Interlocks monitor/ignore
24 Cap map selection
25 PS Vin fault low
26 PS Vin fault high
27 DCBias auto range low->high
28 DCBias auto range high->low
29 Allow HVDC rise time
30 HVDC fault high limit

# HF Match Params
101-169 HF match parameters

# LF Match Params
201-269 LF match parameters
"""


def build_desc_map_from_text(text: str) -> Dict[str, Dict[int, str]]:
    desc: Dict[str, Dict[int, str]] = {}
    section = "General Parameters"
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            section = line.lstrip("#").strip()
            desc.setdefault(section, {})
            continue
        m = re.match(r"^(\d+)\s+(.*)$", line)
        if m:
            pid = int(m.group(1))
            d = m.group(2).strip()
            desc.setdefault(section, {})[pid] = d
    return desc


TYKON_DESC = build_desc_map_from_text(TYKON_DESC_TEXT)
QUANTUM_DESC = build_desc_map_from_text(QUANTUM_DESC_TEXT)


def parse_param_pairs_from_line(line: str) -> List[Tuple[int, str]]:
    """
    Parse param id/value pairs from header lines.
    Supports:
      - Quantum style: "1,70.0,2,1111,3,0,..."
      - Tykon style: "2 011001, 3 00, 4 0"
      - Doc style: "101: 10.0 ms = ..."
    """
    s = line.strip()
    out: List[Tuple[int, str]] = []

    # Doc style: "101: 10.0 ms = ..."
    m = re.match(r"^\s*(\d+)\s*:\s*([^=]+?)\s*=", s)
    if m:
        return [(int(m.group(1)), m.group(2).strip())]

    # Quantum comma pairs: id,value,id,value,...
    if "," in s and re.match(r"^\s*\d+\s*,", s):
        toks = [t.strip() for t in s.split(",") if t.strip() != ""]
        i = 0
        while i + 1 < len(toks):
            if re.fullmatch(r"\d+", toks[i]):
                out.append((int(toks[i]), toks[i + 1]))
                i += 2
            else:
                i += 1
        if out:
            return out

    # Tykon: "id value" chunks separated by commas
    chunks = [c.strip() for c in s.split(",")]
    for ch in chunks:
        m2 = re.match(r"^\s*(\d+)\s+(.+?)\s*$", ch)
        if m2:
            out.append((int(m2.group(1)), m2.group(2).strip()))

    return out


def build_param_value_table(header_params: List[Tuple[str, str]]) -> List[Tuple[str, int, str]]:
    rows: List[Tuple[str, int, str]] = []
    for section, line in header_params:
        pairs = parse_param_pairs_from_line(line)
        for pid, val in pairs:
            rows.append((section, pid, val))
    return rows

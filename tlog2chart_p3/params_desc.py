# from __future__ import annotations
#
# import re
# from typing import Dict, List, Tuple
#
# # =============================================================================
# # ----------------------------- Parameter descriptions -------------------------
# # =============================================================================
#
# # NOTE:
# # Descriptions are used in Parameters tab. Values are extracted from tlog header.
# # For v3.4 we keep mapping best-effort; missing items will show blank description.
#
# TYKON_DESC_TEXT = r"""
# # General Parameters
# 2  User Control Input Source. --> 0-ECAT, 1-HW, Six 0/1 digits [MANUAL RF_ON, PLS_EN, C1_SET, C2_SET, PFWD_SET]
# 3  Misc Options --> 0-Disable, 1-Enable. Two 0/1 digits [PULSE_WIDTH_FAULT_ENABLE, PULSE_FAULT_ENABLE]
# 4  FPGA Diagnostic Vector Select (0..15)
# 6  P/S Fault Monitor (0/1)
# 7  Default TLog Mode 0/1/2 (some/all/rf)
# 8  DeviceNet communication timeout (0=disable)
# 9  Disable Devicenet (0=DNet Enabled, 1=DNet Disabled)
# 10 DeviceNet MAC ID
# 11 DeviceNet baud rate
# 12 ECAT Product Code (HEX)
# 13 ADC Speed
# 14 VIP Sampling start (%)
# 15 VIP Sampling stop (%)
# 16 VIP Sampling start (us)
# 17 VIP Sampling length (us)
# 18 VIP Sampling start from end (us)
# 19 VIP Sampling start mode (0=% 1=us 2=us from end)
# 20 VIP Sampling end mode (0=% 1=us len)
# 21 Ignore Fans xyz (000-111)
# 22 Interlocks monitor/ignore
# 23 Cap Dead Time [us]
# 24 Interface Board Rev
# 25 P/S Vin Fault Low Limit [V]
# 26 P/S Vin Fault High Limit [V]
# 27 DCBias AutoRng low->high [V]
# 28 DCBias AutoRng high->low [V]
# 29 Allow HVDC rise time [ms]
# 30 HVDC Fault High Limit [V]
# 31 Amb Temp threshold cumulative log [deg]
# 32 Cap map selection
# 33 MinSample count for matching
# 34 Cap Switching Time [us]
# 35 Analog cap preset noise threshold [%]
# 37 RF off detection time [ms]
# 38 Startup Mode (0 user / 1 factory)
# 39 Control loops per ms
# 40 Local/bench mode selection
# 41 Local mode CW hold time [ms]
# 42 Local mode VDC abs threshold
# 43 Local mode VDC monitoring delay [ms]
# 44 Use local params for remote mode (0/1)
# 45 Data collection algorithm selection
# 46 Wait after PDAC change [us]
# 47 Gamma correction factor for PDAC Adj
# 48 Phase offset for PDAC Adj [deg]
# 49 Max correction counts for PDAC
# 50 Fan fault hold time [ms]
# 51 Fan1 PWM
# 52 Fan1 RPM fault threshold
# 53 Fan1 RPM clear threshold
# 54 Fan2 PWM
# 55 Fan2 RPM fault threshold
# 56 Fan2 RPM clear threshold
# 57 Fan3 PWM
# 58 Fan3 RPM fault threshold
# 59 Fan3 RPM clear threshold
# 60 Use Gen VIP for power ctrl in pulse mode (0/1)
# 61 SetPt threshold switch DC rail [W]
# 62 Apply cal table constant PDAC threshold [W]
# 63 C1 hold offset [%]
# 64 C2 hold offset [%]
# 65 Hold/jump DAC during startup mode
# 66 DCRail voltage for SetPt > param61 [V]
# 67 DCRail voltage for SetPt <= param61 [V]
# 68 DC rail control mode (0 fixed / 1 dynamic)
# 69 Apply setPt % correction for striking
# 70 Average power setPt from analog port
# 71 Hold CW match position in low power pulse mode
#
# # Match Parameters
# 104 Max Vcap raw limit [V]
# 105 Max Vcap avg limit [V]
# 107 Delay after reaching match (steps)
# 109 Delay after losing match (steps)
# 111 Max Vcap cumulative log [V]
# 112 Max Vcap [V]
# 113 HVDC low -> shutdown PS [V]
# 114 HVDC low -> pause matching [V]
# 115 HVDC high -> resume matching [V]
# 116 HVDC target at power up [V]
# 120 Gamma correction angle [deg]
# 121 |Z| multiplicative correction
# 122 |Z| additive correction
# 123 Phase multiplicative correction
# 124 Phase additive correction
# 125 Vpp DAC average log2(samples)
# 126 Vpp correction factor
# 127 RF frequency [MHz]
# 132 Dual restart enable mode
# 133 Max cap movement fine steps
# 139 VIP sensor settling time [us]
# 140 VPP sensor settling time [us]
# 144 Cap toggle limiting interval [ms]
# 145 Max cap toggles within interval
# 146 If RF off, Vpp must exceed to report [V]
# 150 Hunting algorithm enable
# 151 Hunting algorithm selection
# 152 |Gamma| threshold hunting vs table match
# 159 Alg1 target |Zin|
# 160 Alg1 target |Xin|
# 161-169 Pref/Gamma thresholds
#
# # Generator Parameters
# 300 Max power [W]
# 305 Nominal DC voltage limit for DCPS [V]
# 307 Nominal DC current limit [A]
# 315 RF ramp rate [W/s]
# 345 Max PA temp [C]
# """
#
# QUANTUM_DESC_TEXT = r"""
# # General Parameters
# 1  Maximum Ambient temperature
# 2  User Control Input Src (HF/LF control bits)
# 3  Misc Options (pulse fault enables)
# 4  FPGA Diagnostic vector select
# 6  Monitor PS voltages for fault generation
# 7  Default TLog Mode
# 8  DeviceNet communication timeout
# 9  Disable Devicenet
# 10 DeviceNet MAC ID
# 11 DeviceNet baud rate
# 13 Min sample count
# 20 Fan fault hold time
# 21 Ignore fans
# 22 Interlocks monitor/ignore
# 24 Cap map selection
# 25 PS Vin fault low
# 26 PS Vin fault high
# 27 DCBias auto range low->high
# 28 DCBias auto range high->low
# 29 Allow HVDC rise time
# 30 HVDC fault high limit
#
# # HF Match Params
# 101-169 HF match parameters
#
# # LF Match Params
# 201-269 LF match parameters
# """
#
#
# def build_desc_map_from_text(text: str) -> Dict[str, Dict[int, str]]:
#     desc: Dict[str, Dict[int, str]] = {}
#     section = "General Parameters"
#     for raw in text.splitlines():
#         line = raw.strip()
#         if not line:
#             continue
#         if line.startswith("#"):
#             section = line.lstrip("#").strip()
#             desc.setdefault(section, {})
#             continue
#         m = re.match(r"^(\d+)\s+(.*)$", line)
#         if m:
#             pid = int(m.group(1))
#             d = m.group(2).strip()
#             desc.setdefault(section, {})[pid] = d
#     return desc
#
#
# TYKON_DESC = build_desc_map_from_text(TYKON_DESC_TEXT)
# QUANTUM_DESC = build_desc_map_from_text(QUANTUM_DESC_TEXT)
#
#
# def parse_param_pairs_from_line(line: str) -> List[Tuple[int, str]]:
#     """
#     Parse param id/value pairs from header lines.
#     Supports:
#       - Quantum style: "1,70.0,2,1111,3,0,..."
#       - Tykon style: "2 011001, 3 00, 4 0"
#       - Doc style: "101: 10.0 ms = ..."
#     """
#     s = line.strip()
#     out: List[Tuple[int, str]] = []
#
#     # Doc style: "101: 10.0 ms = ..."
#     m = re.match(r"^\s*(\d+)\s*:\s*([^=]+?)\s*=", s)
#     if m:
#         return [(int(m.group(1)), m.group(2).strip())]
#
#     # Quantum comma pairs: id,value,id,value,...
#     if "," in s and re.match(r"^\s*\d+\s*,", s):
#         toks = [t.strip() for t in s.split(",") if t.strip() != ""]
#         i = 0
#         while i + 1 < len(toks):
#             if re.fullmatch(r"\d+", toks[i]):
#                 out.append((int(toks[i]), toks[i + 1]))
#                 i += 2
#             else:
#                 i += 1
#         if out:
#             return out
#
#     # Tykon: "id value" chunks separated by commas
#     chunks = [c.strip() for c in s.split(",")]
#     for ch in chunks:
#         m2 = re.match(r"^\s*(\d+)\s+(.+?)\s*$", ch)
#         if m2:
#             out.append((int(m2.group(1)), m2.group(2).strip()))
#
#     return out
#
#
# def build_param_value_table(header_params: List[Tuple[str, str]]) -> List[Tuple[str, int, str]]:
#     rows: List[Tuple[str, int, str]] = []
#     for section, line in header_params:
#         pairs = parse_param_pairs_from_line(line)
#         for pid, val in pairs:
#             rows.append((section, pid, val))
#     return rows
from __future__ import annotations

import re
from typing import Dict, List, Tuple

# =============================================================================
# ----------------------------- Parameter descriptions -------------------------
# =============================================================================
#
# NOTE:
# - Descriptions are used in Parameters tab.
# - Values are extracted from tlog header blocks.
# - Parameter lists are embedded into code (per project decision).
# - We keep mapping best-effort; missing items will show blank description.
#
# Unit type strings (Option 2):
#   - "Tykon0527"
#   - "Tykon1213"
#   - "Quantum2013"
#   - "Triton2060"
#   - "Chronos 2.0"
#   - "Chronos 2.1"
# =============================================================================


# -----------------------------------------------------------------------------
# Embedded parameter list texts (raw)
# -----------------------------------------------------------------------------

CHRONOS20_DESC_TEXT = r"""
00:25:07>psho 
 ******** Parameter list Version = 3 ******** 
 1: 70 deg = Maximum ambient temperature 
 2: 120 deg = Maximum heat sink temperature 
 6: 1 = 0 - do not monitor PS voltages for fault generation, 1 - monitor PS voltages 
 7: 2 = Default TLog Mode. 0/1/2 = some/all/rf. 'some/all' - continous logging. 'rf' stops logging when tlog is full. 
 11: 5000 RPM = Fan 1 RPM >= this clears fault 
 12: 5000 RPM = Fan 2 RPM >= this clears fault 
 13: 5000 RPM = Fan 3 RPM >= this clears fault 
 14: 100 % = Run Fan 1 at this PWM. 0-100 
 15: 100 % = Run Fan 2 at this PWM. 0-100 
 16: 100 % = Run Fan 3 at this PWM. 0-100 
 17: 1000 RPM = Fan 1 RPM <= this will fault 
 18: 1000 RPM = Fan 2 RPM <= this will fault 
 19: 1000 RPM = Fan 3 RPM <= this will fault 
 20: 200 ms = Fan fault hold time. fan error has to hold this long before fault asserts. 
 21: 111 = Ignore Fans. Three digits # xyz, where x=Fan1, y=Fan2, z=Fan3 0-Monitor,1-Ignore 
 22: 0 = 0 = monitor interlocks, 1 = ignore interlocks 
 25: 22.00 V = PS Vin Fault Low Limit. 15-35V. Fault will assert if Vin < this. 
 26: 27.00 V = PS Vin Fault High Limit. 15-35V. Fault will assert if Vin > this. 
 28: 1320 V = 100 - 2000V. HVDC Fault High Limit. DC_NO_OK Fault Will Assert If HVDC > this 
 29: 3000 ms = allow HVDC this much rise time 
 30: 50 V = If RF is Off, Vpp has to be greater than this to be reported 
 31: 50 deg = amb Temp threshold for cummulative log 
 33: 50.0 us = pulse transient (settling) time (5 .. 1600) 
 34: 70 deg = hs Temp threshold for cummulative log 
 35: 1.0 % = analog cap preset noise threshold (0.0-9.9 %) 
 37: 0 = 1 = show calculated Vpp in tlog, 0 = don't 
 38: 1 = 0/1 = user/factory mode at startup, ** not preserved with 'plst' 
 39: 5 = number of control loops per millisecond 
 40: 0 = 0 = start normally, remote mode, 1 = start in Bench mode, local control 
Use 'psho f' to see match-specific parameters 

00:25:08>// 
00:25:08>psho f1 
104: 1200.0 V = Max Vcap voltage raw limit for fast protection 
105: 1200.0 V = Max Vcap voltage avg limit for fast protection 
106: 0 = 0/1 = disable/enable delay after reaching match 
107: 7 = the match delay in number of control loop runs 
108: 1 = 0/1 = disable/enable delay after losing match 
109: 1 = the unmatch delay in number of control loop runs 
110: 0 = 0/1 = disable/enable elimination of clock beat disturbances (a.k.a 12-second disturbances) 
111: 650 = Max Vcap for cummulative log 
112: 850 = Max Vcap 
113: 750 = HVDC less than this -> shut down power supplies 
114: 800 = HVDC less than this -> pause matching 
115: 850 = HVDC greater than this -> resume matching 
120: 0.0 deg = Gamma correction angle 
121: 1.00 = 
Z
 multiplicative correction term 
122: 0.00 = 
Z
 additive correction term 
123: 1.00 = Phase multiplicative correction term 
124: 0.00 = Phase additive correction term 
125: 2 = cap map: 0 = normal; 2 = Alternate map of 1/24 for new cap array 
126: 1.0 = Vpp Correction Factor 
127: 0.40 MHz = Radio Frequency 
131: 2500 V = Maximum Vpp 
132: 2500 V = Maximum Vpp Scale Value 
134: 0 = log2 of number of V,I,P averaging points, 0.1,...,10 (-> 1,2,4,...,1024 pts) 
135: 0 = cap moves of less than this many fine steps are short 
136: 0 = if both caps' moves are short -> limit them to this many fine steps 
137: 2 = 0/1/2 = dual gamma disable / enable on restart / enable always 
138: 0.100 = high restart gamma (low restart gamma is in the program) 
139: 3 = maximum cap movement in fine steps when low_gamma < gamma < high_gamma 
140: 0 = 0/1 = disable/enable PIN switching limit 
141: 2 = max number of PIN diodes switching simultaneously 
142: 0 = 0 = count coarse only, 1 = count coarse and fine 
143: 0 = 0 = C2 has priority for movement, 1 = move both caps equaly 
144: 15.0 ms = time interval within which number of cap toggles is limited 
145: 30 = max number of cap toggles within the above time period 
147: 112 us = cap dead time - Dead time for cap switching 
148: 125 us = cap switching time 
150: 0 = 0/1 = disable/enable hunting algorithm 
151: 2 = Hunting algorithm selection (1,2,...) - only '2' supported for now 
152: 0.002 = 
Gamma
 threshold for hunting vs table match 
153: 10.0 ms = Delay after the first table match 
154: 10.0 ms = Delay after later table matches 
155: 0 = Alg 1: Initial direction for C2 (0 = up, 1 = down) 
156: 0 = Alg 1: Initial direction for C1 (0 = up, 1 = down) 
157: 0 = Alg 2: Initial direction for C2 (0 = up, 1 = down) 
158: 0 = Alg 2: Initial direction for C1 (0 = up, 1 = down) 
159: 0.020 = Alg 1: target 
Zin

160: 0.005 = Alg 1: target 
Xin

161: 0 = 0/1 = disable/enable variable matching limits 
162: 0.08 W = stop Pr at Pf = 5 W 
163: 1.00 W = stop Pr at Pf = 500 W 
164: 0.10 W = restart Pr at Pf = 5 W 
165: 2.00 W = restart Pr at Pf = 500 W
"""

CHRONOS21_DESC_TEXT = r"""
 ******** Parameter list Version = 5 ******** 
 1: 70 deg = Maximum ambient temperature 
 2: 120 deg = Maximum heat sink temperature 
 3: 00000 = User Control Input Src. 0-ECAT 1-HW Five 0/1 digits: MANUAL RF_ON PLS_EN C1_SET C2_SET. eg 01010 = Use hw for RF_ON and C1_Set 
 4: 0 = Disable ECAT. 0 = ECAT Enabled, 1 = ECAT Disabled 
 6: 1 = 0 - do not monitor PS voltages for fault generation, 1 - monitor PS voltages 
 7: 2 = Default TLog Mode. 0/1/2 = some/all/rf. 'some/all' - continous logging. 'rf' stops logging when tlog is full. 
 8: 0.0 ms = ECAT communication timeout (0 = disable) 
 9: 0x000006aa = ECAT Vendor ID - enter hex values when changing 
 10: 0x00000401 = ECAT Product code - enter hex values when changing 
 11: 5000 RPM = Fan 1 RPM >= this clears fault 
 12: 5000 RPM = Fan 2 RPM >= this clears fault 
 13: 5000 RPM = Fan 3 RPM >= this clears fault 
 14: 100 % = Run Fan 1 at this PWM. 0-100 
 15: 100 % = Run Fan 2 at this PWM. 0-100 
 16: 100 % = Run Fan 3 at this PWM. 0-100 
 17: 1000 RPM = Fan 1 RPM <= this will fault 
 18: 1000 RPM = Fan 2 RPM <= this will fault 
 19: 1000 RPM = Fan 3 RPM <= this will fault 
 20: 200 ms = Fan fault hold time. fan error has to hold this long before fault asserts. 
 21: 111 = Ignore Fans. Three digits # xyz, where x=Fan1, y=Fan2, z=Fan3 0-Monitor,1-Ignore 
 22: 0 = 0 = monitor interlocks, 1 = ignore interlocks 
 23: 112      = ECAT ID (Used for alias addressing) 
 25: 22.00 V = PS Vin Fault Low Limit. 15-35V. Fault will assert if Vin < this. 
 26: 27.00 V = PS Vin Fault High Limit. 15-35V. Fault will assert if Vin > this. 
 28: 1320 V = 100 - 2000V. HVDC Fault High Limit. DC_NO_OK Fault Will Assert If HVDC > this 
 29: 3000 ms = allow HVDC this much rise time 
 30: 50 V = If RF is Off, Vpp has to be greater than this to be reported 
 31: 50 deg = amb Temp threshold for cummulative log 
 32: 10 = Report val Average. log2 of number of reporting value samples to average (0 - 10 : 1 to 1024 samples) 
 33: 50.0 us = pulse transient (settling) time (5 .. 1600) 
 34: 70 deg = hs Temp threshold for cummulative log 
 35: 1.0 % = analog cap preset noise threshold (0.0-9.9 %) 
 37: 0 = 1 = show calculated Vpp in tlog, 0 = don't 
 38: 1 = 0/1 = user/factory mode at startup, ** not preserved with 'plst' 
 39: 5 = number of control loops per millisecond 
 40: 0 = 0 = start normally, remote mode, 1 = start in Bench mode, local control 
Use 'psho f' to see match-specific parameters 
00:01:03>psho f 
104: 1100.0 V = Max Vcap voltage raw limit for fast protection 
105: 1000.0 V = Max Vcap voltage avg limit for fast protection 
106: 0 = 0/1 = disable/enable delay after reaching match 
107: 7 = the match delay in number of control loop runs 
108: 1 = 0/1 = disable/enable delay after losing match 
109: 1 = the unmatch delay in number of control loop runs 
110: 0 = 0/1 = disable/enable elimination of clock beat disturbances (a.k.a 12-second disturbances) 
111: 650 = Max Vcap for cummulative log 
112: 850 = Max Vcap 
113: 750 = HVDC less than this -> shut down power supplies 
114: 800 = HVDC less than this -> pause matching 
115: 850 = HVDC greater than this -> resume matching 
120: 0.0 deg = Gamma correction angle 
121: 1.00 = 
Z
 multiplicative correction term 
122: 0.00 = 
Z
 additive correction term 
123: 1.00 = Phase multiplicative correction term 
124: 0.00 = Phase additive correction term 
125: 2 = cap map: 0 = normal; 2 = Alternate map of 1/24 for new cap array 
126: 1.0 = Vpp Correction Factor 
127: 0.43 MHz = Radio Frequency 
131: 2000 V = Maximum Vpp 
132: 2000 V = Maximum Vpp Scale Value 
134: 0 = log2 of number of V,I,P averaging points, 0.1,...,10 (-> 1,2,4,...,1024 pts) 
135: 0 = cap moves of less than this many fine steps are short 
136: 0 = if both caps' moves are short -> limit them to this many fine steps 
137: 2 = 0/1/2 = dual gamma disable / enable on restart / enable always 
138: 0.100 = high restart gamma (low restart gamma is in the program) 
139: 3 = maximum cap movement in fine steps when low_gamma < gamma < high_gamma 
140: 0 = 0/1 = disable/enable PIN switching limit 
141: 2 = max number of PIN diodes switching simultaneously 
142: 0 = 0 = count coarse only, 1 = count coarse and fine 
143: 0 = 0 = C2 has priority for movement, 1 = move both caps equaly 
144: 15.0 ms = time interval within which number of cap toggles is limited 
145: 30 = max number of cap toggles within the above time period 
147: 112 us = cap dead time - Dead time for cap switching 
148: 125 us = cap switching time 
150: 0 = 0/1 = disable/enable hunting algorithm 
151: 2 = Hunting algorithm selection (1,2,...) - only '2' supported for now 
152: 0.002 = 
Gamma
 threshold for hunting vs table match 
153: 10.0 ms = Delay after the first table match 
154: 10.0 ms = Delay after later table matches 
155: 0 = Alg 1: Initial direction for C2 (0 = up, 1 = down) 
156: 0 = Alg 1: Initial direction for C1 (0 = up, 1 = down) 
157: 0 = Alg 2: Initial direction for C2 (0 = up, 1 = down) 
158: 0 = Alg 2: Initial direction for C1 (0 = up, 1 = down) 
159: 0.020 = Alg 1: target 
Zin

160: 0.005 = Alg 1: target 
Xin

161: 0.60 W = stop Pr at Pf = 5 W 
162: 1.00 W = stop Pr at Pf = 500 W 
163: 0.10 W = restart Pr at Pf = 5 W 
164: 2.00 W = restart Pr at Pf = 500 W
"""

TYKON0527_DESC_TEXT = r"""
*** Parameter list Version 16 
* General Parameters 
 2: 011001 = User Control Input Src. 0-DNet 1-HW Six 0/1 digits: MANUAL RF_ON PLS_EN C1_SET C2_SET PFWD_SET. eg 010100 = Use hw for RF_ON and C1_Set 
 3: 00 = Misc Options. 0-Disable 1-Enable. Two 0/1 digits: PULSE_WIDTH_FAULT_ENABLE PULSE_FAULT_ENABLE. 
 4: 0 = FPGA Diagnostic vector select (0..15) 
 6: 1 = 0 = do not monitor PS voltages for fault generation, 1 = monitor PS voltages 
 7: 0 = Default TLog Mode. 0/1/2 = some/all/rf. 'some/all' - continous logging. 'rf' stops logging when tlog is full. 
 8: 0.0 ms = DeviceNet communication timeout (0 = disable) 
 9: 0 = Disable Devicenet. 0 = DNet Enabled, 1 = DNet Disabled 
 10: 34 = DeviceNet MAC ID (if 0 -> use switches) 
 11: 2 = DeviceNet Baud Rate (0,1,2) (125K/250K/500K); only used if param 10 <> 0 
 13: 10000 us = DNET processing loop time in us (5000 to 50000 us = 5 to 50 ms) 
 14: 0.0 % = start sampling V,I,P at this time as % of pulse duration 
 15: 100.0 % = when to stop sampling V,I,P as % of pulse duration 
 16: 13 us = when to start sampling V,I,P within pulse duration 
 17: 20 us = for how long to sample V,I,P 
 18: 30 us = start sampling V,I,P at absolute time in us before the pulse end 
 19: 0 = which parameters specify start of VIP sampling: 0 = %; 1 = us; 2 = us from end 
 20: 0 = which parameters specify end of VIP sampling: 0 = %; 1 = us len 
 21: 000 = Ignore Fans. Three digit 'xyz' for fan 1,2,3. '1' = ignore, '0' = monitor 
 22: 0 = 0 = monitor interlocks, 1 = ignore interlocks 
 23: 25 us = cap dead time - Dead time for cap switching 
 24: 0 = 1 = Rev_A I/F installed, 0 = Rev_A support not required 
 25: 20.00 V = PS Vin Fault Low Limit. 15-35V. Fault will assert if Vin < this. 
 26: 27.00 V = PS Vin Fault High Limit. 15-35V. Fault will assert if Vin > this. 
 27: 100.0 V = DCBias Auto Rng, Low to High Threshold. 
 28: 98.0 V = DCBias Auto Rng, High to Low Threshold. 
 29: 1500 ms = allow HVDC this much rise time 
 30: 1320 V = 100 - 2000V. HVDC Fault High Limit. DC_NO_OK Fault Will Assert If HVDC > this 
 31: 50 deg = Temp threshold for cumulative log 
 32: 2 = cap map : 0 = normal; 2 = Alternate map of 1/24 for new cap array 
 33: 4 = MinSample count for matching. (4 - 200) 
 34: 25 us = cap switching time 
 35: 1.0 % = analog cap preset noise threshold (0.0-9.9 %%) 
 37: 0 ms = Local Mode: Time limit in ms for 'RF setpoint not at 90%' (0 to disable) 
 38: 0 = 0/1 = user/factory mode at startup. 
 39: 4 = number of control loops per millisecond 
 40: 0 = 0 = start normally, remote mode, 1 = start in Bench mode, local control 
 41: 2 ms = Local Mode: Keep RF in CW mode for this many ms before switching to Pulse mode 
 42: 0 V = Local Mode: Absolute values of VDC lower than this indicate that VDC is 0 
 43: 0 ms = Local Mode: VDC monitoring will start this many milliseconds after RF On 
 44: 1 = 1 = use the params 37 and 41-43 for pulsing and RF controls in remote mode; 0 = use ECAT settings 
 45: 2 = 0 = regular method of data collection and ctrl loop order; 1 - 4 = use algorithms 1 thru 4 
 46: 30 us = 0-300, wait this many us before collecting match data after PDAC change 
 47: 2 = 0 - 10, Number of loops to stay at 0%,100% cap positions when NegR detected 
 50: 50 ms = Fan fault hold time. fan error has to hold this long before fault asserts. 
 51: 100 % = Run Fan 1 at this PWM. 0-100 
 52: 1000 RPM = Fan 1 RPM <= this will fault 
 53: 5000 RPM = Fan 1 RPM >= this clears fault 
 54: 100 % = Run Fan 2 at this PWM. 0-100 
 55: 1000 RPM = Fan 2 RPM <= this will fault 
 56: 5000 RPM = Fan 2 RPM >= this clears fault 
 57: 100 % = Run Fan 3 at this PWM. 0-100 
 58: 1000 RPM = Fan 3 RPM <= this will fault 
 59: 5000 RPM = Fan 3 RPM >= this clears fault 
 60: 1 = 1 - use Gen VIP for power ctrl in pulse mode; 0 - use Match side VIP for power ctrl in pulse mode 
 61: 50.0 W = 0 - 500 Watts, SetPt value for switching to higher DC Rail value, 0 - disable, (non-zero value overrides param #68, and param #66 & #67 become effective) 
 62: 30.0 W = 0 - 1500 Watts, Pwr set point for Low Pwr Operations, params 63,64, 65 and 72 are used. 
 63: 0.0 % = 0 to 100.0 %, Off preset % to apply to C1 position in pulse mode when enabled by param #69 or #71 
 64: 100.0 % = 0 to 100.0 %, Off preset % to apply to C2 position in pulse mode when enabled by param #69 or #71 
 65: 2 = 0 - Do not hold/jump DAC during start-up for setPt < (param #62) Watts; 1 - hold DAC at cal table based values; 2 - Jump to DAC using cal table value and apply PID 
 66: 36.0 V = DCRail voltage for SetPt > param 61; 0 to disable (non zero value overrides param #68) 
 67: 20.0 V = DCRail voltage for SetPt <= param 61; 0 to disable (non-zero value overrides param #68) 
 68: 1 = 0 - Set DC rail voltage at param 305 value; 1 - Set DC rail voltage based on RF setPt (More dynamic range than param #66 and #67, use 'dcps' to view ranges) 
 69: 0.125 ms = 0.0 - 1.638 ms; Apply Pulse off preset for this much time after pulse starts in Low Pwr mode 
 70: 1 = 0 - Do not average Pwr setPt value from analog port; 1 - Enable averaging for the same 
 71: 0.125 ms = 0.0 - 1.638 ms; Apply Pulse off preset for this much time after pulse starts in High Pwr mode 
 72: 3.60 W = -20.0 to 20.0 W; Apply this offset in Watts to Low Pwr mode Setpoint defined by param 62 
Use 'psho g' and 'psho m' for generator- and match-specific parameters, respectively 
**** Running cmd : psho m **** 
**** Parameter list Version 16 **** 
*** Match Parameters 
 104: 5000.0 V = Max Vcap voltage raw limit for fast protection 
 105: 1000.0 V = Max Vcap voltage avg limit for fast protection 
 107: 0 = delay after reaching match - number of steps of inactivity 
 109: 0 = delay after losing match - number of steps of inactivity 
 111: 650 V = Max Vcap for cummulative log 
 112: 850 V = Max Vcap 
 113: 650 V = HVDC less than this -> shut down power supplies 
 114: 850 V = HVDC less than this -> pause matching 
 115: 900 V = HVDC greater than this -> resume matching 
 116: 1200 V = HVDC target voltage at power up (i.e. HVDC > this -> HVDC is OK) 
 120: 0.00 deg = Gamma correction angle 
 121: 1.00 = 
Z
 multiplicative correction term 
 122: 0.00 = 
Z
 additive correction term 
 123: 1.00 = Phase multiplicative correction term 
 124: 0.00 = Phase additive correction term 
 125: 6 = Vpp DAC Average. log2 of number of Vpp samples to average (0 - 10 : 1 to 1024 samples) 
 126: 1.0 = Vpp Correction Factor 
 127: 27.120 MHz = Radio Frequency 
 131: 1000 = Max Vpp Scale for analog port reporting as (0-10) volts 
 132: 2 = 0/1/2 = dual restart limits disable / enable on restart / enable always 
 133: 60 = maximum cap movement in fine steps when low_limit < gamma/pref < high_limit 
 135: 0 = C1: moves of this many or fewer fine steps are short 
 136: 0 = C2: moves of this many or fewer fine steps are short 
 137: 0 = C1: if a short move -> limit to this many fine steps 
 138: 0 = C2: if a short move -> limit to this many fine steps 
 139: 50 us = VIP Sensor settling time 
 140: 5 us = Vpp Sensor settling time 
 144: 15.0 ms = time interval within which number of cap toggles is limited 
 145: 30 = max number of cap toggles within the above time period 
 146: 0 V = If RF is Off, Vpp has to be greater than this to be reported to AO 
 150: 0 = 0/1 = disable/enable hunting algorithm 
 151: 2 = Hunting algorithm selection (1,2,...) - only '2' supported for now 
 152: 0.002 = 
Gamma
 threshold for hunting vs table match 
 153: 0.0 ms = Delay after the first table match 
 154: 0.0 ms = Delay after later table matches 
 155: 0 = Alg 1: Initial direction for C2 (0 = up, 1 = down) 
 156: 0 = Alg 1: Initial direction for C1 (0 = up, 1 = down) 
 157: 0 = Alg 2: Initial direction for C2 (0 = up, 1 = down) 
 158: 0 = Alg 2: Initial direction for C1 (0 = up, 1 = down) 
 159: 0.020 = 
Gamma
 threshold for hunting vs table match 
 160: 0.005 = Alg 1: target 
Xin

 161: 1.10 W = Pfwd < 100 W: Pref stop 
 162: 1.50 W = Pref restart 
 163: 2.00 W = Pref high restart (when enabled by p132) 
 164: 0.050 = Pfwd 100 - 500 W: Gamma stop 
 165: 0.070 = Gamma restart 
 166: 0.090 = Gamma high restart (when enabled by p132) 
 167: 3.00 W = Pfwd > 500 W: Pref stop 
 168: 4.00 W = Pref restart 
 169: 5.00 W = Pref high restart (when enabled by p132) 
**** Running cmd : psho g **** 
**** Parameter list Version 16 **** 
*** Generator Parameters 
 300: 500 W = Max Power 
 301: -2.50 V = Power DAC Setting - Min 
 302: 0.50 V = - Max 
 303: -2.18 V = DAC value when RF is Off 
 304: 3000 W = Max power level for DC Power Supply -- not used, but set it to a reasonable value 
 305: 36.0 V = Nominal DC Voltage Limit for DCPS 
 306: 100 ms = After changing VDC, wait this long before checking the voltage 
 307: 40.0 A = Nominal DC Current Limit for DCPS 
 308: 0.100 s = Max Silence time to declare DC PS Commn Err (0.1 to 10 Secs) 
 309: 5 W = Setpoint target window 
 310: 2 W = Forward pacifying window 
 311: 2 W = Reflected pacifying window 
 312: 0 = Power leveling (0 = forward 1 = load for Pulsing only, 2 = load for CW and Pulsing ) 
 313: 0 = RF Ramp up/down at RF On (1 - Enable, 0 - Disable) 
 314: 0 = RF Ramp up/down at RF setpt change (1 - Enable, 0 - Disable) 
 315: 3330 W = RF Power Ramp in Watts Per Second (100 to 3330) 
 316: 0 = Fault on pulses are out of range (1 - Enable, 0 - Disable) 
 317: 1.000 = Ambient Temperature correction factor for V and I (0.9 to 1.1) 
 318: 1 = Total number of FETs 
 319: 50.0 ms = Wait this long after RF Off before checking current 
 320: 1 = Averaging for Fwd/Ref Monitor DAC output (1 - Enable, 0 - Disable) 
 321: 0 = Rref VIP interval usage for reporting (1 - Enable, 0 - Disable -> use full pulse data) 
 322: 0 = Power control using Rref VIP intervals (1 - Enable, 0 - Disable -> use full pulse data) 
 323: 0 W = Min Power 
 324: 5 W = Max Pwr limit when RF is Off (Above this value, fault gets generated, 0 to disable fault) 
 325: 2 = Use CEX For RF Generation. 0 - Use DDS. 1 - Use CEX 2 - Use CEX with no freq validation 
 326: 1 = Use Gen/Match side values for Fwd/Ref reporting (0 - Match Side, 1 - Gen Side) 
 340: 50.0 A = Max PA current 
 341: 7.0 A = Max PA Current when RF is OFF 
 342: 550.0 W = Max Dissipation/FET for low Fwd Pwr 
 343: 10.0 W = Max Fwd Pwr for the above limit 
 344: 550.0 W = Max Dissipation / FET (foldback) 
 345: 70.0 degC = Max PA Temperature 
 346: 200.0 W = Max Reflected Power (foldback) 
 347: 2.0 A = Max Exciter Current 
 348: 70.0 degC = Max Amb Temperature 
 349: 50.0 degC = Count Amb Temperature if higher than this 
 350: 50.0 degC = Count PA Temperature if higher than this 
 351: 180.0 V = Max Drain voltage (foldback)
"""

TYKON1213_DESC_TEXT = r"""
*** Parameter list Version 6 
* General Parameters 
 2: 011001 = User Control Input Src. 0-DNet 1-HW Six 0/1 digits: MANUAL RF_ON PLS_EN C1_SET C2_SET PFWD_SET. eg 010100 = Use hw for RF_ON and C1_Set 
 3: 00 = Misc Options. 0-Disable 1-Enable. Two 0/1 digits: PULSE_WIDTH_FAULT_ENABLE PULSE_FAULT_ENABLE. 
 4: 0 = FPGA Diagnostic vector select (0..15) 
 6: 1 = 0 = do not monitor PS voltages for fault generation, 1 = monitor PS voltages 
 7: 0 = Default TLog Mode. 0/1/2 = some/all/rf. 'some/all' - continous logging. 'rf' stops logging when tlog is full. 
 8: 0.0 ms = DeviceNet communication timeout (0 = disable) 
 9: 0 = Disable Devicenet. 0 = DNet Enabled, 1 = DNet Disabled 
 10: 48 = DeviceNet MAC ID (if 0 -> use switches) 
 11: 2 = DeviceNet Baud Rate (0,1,2) (125K/250K/500K); only used if param 10 <> 0 
 14: 0.0 % = start sampling V,I,P at this time as % of pulse duration 
 15: 100.0 % = when to stop sampling V,I,P as % of pulse duration 
 16: 5 us = when to start sampling V,I,P within pulse duration 
 17: 13 us = for how long to sample V,I,P 
 18: 20 us = start sampling V,I,P at absolute time in us before the pulse end 
 19: 0 = which parameters specify start of VIP sampling: 0 = %; 1 = us; 2 = us from end 
 20: 0 = which parameters specify end of VIP sampling: 0 = %; 1 = us len 
 21: 000 = Ignore Fans. Three digit 'xyz' for fan 1,2,3. '1' = ignore, '0' = monitor 
 22: 0 = 0 = monitor interlocks, 1 = ignore interlocks 
 23: 25 us = cap dead time - Dead time for cap switching 
 24: 0 = 1 = Rev_A I/F installed, 0 = Rev_A support not required 
 25: 20.00 V = PS Vin Fault Low Limit. 15-35V. Fault will assert if Vin < this. 
 26: 27.00 V = PS Vin Fault High Limit. 15-35V. Fault will assert if Vin > this. 
 27: 100.0 V = DCBias Auto Rng, Low to High Threshold. 
 28: 98.0 V = DCBias Auto Rng, High to Low Threshold. 
 29: 1500 ms = allow HVDC this much rise time 
 30: 1320 V = 100 - 2000V. HVDC Fault High Limit. DC_NO_OK Fault Will Assert If HVDC > this 
 31: 50 deg = Temp threshold for cumulative log 
 32: 2 = cap map : 0 = normal; 2 = Alternate map of 1/24 for new cap array 
 34: 25 us = cap switching time 
 35: 1.0 % = analog cap preset noise threshold (0.0-9.9 %%) 
 37: 0 ms = Time limit in ms for 'RF setpoint not at 90%' (0 to disable) 
 38: 0 = 0/1 = user/factory mode at startup. 
 39: 4 = number of control loops per millisecond 
 40: 0 = 0 = start normally, remote mode, 1 = start in Bench mode, local control 
 50: 50 ms = Fan fault hold time. fan error has to hold this long before fault asserts. 
 51: 100 % = Run Fan 1 at this PWM. 0-100 
 52: 1000 RPM = Fan 1 RPM <= this will fault 
 53: 5000 RPM = Fan 1 RPM >= this clears fault 
 54: 100 % = Run Fan 2 at this PWM. 0-100 
 55: 1000 RPM = Fan 2 RPM <= this will fault 
 56: 5000 RPM = Fan 2 RPM >= this clears fault 
 57: 100 % = Run Fan 3 at this PWM. 0-100 
 58: 1000 RPM = Fan 3 RPM <= this will fault 
 59: 5000 RPM = Fan 3 RPM >= this clears fault 
Use 'psho g' and 'psho m' for generator- and match-specific parameters, respectively 
**** Running cmd : psho m **** 
*** Match Parameters 
 104: 5000.0 V = Max Vcap voltage raw limit for fast protection 
 105: 1000.0 V = Max Vcap voltage avg limit for fast protection 
 107: 0 = delay after reaching match - number of steps of inactivity 
 109: 0 = delay after losing match - number of steps of inactivity 
 111: 650 V = Max Vcap for cummulative log 
 112: 850 V = Max Vcap 
 113: 650 V = HVDC less than this -> shut down power supplies 
 114: 850 V = HVDC less than this -> pause matching 
 115: 900 V = HVDC greater than this -> resume matching 
 116: 1200 V = HVDC target voltage at power up (i.e. HVDC > this -> HVDC is OK) 
 120: 0.00 deg = Gamma correction angle 
 121: 1.00 = 
Z
 multiplicative correction term 
 122: 0.00 = 
Z
 additive correction term 
 123: 1.00 = Phase multiplicative correction term 
 124: 0.00 = Phase additive correction term 
 125: 6 = Vpp DAC Average. log2 of number of Vpp samples to average (0 - 10 : 1 to 1024 samples) 
 126: 1.0 = Vpp Correction Factor 
 127: 13.560 MHz = Radio Frequency 
 132: 2 = 0/1/2 = dual restart limits disable / enable on restart / enable always 
 133: 60 = maximum cap movement in fine steps when low_limit < gamma/pref < high_limit 
 135: 0 = C1: moves of this many or fewer fine steps are short 
 136: 0 = C2: moves of this many or fewer fine steps are short 
 137: 0 = C1: if a short move -> limit to this many fine steps 
 138: 0 = C2: if a short move -> limit to this many fine steps 
 139: 12 us = VIP Sensor settling time 
 140: 5 us = Vpp Sensor settling time 
 144: 15.0 ms = time interval within which number of cap toggles is limited 
 145: 30 = max number of cap toggles within the above time period 
 146: 0 V = If RF is Off, Vpp has to be greater than this to be reported to AO 
 150: 0 = 0/1 = disable/enable hunting algorithm 
 151: 2 = Hunting algorithm selection (1,2,...) - only '2' supported for now 
 152: 0.002 = 
Gamma
 threshold for hunting vs table match 
 153: 0.0 ms = Delay after the first table match 
 154: 0.0 ms = Delay after later table matches 
 155: 0 = Alg 1: Initial direction for C2 (0 = up, 1 = down) 
 156: 0 = Alg 1: Initial direction for C1 (0 = up, 1 = down) 
 157: 0 = Alg 2: Initial direction for C2 (0 = up, 1 = down) 
 158: 0 = Alg 2: Initial direction for C1 (0 = up, 1 = down) 
 159: 0.020 = Alg 1: target 
Zin

 160: 0.005 = Alg 1: target 
Xin

 161: 0.60 W = Pfwd < 100 W: Pref stop 
 162: 1.40 W = Pref restart 
 163: 1.80 W = Pref high restart (when enabled by p132) 
 164: 0.050 = Pfwd 100 - 500 W: Gamma stop 
 165: 0.070 = Gamma restart 
 166: 0.090 = Gamma high restart (when enabled by p132) 
 167: 3.00 W = Pfwd > 500 W: Pref stop 
 168: 4.00 W = Pref restart 
 169: 5.00 W = Pfwd > 500 W: Pref high restart (when enabled by p132) 
**** Running cmd : psho g **** 
*** Generator Parameters 
 300: 1200 W = Max Power 
 301: -2.50 V = Power DAC Setting - Min 
 302: 0.90 V = - Max 
 303: -2.35 V = DAC value when RF is Off 
 304: 3000 W = Max power level for DC Power Supply -- not used, but set it to a reasonable value 
 305: 47.0 V = Nominal DC Voltage Limit for DCPS 
 306: 100 ms = After changing VDC, wait this long before checking the voltage 
 307: 40.0 A = Nominal DC Current Limit for DCPS 
 308: 0.100 s = Max Silence time to declare DC PS Commn Err (0.1 to 10 Secs) 
 309: 5 W = Setpoint target window 
 310: 2 W = Forward pacifying window 
 311: 2 W = Reflected pacifying window 
 312: 0 = Power leveling (1 = load, 0 = forward) 
 313: 0 = RF Ramp up/down at RF On (1 - Enable, 0 - Disable) 
 314: 0 = RF Ramp up/down at RF setpt change (1 - Enable, 0 - Disable) 
 315: 3330 W = RF Power Ramp in Watts Per Second (100 to 3330) 
 316: 0 = Fault on pulses are out of range (1 - Enable, 0 - Disable) 
 317: 1.000 = Ambient Temperature correction factor for V and I (0.9 to 1.1) 
 318: 1 = Total number of FETs 
 319: 50.0 ms = Wait this long after RF Off before checking current 
 320: 1 = Averaging for Fwd/Ref Monitor DAC output (1 - Enable, 0 - Disable) 
 321: 0 = Rref VIP interval usage for reporting (1 - Enable, 0 - Disable -> use full pulse data) 
 322: 0 = Power control using Rref VIP intervals (1 - Enable, 0 - Disable -> use full pulse data) 
 323: 0 W = Min Power 
 324: 5 W = Max Pwr limit when RF is Off (Above this value, fault gets generated, 0 to disable fault) 
 325: 1 = Use CEX For RF Generation. 0 - Use DDS. 1 - Use CEX 2 - Use CEX with no freq validation 
 340: 50.0 A = Max PA current 
 341: 7.0 A = Max PA Current when RF is OFF 
 342: 550.0 W = Max Dissipation/FET for low Fwd Pwr 
 343: 10.0 W = Max Fwd Pwr for the above limit 
 344: 550.0 W = Max Dissipation / FET (foldback) 
 345: 70.0 degC = Max PA Temperature 
 346: 240.0 W = Max Reflected Power (foldback) 
 347: 2.0 A = Max Exciter Current 
 348: 70.0 degC = Max Amb Temperature 
 349: 50.0 degC = Count Amb Temperature if higher than this 
 350: 50.0 degC = Count PA Temperature if higher than this 
 351: 180.0 V = Max Drain voltage (foldback)
"""

QUANTUM2013_DESC_TEXT = r"""
>psho 
 ******** Parameter list Version = 13 ******** 
 1: 70 deg = Maximum Ambient temperature 
 2: 1111 = User Control Input Src. 0-DNet 1-HW Four 0/1 digits: HF_RF_ON HF_PLS_EN LF_RF_ON LF_PLS_EN. eg 1010 = HF/LF_RF_ON-HW 
 3: 00 = Misc Options. 0-Disable 1-Enable. Two 0/1 digits: PULSE_WIDTH_FAULT_ENABLE PULSE_FAULT_ENABLE. 
 4: 0 = FPGA Diagnostic vector select (0..15) 
 6: 1 = 0 - do not monitor PS voltages for fault generation, 1 - monitor PS voltages 
 7: 0 = Default TLog Mode. 0/1/2 = some/all/rf. 'some/all' - continous logging. 'rf' stops logging when tlog is full. 
 8: 0.0 ms = DeviceNet communication timeout (0 = disable) 
 9: 0 = Disable Devicenet. 0 = DNet Enabled, 1 = DNet Disabled 
 10: 48 = DeviceNet MAC ID (if 0 -> use switches) 
 11: 2 = DeviceNet Baud Rate (0,1,2) (125K/250K/500K); only used if param 10 <> 0 
 13: 64 = Min Sample count (4-100) 
 14: 5000 RPM = Fan 1 RPM >= this clears fault 
 15: 5000 RPM = Fan 2 RPM >= this clears fault 
 16: 100 % = Run Fan 1 at this PWM. 0-100 
 17: 100 % = Run Fan 2 at this PWM. 0-100 
 18: 3000 RPM = Fan 1 RPM <= this will fault 
 19: 3000 RPM = Fan 2 RPM <= this will fault 
 20: 200 ms = Fan fault hold time. fan error has to hold this long before fault asserts. 
 21: 000 = Ignore Fans. Three digits # xyz, where x=Fan1, y=Fan2. z=Fan3 000 thru 111 
 22: 0 = 0 = monitor interlocks, 1 = ignore interlocks 
 23: 0 = 1 = Rev_A I/F installed, 0 = Rev_A support not required 
 24: 2 = cap map : 0 = normal; 1 = Alternate map (1) for HF Sh2 Cap array; 2 = Alternate map of 1/24 for new cap array 
 25: 20.00 V = PS Vin Fault Low Limit. 15-35V. Fault will assert if Vin < this. 
 26: 27.00 V = PS Vin Fault High Limit. 15-35V. Fault will assert if Vin > this. 
 27: 100.0 V = DCBias Auto Rng, Low to High Threshold. 
 28: 98.0 V = DCBias Auto Rng, High to Low Threshold. 
 29: 1500 ms = allow HVDC this much rise time 
 30: 1320 V = 100 - 2000V. HVDC Fault High Limit. DC_NO_OK Fault Will Assert If HVDC > this. 
 31: 50 deg = Amb Temp threshold for cumulative log 
 32: 5 = Vdc Average. log2 of number of Vdc samples to average (0 - 10 : 1 to 1024 samples) 
 33: 70 deg = Hs Temp threshold for cumulative log 
 35: 1.0 % = analog cap preset noise threshold (0.0-9.9 %) 
 36: 90 deg = Maximum heat Sink temperature 
 37: 1 = CW pulsing - see cwpl command 
 38: 0 = 0/1 = user/factory mode at startup. 
 39: 3 = number of control loops per millisecond 
 40: 0 = 0 = start normally, remote mode, 1 = start in Bench mode, local control 
 41: 5000 RPM = Fan 3 RPM >= this clears fault 
 42: 100 % = Run Fan 3 at this PWM. 0-100 
 43: 3000 RPM = Fan 3 RPM <= this will fault 
Use 'psho f' to see match-specific parameters 
>// 
>psho f 
// HF 
101: 10.0 ms = CW to Pulse mode transition delay 
102: 20.0 ms = Pulse to CW mode transition delay 
103: 0.0 ms = Pulse mode cap preset holding time during RF ramping 
104: 1100.0 V = Max Vcap voltage raw limit for fast protection 
105: 1000.0 V = Max Vcap voltage avg limit for fast protection 
106: 0 = Ignore RF On Request. 0 - Use RF On Request Signal. 1 - Don't Use 
107: 1 = delay after reaching match - number of steps of inactivity 
109: 1 = delay after losing match - number of steps of inactivity 
111: 650 V = Max Vcap for cummulative log 
112: 850 V = Max Vcap 
113: 650 V = HVDC less than this -> shut down power supplies 
114: 850 V = HVDC less than this -> pause matching 
115: 900 V = HVDC greater than this -> resume matching 
120: 0.0 deg = Gamma correction angle 
121: 1.00 = 
Z
 multiplicative correction term 
122: 0.00 = 
Z
 additive correction term 
123: 1.00 = Phase multiplicative correction term 
124: 0.00 = Phase additive correction term 
125: 1 = Vpp DAC Average. log2 of number of Vpp samples to average (0 - 10 : 1 to 1024 samples) 
126: 1.0 = Vpp Correction Factor 
127: 12.900 MHz = Radio Frequency 
132: 2 = 0/1/2 = dual restart limits disable / enable on restart / enable always 
133: 60 = maximum cap movement in fine steps when low_limit < gamma/pref < high_limit 
135: 0 = C1: moves of this many or fewer fine steps are short 
136: 0 = C2: moves of this many or fewer fine steps are short 
137: 2 = C1: if a short move -> limit to this many fine steps 
138: 0 = C2: if a short move -> limit to this many fine steps 
139: 12 us = VIP Sensor settling time 
140: 5 us = VPP Sensor settling time 
141: 1 us = RF Delay after Pulse On 
144: 15.0 ms = time interval within which number of cap toggles is limited 
145: 30 = max number of cap toggles within the above time period 
146: 50 V = If RF is Off, Vpp has to be greater than this to be reported to AO 
147: 25 us = cap dead time - Dead time for cap switching 
148: 25 us = cap switching time 
150: 0 = 0/1 = disable/enable hunting algorithm 
151: 2 = Hunting algorithm selection (1,2,...) - only '2' supported for now 
152: 0.002 = 
Gamma
 threshold for hunting vs table match 
153: 0.0 ms = Delay after the first table match 
154: 0.0 ms = Delay after later table matches 
155: 0 = Alg 1: Initial direction for C2 (0 = up, 1 = down) 
156: 0 = Alg 1: Initial direction for C1 (0 = up, 1 = down) 
157: 0 = Alg 2: Initial direction for C2 (0 = up, 1 = down) 
158: 0 = Alg 2: Initial direction for C1 (0 = up, 1 = down) 
159: 0.020 = Alg 1: target 
Zin

160: 0.005 = Alg 1: target 
Xin

161: 0.60 W = Pfwd < 100 W: Pref stop 
162: 1.40 W = Pref restart 
163: 1.80 W = Pref high restart (when enabled by p132) 
164: 0.060 = Pfwd 100 - 500 W: Gamma stop 
165: 0.090 = Gamma restart 
166: 0.100 = Gamma high restart (when enabled by p132) 
167: 3.00 W = Pfwd > 500 W: Pref stop 
168: 4.00 W = Pref restart 
169: 5.00 W = Pfwd > 500 W: Pref high restart (when enabled by p132) 
// LF 
201: 10.0 ms = CW to Pulse mode transition delay 
202: 20.0 ms = Pulse to CW mode transition delay 
203: 0.0 ms = Pulse mode cap preset holding time during RF ramping 
204: 1100.0 V = Max Vcap voltage raw limit for fast protection 
205: 1000.0 V = Max Vcap voltage avg limit for fast protection 
206: 0 = Ignore RF On Request. 0 - Use RF On Request Signal. 1 - Don't Use 
207: 1 = delay after reaching match - number of steps of inactivity 
209: 1 = delay after losing match - number of steps of inactivity 
211: 650 V = Max Vcap for cummulative log 
212: 850 V = Max Vcap 
220: 0.0 deg = Gamma correction angle 
221: 1.00 = 
Z
 multiplicative correction term 
222: 0.00 = 
Z
 additive correction term 
223: 1.00 = Phase multiplicative correction term 
224: 0.00 = Phase additive correction term 
225: 1 = Vpp DAC Average. log2 of number of Vpp samples to average (0 - 10 : 1 to 1024 samples) 
226: 1.0 = Vpp Correction Factor 
227: 0.430 MHz = Radio Frequency 
232: 2 = 0/1/2 = dual restart limits disable / enable on restart / enable always 
233: 60 = maximum cap movement in fine steps when low_limit < gamma/pref < high_limit 
235: 0 = C3: moves of this many or fewer fine steps are short 
236: 0 = C4: moves of this many or fewer fine steps are short 
237: 2 = C3: if a short move -> limit to this many fine steps 
238: 0 = C4: if a short move -> limit to this many fine steps 
239: 25 us = VIP Sensor settling time 
240: 25 us = VPP Sensor settling time 
241: 65 us = RF Delay after Pulse On 
244: 15.0 ms = time interval within which number of cap toggles is limited 
245: 30 = max number of cap toggles within the above time period 
246: 0 V = If RF is Off, Vpp has to be greater than this to be reported to AO 
247: 112 us = cap dead time - Dead time for cap switching 
248: 125 us = cap switching time 
250: 0 = 0/1 = disable/enable hunting algorithm 
251: 2 = Hunting algorithm selection (1,2,...) - only '2' supported for now 
252: 0.002 = 
Gamma
 threshold for hunting vs table match 
253: 0.0 ms = Delay after the first table match 
254: 0.0 ms = Delay after later table matches 
255: 0 = Alg 1: Initial direction for C4 (0 = up, 1 = down) 
256: 0 = Alg 1: Initial direction for C3 (0 = up, 1 = down) 
257: 0 = Alg 2: Initial direction for C4 (0 = up, 1 = down) 
258: 0 = Alg 2: Initial direction for C3 (0 = up, 1 = down) 
259: 0.020 = Alg 1: target 
Zin

260: 0.005 = Alg 1: target 
Xin

261: 0.60 W = Pfwd < 100 W: Pref stop 
262: 1.40 W = Pref restart 
263: 1.80 W = Pref high restart (when enabled by p132) 
264: 0.060 = Pfwd 100 - 500 W: Gamma stop 
265: 0.090 = Gamma restart 
266: 0.100 = Gamma high restart (when enabled by p132) 
267: 3.00 W = Pfwd > 500 W: Pref stop 
268: 4.00 W = Pfwd > 500 W: Pref restart 
269: 5.00 W = Pfwd > 500 W: Pref high restart (when enabled by p132)
"""

TRITON2060_DESC_TEXT = r"""
*** Parameter list Version 10 
* General Parameters 
 2: 011001 = User Control Input Src. 0-ECAT 1-HW Six 0/1 digits: MANUAL RF_ON PLS_EN C1_SET C2_SET PFWD_SET. eg 010100 = Use hw for RF_ON and C1_Set 
 3: 00 = Misc Options. 0-Disable 1-Enable. Two 0/1 digits: PULSE_WIDTH_FAULT_ENABLE PULSE_FAULT_ENABLE. 
 4: 0 = FPGA Diagnostic vector select (0..15) 
 6: 1 = 0 = do not monitor PS voltages for fault generation, 1 = monitor PS voltages 
 7: 0 = Default TLog Mode. 0/1/2 = some/all/rf. 'some/all' - continous logging. 'rf' stops logging when tlog is full. 
 8: 0.0 ms = ECAT communication timeout (0 = disable) 
 9: 0 = Disable ECAT. 0 = ECAT Enabled, 1 = ECAT Disabled 
 10: 48 = ECAT ID (Used for alias addressing) 
 11: 0x000006aa = ECAT Vendor ID - enter hex values when changing 
 12: 0x00000301 = ECAT Product code - enter hex values when changing 
 14: 0.0 % = start sampling V,I,P at this time as % of pulse duration 
 15: 100.0 % = when to stop sampling V,I,P as % of pulse duration 
 16: 5 us = when to start sampling V,I,P within pulse duration 
 17: 13 us = for how long to sample V,I,P 
 18: 20 us = start sampling V,I,P at absolute time in us before the pulse end 
 19: 0 = which parameters specify start of VIP sampling: 0 = %; 1 = us; 2 = us from end 
 20: 0 = which parameters specify end of VIP sampling: 0 = %; 1 = us len 
 21: 000 = Ignore Fans. Three digit 'xyz' for fan 1,2,3. '1' = ignore, '0' = monitor 
 22: 0 = 0 = monitor interlocks, 1 = ignore interlocks 
 23: 25 us = cap dead time - Dead time for cap switching 
 24: 0 = 1 = Rev_A I/F installed, 0 = Rev_A support not required 
 25: 20.00 V = PS Vin Fault Low Limit. 15-35V. Fault will assert if Vin < this. 
 26: 27.00 V = PS Vin Fault High Limit. 15-35V. Fault will assert if Vin > this. 
 27: 100.0 V = DCBias Auto Rng, Low to High Threshold. 
 28: 98.0 V = DCBias Auto Rng, High to Low Threshold. 
 29: 1500 ms = allow HVDC this much rise time 
 30: 1320 V = 100 - 2000V. HVDC Fault High Limit. DC_NO_OK Fault Will Assert If HVDC > this 
 31: 50 deg = Temp threshold for cumulative log 
 32: 2 = cap map : 0 = normal; 2 = Alternate map of 1/24 for new cap array 
 33: 4 = MinSample count for matching. (4 - 200) 
 34: 25 us = cap switching time 
 35: 1.0 % = analog cap preset noise threshold (0.0-9.9 %%) 
 37: 0 ms = Local Mode: Time limit in ms for 'RF setpoint not at 90%' (0 to disable) 
 38: 0 = 0/1 = user/factory mode at startup. 
 39: 3 = number of control loops per millisecond 
 40: 0 = 0 = start normally, remote mode, 1 = start in Bench mode, local control 
 41: 0 ms = Local Mode: Keep RF in CW mode for this many ms before switching to Pulse mode 
 42: 0 V = Local Mode: Absolute values of VDC lower than this indicate that VDC is 0 
 43: 0 ms = Local Mode: VDC monitoring will start this many milliseconds after RF On 
 44: 0 = 1 = use the params 37 and 41-43 for pulsing and RF controls in remote mode; 0 = use ECAT settings 
 50: 50 ms = Fan fault hold time. fan error has to hold this long before fault asserts. 
 51: 100 % = Run Fan 1 at this PWM. 0-100 
 52: 1000 RPM = Fan 1 RPM <= this will fault 
 53: 5000 RPM = Fan 1 RPM >= this clears fault 
 54: 100 % = Run Fan 2 at this PWM. 0-100 
 55: 1000 RPM = Fan 2 RPM <= this will fault 
 56: 5000 RPM = Fan 2 RPM >= this clears fault 
 57: 100 % = Run Fan 3 at this PWM. 0-100 
 58: 1000 RPM = Fan 3 RPM <= this will fault 
 59: 5000 RPM = Fan 3 RPM >= this clears fault 
 76: 4 = Diagnostic O/P signal selection for AO1 (0-29); Use 'daos' command for details. 
 77: 5 = Diagnostic O/P signal selection for AO2 (0-29); Use 'daos' command for details. 
Use 'psho g' and 'psho m' for generator- and match-specific parameters, respectively 
(1) 19:39:23>psho m 
*** Parameter list Version 10 
* Match Parameters 
 104: 5000.0 V = Max Vcap voltage raw limit for fast protection 
 105: 1000.0 V = Max Vcap voltage avg limit for fast protection 
 107: 0 = delay after reaching match - number of steps of inactivity 
 109: 0 = delay after losing match - number of steps of inactivity 
 111: 650 V = Max Vcap for cummulative log 
 112: 850 V = Max Vcap 
 113: 650 V = HVDC less than this -> shut down power supplies 
 114: 850 V = HVDC less than this -> pause matching 
 115: 900 V = HVDC greater than this -> resume matching 
 116: 1200 V = HVDC target voltage at power up (i.e. HVDC > this -> HVDC is OK) 
 120: 0.00 deg = Gamma correction angle 
 121: 1.00 = 
Z
 multiplicative correction term 
 122: 0.00 = 
Z
 additive correction term 
 123: 1.00 = Phase multiplicative correction term 
 124: 0.00 = Phase additive correction term 
 125: 6 = Vpp DAC Average. log2 of number of Vpp samples to average (0 - 10 : 1 to 1024 samples) 
 126: 1.0 = Vpp Correction Factor 
 127: 60.000 MHz = Radio Frequency 
 131: 15 = Voltage^2 average samples. log2 of number of Voltage samples to average (0 - 16 : 1 to 65536 samples) 
 132: 2 = 0/1/2 = dual restart limits disable / enable on restart / enable always 
 133: 60 = maximum cap movement in fine steps when low_limit < gamma/pref < high_limit 
 135: 0 = C1: moves of this many or fewer fine steps are short 
 136: 0 = C2: moves of this many or fewer fine steps are short 
 137: 0 = C1: if a short move -> limit to this many fine steps 
 138: 0 = C2: if a short move -> limit to this many fine steps 
 139: 12 us = VIP Sensor settling time 
 140: 5 us = Vpp Sensor settling time 
 144: 15.0 ms = time interval within which number of cap toggles is limited 
 145: 30 = max number of cap toggles within the above time period 
 146: 0 V = If RF is Off, Vpp has to be greater than this to be reported to AO 
 147: 3000 V = Maximum Vpp value to report on DAC 
 150: 0 = 0/1 = disable/enable hunting algorithm 
 151: 2 = Hunting algorithm selection (1,2,...) - only '2' supported for now 
 152: 0.002 = 
Gamma
 threshold for hunting vs table match 
 153: 0.0 ms = Delay after the first table match 
 154: 0.0 ms = Delay after later table matches 
 155: 0 = Alg 1: Initial direction for C2 (0 = up, 1 = down) 
 156: 0 = Alg 1: Initial direction for C1 (0 = up, 1 = down) 
 157: 0 = Alg 2: Initial direction for C2 (0 = up, 1 = down) 
 158: 0 = Alg 2: Initial direction for C1 (0 = up, 1 = down) 
 159: 0.020 = Alg 1: target 
Zin

 160: 0.005 = Alg 1: target 
Xin

 161: 0.60 W = Pfwd < 100 W: Pref stop 
 162: 1.40 W = Pref restart 
 163: 1.80 W = Pref high restart (when enabled by p132) 
 164: 0.050 = Pfwd 100 - 500 W: Gamma stop 
 165: 0.070 = Gamma restart 
 166: 0.090 = Gamma high restart (when enabled by p132) 
 167: 3.00 W = Pfwd > 500 W: Pref stop 
 168: 4.00 W = Pref restart 
 169: 5.00 W = Pref high restart (when enabled by p132) 
(1) 19:39:23>psho g 
*** Parameter list Version 10 
* Generator Parameters 
 300: 2000 W = Max Power 
 301: -2.35 V = Power DAC Setting - Min 
 302: 0.21 V = - Max 
 303: -2.50 V = DAC value when RF is Off 
 304: 3500 W = Max power level for DC Power Supply -- not used, but set it to a reasonable value 
 305: 55.0 V = Nominal DC Voltage Limit for DCPS 
 306: 100 ms = After changing VDC, wait this long before checking the voltage 
 307: 60.0 A = Nominal DC Current Limit for DCPS 
 308: 0.100 s = Max Silence time to declare DC PS Commn Err (0.1 to 10 Secs) 
 309: 5 W = Setpoint target window 
 310: 2 W = Forward pacifying window 
 311: 2 W = Reflected pacifying window 
 312: 0 = Power leveling (1 = load, 0 = forward) 
 313: 0 = RF Ramp up/down at RF On (1 - Enable, 0 - Disable) 
 314: 0 = RF Ramp up/down at RF setpt change (1 - Enable, 0 - Disable) 
 315: 3330 W = RF Power Ramp in Watts Per Second (100 to 3330) 
 316: 0 = Fault on pulses are out of range (1 - Enable, 0 - Disable) 
 317: 1.000 = Ambient Temperature correction factor for V and I (0.9 to 1.1) 
 318: 2 = Total number of FETs 
 319: 50.0 ms = Wait this long after RF Off before checking current 
 320: 1 = Averaging for Fwd/Ref Monitor DAC output (1 - Enable, 0 - Disable) 
 321: 0 = Rref VIP interval usage for reporting (1 - Enable, 0 - Disable -> use full pulse data) 
 322: 0 = Power control using Rref VIP intervals (1 - Enable, 0 - Disable -> use full pulse data) 
 323: 0 W = Min Power 
 324: 5 W = Max Pwr limit when RF is Off (Above this value, fault gets generated, 0 to disable fault) 
 325: 2 = Use CEX For RF Generation. 0 - Use DDS. 1 - Use CEX 2 - Use CEX with no freq validation 
 340: 50.0 A = Max PA current/FET 
 341: 7.0 A = Max PA Current/FET when RF is OFF 
 342: 500.0 W = Max Dissipation/FET for low Fwd Pwr 
 343: 10.0 W = Max Fwd Pwr for the above limit 
 344: 500.0 W = Max Dissipation / FET (foldback) 
 345: 70.0 degC = Max PA Temperature 
 346: 200.0 W = Max Reflected Power (foldback) 
 347: 2.0 A = Max Exciter Current 
 348: 70.0 degC = Max Amb Temperature 
 349: 50.0 degC = Count Amb Temperature if higher than this 
 350: 50.0 degC = Count PA Temperature if higher than this 
 351: 180.0 V = Max Drain voltage (foldback) 
 352: 90.0 degC = Max Exciter Temperature 
 353: 90.0 degC = Max Filter Temperature 
 354: 100.0 W = RF Input Sensor HALO Mode SetPt limit (0.0 to disable HALO mode) 
 355: 2 = Vin HALO mode selection; 0 - 'halo' cmd based selection; 1 - Future use (Sensor based HALO Not supported yet); 2 - Switch to HALO Cal tables based on param 354 
 356: 5.0 = Max PA Current Diff between PA1 and PA2; Open interlock when exceeded 
(1) 19:39:23>csho l
"""


# -----------------------------------------------------------------------------
# Robust description parser: supports both "pid desc" and "pid: ... = desc"
# -----------------------------------------------------------------------------

def build_desc_map_from_text(text: str) -> Dict[str, Dict[int, str]]:
    """
    Build description map: {section_name: {param_id: description_string}}

    Supported description line styles:
      A) "104 Max Vcap raw limit [V]"
      B) "104: 1100.0 V = Max Vcap voltage raw limit for fast protection"
    """
    desc: Dict[str, Dict[int, str]] = {}
    section = "General Parameters"

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        # Section headers: allow "#", "*", "//"
        if line.startswith("#") or line.startswith("*") or line.startswith("//"):
            sec = line.lstrip("#*/ ").strip()
            if sec:
                section = sec
                desc.setdefault(section, {})
            continue

        # Style B: "pid: <default...> = <desc>"
        mB = re.match(r"^(\d+)\s*:\s*([^=]*?)\s*=\s*(.+)$", line)
        if mB:
            pid = int(mB.group(1))
            default_part = mB.group(2).strip()
            d = mB.group(3).strip()
            if default_part:
                d = f"{d} (default: {default_part})"
            desc.setdefault(section, {})[pid] = d
            continue

        # Style A: "pid  description"
        mA = re.match(r"^(\d+)\s+(.*)$", line)
        if mA:
            pid = int(mA.group(1))
            d = mA.group(2).strip()
            desc.setdefault(section, {})[pid] = d
            continue

    return desc


# -----------------------------------------------------------------------------
# Build maps per unit type (Option 2)
# -----------------------------------------------------------------------------

CHRONOS20_DESC = build_desc_map_from_text(CHRONOS20_DESC_TEXT)
CHRONOS21_DESC = build_desc_map_from_text(CHRONOS21_DESC_TEXT)

TYKON0527_DESC = build_desc_map_from_text(TYKON0527_DESC_TEXT)
TYKON1213_DESC = build_desc_map_from_text(TYKON1213_DESC_TEXT)

QUANTUM2013_DESC = build_desc_map_from_text(QUANTUM2013_DESC_TEXT)
TRITON2060_DESC = build_desc_map_from_text(TRITON2060_DESC_TEXT)


def get_desc_map_for_unit(unit_type: str) -> Dict[str, Dict[int, str]]:
    """
    Return description map based on unit type string used in GUI (Option 2).
    """
    u = (unit_type or "").strip().lower()

    if u == "chronos 2.0":
        return CHRONOS20_DESC
    if u == "chronos 2.1":
        return CHRONOS21_DESC

    if u == "tykon0527":
        return TYKON0527_DESC
    if u == "tykon1213":
        return TYKON1213_DESC

    if u == "quantum2013":
        return QUANTUM2013_DESC

    if u == "triton2060":
        return TRITON2060_DESC

    return {}


# =============================================================================
# ------------------------ Parameter values parsed from tlog -------------------
# =============================================================================

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
    """
    Convert header param blocks to a flat table: (section, pid, value)
    header_params is List[(section_name, raw_line)]
    """
    rows: List[Tuple[str, int, str]] = []
    for section, line in header_params:
        pairs = parse_param_pairs_from_line(line)
        for pid, val in pairs:
            rows.append((section, pid, val))
    return rows

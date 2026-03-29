# tlog2chart_P3 Release Note (External)

## Version
- Product: `tlog2chart_P3`
- Version: `v1.3.12`
- Release date: `2026-03-30`

## Highlights
- Finalized Step 4 alarm report behavior for all product families.
- Step 5 reflected-power checks remain stable and verified.
- Step 6 pulse-mode alarm reporting now clearly handles both missing pulse detection and CW-only logs.

## What's New

### 1) Step 4 alarm report finalized
- Supports unit-aware setpoint logic:
  - Tykon / Triton: use hardware setpoint (`SetPt`/`Pset`)
  - Quantum / Chronos: derive setpoint from cycle Pfwd (50% to 100% window)
- Reports alarm-focused cycles only.
- Alarm criteria:
  - Rise-to-95% too slow (CW > 6 ms, Pulse > 12 ms)
  - Overshoot > 20%
  - Pfwd mismatch beyond +/-10%

### 2) Step 6 pulse-mode range alarms improved
- If pulse mode exists but EVC does not provide valid pulse frequency/duty values, report:
  - `PulseFreqNotDetected`
  - `PulseDutyNotDetected`
- If the tlog is CW-only, Step 6 explicitly reports:
  - `No pulse mode detected in this tlog (CW-only).`

### 3) Report structure clarity
- Pulse analysis section is clearly labeled as:
  - `Step 6 - Pulse Mode Range Alarms`

## Packaging / Release Notes
- Use `RELEASE_CHECKLIST_vx.x.x.md` as the standard release runbook.
- Example EXE naming for this release:
  - `dist\tlog2chart_P3_v1.3.12.exe`

## Upgrade Impact
- Existing workflow remains unchanged for users.
- Recommended flow remains:
  - Load tlog -> Custom Scale -> Carry X -> Analysis -> Export to Word


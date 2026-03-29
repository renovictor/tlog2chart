# tlog2chart_P3 Release Note (External)

## Version
- Product: `tlog2chart_P3`
- Version: `v1.3.11`
- Release date: `2026-03-29`

## Highlights
- Improved Phase 3 Word report quality and consistency.
- Better usability for time-window-based analysis.
- More reliable handoff from GUI settings to analysis engine.

## What's New

### 1) Step 1 report overview is more informative
Step 1 now includes:
- Full-scale duration
- Mode classification (CW / Pulse / Mixed)
- Max forward power
- Second-highest forward power (filtered to avoid near-peak jitter)
- RF ON/OFF cycle count

### 2) Step 2 now focuses on the last 2 seconds
Step 2 behavior is updated from a fixed full-scale/100 zoom rule to a fixed last-2-seconds view, so results are easier to compare across tlogs with different total durations.

### 3) Step 3 custom time range behavior fixed
For custom ranges (for example 10 to 13 seconds):
- Figure 3 now follows the selected absolute time range.
- Step 3 cycle metrics now reflect cycles in the selected window.
- GUI custom range is passed correctly into analysis.

## User-facing Improvements
- Figure 3 caption is now:
  - `Power plot for the user-selected custom time range.`

## Packaging / Release Notes
- Use `RELEASE_CHECKLIST_vx.x.x.md` as the standard release runbook for build, validation, tagging, and push.
- Example EXE naming for this release:
  - `dist\tlog2chart_P3_v1.3.11.exe`

## Upgrade Impact
- No workflow change required for standard users.
- Recommended flow remains:
  - Load tlog -> Custom Scale -> Carry X -> Analysis -> Export to Word


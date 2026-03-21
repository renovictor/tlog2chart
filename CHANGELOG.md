\# Changelog – tlog2chart\_P3



All notable changes to this project are documented in this file.

This project follows a project-level versioning scheme.

## [1.3.6] – 2026-03-10
### Fixed
- Task I: Improved compatibility across multiple tlog formats (Tykon/Quantum/Chronos 2.x/Triton) including header variations and multi-header segments.
- Task I: Chronos 2.0 parsing robustness improvements (header/time handling, token alignment) enabling correct Step 3 figure and metrics table generation.
- UX: Added “Carry X → Analysis Input” from Custom Scale to copy X-axis min/max into Step 3 time window.
- UX: Removed unnecessary “Phase 3 analysis started…please wait…” popup.
- UX: Improved visibility of “Select items to plot” pull-down control.

## [1.3.8] - 2026-03-21
### Added
- Tetris submenu under Help to launch bundled Tetris game as a separate process; log output is shown in a transient window for diagnostics.
- Instruction dialog with clearer, professional workflow steps (larger font for readability).

### Changed
- Bumped application version to 1.3.8

### Fixed
- Robust Tetris launcher: uses project root as cwd and displays child process stdout/stderr in a log window; falls back to threaded launch if needed.

### Known Issues
- Unit Type auto-detection for Tykon variants may default to **Tykon1213** even when loading a **Tykon0527 (27.12 MHz)** log. Manual selection of unit type is recommended when parameter descriptions must match the exact Tykon variant. Root cause: multiple unit-type setters exist in GUI logic and the frequency-based discriminator (Match param **127**) is not consistently applied at runtime; param 127 distinguishes **27.120 MHz (Tykon0527)** vs **13.560 MHz (Tykon1213)**. [1](https://oneasm-my.sharepoint.com/personal/victor_huang_asm_com/Documents/Microsoft%20Copilot%20Chat%20Files/07%20Tykon0527%20par%20list.txt)[1](https://oneasm-my.sharepoint.com/personal/victor_huang_asm_com/Documents/Microsoft%20Copilot%20Chat%20Files/07%20Tykon0527%20par%20list.txt)[2](https://oneasm-my.sharepoint.com/personal/victor_huang_asm_com/Documents/Microsoft%20Copilot%20Chat%20Files/07%20Tykon1213%20par%20list.txt)

## [1.3.6] – 2026-03-09
### Fixed
- Task I: Tykon1213 logs with leading timestamp prefixes now parse correctly (timestamp stripped before header detection).
- Task I: Chronos 2.0 header detection supports `sec ms` format and normalizes to canonical `sec,_ms.`.
- Task I: Chronos 2.0 parsing fixed for `C1c,f` and `C2c,f` tokens like `0, 0` (prevents column shift).
- Task I: Chronos 2.0 Step 3 metrics table restored using RF status column `RF`.
- Task I: Quantum (Q2013) RF ON/OFF naming differences handled (Step 3 metrics works).

### Improved
- Custom Scale dialog: “Carry X → Analysis Input” button added to copy X range into Step 3 time window.
- Analysis: removed unnecessary “Phase 3 analysis started…please wait…” popup.
- Graph toolbar: “Select items to plot” pull-down made more noticeable (hand cursor + hover emphasis).

## [1.3.5] – 2026-03-08
### Added
- New “Analysis Input” tab
- Step 3 custom time-range analysis (user enters start/end time; report focuses on that window)

### Changed
- Step 3 report title and narrative updated to reflect custom time-range analysis
- Step 3 metrics table now analyzes cycles/segments within the user-selected time window (not limited to first 6)

### Fixed
- Prevent out-of-range Step 3 inputs via GUI validation (warn if outside data range)
- Align Step 3 analysis timebase with Graph timebase to avoid mismatch between Graph and report

## [1.3.2] – 2026-03-xx
### Added
- Annotate tool (click → input text → place label; multiple; Clear Markups supported)
### Changed
- Tool routing: zoom zone always wins across all tool modes
### Fixed
- Prevent Ruler from falling back to legacy two-click handler (legacy kept but unused)
---
## [1.3.1] – 2026-03-05
### Changed
- Ruler tool upgraded to JMP-style drag workflow (press→drag preview→release finalize)
- Support multiple ruler lines (temporary markups)
### Fixed
- Hover interactions stabilized across Graph and Smith chart
---
\## \[1.2.0] – 2026-03-03

\### Changed

\- Refactored from a single-file script into a multi-module project structure

\- Separated GUI, data parser, plotting, and analysis logic

\- Improved maintainability and extensibility without changing behavior



\### Fixed

\- RF ON/OFF detection unified to use RF:UC (\* / -)

\- Step 3 RF-cycle metrics consistency



\### Verified

\- Phase 3 analysis Step 1–5

\- Single tlog workflow

\- Word report export



---



\## \[1.1.0] – 2025-02-20

\### Added

\- Phase 3 analysis framework

\- Step 1–5 analysis flow

\- Word report export (PNG figures + tables)



\### Changed

\- Added RF-cycle-based analysis concept



---



\## \[1.0.0] – Initial

\### Added

\- Basic tlog parsing

\- Graph visualization

\- Smith chart visualization

``


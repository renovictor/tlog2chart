\# Changelog – tlog2chart\_P3



All notable changes to this project are documented in this file.

This project follows a project-level versioning scheme.

## [1.3.6] – 2026-03-02
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

## [1.3.5] – 2026-03-xx
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


\# Changelog – tlog2chart\_P3



All notable changes to this project are documented in this file.

This project follows a project-level versioning scheme.

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


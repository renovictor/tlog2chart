\# Changelog – tlog2chart\_P3



All notable changes to this project are documented in this file.

This project follows a project-level versioning scheme.

## [1.3.4] – 2026-03-02
### Added
- Shape tool (Rectangle / Circle) with JMP-style interaction:
  - Mouse press → start
  - Drag → live preview (outline + translucent fill)
  - Release → finalize and keep shape
- Multiple shapes supported per plot
- Custom shape color selection
- Adjustable shape fill transparency (alpha)

### Changed
- Unified tool interaction model across Ruler / Line / Shape:
  - Zoom zone always takes priority
  - Drag state properly finalized on mouse release
- Clear Markups now removes:
  - Rulers
  - Annotations
  - Lines
  - Shapes

### Fixed
- Shape preview no longer updates when mouse moves without button pressed
- Shapes no longer disappear on mouse release or second click
- Eliminated ghost-drag behavior caused by incomplete drag state reset

## [1.3.3] – 2026-03-02
### Added
- Line tool with JMP-style interaction:
  - Mouse press → start
  - Drag → live preview line
  - Release → finalize and keep line
- Multiple lines supported per plot
- Optional Ctrl key constraint for horizontal / vertical lines

### Changed
- Clear Markups now removes:
  - Rulers
  - Annotations
  - Lines
- Unified drag interaction model shared across Ruler and Line tools

### Fixed
- Tool interaction routing stabilized:
  - Zoom zone always takes priority in all tool modes
  - Line tool no longer interferes with zoom or hover behavior

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


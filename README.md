# tlog2chart_P3

Professional tool for loading, visualizing, and analyzing EVC `.tlog` files.

## Version Information

- Current version: **v1.3.10**
- Release date: **2026-03-29**
- Startup improvement in this version: application now shows a splash screen with loading progress so users see feedback immediately while the EXE initializes.

## What This App Does

`tlog2chart_P3` helps engineers:

- Load and parse EVC tlog data
- Plot multi-channel time-series waveforms
- View Smith chart trends
- Use graph tools (`Arrow`, `Ruler`, `Annotate`, `Line`, `Shape`) for inspection and markup
- Run analysis workflow and export report to Word

## How to Run (User)

This application is intended to run from the packaged Windows executable.

1. Open the project folder.
2. Go to `dist`.
3. Double-click the EXE file (example: `tlog2chart_P3_v1.3.10.exe`).

If startup takes some time, this is expected for a one-file EXE. You should see a splash/loading window during initialization.

## Recommended User Workflow

1. Open a `.tlog` file (`File -> Open`).
2. Review plotted channels and select items to display.
3. Use `Custom Scale` to focus on the time range of interest.
4. Click `Carry x` to pass selected X-range into analysis.
5. Run `Analysis`.
6. Click `Export to Word` to generate a report.

## Help Inside the App

- `Help -> Instruction`: step-by-step usage guide
- `Help -> About`: version, release date, author, and product information

## FAQ (Common Questions)

### 1) Why does the app take time to open?
- This EXE is packaged in one file, so it needs time to unpack and load modules at startup.
- In v1.3.10, a splash/loading window is shown so you can see startup progress.

### 2) I loaded a `.tlog` file but no chart appears. What should I check?
- Confirm the file is a valid tlog text file and not empty.
- Check `Unit Type` and `Band Filter` settings.
- Open `Select items to plot` and make sure at least one channel is selected.
- Try `Full Scale` to reset the graph view.

### 3) Why is `Export to Word` disabled?
- `Export to Word` is enabled only after a successful `Analysis` run.
- Recommended order: load file -> set range -> `Carry x` -> `Analysis` -> `Export to Word`.

### 4) Why is first startup after rebuild slower than later runs?
- This can happen due to Windows cache and antivirus scanning behavior on new EXE files.
- Later launches are often faster after the first run.

### 5) The app icon looks different when running in IDE vs EXE. Is this normal?
- Yes, this can differ by launch method on Windows.
- For end users, the packaged EXE icon is the reference behavior.

### 6) Where can I find usage guidance inside the app?
- `Help -> Instruction` provides the recommended workflow.
- `Help -> About` shows version, release date, and product information.


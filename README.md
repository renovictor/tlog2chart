# tlog2chart_P3 v1.2 (refactored multi-file)

## Run (dev)
```bash
python -m tlog2chart_p3.main
```

## Build EXE (PyInstaller onefile, Windows)
From the folder that contains `tlog2chart_p3/` and `smithchart.ico`:

```bash
pyinstaller -F -w --name tlog2chart_P3_V1.2 --icon smithchart.ico   --add-data "smithchart.ico;."   -m tlog2chart_p3.main
```

Notes:
- `--add-data "src;dest"` uses semicolon on Windows. On Linux/macOS use colon.
- The app loads the icon via `resource_path()` so it works in onefile mode.

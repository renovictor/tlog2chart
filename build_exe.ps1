$ErrorActionPreference = "Stop"

$ver = python -c "import tlog2chart_p3.version as v; print(v.APP_VERSION)"
$exeName = "tlog2chart_P3_v$ver"

Write-Host "Building EXE: $exeName.exe"

pyinstaller --clean --noconfirm --onefile --windowed `
  --icon smithchart.ico `
  --name $exeName `
  run_app.py
$ErrorActionPreference = 'Stop'

# Find python executable
try {
    $python = (Get-Command python -ErrorAction Stop).Source
} catch {
    Write-Error "Python executable not found in PATH. Activate your venv or add python to PATH."
    exit 1
}

# Read version from package
$ver = & $python -c "import tlog2chart_p3.version as v; print(v.APP_VERSION)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Failed to read version; using fallback 0.0.0. Output: $ver"
    $ver = '0.0.0'
}

$exeName = "tlog2chart_P3_v$ver"
Write-Host "Building EXE: $exeName.exe"

# Paths
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projRoot = Resolve-Path $scriptDir
$pkgDir = Join-Path $projRoot 'tlog2chart_p3'

# Collect --add-data entries
$dataFiles = @()
function Add-DataIfExists($relPath, $dest) {
    $src = Join-Path $pkgDir $relPath
    if (Test-Path $src) { $script:dataFiles += "${src};${dest}"; Write-Host "Include: $src -> $dest" }
}

Add-DataIfExists 'asm-logo-small.gif' 'tlog2chart_p3'
Add-DataIfExists 'asm-logo.gif' 'tlog2chart_p3'
Add-DataIfExists 'company_logo.png' 'tlog2chart_p3'
Add-DataIfExists 'music.mp3' 'tlog2chart_p3'
Add-DataIfExists 'music.ogg' 'tlog2chart_p3'
Add-DataIfExists 'smithchart.ico' 'tlog2chart_p3'

# Also bundle VERSION.txt from project root
$versionTxt = Join-Path $projRoot 'VERSION.txt'
if (Test-Path $versionTxt) { $script:dataFiles += "${versionTxt};."; Write-Host "Include: $versionTxt -> ." }

# Icon (used for EXE file icon – lives inside the package dir)
$iconPath = Join-Path $pkgDir 'smithchart.ico'
if (-not (Test-Path $iconPath)) { Write-Warning "Icon not found: $iconPath" }

# Build PyInstaller args
$pyiArgs = @('--clean', '--noconfirm', '--onefile', '--windowed', '--name', $exeName)
if (Test-Path $iconPath) { $pyiArgs += @('--icon', $iconPath) }
foreach ($d in $dataFiles) { $pyiArgs += @('--add-data', $d) }

# Hidden imports
$hiddenImports = @('pygame', 'matplotlib.backends.backend_tkagg', 'docx', 'PIL', 'PIL._tkinter_finder')
foreach ($h in $hiddenImports) { $pyiArgs += @('--hidden-import', $h) }

# Entry script
$pyiArgs += 'run_app.py'

Write-Host "pyinstaller args: $($pyiArgs -join ' ')"

# Run PyInstaller
& $python -m PyInstaller @pyiArgs

if ($LASTEXITCODE -eq 0) { Write-Host "Build success: dist\$exeName.exe" } else { Write-Error "PyInstaller failed (exit $LASTEXITCODE)" }

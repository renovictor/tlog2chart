# Release checklist — `v1.3.11`

Use this checklist to prepare, build, validate, and publish release `v1.3.11` for `tlog2chart_P3`.

---

## Summary plan

1. Pre-checks (code, docs, version files)
2. Quick run validation in development environment
3. Build EXE (packaging)
4. Git: commit, tag
5. Push branch and tag to remote
6. Post-release verification

---

## 0) Prepare version files

- Confirm `tlog2chart_p3/version.py` shows:
  - `APP_VERSION = "1.3.11"`
  - `RELEASE_DATE = "2026-03-29"`
- Confirm `VERSION.txt` shows:
  - `Version: 1.3.11`
- Confirm `CHANGELOG.md` has `## [1.3.11]` entry.
- Confirm `README.md` references `v1.3.11`.

## 1) Pre-checks

```powershell
. .venv\Scripts\Activate.ps1
python -u run_app.py
```

Manual smoke checks:
- App launches
- Company logo visible
- Menu bar works (`File`, `Graph`, `Help`)
- Load a known tlog from `Testing/`
- Charts render normally
- `Analysis` and `Export to Word` work

## 2) Build EXE

```powershell
. .venv\Scripts\Activate.ps1
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

Expected output pattern:
- `dist\tlog2chart_P3_v1.3.11.exe`

## 3) Git commit + tag

```powershell
git add -A
git commit -m "Release v1.3.11"
git tag -a v1.3.11 -m "Release v1.3.11"
```

## 4) Push branch + tag

```powershell
git push origin HEAD
git push origin v1.3.11
```

## 5) Post-release verification

From a clean folder/machine:

```powershell
.\tlog2chart_P3_v1.3.11.exe
```

Verify:
- Startup splash appears
- App window + icon are correct
- Load tlog + plot works
- Step 1/2/3 report output is correct
- `Help -> About` shows `v1.3.11`

---

## Quick troubleshooting

- If callback missing-method errors appear, verify handler methods are class-level in `Tlog2ChartP2App` and not accidentally nested by indentation.
- If build misses assets, update PyInstaller add-data entries/spec and rebuild.
- If Step 3 range looks wrong, verify GUI custom range is passed to analysis before export.


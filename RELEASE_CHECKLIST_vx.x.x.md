# Release checklist — `vx.x.x`

Use this checklist to prepare, build, validate and publish a release for the tlog2chart_p3 application. Replace `vx.x.x` with the real version (for example `v1.3.8`).

---

## Summary plan

1. Pre-checks (code, docs, version files)
2. Quick run validation in development environment
3. Build EXE (packaging)
4. Git: commit, tag
5. Push branch and tag to remote
6. Post-release verification (sanity tests on the produced artifact)

---

## Checklist (step-by-step)

### 0. Prepare: update version and changelog

- Update `VERSION.txt` to the new version string (e.g. `v1.3.8`).
- Update `CHANGELOG.md` with release notes for the new version.
- Ensure the `README.md` and any about/help text inside the GUI mentions the new version if required.

Suggested commit message: "Bump version to vx.x.x and update changelog"

Example (PowerShell):

```powershell
# Edit files manually or with an editor, then:
git add VERSION.txt CHANGELOG.md README.md
git commit -m "Bump version to vx.x.x and update changelog"
```


### 1. Pre-checks (required before building)

- Run linting and static checks if available (e.g., flake8, mypy).
- Ensure the virtual environment is active and dependencies installed (if packaging from a venv):

```powershell
# from project root
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt  # or pip install -r tools/requirements.txt
```

- Confirm tests (if any) pass. If there are no automated tests, perform a short manual smoke test (see Quick Run).
- Confirm that `asm-logo-small.gif` and other assets are in `tlog2chart_p3/` and correctly referenced.
- Confirm `build_exe.ps1` is up to date.


### 2. Quick run validation (dev)

Before building the final EXE, run the app from source and perform these quick checks:

- Start the app:

```powershell
# From project root
python -u run_app.py
```

- Manual checks in the GUI:
  - Logo loads and is visible top-right
  - Menu bar (File, Graph, Help) appears and submenu items work
  - Load a typical tlog file (use a known file under `Testing/`) and ensure charts render
  - Verify the toolbar icons (original view, left/right arrows) are visible and functional
  - Run the `Tetris` submenu item to launch the game and ensure it runs and does not immediately exit
  - Open Help -> Instruction and confirm font size is acceptable
  - Run Export to Word (if that flow is part of release) and verify output file generates (or shows appropriate error if dependency missing)

- If any problems are found, fix them and iterate until the quick run passes.


### 3. Build EXE (packaging)

This repository already includes a `build_exe.ps1`. Use it to create the distributable executable. Example:

```powershell
# From project root
# Make sure you are in an activated venv with required build tools (pyinstaller or cx_Freeze as required)
. .venv\Scripts\Activate.ps1
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

Notes:
- The script should produce `dist\tlog2chart_P3_vx.x.x.exe` (or similar) according to existing spec files.
- If the build script wraps PyInstaller, check the generated `dist` folder for required assets (`asm-logo-small.gif`, icons, etc.).
- If packaging fails, capture the build log and fix missing imports/assets.


### 4. Git — Commit + Tag

Before tagging, make sure all changes (version bump, changelog, build scripts) are committed.

```powershell
# Add any outstanding changes
git add -A
# Commit with a clear message
git commit -m "Release vx.x.x"

# Create an annotated tag
git tag -a vx.x.x -m "Release vx.x.x"
```

If a tag already exists, consider bumping the version (e.g. vx.x.x+1) or delete the old tag locally (and remotely if necessary) before recreating—only do this if you understand the consequences.


### 5. Push branch and tag

Push the current branch and the tag to origin:

```powershell
# push current branch
git push origin HEAD
# push tags
git push origin vx.x.x
# or push all tags
git push origin --tags
```

If you prefer creating a GitHub release, after pushing tags:
- Open GitHub Releases for the repository
- Draft a new release based on tag `vx.x.x`, paste changelog notes, attach binaries if needed


### 6. Post-release verification

On a clean environment (or at least a different directory/machine), perform these checks:

1. Download or copy the `dist\tlog2chart_P3_vx.x.x.exe` to a temp folder.
2. Run the EXE:

```powershell
# from a fresh folder
.\tlog2chart_P3_vx.x.x.exe
```

3. Verify the following (smoke tests):
   - Application launches and GUI appears
   - Company logo displays correctly
   - Menu bar and `Graph` submenu (None, Arrow, Ruler, Annotate, Line, Shape) work
   - Help -> Instruction opens and font size is readable
   - Load a sample tlog and ensure chart is rendered (use a bundled sample or copy from `Testing/`)
   - Tetris submenu launches the game and it remains visible and playable
   - Export to Word works (if Word dependency is present) or the app shows an informative error
   - Check About/Version shows `vx.x.x`

4. If automated telemetry or crash reporting exists, check that no new errors are reported.

5. If distributing an installer or uploading to releases, attach the EXE and any ZIP/installer.


## Example: release `v1.3.8`

Replace the placeholder with the actual version and follow steps above. Example git commands for v1.3.8:

```powershell
git add -A
git commit -m "Release v1.3.8"
git tag -a v1.3.8 -m "Release v1.3.8"
git push origin HEAD
git push origin v1.3.8
```


## Quick troubleshooting notes

- If GUI callbacks complain about missing methods (AttributeError: '_tkinter.tkapp' object has no attribute '...'), ensure none of the methods were accidentally defined inside another function or lost indentation; ensure all `def _on_xxx` handler methods exist on the `Tlog2ChartP2App` class.
- If packaging launches the main app instead of a submodule (for example launching Tetris via `-m tlog2chart_p3.Tetris` caused the main app to open), consider embedding the Tetris runner inside the main package as a callable function or launching it via a subprocess that calls Python with the right module path. Test the approach from a built EXE before tagging.
- If the EXE build misses assets, confirm asset inclusion by checking PyInstaller spec or the build script. Add `--add-data` entries as needed.


---

If you want, I can now:
- Replace `vx.x.x` with `v1.3.8` and create `RELEASE_CHECKLIST_v1.3.8.md` instead, or
- Update `VERSION.txt` and `CHANGELOG.md` and create a sample git commit and tag for `v1.3.8`.

Tell me which of the two you prefer and I will proceed (I can also perform the git commit/tag if you want and if the environment has git configured).

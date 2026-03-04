from __future__ import annotations

import os
import sys


def resource_path(relative_path: str) -> str:
    """Return absolute path to resource; works for PyInstaller onefile/onedir."""
    # When bundled by PyInstaller, sys._MEIPASS points to the temp extraction dir.
    base = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base, relative_path)
def read_project_version(default: str = "?.?.?") -> str:
    """
    Read project version string from VERSION.txt.

    Expected line format inside VERSION.txt:
      Version: x.y.z

    Search order:
      1) Project root (parent of this package folder)
      2) Current working directory
      3) PyInstaller temp folder via resource_path() (fallback)
    """
    import os
    import re

    candidates = []

    # (1) project root = one level above this package folder
    pkg_dir = os.path.abspath(os.path.dirname(__file__))           # .../tlog2chart_p3
    root_dir = os.path.abspath(os.path.join(pkg_dir, os.pardir))   # .../project_root
    candidates.append(os.path.join(root_dir, "VERSION.txt"))

    # (2) current working directory
    candidates.append(os.path.join(os.getcwd(), "VERSION.txt"))

    # (3) PyInstaller temp folder (onefile) fallback
    try:
        candidates.append(resource_path("VERSION.txt"))
    except Exception:
        pass

    # Read first valid match
    for path in candidates:
        try:
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

            m = re.search(
                r"^\\s*Version\\s*:\\s*([0-9]+\\.[0-9]+\\.[0-9]+)\\s*$",
                text,
                flags=re.MULTILINE
            )
            if m:
                return m.group(1).strip()
        except Exception:
            continue

    return default

def read_project_version(default: str = "?.?.?") -> str:
    """
    Read project version string from VERSION.txt.

    Search order:
      1) Project root: one level above this package folder
      2) Current working directory (fallback)
      3) PyInstaller temp folder via resource_path() (fallback)
    """
    import os
    import re

    candidates = []

    # 1) project root = .../tlog2chart_P3_V1_2 (parent of package dir)
    pkg_dir = os.path.abspath(os.path.dirname(__file__))           # .../tlog2chart_p3
    root_dir = os.path.abspath(os.path.join(pkg_dir, os.pardir))   # .../tlog2chart_P3_V1_2
    candidates.append(os.path.join(root_dir, "VERSION.txt"))

    # 2) current working directory
    candidates.append(os.path.join(os.getcwd(), "VERSION.txt"))

    # 3) resource_path (PyInstaller onefile temp dir)
    try:
        candidates.append(resource_path("VERSION.txt"))
    except Exception:
        pass

    # read the first match
    for path in candidates:
        try:
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

            # Accept formats like:
            # Version: 1.2.0
            m = re.search(
                r"^\s*version\s*[:=]\s*v?([0-9]+\.[0-9]+(?:\.[0-9]+)?)\s*$",
                text,
                flags=re.MULTILINE | re.IGNORECASE
            )
            if m:
                return m.group(1).strip()
        except Exception:
            continue

    return default
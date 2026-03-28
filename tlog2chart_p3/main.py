from __future__ import annotations
import os
import sys

# Set Windows taskbar icon before any tkinter import
# Only needed when running from source (python.exe shows a leaf).
# When frozen (PyInstaller EXE), --icon already embeds the correct icon.
if os.name == 'nt' and not getattr(sys, 'frozen', False):
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            'ASM.tlog2chart_P3.1')
    except Exception:
        pass

from .gui_app import Tlog2ChartP2App


def main() -> None:
    # If the executable is invoked with --run-tetris we launch the Tetris subroutine
    if '--run-tetris' in sys.argv:
        try:
            from . import Tetris
            # run blocking in this process (standalone game)
            Tetris.run(blocking=True, as_process=False)
        except Exception:
            try:
                # fallback: call module main
                import tlog2chart_p3.Tetris as mod
                mod.main()
            except Exception:
                pass
        return

    app = Tlog2ChartP2App()
    app.mainloop()


if __name__ == '__main__':
    main()

from __future__ import annotations
import sys

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

# ---------------------------------------------------------------------------
# run_app.py  –  Entry point for tlog2chart_P3
#
# Shows a lightweight splash screen with an indeterminate progress bar while
# heavy modules (numpy, pandas, matplotlib, PIL, docx …) are imported in a
# background thread.  Once all imports are cached in sys.modules the splash
# is closed and the real application window is created.
# ---------------------------------------------------------------------------
import sys
import os
import threading

# Set Windows AppUserModelID BEFORE any tkinter import so the correct icon
# appears on the Windows taskbar (only needed when running from source).
if os.name == 'nt' and not getattr(sys, 'frozen', False):
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            'ASM.tlog2chart_P3.1')
    except Exception:
        pass


# ── helper: locate asset file (works both from source and frozen EXE) ──────
def _find_asset(name: str):
    """Return the absolute path to *name* or None if not found."""
    candidates = []
    # When frozen, _MEIPASS/tlog2chart_p3/<name>
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidates.append(os.path.join(meipass, 'tlog2chart_p3', name))
        candidates.append(os.path.join(meipass, name))
    # When running from source: <project>/tlog2chart_p3/<name>
    pkg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'tlog2chart_p3')
    candidates.append(os.path.join(pkg_dir, name))
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


# ── Splash screen ─────────────────────────────────────────────────────────
def _run_with_splash():
    """Create a small splash window, import heavy modules, then launch app."""
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.overrideredirect(True)          # borderless window
    root.attributes('-topmost', True)    # keep on top while loading

    # ---- geometry: centred on screen ----
    w, h = 420, 230
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    root.geometry(f'{w}x{h}+{x}+{y}')
    root.configure(bg='#2b2b2b')

    # ---- icon (if available) ----
    ico_path = _find_asset('smithchart.ico')
    if ico_path:
        try:
            root.iconbitmap(ico_path)
        except Exception:
            pass

    # ---- company logo ----
    logo_img = None          # prevent garbage-collection
    for name in ('asm-logo-small.gif', 'ASM-logo-small.gif'):
        p = _find_asset(name)
        if p:
            try:
                logo_img = tk.PhotoImage(file=p)
                break
            except Exception:
                logo_img = None
    if logo_img:
        lbl = tk.Label(root, image=logo_img, bg='#2b2b2b')
        lbl.image = logo_img        # prevent GC
        lbl.pack(pady=(18, 4))

    # ---- title ----
    tk.Label(root, text='tlog2chart_P3',
             font=('Segoe UI', 16, 'bold'),
             fg='white', bg='#2b2b2b').pack(pady=(6, 2))

    # ---- status text ----
    status_var = tk.StringVar(value='Initializing...')
    status_lbl = tk.Label(root, textvariable=status_var,
                          font=('Segoe UI', 9), fg='#aaaaaa', bg='#2b2b2b')
    status_lbl.pack(pady=(2, 10))

    # ---- progress bar ----
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('Splash.Horizontal.TProgressbar',
                    troughcolor='#444444', background='#00aaff')
    pbar = ttk.Progressbar(root, mode='indeterminate', length=340,
                           style='Splash.Horizontal.TProgressbar')
    pbar.pack(pady=(0, 18))
    pbar.start(15)

    # ---- shared state between threads ----
    result = {'done': False, 'error': None, 'main_func': None}

    def _set_status(text):
        """Thread-safe status update via Tk event queue."""
        try:
            root.after_idle(lambda t=text: status_var.set(t))
        except Exception:
            pass

    def _do_imports():
        """Run in a daemon thread - import heavy packages one by one."""
        try:
            _set_status('Loading NumPy...')
            import numpy                           # noqa: F401

            _set_status('Loading Pandas...')
            import pandas                          # noqa: F401

            _set_status('Loading Matplotlib...')
            import matplotlib                      # noqa: F401
            matplotlib.use('TkAgg')

            _set_status('Loading image libraries...')
            try:
                from PIL import Image, ImageTk     # noqa: F401
            except Exception:
                pass

            _set_status('Loading document library...')
            try:
                import docx                        # noqa: F401
            except Exception:
                pass

            _set_status('Loading application...')
            from tlog2chart_p3.main import main
            result['main_func'] = main
            result['done'] = True
        except Exception as e:
            result['error'] = e
            result['done'] = True

    threading.Thread(target=_do_imports, daemon=True).start()

    # ---- poll until imports finish ----
    def _poll():
        if not result['done']:
            root.after(80, _poll)
            return
        pbar.stop()
        if result['error']:
            status_var.set(f'Load error: {result["error"]}')
            root.after(4000, root.destroy)
        else:
            status_var.set('Ready!')
            root.after(300, lambda: _launch_app(root, result['main_func']))

    root.after(80, _poll)
    root.mainloop()


def _launch_app(splash_root, main_func):
    """Close splash and start the real application."""
    splash_root.destroy()
    if main_func:
        main_func()


# ── entry point ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    # Tetris sub-routine shortcut (used by the frozen EXE)
    if '--run-tetris' in sys.argv:
        from tlog2chart_p3.main import main
        main()
    else:
        _run_with_splash()

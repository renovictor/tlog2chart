"""
Quick test: verify smithchart.ico loads correctly and shows on BOTH
title bar AND Windows taskbar (not the Python leaf).
"""
import os, sys

# Step 0: Set AppUserModelID BEFORE any tkinter import
if os.name == 'nt':
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('ASM.tlog2chart_P3.1')
    print("[OK] Step 0: SetCurrentProcessExplicitAppUserModelID done")

import tkinter as tk

root = tk.Tk()
root.title("Taskbar Icon Test")
root.geometry("400x200")

# Locate the ico file
ico_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        'tlog2chart_p3', 'smithchart.ico')
print(f"[INFO] ico_path = {ico_path}")
print(f"[INFO] exists   = {os.path.exists(ico_path)}")

# Step 1: iconbitmap (title bar)
try:
    root.iconbitmap(ico_path)
    root.iconbitmap(default=ico_path)
    print("[OK] Step 1: iconbitmap set (title bar)")
except Exception as e:
    print(f"[FAIL] Step 1: iconbitmap failed: {e}")

# Step 2: PIL open + resize
try:
    from PIL import Image, ImageTk
    img = Image.open(ico_path)
    print(f"[OK] Step 2a: PIL opened ico — size={img.size}, mode={img.mode}")
    img = img.resize((48, 48), Image.LANCZOS)
    print(f"[OK] Step 2b: Resized to {img.size}")
except Exception as e:
    print(f"[FAIL] Step 2: PIL load/resize failed: {e}")
    img = None

# Step 3: Convert to ImageTk.PhotoImage
photo = None
if img is not None:
    try:
        photo = ImageTk.PhotoImage(img)
        print(f"[OK] Step 3: ImageTk.PhotoImage created — width={photo.width()}, height={photo.height()}")
    except Exception as e:
        print(f"[FAIL] Step 3: ImageTk.PhotoImage failed: {e}")

# Step 4: wm_iconphoto
if photo is not None:
    try:
        root.wm_iconphoto(True, photo)
        print("[OK] Step 4: wm_iconphoto set (taskbar + title bar)")
    except Exception as e:
        print(f"[FAIL] Step 4: wm_iconphoto failed: {e}")

# Show a label so user can check taskbar
tk.Label(root, text="Check the TASKBAR icon below.\n"
                     "It should be smithchart, NOT a leaf.\n\n"
                     "Close this window when done.",
         font=("Segoe UI", 12), pady=30).pack()

print("\n>>> Window is open. Check the taskbar icon, then close the window.")
root.mainloop()


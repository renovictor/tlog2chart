import tkinter as tk

root = tk.Tk()
root.title('ASM Logo Test')

try:
    logo_img = tk.PhotoImage(file='asm-logo.gif')
    logo_label = tk.Label(root, image=logo_img, borderwidth=2, relief="groove", bg="white")
    logo_label.pack(padx=10, pady=10)
    print('Logo loaded successfully.')
except Exception as e:
    print(f'Logo load failed: {e}')

root.mainloop()


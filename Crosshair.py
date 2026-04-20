import tkinter as tk
import sys

def draw_crosshair():
    root = tk.Tk()
    # Pencere çerçevelerini yok et, her şeyin üstünde tut, beyazı şeffaf yap
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", "white")
    root.config(bg="white")
    
    # Ekran boyutunu al ve tam ekran yap
    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    root.geometry(f"{w}x{h}+0+0")
    
    # Tıklamaları pencerenin içinden geçir (Mouse tıklamalarını engellemesin)
    root.attributes("-disabled", True)
    
    canvas = tk.Canvas(root, width=w, height=h, bg="white", highlightthickness=0)
    canvas.pack()
    
    # Tam merkeze kırmızı/neon e-spor nişangahı çiz
    cx, cy = w // 2, h // 2
    canvas.create_line(cx - 15, cy, cx + 15, cy, fill="#ff0055", width=2)
    canvas.create_line(cx, cy - 15, cx, cy + 15, fill="#ff0055", width=2)
    canvas.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill="#00f3ff", outline="")
    
    root.mainloop()

if __name__ == "__main__":
    draw_crosshair()
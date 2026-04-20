"""
Strom Crosshair — Bağımsız Çalışan Modül
==========================================
Bu dosya iki şekilde kullanılır:
  1. python Crosshair.py                          → Varsayılan ayarlarla başlatır
  2. python Crosshair.py '{"color":"#00ff00",...}' → JSON argümanıyla başlatır

SystemEngine.py ise geçici bir _strom_crosshair.py üretir ve onu
pythonw ile arka planda spawn eder. Bu dosya doğrudan da çalışır.

Desteklenen şekiller: cross | dot | circle | cross+dot
Hotkey: INSERT tuşu ile kapatır (keyboard kütüphanesi yüklüyse)
"""

import tkinter as tk
import sys
import json
import threading

# ─────────────────────────────────────────────────────────────
# VARSAYILAN AYARLAR
# ─────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "color":     "#ff0055",   # Ana renk (çizgiler)
    "dot_color": "#00f3ff",   # Merkez nokta rengi
    "size":      15,          # Çizgi yarı-uzunluğu (px)
    "thickness": 2,           # Çizgi kalınlığı (px)
    "shape":     "cross+dot", # cross | dot | circle | cross+dot
    "hotkey":    True,        # INSERT ile kapat
    "opacity":   1.0,         # 0.1 – 1.0 (pencere saydamlığı, şeffaf renk != bu)
}


def parse_config():
    """Komut satırı argümanından JSON config okur, yoksa varsayılan kullanır."""
    config = DEFAULT_CONFIG.copy()
    if len(sys.argv) > 1:
        try:
            user_cfg = json.loads(sys.argv[1])
            config.update(user_cfg)
        except Exception as e:
            print(f"[!] Config parse hatası: {e}. Varsayılan kullanılıyor.")
    return config


def draw_crosshair(canvas, cx, cy, config):
    """Canvas üzerine seçilen şekli çizer."""
    canvas.delete("all")
    color     = config["color"]
    dot_color = config["dot_color"]
    size      = int(config["size"])
    thickness = int(config["thickness"])
    shape     = config["shape"]

    if shape in ("cross", "cross+dot"):
        # Yatay çizgi
        canvas.create_line(
            cx - size, cy, cx + size, cy,
            fill=color, width=thickness
        )
        # Dikey çizgi
        canvas.create_line(
            cx, cy - size, cx, cy + size,
            fill=color, width=thickness
        )

    if shape == "circle":
        canvas.create_oval(
            cx - size, cy - size, cx + size, cy + size,
            outline=color, width=thickness
        )

    if shape == "dot":
        r = max(2, thickness + 1)
        canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill=color, outline=""
        )

    if shape == "cross+dot":
        r = max(2, thickness + 1)
        canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill=dot_color, outline=""
        )


def setup_hotkey(root):
    """
    INSERT tuşuna basıldığında pencereyi kapatır.
    'keyboard' kütüphanesi kurulu değilse sessizce atlar.
    Kurulum: pip install keyboard
    """
    try:
        import keyboard
        def on_insert():
            root.after(0, root.destroy)  # tkinter thread-safe kapatma
        keyboard.add_hotkey("insert", on_insert)
        print("[+] Hotkey aktif: INSERT → Crosshair kapat")
    except ImportError:
        print("[!] 'keyboard' kütüphanesi bulunamadı. Hotkey devre dışı.")
        print("[!] Kurmak için: pip install keyboard")
    except Exception as e:
        print(f"[!] Hotkey kurulamadı: {e}")


def main():
    config = parse_config()
    print(f"[+] Strom Crosshair başlatılıyor: {config}")

    root = tk.Tk()

    # ── Pencere ayarları ──────────────────────────────────────
    root.overrideredirect(True)                       # Başlık barını kaldır
    root.attributes("-topmost", True)                 # Her zaman üstte
    root.attributes("-transparentcolor", "white")     # Beyazı şeffaf yap
    root.config(bg="white")

    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    root.geometry(f"{w}x{h}+0+0")                    # Tam ekran

    # Mouse tıklamalarını geçir (oyun kontrolünü engellemez)
    root.attributes("-disabled", True)

    # Opaklık (isteğe bağlı, 1.0 = tam opak)
    opacity = float(config.get("opacity", 1.0))
    if opacity < 1.0:
        root.attributes("-alpha", opacity)

    # ── Canvas ───────────────────────────────────────────────
    canvas = tk.Canvas(
        root, width=w, height=h,
        bg="white", highlightthickness=0
    )
    canvas.pack()

    cx, cy = w // 2, h // 2
    draw_crosshair(canvas, cx, cy, config)

    # ── Hotkey ───────────────────────────────────────────────
    if config.get("hotkey", True):
        # Hotkey'i ayrı thread'de kur (tkinter mainloop'u bloklamasın)
        t = threading.Thread(target=setup_hotkey, args=(root,), daemon=True)
        t.start()

    # ── Ekran boyutu değişirse crosshair'i yeniden ortala ───
    def on_resize(event):
        nonlocal cx, cy
        cx = root.winfo_screenwidth() // 2
        cy = root.winfo_screenheight() // 2
        draw_crosshair(canvas, cx, cy, config)

    root.bind("<Configure>", on_resize)

    root.mainloop()
    print("[+] Crosshair kapatıldı.")


if __name__ == "__main__":
    main()

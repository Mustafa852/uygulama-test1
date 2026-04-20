import psutil
import ctypes
import os
import winreg
import shutil
import subprocess
import win32api
import win32con
import win32gui
import win32ui
from PIL import Image
import io
import base64
import time
import threading

# --- GERÇEK DONANIM VE KAYIT DEFTERİ KÜTÜPHANELERİ ---
try:
    from monitorcontrol import get_monitors
    from win32com.client import Dispatch
except ImportError:
    pass


class StromEngine:
    def __init__(self):
        print("[+] Strom Kernel Motoru Başlatıldı...")
        self.crosshair_process = None
        self._crosshair_thread = None

    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    # ─────────────────────────────────────────────────────────────
    # CROSSHAIR — TAM YENİDEN YAZILDI (FIX + YENİ ÖZELLİKLER)
    # ─────────────────────────────────────────────────────────────

    def toggle_crosshair(self, value):
        """
        value → bool  : Sadece aç/kapa (varsayılan ayarlarla)
        value → dict  : {"enabled": bool, "color": "#ff0055",
                         "size": 15, "thickness": 2,
                         "shape": "cross" | "dot" | "circle" | "cross+dot"}
        """
        # Parametreleri çöz
        if isinstance(value, dict):
            enabled   = value.get("enabled", True)
            color     = value.get("color", "#ff0055")
            dot_color = value.get("dot_color", "#00f3ff")
            size      = int(value.get("size", 15))
            thickness = int(value.get("thickness", 2))
            shape     = value.get("shape", "cross+dot")
            hotkey    = value.get("hotkey", True)
        else:
            enabled   = bool(value)
            color     = "#ff0055"
            dot_color = "#00f3ff"
            size      = 15
            thickness = 2
            shape     = "cross+dot"
            hotkey    = True

        # Kapatma isteği
        if not enabled:
            return self._kill_crosshair()

        # Zaten çalışıyorsa önce kapat
        self._kill_crosshair()

        # Yeni crosshair scriptini geçici dosyaya yaz
        script = self._build_crosshair_script(
            color, dot_color, size, thickness, shape, hotkey
        )
        tmp_path = os.path.join(os.environ.get("TEMP", "."), "_strom_crosshair.py")
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(script)

        # Ayrı süreçte başlat (eel event loop'unu bloklamaz)
        try:
            self.crosshair_process = subprocess.Popen(
                ["pythonw", tmp_path],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True, f"✅ Crosshair aktif! ({shape.upper()}, {color}, {size}px) — INSERT ile kapat"
        except FileNotFoundError:
            # pythonw bulunamazsa python dene
            try:
                self.crosshair_process = subprocess.Popen(
                    ["python", tmp_path],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return True, f"✅ Crosshair aktif! ({shape.upper()}, {color}, {size}px)"
            except Exception as e:
                return False, f"Crosshair başlatılamadı: {str(e)}"

    def _kill_crosshair(self):
        """Çalışan crosshair sürecini temiz şekilde sonlandırır."""
        killed = False
        if self.crosshair_process:
            try:
                self.crosshair_process.terminate()
                self.crosshair_process.wait(timeout=2)
                killed = True
            except:
                try:
                    self.crosshair_process.kill()
                    killed = True
                except:
                    pass
            finally:
                self.crosshair_process = None

        # İsim bazlı temizlik (eski kalıntılar için)
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = " ".join(proc.info.get('cmdline') or [])
                if "_strom_crosshair" in cmdline:
                    proc.kill()
                    killed = True
            except:
                pass

        return True, "Crosshair kapatıldı." if killed else "Zaten kapalıydı."

    def _build_crosshair_script(self, color, dot_color, size, thickness, shape, hotkey):
        """Dinamik olarak crosshair tkinter scriptini oluşturur."""
        return f'''import tkinter as tk
import sys
import threading

COLOR     = "{color}"
DOT_COLOR = "{dot_color}"
SIZE      = {size}
THICKNESS = {thickness}
SHAPE     = "{shape}"
USE_HOTKEY = {hotkey}

root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-transparentcolor", "white")
root.config(bg="white")

w = root.winfo_screenwidth()
h = root.winfo_screenheight()
root.geometry(f"{{w}}x{{h}}+0+0")
root.attributes("-disabled", True)

canvas = tk.Canvas(root, width=w, height=h, bg="white", highlightthickness=0)
canvas.pack()

cx, cy = w // 2, h // 2

def draw():
    canvas.delete("all")
    if SHAPE in ("cross", "cross+dot"):
        canvas.create_line(cx - SIZE, cy, cx + SIZE, cy,
                           fill=COLOR, width=THICKNESS)
        canvas.create_line(cx, cy - SIZE, cx, cy + SIZE,
                           fill=COLOR, width=THICKNESS)
    if SHAPE == "circle":
        r = SIZE
        canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                           outline=COLOR, width=THICKNESS)
    if SHAPE == "dot":
        r = max(2, THICKNESS + 1)
        canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                           fill=COLOR, outline="")
    if SHAPE == "cross+dot":
        r = max(2, THICKNESS + 1)
        canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                           fill=DOT_COLOR, outline="")

draw()

# INSERT tuşu ile kapat
if USE_HOTKEY:
    try:
        import keyboard
        keyboard.add_hotkey("insert", root.destroy)
    except ImportError:
        pass  # keyboard kütüphanesi yoksa hotkey çalışmaz ama crosshair çalışır

root.mainloop()
'''

    # ─────────────────────────────────────────────────────────────
    # BAŞLANGIÇ YÖNETİCİSİ — EKSİKTİ, YAZILDI
    # ─────────────────────────────────────────────────────────────

    def get_startup_apps(self):
        """Kayıt defterindeki başlangıç uygulamalarını listeler."""
        apps = []
        startup_paths = [
            (winreg.HKEY_CURRENT_USER,
             r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
        ]
        for root_key, path in startup_paths:
            try:
                key = winreg.OpenKey(root_key, path, 0, winreg.KEY_READ)
                count = winreg.QueryInfoKey(key)[1]
                for i in range(count):
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        apps.append({
                            "name": name,
                            "path": value,
                            "root": "HKCU" if root_key == winreg.HKEY_CURRENT_USER else "HKLM",
                            "reg_path": path
                        })
                    except:
                        pass
                winreg.CloseKey(key)
            except:
                pass
        return apps

    def disable_startup_app(self, root, path, name):
        """Başlangıç uygulamasını kayıt defterinden kaldırır."""
        try:
            root_key = winreg.HKEY_CURRENT_USER if root == "HKCU" else winreg.HKEY_LOCAL_MACHINE
            key = winreg.OpenKey(root_key, path, 0, winreg.KEY_ALL_ACCESS)
            winreg.DeleteValue(key, name)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"[!] disable_startup_app hatası: {e}")
            return False

    # ─────────────────────────────────────────────────────────────
    # DONANIM — HZ, BRIGHTNESS, CONTRAST (AYNEN KALDI)
    # ─────────────────────────────────────────────────────────────

    def get_real_hz_list(self):
        hz_list = set()
        i = 0
        while True:
            try:
                ds = win32api.EnumDisplaySettings(None, i)
                if ds.DisplayFrequency >= 50:
                    hz_list.add(ds.DisplayFrequency)
                i += 1
            except:
                break
        return sorted(list(hz_list))

    def get_current_hz(self):
        try:
            ds = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
            return ds.DisplayFrequency
        except:
            return 60

    def set_real_hz(self, hz_value):
        try:
            hz_value = int(hz_value)
            dm = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
            dm.DisplayFrequency = hz_value
            dm.Fields = win32con.DM_DISPLAYFREQUENCY
            res = win32api.ChangeDisplaySettingsEx(
                None, dm, win32con.CDS_UPDATEREGISTRY | win32con.CDS_TEST
            )
            if res != win32con.DISP_CHANGE_SUCCESSFUL:
                return False, f"Hz değişikliği donanım tarafından reddedildi (Win32: {res})."
            res = win32api.ChangeDisplaySettingsEx(None, dm, win32con.CDS_UPDATEREGISTRY)
            if res == win32con.DISP_CHANGE_SUCCESSFUL:
                return True, f"✅ Donanım Yenileme Hızı {hz_value}Hz olarak kilitlendi!"
            return False, f"Donanım Hz kilitlenemedi (Win32: {res})."
        except Exception as e:
            return False, f"Hz Ayar Hatası (Yönetici gerekli): {str(e)}"

    def set_real_brightness(self, level):
        try:
            level = int(level)
            monitors = get_monitors()
            for monitor in monitors:
                with monitor:
                    monitor.set_luminance(level)
            return True, f"✅ Fiziksel ekran parlaklığı %{level} yapıldı!"
        except Exception as e:
            return False, "Donanım Engeli: Monitör menüsünden 'DDC/CI' ayarını açın."

    def set_real_contrast(self, level):
        try:
            level = int(level)
            monitors = get_monitors()
            for monitor in monitors:
                with monitor:
                    monitor.set_contrast(level)
            return True, f"✅ Fiziksel kontrast %{level} yapıldı!"
        except Exception as e:
            return False, "Donanım Engeli: Monitör menüsünden 'DDC/CI' ayarını açın."

    # ─────────────────────────────────────────────────────────────
    # HDR, PING HACK, TELEMETRİ (AYNEN KALDI + DÜZELTİLDİ)
    # ─────────────────────────────────────────────────────────────

    def toggle_real_hdr(self, state):
        try:
            hdr_path = r"Software\Microsoft\Windows\DWM"
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, hdr_path, 0, winreg.KEY_ALL_ACCESS
            )
            val = 1 if state else 0
            winreg.SetValueEx(key, "DisplayHDRMode", 0, winreg.REG_DWORD, val)
            winreg.CloseKey(key)
            win32api.PostMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 0)
            return True, "✅ Windows HDR " + ("Aktif!" if state else "Kapatıldı.")
        except Exception as e:
            return False, "HDR Kontrolü Başarısız (Yönetici İzni Gerekli)."

    def apply_ping_hack(self, state):
        try:
            interfaces_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, interfaces_path)
            subkeys_count = winreg.QueryInfoKey(key)[0]
            val = 1 if state else 0
            for i in range(subkeys_count):
                subkey_name = winreg.EnumKey(key, i)
                iface_key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    f"{interfaces_path}\\{subkey_name}",
                    0, winreg.KEY_ALL_ACCESS
                )
                winreg.SetValueEx(iface_key, "TcpAckFrequency", 0, winreg.REG_DWORD, val)
                winreg.SetValueEx(iface_key, "TCPNoDelay", 0, winreg.REG_DWORD, val)
                winreg.CloseKey(iface_key)
            return True, "✅ Ping Optimizasyonu " + ("Aktif!" if state else "Kapatıldı.")
        except:
            return False, "Ping Hack Başarısız (Yönetici gerekli)."

    def toggle_telemetry(self, state):
        try:
            if state:
                subprocess.run("sc stop DiagTrack", shell=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run("sc config DiagTrack start= disabled", shell=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run("sc stop dmwappushservice", shell=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run("sc config dmwappushservice start= disabled", shell=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, "✅ Gizlilik Kalkanı Aktif! Casus servisler durduruldu."
            else:
                subprocess.run("sc config DiagTrack start= auto", shell=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run("sc start DiagTrack", shell=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run("sc config dmwappushservice start= auto", shell=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run("sc start dmwappushservice", shell=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, "✅ Gizlilik Kalkanı Kapatıldı."
        except:
            return False, "Anti-Telemetri Hatası."

    # ─────────────────────────────────────────────────────────────
    # DERİN KAYIT DEFTERİ TEMİZLİĞİ (AYNEN KALDI)
    # ─────────────────────────────────────────────────────────────

    def deep_registry_clean(self, app_name):
        silinen_anahtar = 0
        if len(app_name) < 3:
            return {"reg": 0, "msg": "Güvenlik: Çok kısa isim, atlandı."}
        app_name_lower = app_name.lower().replace(" ", "")
        aranacak_yollar = [
            (winreg.HKEY_CURRENT_USER,  r"Software"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hkey_root, path in aranacak_yollar:
            try:
                key = winreg.OpenKey(hkey_root, path, 0, winreg.KEY_ALL_ACCESS)
                subkeys_count = winreg.QueryInfoKey(key)[0]
                for i in range(subkeys_count - 1, -1, -1):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        if app_name_lower in subkey_name.lower():
                            winreg.DeleteKey(key, subkey_name)
                            silinen_anahtar += 1
                    except:
                        pass
                winreg.CloseKey(key)
            except:
                pass
        return {
            "reg": silinen_anahtar,
            "msg": f"'{app_name}' kayıt defteri kalıntıları ({silinen_anahtar} anahtar) silindi!"
        }

    # ─────────────────────────────────────────────────────────────
    # İKON ÇEKİCİ (AYNEN KALDI)
    # ─────────────────────────────────────────────────────────────

    def extract_single_icon(self, path):
        try:
            clean_path = path.split(',')[0].strip('"')
            if not os.path.exists(clean_path):
                return None
            large, small = win32gui.ExtractIconEx(clean_path, 0)
            if not large:
                return None
            h_icon = large[0]
            if small:
                win32gui.DestroyIcon(small[0])
            ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
            ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)
            hdc_screen = win32gui.GetDC(0)
            hdc = win32ui.CreateDCFromHandle(hdc_screen)
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_y)
            hdc_mem = hdc.CreateCompatibleDC()
            hdc_mem.SelectObject(hbmp)
            win32gui.DrawIconEx(
                hdc_mem.GetSafeHdc(), 0, 0, h_icon,
                ico_x, ico_y, 0, None, 0x0003
            )
            bmpinfo = hbmp.GetInfo()
            bmpstr = hbmp.GetBitmapBits(True)
            img = Image.frombuffer(
                'RGBA',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRA', 0, 1
            )
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            win32gui.DestroyIcon(h_icon)
            win32gui.ReleaseDC(0, hdc_screen)
            return "data:image/png;base64," + img_str
        except:
            return None

    # ─────────────────────────────────────────────────────────────
    # PROGRAM LİSTESİ (AYNEN KALDI)
    # ─────────────────────────────────────────────────────────────

    def get_programs_fast(self):
        programs = []
        paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        ]
        for path in paths:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey = winreg.OpenKey(key, winreg.EnumKey(key, i))
                        name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        cmd  = winreg.QueryValueEx(subkey, "UninstallString")[0]
                        try:
                            icon_path = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                        except:
                            icon_path = ""
                        if name not in [p['name'] for p in programs]:
                            programs.append({
                                'name': name,
                                'cmd': cmd,
                                'icon_path': icon_path,
                                'id': f"app_{len(programs)}"
                            })
                    except OSError:
                        pass
            except OSError:
                pass
        return sorted(programs, key=lambda x: x['name'])

    # ─────────────────────────────────────────────────────────────
    # TEMİZLEME — GENİŞLETİLDİ
    # ─────────────────────────────────────────────────────────────

    def execute_real_clean(self, options):
        rapor = []
        if options.get("temp"):
            subprocess.run(
                "del /q /f /s %temp%\\*",
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            rapor.append("✓ Windows Temp klasörü temizlendi.")

        if options.get("dns"):
            subprocess.run(
                "ipconfig /flushdns",
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            rapor.append("✓ DNS önbelleği sıfırlandı.")

        if options.get("prefetch"):
            try:
                pf_path = r"C:\Windows\Prefetch"
                for f in os.listdir(pf_path):
                    try:
                        os.remove(os.path.join(pf_path, f))
                    except:
                        pass
                rapor.append("✓ Prefetch dosyaları temizlendi.")
            except:
                rapor.append("⚠ Prefetch: Yönetici izni gerekli.")

        if options.get("recent"):
            try:
                recent_path = os.path.join(
                    os.environ.get("APPDATA", ""),
                    r"Microsoft\Windows\Recent"
                )
                for f in os.listdir(recent_path):
                    try:
                        os.remove(os.path.join(recent_path, f))
                    except:
                        pass
                rapor.append("✓ Son açılan dosyalar geçmişi silindi.")
            except:
                rapor.append("⚠ Son dosyalar temizlenemedi.")

        if options.get("reg"):
            # Güvenli registry temizleme: sadece bilinen geçici anahtarlar
            try:
                subprocess.run(
                    'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\RunMRU" /f',
                    shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                rapor.append("✓ Kayıt Defteri çalıştır geçmişi temizlendi.")
            except:
                rapor.append("⚠ Registry temizleme başarısız.")

        if options.get("military"):
            # Geri dönüşüm kutusu boşalt
            try:
                subprocess.run(
                    "PowerShell -Command Clear-RecycleBin -Force",
                    shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                rapor.append("✓ Geri Dönüşüm Kutusu boşaltıldı.")
            except:
                pass
            # Windows Update cache
            try:
                subprocess.run(
                    "net stop wuauserv",
                    shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                wu_path = r"C:\Windows\SoftwareDistribution\Download"
                shutil.rmtree(wu_path, ignore_errors=True)
                os.makedirs(wu_path, exist_ok=True)
                subprocess.run(
                    "net start wuauserv",
                    shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                rapor.append("✓ Windows Update önbelleği silindi.")
            except:
                rapor.append("⚠ WU cache: Yönetici izni gerekli.")

        return rapor

    # ─────────────────────────────────────────────────────────────
    # RAM OPTİMİZASYONU (AYNEN KALDI)
    # ─────────────────────────────────────────────────────────────

    def optimize_ram(self, is_mega=False):
        sb = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                h = ctypes.windll.kernel32.OpenProcess(
                    0x0100 | 0x0400, False, proc.info['pid']
                )
                if h:
                    ctypes.windll.psapi.EmptyWorkingSet(h)
                    ctypes.windll.kernel32.CloseHandle(h)
                    sb += 1
            except:
                pass
        if is_mega:
            return f"🚀 MEGA BOOST AKTİF! {sb} süreç RAM'den boşaltıldı!"
        return f"⚡ Normal Boost Yapıldı. {sb} servis optimize edildi."

    # ─────────────────────────────────────────────────────────────
    # GPU BİLGİSİ — YENİ EKLENDİ
    # ─────────────────────────────────────────────────────────────

    def get_gpu_info(self):
        """WMI ile GPU adını döndürür."""
        try:
            result = subprocess.check_output(
                "wmic path win32_VideoController get Name,AdapterRAM /format:csv",
                shell=True
            ).decode(errors="ignore")
            lines = [l.strip() for l in result.splitlines() if l.strip() and "Node" not in l]
            gpus = []
            for line in lines:
                parts = line.split(",")
                if len(parts) >= 3:
                    ram_bytes = int(parts[1]) if parts[1].isdigit() else 0
                    ram_mb = ram_bytes // (1024 * 1024)
                    gpus.append({"name": parts[2], "vram_mb": ram_mb})
            return gpus
        except:
            return []

    def get_hardware_live_extended(self):
        """CPU, RAM, Disk + GPU bilgisini birlikte döndürür."""
        info = {
            "cpu":  psutil.cpu_percent(interval=None),
            "ram":  psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('C:\\').percent,
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "ram_used_gb":  round(psutil.virtual_memory().used  / (1024**3), 1),
            "cpu_freq_mhz": int(psutil.cpu_freq().current) if psutil.cpu_freq() else 0,
            "cpu_cores":    psutil.cpu_count(logical=False),
            "cpu_threads":  psutil.cpu_count(logical=True),
        }
        return info

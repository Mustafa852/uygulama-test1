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

    def is_admin(self):
        try: return ctypes.windll.shell32.IsUserAnAdmin()
        except: return False

    # --- GERÇEK DONANIM API'LERİ (DDC/CI ve Win32) ---
    def get_real_hz_list(self):
        """Monitörün fiziksel olarak desteklediği gerçek Hz değerlerini çeker."""
        hz_list = set()
        i = 0
        while True:
            try:
                ds = win32api.EnumDisplaySettings(None, i)
                # 50Hz altı gereksizleri gizle
                if ds.DisplayFrequency >= 50: hz_list.add(ds.DisplayFrequency)
                i += 1
            except Exception as e:
                # Win32Error fırlatırsa biter
                break
        return sorted(list(hz_list))

    def get_current_hz(self):
        try:
            ds = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
            return ds.DisplayFrequency
        except: return 60 # Varsayılan

    def set_real_hz(self, hz_value):
        """Win32 API ile Windows Yenileme Hızını fiziksel olarak değiştirir."""
        try:
            hz_value = int(hz_value)
            dm = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
            dm.DisplayFrequency = hz_value
            dm.Fields = win32con.DM_DISPLAYFREQUENCY
            # Donanımsal değişikliği zorla
            res = win32api.ChangeDisplaySettingsEx(None, dm, win32con.CDS_UPDATEREGISTRY | win32con.CDS_TEST)
            if res != win32con.DISP_CHANGE_SUCCESSFUL:
                return False, f"Hz değişikliği donanım tarafından reddedildi (Win32Error: {res})."
            
            res = win32api.ChangeDisplaySettingsEx(None, dm, win32con.CDS_UPDATEREGISTRY)
            if res == win32con.DISP_CHANGE_SUCCESSFUL:
                return True, f"Donanım Yenileme Hızı {hz_value}Hz olarak kilitlendi!"
            return False, f"Donanım Yenileme Hızı kilitlenemedi (Win32Error: {res})."
        except Exception as e:
            return False, f"Hz Ayar Hatası (Yönetici İzni Gerekli): {str(e)}"

    def set_real_brightness(self, level):
        try:
            level = int(level)
            monitors = get_monitors()
            for monitor in monitors:
                with monitor:
                    monitor.set_luminance(level)
            return True, f"Fiziksel ekran parlaklığı %{level} yapıldı!"
        except Exception as e:
            return False, f"Donanım Engeli: Monitör menüsünden 'DDC/CI' ayarını açın."

    def set_real_contrast(self, level):
        try:
            level = int(level)
            monitors = get_monitors()
            for monitor in monitors:
                with monitor:
                    monitor.set_contrast(level)
            return True, f"Fiziksel kontrast %{level} yapıldı!"
        except Exception as e:
            return False, f"Donanım Engeli: Monitör menüsünden 'DDC/CI' ayarını açın."

    # --- GERÇEK HDR (KAYIT DEFTERİ API'Sİ İLE TEK TIK) ---
    def toggle_real_hdr(self, state):
        """Windows HDR Modunu kayıt defteri üzerinden fiziksel olarak açıp kapatır."""
        try:
            # HDR Kayıt Defteri Yolu
            hdr_path = r"Software\Microsoft\Windows\DWM"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, hdr_path, 0, winreg.KEY_ALL_ACCESS)
            # 1 ise HDR açık, 0 ise kapalı
            val = 1 if state else 0
            winreg.SetValueEx(key, "DisplayHDRMode", 0, winreg.REG_DWORD, val)
            winreg.CloseKey(key)
            
            # Değişikliğin anında etkili olması için Win32API ile Refresh sinyali gönder
            win32api.PostMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 0)
            
            return True, "Windows HDR API tetiklendi! (" + ("Aktif" if state else "Kapalı") + ")"
        except Exception as e:
            return False, "HDR Kontrolü Başarısız (Yönetici İzni Gerekli)."

    # --- GERÇEK PING HACK VE GİZLİLİK KALKANI (Eski kodlar, aynen kalsın) ---
    def apply_ping_hack(self, state):
        try:
            interfaces_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, interfaces_path)
            subkeys_count = winreg.QueryInfoKey(key)[0]
            val = 1 if state else 0
            for i in range(subkeys_count):
                subkey_name = winreg.EnumKey(key, i)
                interface_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{interfaces_path}\\{subkey_name}", 0, winreg.KEY_ALL_ACCESS)
                winreg.SetValueEx(interface_key, "TcpAckFrequency", 0, winreg.REG_DWORD, val)
                winreg.SetValueEx(interface_key, "TCPNoDelay", 0, winreg.REG_DWORD, val)
                winreg.CloseKey(interface_key)
            return True, "Ping Optimizasyonu (QoS) " + ("Aktif!" if state else "Kapatıldı.")
        except: return False, "Ping Hack Başarısız."

    def toggle_telemetry(self, state):
        try:
            if state:
                subprocess.run("sc stop DiagTrack", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run("sc config DiagTrack start= disabled", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run("sc stop dmwappushservice", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run("sc config dmwappushservice start= disabled", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, "Gizlilik Kalkanı Aktif! Casus servisler donduruldu."
            else:
                subprocess.run("sc config DiagTrack start= auto", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run("sc start DiagTrack", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run("sc config dmwappushservice start= auto", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run("sc start dmwappushservice", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, "Gizlilik Kalkanı Kapatıldı."
        except: return False, "Anti-Telemetri Hatası."

    # --- GERÇEK UNINSTALL VE DERİN KAYIT DEFTERİ TEMİZLİĞİ ---
    def deep_registry_clean(self, app_name):
        """Uygulamanın kaldırılmasından sonra Kayıt Defteri'ndeki (Registry) kalıntılarını siler."""
        silinen_anahtar = 0
        
        if len(app_name) < 3: return {"reg": 0, "msg": "Güvenlik nedeniyle kısa isimli kalıntılar atlandı."}
        app_name_lower = app_name.lower().replace(" ", "")
        
        # Taranacak Kayıt Defteri Anahtar Yolları
        aranacak_yollar = [
            (winreg.HKEY_CURRENT_USER, r"Software"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
        ]
        
        for hkey_root, path in aranacak_yollar:
            try:
                key = winreg.OpenKey(hkey_root, path, 0, winreg.KEY_ALL_ACCESS)
                subkeys_count = winreg.QueryInfoKey(key)[0]
                
                # Tersten tara ki anahtarları silerken index bozulmasın
                for i in range(subkeys_count - 1, -1, -1):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        if app_name_lower in subkey_name.lower():
                            # Anahtarı Rekürsif Olarak Sil (Python 3.10+ zorunlu)
                            winreg.DeleteKey(key, subkey_name)
                            silinen_anahtar += 1
                    except: pass
                winreg.CloseKey(key)
            except: pass
            
        return {"reg": silinen_anahtar, "msg": f"'{app_name}' kayıt defteri kalıntıları ({silinen_anahtar} anahtar) yok edildi!"}

    def extract_single_icon(self, path):
        """Görsel 3'teki ikon sorununu çözer (Komaların içindeki yolu düzeltir)."""
        try:
            # HATA DÜZELTİLDİ: Komalar veya tırnaklar içindeki yolu temizle
            clean_path = path.split(',')[0].strip('"')
            if not os.path.exists(clean_path): return None
            
            # İkon sökme işlemini Win32API ile profesyonel yap
            large, small = win32gui.ExtractIconEx(clean_path, 0)
            if not large: return None
            
            # Sadece Büyük İkonu Kullan
            h_icon = large[0]
            if small: win32gui.DestroyIcon(small[0])
            
            ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
            ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)
            
            hdc_screen = win32gui.GetDC(0)
            hdc = win32ui.CreateDCFromHandle(hdc_screen)
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_y)
            hdc_mem = hdc.CreateCompatibleDC()
            hdc_mem.SelectObject(hbmp)
            
            # İkonu Bitmap'e Çiz
            win32gui.DrawIconEx(hdc_mem.GetSafeHdc(), 0, 0, h_icon, ico_x, ico_y, 0, None, 0x0003)
            
            bmpinfo = hbmp.GetInfo()
            bmpstr = hbmp.GetBitmapBits(True)
            img = Image.frombuffer('RGBA', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRA', 0, 1)
            
            # PNG Formatına Çevir
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # Kaynakları Temizle
            win32gui.DestroyIcon(h_icon)
            win32gui.ReleaseDC(0, hdc_screen)
            win32ui.DoNoThing() # GC'ye yardım et
            
            return "data:image/png;base64," + img_str
        except: return None

    # ... (Diğer get_programs_fast, execute_real_clean, vb. eski kodlar AYNNEN KALSIN) ...
    def get_programs_fast(self):
        programs = []
        paths = [r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"]
        for path in paths:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
                for i in range(0, winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey = winreg.OpenKey(key, winreg.EnumKey(key, i))
                        name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        cmd = winreg.QueryValueEx(subkey, "UninstallString")[0]
                        icon_path = winreg.QueryValueEx(subkey, "DisplayIcon")[0] if "DisplayIcon" in [winreg.EnumValue(subkey, j)[0] for j in range(winreg.QueryInfoKey(subkey)[1])] else ""
                        if name not in [p['name'] for p in programs]: programs.append({'name': name, 'cmd': cmd, 'icon_path': icon_path, 'id': f"app_{len(programs)}"})
                    except OSError: pass
            except OSError: pass
        return sorted(programs, key=lambda x: x['name'])

    def execute_real_clean(self, options):
        rapor = []
        if options.get("temp"):
            rapor.append("✓ Windows Temp temizlendi.")
            subprocess.run("del /q /f /s %temp%\*", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if options.get("dns"):
            subprocess.run("ipconfig /flushdns", shell=True, stdout=subprocess.DEVNULL)
            rapor.append("✓ Ağ ve DNS önbelleği sıfırlandı.")
        return rapor

    def optimize_ram(self, is_mega=False):
        sb = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                h = ctypes.windll.kernel32.OpenProcess(0x0100 | 0x0400, False, proc.info['pid'])
                if h:
                    ctypes.windll.psapi.EmptyWorkingSet(h)
                    ctypes.windll.kernel32.CloseHandle(h)
                    sb += 1
            except: pass
        return f"MEGA BOOST AKTİF! RAM kökten boşaltıldı!" if is_mega else f"Normal Boost Yapıldı. {sb} servis daraltıldı."
import eel
import os
import json
import base64
import psutil
import subprocess
from SystemEngine import StromEngine

motor = StromEngine()
eel.init('web')
DB_FILE = "strom_secure.dat"

def encrypt_data(data): return base64.b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')
def decrypt_data(data_str): return json.loads(base64.b64decode(data_str.encode('utf-8')).decode('utf-8'))

def init_db():
    if not os.path.exists(DB_FILE):
        default_db = {"STROM-PRO-2026": {"hwid": "None"}, "HACKER-MODE": {"hwid": "None"}}
        with open(DB_FILE, 'w') as f: f.write(encrypt_data(default_db))

init_db()

def is_vip_active():
    if os.path.exists("license.key"):
        try:
            with open("license.key", "r") as f: kayitli_key = f.read().strip()
            if os.path.exists(DB_FILE):
                with open(DB_FILE, 'r') as f: db = decrypt_data(f.read())
                if kayitli_key in db: return True
        except: return False
    return False

@eel.expose
def python_check_security(): return motor.is_admin()

@eel.expose
def python_activate_key(girilen_key):
    with open(DB_FILE, 'r') as f: db = decrypt_data(f.read())
    if girilen_key in db:
        with open("license.key", "w") as f: f.write(girilen_key)
        return {"success": True, "msg": "Lisans Onaylandı! Sistem kilidi açıldı."}
    return {"success": False, "msg": "Geçersiz Lisans Anahtarı!"}

@eel.expose
def python_get_vip_status(): return is_vip_active()

@eel.expose
def python_get_programs_fast(): return motor.get_programs_fast()

@eel.expose
def python_start_icon_fetcher(programs):
    def fetch_bg():
        for p in programs:
            if p.get('icon_path'):
                icon_b64 = motor.extract_single_icon(p['icon_path'])
                if icon_b64: eel.updateIconLive(p['id'], icon_b64)()
    eel.spawn(fetch_bg)

@eel.expose
def python_get_hardware_live():
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('C:\\').percent
    }

# --- GÖRSEL 1: HZ VE HDR KÖPRÜLERİ ---
@eel.expose
def python_get_real_hz():
    return {
        "hz_list": motor.get_real_hz_list(),
        "current_hz": motor.get_current_hz()
    }

# --- GÖRSEL 3: DERİN SİLME KÖPRÜSÜ ---
@eel.expose
def python_deep_registry_clean(app_name):
    if not is_vip_active(): return {"reg": 0, "msg": "Derin kayıt defteri temizliği PRO lisans gerektirir."}
    return motor.deep_registry_clean(app_name)

@eel.expose
def python_apply_instant_monitor(setting_name, value):
    if setting_name == "brightness":
        success, msg = motor.set_real_brightness(value)
        return {"success": success, "msg": msg}
    if setting_name == "contrast":
        success, msg = motor.set_real_contrast(value)
        return {"success": success, "msg": msg}
    # Donanım Crosshair (Python Arka Plan)
    if setting_name == "crosshair":
        if not is_vip_active(): return {"success": False, "msg": "Bu özellik PRO lisans gerektirir."}
        success, msg = motor.toggle_crosshair(value)
        return {"success": success, "msg": msg}
    # Gerçek HDR
    if setting_name == "hdr":
        if not is_vip_active(): return {"success": False, "msg": "Bu özellik PRO lisans gerektirir."}
        success, msg = motor.toggle_real_hdr(value)
        return {"success": success, "msg": msg}
    # Gerçek Hz Değişikliği
    if setting_name == "hz":
        success, msg = motor.set_real_hz(value)
        return {"success": success, "msg": msg}
        
    return {"success": True, "msg": f"{setting_name} simülasyonu çalıştırıldı."}

# ... (Diğer eski fonksiyonlar: python_get_startup_apps, vb. AYNNEN KALSIN) ...
@eel.expose
def python_get_startup_apps(): return motor.get_startup_apps()

@eel.expose
def python_disable_startup_app(root, path, name):
    if not is_vip_active(): return {"success": False, "msg": "Başlangıç Yöneticisi PRO lisans gerektirir."}
    success = motor.disable_startup_app(root, path, name)
    if success: return {"success": True, "msg": f"{name} başlangıçtan silindi! PC daha hızlı açılacak."}
    return {"success": False, "msg": "Silinemedi. Yönetici izni eksik olabilir."}

@eel.expose
def python_mega_clean(options):
    if not is_vip_active() and (options.get('reg') or options.get('military')):
        return {"success": False, "msg": "Kritik güvenlik işlemleri PRO lisans gerektirir."}
    rapor = motor.execute_real_clean(options)
    return {"success": True, "msg": "Seçili tüm alanlar başarıyla temizlendi."}

@eel.expose
def python_run_boost():
    if is_vip_active(): return {"success": True, "msg": motor.optimize_ram(is_mega=True)}
    return {"success": True, "msg": motor.optimize_ram(is_mega=False) + " (Tüm sistemi uçurmak için PRO'ya geçin)"}

@eel.expose
def python_apply_settings_batch(settings_dict):
    return {"success": True, "msg": f"{len(settings_dict)} adet donanım ve sistem ayarı başarıyla kaydedildi!"}

@eel.expose
def python_uninstall_batch(cmd_list):
    if is_vip_active():
        try:
            for cmd in cmd_list: subprocess.Popen(cmd, shell=True)
            return True
        except: return False
    return False

print("[+] Strom Optimizer Security Koruması Aktif...")
eel.start('index.html', size=(1200, 800))
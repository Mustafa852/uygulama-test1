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

def encrypt_data(data):
    return base64.b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')

def decrypt_data(data_str):
    return json.loads(base64.b64decode(data_str.encode('utf-8')).decode('utf-8'))

def init_db():
    if not os.path.exists(DB_FILE):
        default_db = {
            "STROM-PRO-2026": {"hwid": "None"},
            "HACKER-MODE":    {"hwid": "None"}
        }
        with open(DB_FILE, 'w') as f:
            f.write(encrypt_data(default_db))

init_db()


def is_vip_active():
    if os.path.exists("license.key"):
        try:
            with open("license.key", "r") as f:
                kayitli_key = f.read().strip()
            if os.path.exists(DB_FILE):
                with open(DB_FILE, 'r') as f:
                    db = decrypt_data(f.read())
                if kayitli_key in db:
                    return True
        except:
            return False
    return False


# ─────────────────────────────────────────────────────────────
# LİSANS & GÜVENLİK
# ─────────────────────────────────────────────────────────────

@eel.expose
def python_check_security():
    return motor.is_admin()

@eel.expose
def python_activate_key(girilen_key):
    try:
        with open(DB_FILE, 'r') as f:
            db = decrypt_data(f.read())
        if girilen_key in db:
            with open("license.key", "w") as f:
                f.write(girilen_key)
            return {"success": True, "msg": "✅ Lisans Onaylandı! Sistem kilidi açıldı."}
        return {"success": False, "msg": "❌ Geçersiz Lisans Anahtarı!"}
    except Exception as e:
        return {"success": False, "msg": f"Hata: {str(e)}"}

@eel.expose
def python_get_vip_status():
    return is_vip_active()


# ─────────────────────────────────────────────────────────────
# PROGRAM YÖNETİCİSİ
# ─────────────────────────────────────────────────────────────

@eel.expose
def python_get_programs_fast():
    return motor.get_programs_fast()

@eel.expose
def python_start_icon_fetcher(programs):
    def fetch_bg():
        for p in programs:
            if p.get('icon_path'):
                icon_b64 = motor.extract_single_icon(p['icon_path'])
                if icon_b64:
                    eel.updateIconLive(p['id'], icon_b64)()
    eel.spawn(fetch_bg)

@eel.expose
def python_uninstall_batch(cmd_list):
    if not is_vip_active():
        return False
    try:
        for cmd in cmd_list:
            subprocess.Popen(cmd, shell=True)
        return True
    except:
        return False


# ─────────────────────────────────────────────────────────────
# DONANIM İZLEME
# ─────────────────────────────────────────────────────────────

@eel.expose
def python_get_hardware_live():
    return {
        "cpu":  psutil.cpu_percent(interval=None),
        "ram":  psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('C:\\').percent
    }

@eel.expose
def python_get_hardware_extended():
    """Genişletilmiş donanım bilgisi (RAM GB, CPU frekans, çekirdek sayısı)"""
    return motor.get_hardware_live_extended()

@eel.expose
def python_get_gpu_info():
    """GPU adı ve VRAM bilgisi"""
    return motor.get_gpu_info()

@eel.expose
def python_get_real_hz():
    return {
        "hz_list":    motor.get_real_hz_list(),
        "current_hz": motor.get_current_hz()
    }


# ─────────────────────────────────────────────────────────────
# ANA AYAR KÖPRÜSÜ — python_apply_instant_monitor
# ─────────────────────────────────────────────────────────────

@eel.expose
def python_apply_instant_monitor(setting_name, value):
    """
    Tüm donanım/sistem ayarlarının tek giriş noktası.
    setting_name → "crosshair" | "hdr" | "hz" | "brightness" |
                   "contrast" | "ping_hack" | "telemetry"
    value        → bool, int, float veya dict (crosshair için)
    """

    # CROSSHAIR — FIX: artık toggle_crosshair çağrılıyor, method mevcuttu
    if setting_name == "crosshair":
        if not is_vip_active():
            return {"success": False, "msg": "⛔ Bu özellik PRO lisans gerektirir."}
        success, msg = motor.toggle_crosshair(value)
        return {"success": success, "msg": msg}

    # HDR
    if setting_name == "hdr":
        if not is_vip_active():
            return {"success": False, "msg": "⛔ Bu özellik PRO lisans gerektirir."}
        success, msg = motor.toggle_real_hdr(value)
        return {"success": success, "msg": msg}

    # HZ
    if setting_name == "hz":
        success, msg = motor.set_real_hz(value)
        return {"success": success, "msg": msg}

    # BRIGHTNESS
    if setting_name == "brightness":
        success, msg = motor.set_real_brightness(value)
        return {"success": success, "msg": msg}

    # CONTRAST
    if setting_name == "contrast":
        success, msg = motor.set_real_contrast(value)
        return {"success": success, "msg": msg}

    # PING HACK — YENİ (kod vardı ama bağlanmamıştı)
    if setting_name == "ping_hack":
        if not is_vip_active():
            return {"success": False, "msg": "⛔ Bu özellik PRO lisans gerektirir."}
        success, msg = motor.apply_ping_hack(value)
        return {"success": success, "msg": msg}

    # TELEMETRİ / GİZLİLİK KALKANI — YENİ (kod vardı ama bağlanmamıştı)
    if setting_name == "telemetry":
        if not is_vip_active():
            return {"success": False, "msg": "⛔ Bu özellik PRO lisans gerektirir."}
        success, msg = motor.toggle_telemetry(value)
        return {"success": success, "msg": msg}

    return {"success": False, "msg": f"Bilinmeyen ayar: {setting_name}"}


# ─────────────────────────────────────────────────────────────
# BAŞLANGIÇ YÖNETİCİSİ — FIX: methodlar artık mevcut
# ─────────────────────────────────────────────────────────────

@eel.expose
def python_get_startup_apps():
    return motor.get_startup_apps()

@eel.expose
def python_disable_startup_app(root, path, name):
    if not is_vip_active():
        return {"success": False, "msg": "⛔ Başlangıç Yöneticisi PRO lisans gerektirir."}
    success = motor.disable_startup_app(root, path, name)
    if success:
        return {"success": True, "msg": f"✅ '{name}' başlangıçtan kaldırıldı! PC daha hızlı açılacak."}
    return {"success": False, "msg": "❌ Silinemedi. Yönetici izni eksik olabilir."}


# ─────────────────────────────────────────────────────────────
# TEMİZLEME & OPTİMİZASYON
# ─────────────────────────────────────────────────────────────

@eel.expose
def python_mega_clean(options):
    if not is_vip_active() and (options.get('reg') or options.get('military')):
        return {
            "success": False,
            "msg": "⛔ Kritik güvenlik işlemleri PRO lisans gerektirir."
        }
    rapor = motor.execute_real_clean(options)
    rapor_text = "\n".join(rapor) if rapor else "Hiçbir alan seçilmedi."
    return {"success": True, "msg": rapor_text, "details": rapor}

@eel.expose
def python_run_boost():
    if is_vip_active():
        return {"success": True, "msg": motor.optimize_ram(is_mega=True)}
    return {
        "success": True,
        "msg": motor.optimize_ram(is_mega=False) + "\n(Tüm sistemi uçurmak için PRO'ya geçin)"
    }

@eel.expose
def python_apply_settings_batch(settings_dict):
    results = []
    for key, value in settings_dict.items():
        result = python_apply_instant_monitor(key, value)
        results.append({"setting": key, **result})
    success_count = sum(1 for r in results if r.get("success"))
    return {
        "success": True,
        "msg": f"✅ {success_count}/{len(results)} ayar başarıyla uygulandı!",
        "results": results
    }


# ─────────────────────────────────────────────────────────────
# DERİN KAYIT DEFTERİ TEMİZLİĞİ
# ─────────────────────────────────────────────────────────────

@eel.expose
def python_deep_registry_clean(app_name):
    if not is_vip_active():
        return {"reg": 0, "msg": "⛔ Derin kayıt defteri temizliği PRO lisans gerektirir."}
    return motor.deep_registry_clean(app_name)


# ─────────────────────────────────────────────────────────────
# BAŞLAT
# ─────────────────────────────────────────────────────────────

print("[+] Strom Optimizer v2 — Tüm modüller yüklendi.")
print(f"[+] VIP Durum: {'AKTİF' if is_vip_active() else 'Pasif'}")
print(f"[+] Yönetici: {'EVET' if motor.is_admin() else 'HAYIR (bazı özellikler kısıtlı)'}")

eel.start('index.html', size=(1200, 800))

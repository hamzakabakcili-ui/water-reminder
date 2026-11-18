#!/usr/bin/env python3
"""Su Hatırlatıcı — mesai boyunca su içmeyi ve termosu doldurmayı hatırlatır.

Sadece Python 3 + macOS (osascript) kullanır, ek kurulum gerekmez.

Kullanım:
    python3 su_hatirlatici.py                    # çalıştır
    python3 su_hatirlatici.py --test             # hemen bir hatırlatma göster
    python3 su_hatirlatici.py --install-autostart  # oturum açılınca otomatik başlat
    python3 su_hatirlatici.py --ayarla           # hedef, saat aralığı, termos/bardak boyu seç
    python3 su_hatirlatici.py --skip-today       # sadece bugün için sustur
    python3 su_hatirlatici.py --uninstall-autostart
"""
import datetime as dt
import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

# ---- Varsayılan ayarlar (kullanıcı --ayarla ile değiştirebilir) -------------
START = dt.time(9, 30)       # iş başı
END = dt.time(18, 0)         # iş bitişi
GOAL_ML = 2500               # günlük hedef
SIP_ML = 150                 # her hatırlatmada içilecek miktar
DEFAULT_SIP_ML = SIP_ML
INTERVAL_MIN = 30            # hatırlatma aralığı
SNOOZE_MIN = 5               # "Ertele" süresi
THERMOS_ML = 500             # termos hacmi
DIALOG_TIMEOUT_S = 90        # cevap verilmezse pencere kapanır, ertelenir
# ---------------------------------------------------------------------------
DEFAULTS = {"start": START.strftime("%H:%M"), "end": END.strftime("%H:%M"),
            "goal_ml": GOAL_ML, "vessel_ml": THERMOS_ML}

POPUP_JS = Path(__file__).resolve().parent / "popup.js"
STATE_FILE = Path.home() / ".su_hatirlatici.json"
SETTINGS_FILE = Path.home() / ".su_hatirlatici_ayar.json"
PLIST = Path.home() / "Library/LaunchAgents/local.su-hatirlatici.plist"
LABEL = "local.su-hatirlatici"


def parse_hhmm(text):
    try:
        return dt.datetime.strptime(text.strip(), "%H:%M").time()
    except ValueError:
        raise ValueError("Saat HH:MM biçiminde olmalı (örn. 09:30): %r" % text)


def validate(cfg):
    """Ayarları doğrular; geçersizse Türkçe mesajlı ValueError fırlatır."""
    start, end = parse_hhmm(cfg["start"]), parse_hhmm(cfg["end"])
    if start >= end:
        raise ValueError("Başlangıç saati bitişten önce olmalı.")
    if not 500 <= cfg["goal_ml"] <= 6000:
        raise ValueError("Günlük hedef 0,5 ile 6 litre arasında olmalı.")
    if not 100 <= cfg["vessel_ml"] <= 2000:
        raise ValueError("Termos/bardak 100 ile 2000 ml arasında olmalı.")
    return cfg


def load_settings():
    """Kayıtlı ayarları döndürür; dosya yok ya da bozuksa varsayılanlar."""
    cfg = dict(DEFAULTS)
    try:
        cfg.update(json.loads(SETTINGS_FILE.read_text()))
        return validate(cfg)
    except (OSError, ValueError, KeyError, TypeError):
        return dict(DEFAULTS)


def apply_settings():
    """Ayarları modül sabitlerine uygular. Aralık, hedefe mesai bitmeden
    ulaşılacak şekilde hesaplanır (varsayılanda 17 hatırlatma = 30 dk)."""
    global START, END, GOAL_ML, THERMOS_ML, SIP_ML, INTERVAL_MIN
    cfg = load_settings()
    START, END = parse_hhmm(cfg["start"]), parse_hhmm(cfg["end"])
    GOAL_ML, THERMOS_ML = cfg["goal_ml"], cfg["vessel_ml"]
    SIP_ML = min(DEFAULT_SIP_ML, THERMOS_ML)
    span = (END.hour - START.hour) * 60 + END.minute - START.minute
    INTERVAL_MIN = max(10, min(60, span // math.ceil(GOAL_ML / SIP_ML)))


def configure(args):
    """--ayarla: bayraklarla ya da (bayrak yoksa) sorularla ayarları kaydeder."""
    ap = argparse.ArgumentParser(prog="su_hatirlatici.py --ayarla")
    ap.add_argument("--hedef-litre", type=float, help="günlük hedef, litre (örn. 2.5)")
    ap.add_argument("--baslangic", help="mesai başı, HH:MM")
    ap.add_argument("--bitis", help="mesai sonu, HH:MM")
    ap.add_argument("--kap-ml", type=int, help="termos/bardak hacmi, ml")
    a = ap.parse_args(args)
    cfg = load_settings()
    if not any(v is not None for v in vars(a).values()):
        def ask_in(label, cur):
            return input("%s [%s]: " % (label, cur)).strip().replace(",", ".")
        v = ask_in("Günlük hedef (litre)", cfg["goal_ml"] / 1000)
        a.hedef_litre = float(v) if v else None
        a.baslangic = ask_in("Başlangıç saati (SS:DD)", cfg["start"]) or None
        a.bitis = ask_in("Bitiş saati (SS:DD)", cfg["end"]) or None
        v = ask_in("Termos/bardak hacmi (ml)", cfg["vessel_ml"])
        a.kap_ml = int(float(v)) if v else None
    if a.hedef_litre is not None:
        cfg["goal_ml"] = int(round(a.hedef_litre * 1000))
    if a.baslangic:
        cfg["start"] = a.baslangic.strip()
    if a.bitis:
        cfg["end"] = a.bitis.strip()
    if a.kap_ml is not None:
        cfg["vessel_ml"] = a.kap_ml
    try:
        validate(cfg)
    except ValueError as e:
        print("Hata:", e)
        sys.exit(1)
    SETTINGS_FILE.write_text(json.dumps(cfg))
    apply_settings()
    print("Kaydedildi: hedef %.1f L, %s–%s, kap %d ml, ~%d dakikada bir hatırlatma."
          % (GOAL_ML / 1000, START.strftime("%H:%M"), END.strftime("%H:%M"),
             THERMOS_ML, INTERVAL_MIN))
    print("Çalışan hatırlatıcı yeni ayarı birkaç saniye içinde otomatik alır.")


def load_state():
    today = dt.date.today().isoformat()
    try:
        s = json.loads(STATE_FILE.read_text())
        if s.get("date") == today:
            return s
    except (OSError, ValueError):
        pass
    return {"date": today, "drunk": 0, "thermos": 0}  # sabah termos boş varsayılır


def save_state(s):
    try:
        STATE_FILE.write_text(json.dumps(s))
    except OSError:
        pass


def ask(message, buttons, default, theme="su", timeout=None):
    """Sağ altta bildirim kartı (popup.js). Seçilen butonu döndürür, zaman aşımında None.

    theme: "su" (mavi), "doldur" (turuncu), "ozet" (yeşil). `default` artık kullanılmıyor
    (pencere klavye odağı almadığı için Enter ile seçim yok).
    """
    r = subprocess.run(
        ["osascript", "-l", "JavaScript", str(POPUP_JS), theme, message,
         str(timeout or DIALOG_TIMEOUT_S)] + buttons,
        capture_output=True, text=True)
    return r.stdout.strip() or None


def fmt_l(ml):
    """Litre gösterimi; 50 ml'lik adımlar yuvarlanıp yanıltmasın diye gerekirse 2 ondalık (0.85)."""
    return ("%.1f" if ml % 100 == 0 else "%.2f") % (ml / 1000)


def progress(s):
    return "Bugün: %s / %s L" % (fmt_l(s["drunk"]), fmt_l(GOAL_ML))


def next_sip(thermos):
    """Bu hatırlatmada içilecek miktar. Termosta bir sonraki yudumluk kalmayacaksa
    kalanın hepsi içilir; böylece termos tam 3 hatırlatmada biter (150+150+200)."""
    return thermos if thermos - SIP_ML < SIP_ML else SIP_ML


def remind(s):
    """Bir hatırlatma gösterir. True dönerse içildi, False ise ertelendi."""
    s["thermos"] = min(s["thermos"], THERMOS_ML)  # kap küçüldüyse
    need_fill = s["thermos"] < SIP_ML
    if need_fill:
        msg = "Termos bitti!\nSebilden doldur ve su iç.\n\n" + progress(s)
        choice = ask(msg, ["Ertele", "Doldurdum, içtim"], "Doldurdum, içtim", "doldur")
        if choice == "Doldurdum, içtim":
            s["drunk"] += s["thermos"]  # kalan azıcık su da içilmiş sayılır
            s["thermos"] = THERMOS_ML
        else:
            return False
    else:
        sip = next_sip(s["thermos"])
        msg = "Birkaç yudum su iç (~%d ml).\nTermosta şu an ~%d ml var, içince ~%d kalır.\n\n%s" % (
            sip, s["thermos"], s["thermos"] - sip, progress(s))
        if ask(msg, ["Ertele", "İçtim"], "İçtim") != "İçtim":
            return False
    sip = next_sip(s["thermos"])
    s["thermos"] -= sip
    s["drunk"] += sip
    save_state(s)
    return True


def is_workday(now):
    return now.weekday() < 5  # 0=Pazartesi ... 4=Cuma


def in_hours(now):
    return is_workday(now) and START <= now.time() < END


def next_start(now):
    """Bir sonraki iş günü başlangıcı (bugün henüz başlamadıysa bugün)."""
    day = now.date()
    if not is_workday(now) or now.time() >= START:
        day += dt.timedelta(days=1)
    while day.weekday() >= 5:
        day += dt.timedelta(days=1)
    return dt.datetime.combine(day, START)


def run(test=False):
    apply_settings()
    s = load_state()
    if test:
        remind(s)
        return
    due = dt.datetime.now()
    summary_day = None
    while True:
        now = dt.datetime.now()
        apply_settings()  # --ayarla ile yapılan değişiklik yeniden başlatmadan geçerli olur
        s = load_state()  # her turda oku: --skip-today dışarıdan yazabilir
        if s.get("skip"):
            due = next_start(now)
            summary_day = s["date"]  # bugünün özeti de gösterilmesin
        elif in_hours(now):
            if now >= due and s["drunk"] < GOAL_ML:
                drank = remind(s)
                delay = INTERVAL_MIN if drank else SNOOZE_MIN
                due = dt.datetime.now() + dt.timedelta(minutes=delay)
        else:
            if is_workday(now) and now.time() >= END and summary_day != s["date"]:
                summary_day = s["date"]
                ok = s["drunk"] >= GOAL_ML
                ask("%s\n\n%s" % ("Hedefe ulaştın, aferin!" if ok
                                  else "Hedefe ulaşamadın\nAkşam biraz daha su iç.",
                                  progress(s)), ["Tamam"], "Tamam", "ozet" if ok else "su")
            due = next_start(now)
        time.sleep(20)


def skip_today():
    s = load_state()
    s["skip"] = True
    save_state(s)
    print("Bugün için hatırlatmalar kapatıldı.")


SETUP_POOLS = {  # kurulum sorularında önerilen seçenekler (varsayılan ayrıca eklenir)
    "goal":   ["2", "3", "3.5", "4"],
    "start":  ["08:00", "08:30", "09:00", "10:00"],
    "end":    ["17:00", "17:30", "18:30", "19:00"],
    "vessel": ["330", "750", "1000", "400"],
}


def first_run_setup():
    """İlk kurulumda ayarları sağ alttaki bildirim kartlarıyla sorar (fareyle seçilir) ve kaydeder.
    Tamamlanırsa True; cevaplanmazsa False (varsayılanlar kalır)."""
    cfg = load_settings()
    steps = [  # (anahtar, başlık, açıklama, birim eki, mevcut değer)
        ("goal", "Günlük su hedefin?", "Bir günde kaç litre içmek istiyorsun?", " L",
         ("%g" % (cfg["goal_ml"] / 1000))),
        ("start", "Mesain kaçta başlıyor?", "İlk hatırlatma bu saatte gelir.", "", cfg["start"]),
        ("end", "Mesain kaçta bitiyor?", "Hatırlatmalar bu saate kadar sürer.", "", cfg["end"]),
        ("vessel", "Termosun / bardağın hacmi?", "Her doldurmada kaç ml su alıyorsun?", " ml",
         str(cfg["vessel_ml"])),
    ]
    chosen = {}
    for n, (key, title, hint, unit, default) in enumerate(steps, 1):
        alts = sorted([c for c in SETUP_POOLS[key] if c != default][:3],
                      key=lambda c: float(c.replace(":", ".")))
        mark = "✓ " + default + unit
        msg = "%s\n%s Beyaz buton önerilen değerdir.\nAdım: %d / %d" % (title, hint, n, len(steps))
        r = ask(msg, [a + unit for a in alts] + [mark], None, theme="kurulum", timeout=300)
        if r is None:
            return False
        chosen[key] = default if r == mark else r[:len(r) - len(unit)] if unit else r
    try:
        new = dict(cfg, goal_ml=int(round(float(chosen["goal"]) * 1000)),
                   start=chosen["start"], end=chosen["end"], vessel_ml=int(chosen["vessel"]))
        validate(new)
    except ValueError:
        return False
    SETTINGS_FILE.write_text(json.dumps(new))
    return True


def ensure_first_run_setup():
    """Ayar dosyası yoksa (ilk kullanım) soruları sorar. Cevaplanırsa bugün susturulur ve
    hatırlatmalar bir sonraki iş gününden başlar. Cevaplanmazsa varsayılanlar kaydedilir
    (soru her açılışta tekrar çıkmasın diye); sonradan --ayarla ile değişir."""
    if SETTINGS_FILE.exists():
        return
    if first_run_setup():
        fresh = load_state()["drunk"] == 0  # bugün su kaydedilmişse (mevcut kullanıcı) susturma
        if fresh:
            skip_today()
        apply_settings()
        print("Ayarlar kaydedildi: hedef %.1f L, %s–%s, kap %d ml."
              % (GOAL_ML / 1000, START.strftime("%H:%M"), END.strftime("%H:%M"), THERMOS_ML))
        if fresh:
            print("Hatırlatmalar bugün değil, bir sonraki iş gününden başlayacak.")
        ask("Hazır!\nHedef %.1f L · %s–%s · kap %d ml\n%s\nDeğiştirmek için: --ayarla"
            % (GOAL_ML / 1000, START.strftime("%H:%M"), END.strftime("%H:%M"), THERMOS_ML,
               "Hatırlatmalar bir sonraki iş gününden itibaren başlar." if fresh
               else "Hatırlatmalar kaldığı yerden devam eder."),
            ["Tamam"], None, theme="ozet", timeout=30)
    else:
        try:
            SETTINGS_FILE.write_text(json.dumps(DEFAULTS))
        except OSError:
            pass
        print("Ayar soruları cevaplanmadı; varsayılanlar geçerli. Sonra: python3 su_hatirlatici.py --ayarla")


def install_autostart():
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>{LABEL}</string>
<key>ProgramArguments</key><array>
<string>/usr/bin/python3</string><string>{Path(__file__).resolve()}</string></array>
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><true/>
</dict></plist>
"""
    ensure_first_run_setup()  # arka plan süreci yüklenmeden önce
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_text(plist)
    subprocess.run(["launchctl", "unload", str(PLIST)], capture_output=True)
    subprocess.run(["launchctl", "load", str(PLIST)])
    print("Otomatik başlatma kuruldu.")


def uninstall_autostart():
    subprocess.run(["launchctl", "unload", str(PLIST)], capture_output=True)
    PLIST.unlink(missing_ok=True)
    print("Otomatik başlatma kaldırıldı.")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--install-autostart":
        install_autostart()
    elif arg == "--ayarla":
        configure(sys.argv[2:])
    elif arg == "--skip-today":
        skip_today()
    elif arg == "--uninstall-autostart":
        uninstall_autostart()
    else:
        if arg == "":
            ensure_first_run_setup()  # düz çalıştırmada da (ve launchd'de) ilk kullanımda sor
        try:
            run(test=(arg == "--test"))
        except KeyboardInterrupt:
            pass

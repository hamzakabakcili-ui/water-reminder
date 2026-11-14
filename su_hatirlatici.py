#!/usr/bin/env python3
"""Su Hatırlatıcı — mesai boyunca su içmeyi ve termosu doldurmayı hatırlatır.

Sadece Python 3 + macOS (osascript) kullanır, ek kurulum gerekmez.

Kullanım:
    python3 su_hatirlatici.py                    # çalıştır
    python3 su_hatirlatici.py --test             # hemen bir hatırlatma göster
    python3 su_hatirlatici.py --install-autostart  # oturum açılınca otomatik başlat
    python3 su_hatirlatici.py --uninstall-autostart
"""
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

# ---- Ayarlar -------------------------------------------------------------
START = dt.time(9, 30)       # iş başı
END = dt.time(18, 0)         # iş bitişi
GOAL_ML = 2500               # günlük hedef
SIP_ML = 150                 # her hatırlatmada içilecek miktar
INTERVAL_MIN = 30            # hatırlatma aralığı
SNOOZE_MIN = 5               # "Ertele" süresi
THERMOS_ML = 500             # termos hacmi
DIALOG_TIMEOUT_S = 90        # cevap verilmezse pencere kapanır, ertelenir
# ---------------------------------------------------------------------------

POPUP_JS = Path(__file__).resolve().parent / "popup.js"
STATE_FILE = Path.home() / ".su_hatirlatici.json"
PLIST = Path.home() / "Library/LaunchAgents/local.su-hatirlatici.plist"
LABEL = "local.su-hatirlatici"


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


def ask(message, buttons, default):
    """Sağ altta küçük pencere (popup.js). Seçilen butonu döndürür, zaman aşımında None."""
    r = subprocess.run(
        ["osascript", "-l", "JavaScript", str(POPUP_JS), message,
         str(DIALOG_TIMEOUT_S)] + buttons,
        capture_output=True, text=True)
    return r.stdout.strip() or None


def progress(s):
    return "Bugün: %.1f / %.1f L" % (s["drunk"] / 1000, GOAL_ML / 1000)


def remind(s):
    """Bir hatırlatma gösterir. True dönerse içildi, False ise ertelendi."""
    need_fill = s["thermos"] < SIP_ML
    if need_fill:
        msg = "Termos bitti. Sebilden doldur ve su iç.\n\n" + progress(s)
        choice = ask(msg, ["Ertele", "Doldurdum, içtim"], "Doldurdum, içtim")
        if choice == "Doldurdum, içtim":
            s["thermos"] = THERMOS_ML
        else:
            return False
    else:
        msg = "Birkaç yudum su iç (~%d ml).\nTermosta ~%d ml var.\n\n%s" % (
            SIP_ML, s["thermos"], progress(s))
        if ask(msg, ["Ertele", "İçtim"], "İçtim") != "İçtim":
            return False
    s["thermos"] -= SIP_ML
    s["drunk"] += SIP_ML
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
    s = load_state()
    if test:
        remind(s)
        return
    due = dt.datetime.now()
    summary_day = None
    while True:
        now = dt.datetime.now()
        if now.date().isoformat() != s["date"]:
            s = load_state()
        if in_hours(now):
            if now >= due and s["drunk"] < GOAL_ML:
                drank = remind(s)
                delay = INTERVAL_MIN if drank else SNOOZE_MIN
                due = dt.datetime.now() + dt.timedelta(minutes=delay)
        else:
            if is_workday(now) and now.time() >= END and summary_day != s["date"]:
                summary_day = s["date"]
                ok = s["drunk"] >= GOAL_ML
                ask("%s\n\n%s" % ("Hedefe ulaştın, aferin! 🎉" if ok
                                  else "Hedefe ulaşamadın. Akşam biraz daha su iç.",
                                  progress(s)), ["Tamam"], "Tamam")
            due = next_start(now)
        time.sleep(20)


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
    elif arg == "--uninstall-autostart":
        uninstall_autostart()
    else:
        try:
            run(test=(arg == "--test"))
        except KeyboardInterrupt:
            pass

import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import su_hatirlatici as m  # noqa: E402


def at(text):
    return dt.datetime.fromisoformat(text)


class ScheduleTests(unittest.TestCase):
    def test_in_hours_weekday_boundaries(self):
        self.assertFalse(m.in_hours(at("2026-11-16 09:29")))  # Pazartesi
        self.assertTrue(m.in_hours(at("2026-11-16 09:30")))
        self.assertTrue(m.in_hours(at("2026-11-16 17:59")))
        self.assertFalse(m.in_hours(at("2026-11-16 18:00")))

    def test_weekend_never_in_hours(self):
        self.assertFalse(m.in_hours(at("2026-11-14 12:00")))  # Cumartesi
        self.assertFalse(m.in_hours(at("2026-11-15 12:00")))  # Pazar

    def test_next_start(self):
        self.assertEqual(m.next_start(at("2026-11-16 08:00")), at("2026-11-16 09:30"))
        self.assertEqual(m.next_start(at("2026-11-16 12:00")), at("2026-11-17 09:30"))
        self.assertEqual(m.next_start(at("2026-11-13 19:00")), at("2026-11-16 09:30"))  # Cuma akşamı
        self.assertEqual(m.next_start(at("2026-11-14 12:00")), at("2026-11-16 09:30"))  # Cumartesi


class StateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch.object(m, "STATE_FILE", Path(tmp.name) / "state.json")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_fresh_state_has_empty_thermos(self):
        s = m.load_state()
        self.assertEqual((s["drunk"], s["thermos"]), (0, 0))

    def test_roundtrip_same_day(self):
        s = m.load_state()
        s["drunk"] = 300
        m.save_state(s)
        self.assertEqual(m.load_state()["drunk"], 300)

    def test_previous_day_is_discarded(self):
        m.STATE_FILE.write_text(json.dumps({"date": "2000-01-01", "drunk": 999, "thermos": 10}))
        self.assertEqual(m.load_state()["drunk"], 0)

    def test_corrupt_file_falls_back(self):
        m.STATE_FILE.write_text("not json")
        self.assertEqual(m.load_state()["drunk"], 0)


class RemindTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(m, "save_state")
        patcher.start()
        self.addCleanup(patcher.stop)

    def state(self, thermos):
        return {"date": "x", "drunk": 0, "thermos": thermos}

    def test_drink_prompt_records_sip(self):
        s = self.state(500)
        with mock.patch.object(m, "ask", return_value="İçtim"):
            self.assertTrue(m.remind(s))
        self.assertEqual((s["drunk"], s["thermos"]), (m.SIP_ML, 500 - m.SIP_ML))

    def test_snooze_changes_nothing(self):
        s = self.state(500)
        with mock.patch.object(m, "ask", return_value="Ertele"):
            self.assertFalse(m.remind(s))
        self.assertEqual((s["drunk"], s["thermos"]), (0, 500))

    def test_timeout_counts_as_snooze(self):
        s = self.state(500)
        with mock.patch.object(m, "ask", return_value=None):
            self.assertFalse(m.remind(s))
        self.assertEqual(s["drunk"], 0)

    def test_empty_thermos_asks_refill_then_drinks(self):
        s = self.state(0)
        with mock.patch.object(m, "ask", return_value="Doldurdum, içtim") as ask:
            self.assertTrue(m.remind(s))
        self.assertIn("Termos bitti", ask.call_args[0][0])
        self.assertEqual(s["thermos"], m.THERMOS_ML - m.SIP_ML)
        self.assertEqual(s["drunk"], m.SIP_ML)

    def test_refill_credits_leftover_water(self):
        s = self.state(50)
        with mock.patch.object(m, "ask", return_value="Doldurdum, içtim"):
            m.remind(s)
        self.assertEqual(s["drunk"], 50 + m.SIP_ML)

    def test_five_thermoses_equal_goal(self):
        s = self.state(0)
        def press(msg, buttons, *a, **k):
            return buttons[-1]  # her zaman olumlu butona bas
        with mock.patch.object(m, "ask", side_effect=press), \
                mock.patch.object(m, "save_state"):
            for _ in range(5 * 3):  # termos başına 3 hatırlatma (150+150+200)
                m.remind(s)
        self.assertEqual((s["drunk"], s["thermos"]), (2500, 0))

    def test_refill_snooze_keeps_thermos_empty(self):
        s = self.state(m.SIP_ML - 1)
        with mock.patch.object(m, "ask", return_value="Ertele"):
            self.assertFalse(m.remind(s))
        self.assertEqual(s["thermos"], m.SIP_ML - 1)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(m, "SETTINGS_FILE", Path(self.tmp.name) / "ayar.json")
        p.start()
        self.addCleanup(p.stop)
        # modül sabitleri testten sonra eski haline dönsün
        for n in ("START", "END", "GOAL_ML", "THERMOS_ML", "SIP_ML", "INTERVAL_MIN"):
            q = mock.patch.object(m, n, getattr(m, n))
            q.start()
            self.addCleanup(q.stop)

    def test_defaults_keep_30_minutes(self):
        m.apply_settings()
        self.assertEqual((m.GOAL_ML, m.THERMOS_ML, m.INTERVAL_MIN), (2500, 500, 30))

    def test_configure_applies_choices(self):
        m.configure(["--hedef-litre", "3", "--baslangic", "08:00",
                     "--bitis", "17:00", "--kap-ml", "330"])
        self.assertEqual((m.GOAL_ML, m.THERMOS_ML), (3000, 330))
        self.assertEqual((m.START, m.END), (dt.time(8, 0), dt.time(17, 0)))
        self.assertEqual(m.INTERVAL_MIN, 540 // 20)  # 3000/150 = 20 hatırlatma

    def test_small_vessel_caps_sip(self):
        m.configure(["--kap-ml", "120"])
        self.assertEqual(m.SIP_ML, 120)

    def test_invalid_settings_rejected(self):
        with self.assertRaises(SystemExit):
            m.configure(["--baslangic", "18:00", "--bitis", "09:00"])
        self.assertFalse(m.SETTINGS_FILE.exists())

    def test_corrupt_file_falls_back_to_defaults(self):
        m.SETTINGS_FILE.write_text("{bozuk")
        self.assertEqual(m.load_settings(), m.DEFAULTS)


if __name__ == "__main__":
    unittest.main()

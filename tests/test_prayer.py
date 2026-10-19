"""Tests for the pure prayer-time logic (no Home Assistant needed)."""

import importlib.util
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# Load prayer.py directly so the package __init__ (which imports HA) is skipped.
_PATH = Path(__file__).parents[1] / "custom_components" / "diyanet_ezan" / "prayer.py"
_spec = importlib.util.spec_from_file_location("prayer", _PATH)
prayer = importlib.util.module_from_spec(_spec)
sys.modules["prayer"] = prayer  # dataclasses look the module up while building
_spec.loader.exec_module(prayer)

AMS = ZoneInfo("Europe/Amsterdam")


def _day(d, imsak, gunes, ogle, ikindi, aksam, yatsi, hijri="8 Cemaziyelevvel 1448"):
    return {
        "MiladiTarihKisa": d, "HicriTarihUzun": hijri,
        "Imsak": imsak, "Gunes": gunes, "Ogle": ogle,
        "Ikindi": ikindi, "Aksam": aksam, "Yatsi": yatsi,
    }


# Real Helmond values from the API, spanning the end of DST on 25 October 2026.
RAW = [
    _day("19.10.2026", "06:16", "08:01", "13:27", "16:08", "18:44", "20:16"),
    _day("20.10.2026", "06:18", "08:02", "13:27", "16:06", "18:42", "20:14"),
    _day("24.10.2026", "06:24", "08:09", "13:27", "16:00", "18:34", "20:06"),
    _day("25.10.2026", "05:26", "07:11", "12:27", "14:58", "17:32", "19:04"),
    {"MiladiTarihKisa": "garbage"},
]
DAYS = prayer.parse_days(RAW)


def test_parse_skips_bad_entries():
    assert len(DAYS) == 4
    assert DAYS[date(2026, 10, 19)].times["ogle"].strftime("%H:%M") == "13:27"


def test_next_prayer_during_day():
    now = datetime(2026, 10, 19, 14, 0, tzinfo=AMS)
    name, at = prayer.next_prayer(DAYS, now)
    assert name == "ikindi"
    assert at == datetime(2026, 10, 19, 16, 8, tzinfo=AMS)


def test_next_prayer_after_yatsi_rolls_to_tomorrow():
    now = datetime(2026, 10, 19, 21, 0, tzinfo=AMS)
    name, at = prayer.next_prayer(DAYS, now)
    assert name == "imsak"
    assert at.date() == date(2026, 10, 20)


def test_next_prayer_at_exact_minute_moves_on():
    now = datetime(2026, 10, 19, 13, 27, 0, 100, tzinfo=AMS)
    assert prayer.next_prayer(DAYS, now)[0] == "ikindi"


def test_next_prayer_none_when_data_missing():
    assert prayer.next_prayer(DAYS, datetime(2027, 1, 1, 12, tzinfo=AMS)) is None


def test_dst_end_uses_winter_offset():
    # After the clocks go back, 12:27 local must be UTC+1, i.e. 11:27 UTC.
    times = prayer.times_on(DAYS, datetime(2026, 10, 25, 9, tzinfo=AMS))
    assert times["ogle"].astimezone(timezone.utc).strftime("%H:%M") == "11:27"
    # The day before is still summer time: 13:27 local = 11:27 UTC.
    before = prayer.times_on(DAYS, datetime(2026, 10, 24, 9, tzinfo=AMS))
    assert before["ogle"].astimezone(timezone.utc).strftime("%H:%M") == "11:27"


def test_prayer_at_minute():
    assert prayer.prayer_at_minute(DAYS, datetime(2026, 10, 19, 18, 44, 0, tzinfo=AMS)) == "aksam"
    assert prayer.prayer_at_minute(DAYS, datetime(2026, 10, 19, 18, 45, 0, tzinfo=AMS)) is None


def test_ramadan_detection():
    days = prayer.parse_days([_day("01.03.2027", "05:00", "06:30", "12:40", "15:40", "18:20", "19:50", "12 Ramazan 1448")])
    assert days[date(2027, 3, 1)].is_ramadan
    assert not DAYS[date(2026, 10, 19)].is_ramadan


def test_localized_order_is_day_order():
    times = DAYS[date(2026, 10, 19)].localize(AMS)
    assert list(times) == list(prayer.PRAYERS)
    values = list(times.values())
    assert all(a < b for a, b in zip(values, values[1:]))

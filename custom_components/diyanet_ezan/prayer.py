"""Pure prayer-time logic, kept free of Home Assistant imports so it is easy to test."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

# Order matters: this is the order of the day.
PRAYERS: tuple[str, ...] = ("imsak", "gunes", "ogle", "ikindi", "aksam", "yatsi")

API_KEYS: dict[str, str] = {
    "imsak": "Imsak",
    "gunes": "Gunes",
    "ogle": "Ogle",
    "ikindi": "Ikindi",
    "aksam": "Aksam",
    "yatsi": "Yatsi",
}


@dataclass(frozen=True)
class DayTimes:
    """Prayer times for one calendar day."""

    day: date
    times: dict[str, time]
    hijri: str | None = None

    @property
    def is_ramadan(self) -> bool:
        """True when the Hijri date falls in Ramazan."""
        return "ramazan" in (self.hijri or "").lower()

    def localize(self, tz: Any) -> dict[str, datetime]:
        """Return the times as timezone-aware datetimes, in prayer order."""
        return {
            prayer: datetime.combine(self.day, self.times[prayer], tzinfo=tz)
            for prayer in PRAYERS
            if prayer in self.times
        }


def _parse_time(value: str) -> time:
    hour, minute = value.strip().split(":")[:2]
    return time(int(hour), int(minute))


def parse_days(raw: Iterable[Mapping[str, Any]]) -> dict[date, DayTimes]:
    """Turn the API's list of days into a dict keyed by date.

    Malformed entries are skipped rather than failing the whole response.
    """
    days: dict[date, DayTimes] = {}
    for entry in raw or []:
        try:
            day = datetime.strptime(entry["MiladiTarihKisa"].strip(), "%d.%m.%Y").date()
            times = {prayer: _parse_time(entry[key]) for prayer, key in API_KEYS.items()}
        except (KeyError, ValueError, AttributeError, TypeError):
            continue
        days[day] = DayTimes(day=day, times=times, hijri=entry.get("HicriTarihUzun"))
    return days


def times_on(days: Mapping[date, DayTimes], now: datetime) -> dict[str, datetime] | None:
    """Today's prayer times as aware datetimes, or None when today is missing."""
    today = days.get(now.date())
    return today.localize(now.tzinfo) if today else None


def next_prayer(days: Mapping[date, DayTimes], now: datetime) -> tuple[str, datetime] | None:
    """The first prayer time strictly after `now`, looking into tomorrow after Yatsı."""
    for offset in (0, 1):
        day = days.get(now.date() + timedelta(days=offset))
        if day is None:
            continue
        for prayer, moment in day.localize(now.tzinfo).items():
            if moment > now:
                return prayer, moment
    return None


def prayer_at_minute(days: Mapping[date, DayTimes], now: datetime) -> str | None:
    """The prayer whose time falls in the same minute as `now`, if any."""
    times = times_on(days, now)
    if not times:
        return None
    for prayer, moment in times.items():
        if moment.hour == now.hour and moment.minute == now.minute:
            return prayer
    return None

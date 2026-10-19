"""Fetches and caches the monthly prayer-time table."""

from __future__ import annotations

from datetime import date, datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import DiyanetApi, DiyanetApiError
from .const import CONF_DISTRICT_ID, DOMAIN, EVENT_PRAYER, LOGGER, UPDATE_INTERVAL
from .prayer import DayTimes, next_prayer, parse_days, prayer_at_minute, times_on

STORAGE_VERSION = 1


class DiyanetCoordinator(DataUpdateCoordinator[dict[date, DayTimes]]):
    """Holds about a month of prayer times for one district."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, LOGGER, name=f"{DOMAIN} {entry.title}", update_interval=UPDATE_INTERVAL)
        self.entry = entry
        self.district_id: str = entry.data[CONF_DISTRICT_ID]
        self._api = DiyanetApi(async_get_clientsession(hass))
        self._store: Store[list] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._cache: dict[date, DayTimes] = {}
        self._last_event_minute: datetime | None = None

    async def async_load_cache(self) -> None:
        """Load the last good response from disk, so startup works offline."""
        raw = await self._store.async_load()
        if raw:
            self._cache = parse_days(raw)

    async def _async_update_data(self) -> dict[date, DayTimes]:
        try:
            raw = await self._api.prayer_times(self.district_id)
            days = parse_days(raw)
            if not days:
                raise DiyanetApiError("Response contained no usable days")
        except DiyanetApiError as err:
            if dt_util.now().date() in self._cache:
                LOGGER.warning("Using cached prayer times, refresh failed: %s", err)
                return self._cache
            raise UpdateFailed(str(err)) from err

        self._cache = days
        await self._store.async_save(raw)
        return days

    # Helpers used by the entities -------------------------------------------------

    def today(self, now: datetime) -> DayTimes | None:
        return (self.data or {}).get(now.date())

    def times(self, now: datetime) -> dict[str, datetime] | None:
        return times_on(self.data or {}, now)

    def next_prayer(self, now: datetime) -> tuple[str, datetime] | None:
        return next_prayer(self.data or {}, now)

    # Called once a minute ----------------------------------------------------------

    @callback
    def async_minute_tick(self) -> None:
        """Refresh entity states and fire the prayer event when a time is reached."""
        now = dt_util.now()
        self.async_update_listeners()

        if self.today(now) is None and now.minute % 15 == 0:
            # Table ran out (e.g. long outage); try again without waiting 12h.
            self.hass.async_create_task(self.async_request_refresh())

        prayer = prayer_at_minute(self.data or {}, now)
        minute = now.replace(second=0, microsecond=0)
        if prayer and minute != self._last_event_minute:
            self._last_event_minute = minute
            today = self.today(now)
            self.hass.bus.async_fire(
                EVENT_PRAYER,
                {
                    "prayer": prayer,
                    "district": self.entry.title,
                    "ramadan": bool(today and today.is_ramadan),
                },
            )

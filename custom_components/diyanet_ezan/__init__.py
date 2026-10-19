"""Diyanet Ezan: official Diyanet prayer times in Home Assistant."""

from __future__ import annotations

from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change

from .coordinator import DiyanetCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

type DiyanetConfigEntry = ConfigEntry[DiyanetCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: DiyanetConfigEntry) -> bool:
    coordinator = DiyanetCoordinator(hass, entry)
    await coordinator.async_load_cache()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    @callback
    def _tick(_now: datetime) -> None:
        coordinator.async_minute_tick()

    # Next prayer, countdown and the prayer event all move once a minute.
    entry.async_on_unload(async_track_time_change(hass, _tick, second=0))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DiyanetConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

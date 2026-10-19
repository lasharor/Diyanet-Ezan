"""Diyanet Ezan: official Diyanet prayer times in Home Assistant."""

from __future__ import annotations

from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change

from .coordinator import DiyanetCoordinator
from .ezan import EzanPlayer

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
]

type DiyanetConfigEntry = ConfigEntry[DiyanetCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: DiyanetConfigEntry) -> bool:
    coordinator = DiyanetCoordinator(hass, entry)
    await coordinator.async_load_cache()
    await coordinator.async_config_entry_first_refresh()

    player = EzanPlayer(hass, coordinator, entry.options)
    coordinator.ezan = player if player.configured else None
    entry.runtime_data = coordinator

    @callback
    def _tick(_now: datetime) -> None:
        coordinator.async_minute_tick()

    # Next prayer, countdown, the prayer event and ezan playback all move once a minute.
    entry.async_on_unload(async_track_time_change(hass, _tick, second=0))
    entry.async_on_unload(entry.add_update_listener(_async_reload))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload(hass: HomeAssistant, entry: DiyanetConfigEntry) -> None:
    """Options changed (speakers etc.): reload so the playback entities follow."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: DiyanetConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

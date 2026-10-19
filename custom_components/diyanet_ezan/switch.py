"""Switch to mute or unmute ezan playback (only when speakers are configured)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import DiyanetConfigEntry
from .entity import DiyanetEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DiyanetConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    if entry.runtime_data.ezan is not None:
        async_add_entities([EzanPlaybackSwitch(entry.runtime_data, "playback")])


class EzanPlaybackSwitch(DiyanetEntity, SwitchEntity, RestoreEntity):
    _attr_icon = "mdi:speaker-wireless"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state == STATE_OFF:
            self.coordinator.ezan.enabled = False

    @property
    def is_on(self) -> bool:
        return self.coordinator.ezan.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.ezan.enabled = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.ezan.enabled = False
        self.async_write_ha_state()

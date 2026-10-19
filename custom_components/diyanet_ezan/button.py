"""Button to play the ezan right away, e.g. to test speakers and volume."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DiyanetConfigEntry
from .entity import DiyanetEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DiyanetConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    if entry.runtime_data.ezan is not None:
        async_add_entities([PlayEzanButton(entry.runtime_data, "play_now")])


class PlayEzanButton(DiyanetEntity, ButtonEntity):
    _attr_icon = "mdi:play-circle"

    async def async_press(self) -> None:
        await self.coordinator.ezan.async_play()

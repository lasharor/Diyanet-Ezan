"""Ramadan binary sensor."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import DiyanetConfigEntry
from .entity import DiyanetEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DiyanetConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([RamadanSensor(entry.runtime_data, "ramadan")])


class RamadanSensor(DiyanetEntity, BinarySensorEntity):
    _attr_icon = "mdi:star-crescent"

    @property
    def is_on(self) -> bool | None:
        today = self.coordinator.today(dt_util.now())
        return today.is_ramadan if today else None

"""Prayer-time sensors."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import DiyanetConfigEntry
from .coordinator import DiyanetCoordinator
from .entity import DiyanetEntity
from .prayer import PRAYERS

ICONS = {
    "imsak": "mdi:weather-night-partly-cloudy",
    "gunes": "mdi:weather-sunset-up",
    "ogle": "mdi:white-balance-sunny",
    "ikindi": "mdi:weather-partly-cloudy",
    "aksam": "mdi:weather-sunset-down",
    "yatsi": "mdi:weather-night",
}


@dataclass(frozen=True, kw_only=True)
class DiyanetSensorDescription(SensorEntityDescription):
    value_fn: Callable[[DiyanetCoordinator, datetime], Any]
    attr_fn: Callable[[DiyanetCoordinator, datetime], dict[str, Any]] | None = None


def _prayer_time(prayer: str) -> Callable[[DiyanetCoordinator, datetime], datetime | None]:
    return lambda c, now: (c.times(now) or {}).get(prayer)


def _next_time(c: DiyanetCoordinator, now: datetime) -> datetime | None:
    nxt = c.next_prayer(now)
    return nxt[1] if nxt else None


def _next_name(c: DiyanetCoordinator, now: datetime) -> str | None:
    nxt = c.next_prayer(now)
    return nxt[0] if nxt else None


def _minutes_left(c: DiyanetCoordinator, now: datetime) -> int | None:
    nxt = c.next_prayer(now)
    if not nxt:
        return None
    return math.ceil((nxt[1] - now).total_seconds() / 60)


def _hijri(c: DiyanetCoordinator, now: datetime) -> str | None:
    today = c.today(now)
    return today.hijri if today else None


SENSORS: tuple[DiyanetSensorDescription, ...] = (
    *(
        DiyanetSensorDescription(
            key=prayer,
            device_class=SensorDeviceClass.TIMESTAMP,
            icon=ICONS[prayer],
            value_fn=_prayer_time(prayer),
        )
        for prayer in PRAYERS
    ),
    DiyanetSensorDescription(
        key="next_prayer",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:hands-pray",
        value_fn=_next_time,
        attr_fn=lambda c, now: {"prayer": _next_name(c, now)},
    ),
    DiyanetSensorDescription(
        key="next_prayer_name",
        device_class=SensorDeviceClass.ENUM,
        options=list(PRAYERS),
        icon="mdi:hands-pray",
        value_fn=_next_name,
    ),
    DiyanetSensorDescription(
        key="time_remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:timer-sand",
        value_fn=_minutes_left,
    ),
    DiyanetSensorDescription(
        key="hijri_date",
        icon="mdi:calendar-star",
        value_fn=_hijri,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DiyanetConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(DiyanetSensor(coordinator, description) for description in SENSORS)


class DiyanetSensor(DiyanetEntity, SensorEntity):
    entity_description: DiyanetSensorDescription

    def __init__(self, coordinator: DiyanetCoordinator, description: DiyanetSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator, dt_util.now())

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attr_fn is None:
            return None
        return self.entity_description.attr_fn(self.coordinator, dt_util.now())

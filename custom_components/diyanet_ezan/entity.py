"""Shared base entity."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DiyanetCoordinator


class DiyanetEntity(CoordinatorEntity[DiyanetCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: DiyanetCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.entry
        self._attr_translation_key = key
        self._attr_unique_id = f"{coordinator.district_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.district_id)},
            name="Diyanet Ezan",
            manufacturer="Diyanet İşleri Başkanlığı",
            model=entry.title,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://namazvakti.diyanet.gov.tr",
        )

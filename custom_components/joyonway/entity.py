"""Base entity for Joyonway Spa."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JoyonwayCoordinator


class JoyonwayEntity(CoordinatorEntity[JoyonwayCoordinator]):
    """Base class for Joyonway entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: JoyonwayCoordinator, key: str, name: str) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.host}_{coordinator.port}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.host}:{self.coordinator.port}")},
            name="Joyonway Spa",
            manufacturer="Joyonway",
            model="Balboa-like RS485",
            configuration_url=f"http://{self.coordinator.host}",
        )

    @property
    def available(self) -> bool:
        """Return True if data is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.get("status") == "ok"
        )

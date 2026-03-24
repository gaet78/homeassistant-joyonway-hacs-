"""Binary sensor platform for Joyonway Spa."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JoyonwayCoordinator
from .entity import JoyonwayEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Joyonway binary sensors."""
    coordinator: JoyonwayCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        JoyonwayBinarySensor(coordinator, "pump1", "Pump 1", "mdi:pump"),
        JoyonwayBinarySensor(coordinator, "pump2", "Pump 2", "mdi:pump"),
        JoyonwayBinarySensor(coordinator, "heating", "Heating", "mdi:fire"),
        JoyonwayBinarySensor(coordinator, "light", "Light", "mdi:lightbulb"),
    ])


class JoyonwayBinarySensor(JoyonwayEntity, BinarySensorEntity):
    """Binary sensor for spa equipment status."""

    def __init__(
        self,
        coordinator: JoyonwayCoordinator,
        key: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, key, name)
        self._attr_icon = icon

    @property
    def is_on(self) -> bool | None:
        """Return True if the equipment is on."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._key)

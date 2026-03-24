"""Switch platform for Joyonway Spa."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JoyonwayCoordinator
from .entity import JoyonwayEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Joyonway switches."""
    coordinator: JoyonwayCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        JoyonwayPumpSwitch(coordinator, 1),
        JoyonwayPumpSwitch(coordinator, 2),
        JoyonwayLightSwitch(coordinator),
    ])


class JoyonwayPumpSwitch(JoyonwayEntity, SwitchEntity):
    """Switch to control a spa pump."""

    _attr_icon = "mdi:pump"

    def __init__(self, coordinator: JoyonwayCoordinator, pump: int) -> None:
        """Initialize."""
        super().__init__(coordinator, f"pump{pump}", f"Pump {pump}")
        self._pump = pump

    @property
    def is_on(self) -> bool | None:
        """Return True if the pump is running."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(f"pump{self._pump}")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the pump on."""
        await self.coordinator.async_set_pump(self._pump, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the pump off."""
        await self.coordinator.async_set_pump(self._pump, False)


class JoyonwayLightSwitch(JoyonwayEntity, SwitchEntity):
    """Switch to control the spa light."""

    _attr_icon = "mdi:lightbulb"

    def __init__(self, coordinator: JoyonwayCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "light", "Light")

    @property
    def is_on(self) -> bool | None:
        """Return True if the light is on."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("light")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self.coordinator.async_set_light(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self.coordinator.async_set_light(False)

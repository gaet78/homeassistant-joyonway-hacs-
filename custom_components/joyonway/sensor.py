"""Sensor platform for Joyonway Spa."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JoyonwayCoordinator
from .entity import JoyonwayEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Joyonway sensors."""
    coordinator: JoyonwayCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        JoyonwayTemperatureSensor(coordinator, "temperature", "Water Temperature"),
        JoyonwayTemperatureSensor(coordinator, "setpoint", "Setpoint"),
        JoyonwayTemperatureSensor(coordinator, "temperature_pac", "Heat Pump Output"),
        JoyonwayModeSensor(coordinator),
        JoyonwayHeatingModeSensor(coordinator),
        JoyonwayFiltrationSensor(coordinator, 1),
        JoyonwayFiltrationSensor(coordinator, 2),
    ]

    async_add_entities(entities)


class JoyonwayTemperatureSensor(JoyonwayEntity, SensorEntity):
    """Temperature sensor (water, setpoint, or heat pump output)."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._key)


class JoyonwayModeSensor(JoyonwayEntity, SensorEntity):
    """Sensor showing the spa operating mode."""

    _attr_icon = "mdi:spa"

    def __init__(self, coordinator: JoyonwayCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "mode", "Mode")

    @property
    def native_value(self) -> str | None:
        """Return the mode."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("mode")


class JoyonwayHeatingModeSensor(JoyonwayEntity, SensorEntity):
    """Sensor showing the heating mode (off/pac/pac_boiler)."""

    def __init__(self, coordinator: JoyonwayCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "heating_mode", "Heating Mode")

    @property
    def icon(self) -> str:
        """Return icon based on heating mode."""
        mode = self.native_value
        if mode == "pac_boiler":
            return "mdi:fire"
        if mode == "pac":
            return "mdi:heat-pump"
        return "mdi:snowflake"

    @property
    def native_value(self) -> str | None:
        """Return the heating mode."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("heating_mode", "off")


class JoyonwayFiltrationSensor(JoyonwayEntity, SensorEntity):
    """Sensor showing filtration schedule."""

    _attr_icon = "mdi:filter"

    def __init__(self, coordinator: JoyonwayCoordinator, slot: int) -> None:
        """Initialize."""
        super().__init__(coordinator, f"filtration{slot}", f"Filtration {slot}")
        self._slot = slot

    @property
    def native_value(self) -> str | None:
        """Return active/inactive."""
        if self.coordinator.data is None:
            return None
        active = self.coordinator.data.get(f"filtration{self._slot}_active")
        if active is None:
            return None
        return "active" if active else "inactive"

    @property
    def extra_state_attributes(self) -> dict:
        """Return schedule details."""
        if self.coordinator.data is None:
            return {}
        s = self._slot
        return {
            "start": self.coordinator.data.get(f"filtration{s}_start"),
            "end": self.coordinator.data.get(f"filtration{s}_end"),
            "active": self.coordinator.data.get(f"filtration{s}_active"),
        }

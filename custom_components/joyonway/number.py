"""Number platform for Joyonway Spa — setpoint and session duration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, DEFAULT_SESSION_DURATION
from .coordinator import JoyonwayCoordinator
from .entity import JoyonwayEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Joyonway number entities."""
    coordinator: JoyonwayCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        JoyonwaySetpointNumber(coordinator),
        JoyonwaySessionDurationNumber(coordinator),
    ])


class JoyonwaySetpointNumber(JoyonwayEntity, NumberEntity, RestoreEntity):
    """Number entity for temperature setpoint target."""

    _attr_icon = "mdi:thermometer-water"
    _attr_native_min_value = 11
    _attr_native_max_value = 39
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: JoyonwayCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "setpoint_target", "Setpoint Target")
        coordinator.register_setpoint_listener(self._on_setpoint_changed)

    async def async_added_to_hass(self) -> None:
        """Restore previous state."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self.coordinator.setpoint_target = float(last_state.state)
            except (ValueError, TypeError):
                pass

    @property
    def native_value(self) -> float:
        """Return current setpoint target."""
        return self.coordinator.setpoint_target

    async def async_set_native_value(self, value: float) -> None:
        """Set new setpoint and send RS485 command."""
        await self.coordinator.async_set_setpoint(value)
        self.async_write_ha_state()

    @callback
    def _on_setpoint_changed(self) -> None:
        """Called when coordinator changes setpoint (e.g. from programme or RS485 sync)."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Setpoint is always available."""
        return True


class JoyonwaySessionDurationNumber(JoyonwayEntity, NumberEntity, RestoreEntity):
    """Number entity for swim session duration."""

    _attr_icon = "mdi:timer-outline"
    _attr_native_min_value = 1
    _attr_native_max_value = 12
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: JoyonwayCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "session_duration", "Session Duration")

    async def async_added_to_hass(self) -> None:
        """Restore previous state."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self.coordinator.session_duration = int(float(last_state.state))
            except (ValueError, TypeError):
                pass

    @property
    def native_value(self) -> int:
        """Return current session duration."""
        return self.coordinator.session_duration

    async def async_set_native_value(self, value: float) -> None:
        """Set new session duration."""
        self.coordinator.session_duration = int(value)
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Always available."""
        return True

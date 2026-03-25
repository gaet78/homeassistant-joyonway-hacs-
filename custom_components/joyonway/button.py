"""Button platform for Joyonway Spa — quick actions."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JoyonwayCoordinator
from .entity import JoyonwayEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Joyonway button entities."""
    coordinator: JoyonwayCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        JoyonwayDiveInButton(coordinator),
        JoyonwayCancelSessionButton(coordinator),
    ])


class JoyonwayDiveInButton(JoyonwayEntity, ButtonEntity):
    """Button to start a swim session (Je plonge!)."""

    _attr_icon = "mdi:pool"

    def __init__(self, coordinator: JoyonwayCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "dive_in", "Dive In")

    async def async_press(self) -> None:
        """Start swim session."""
        await self.coordinator.async_je_plonge()

    @property
    def extra_state_attributes(self) -> dict:
        """Return session info."""
        attrs = {
            "session_active": self.coordinator.plonge_active,
        }
        remaining = self.coordinator.plonge_remaining
        if remaining:
            attrs["remaining"] = remaining
        return attrs

    @property
    def available(self) -> bool:
        """Always available."""
        return True


class JoyonwayCancelSessionButton(JoyonwayEntity, ButtonEntity):
    """Button to cancel a swim session."""

    _attr_icon = "mdi:close-circle"

    def __init__(self, coordinator: JoyonwayCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "cancel_session", "Cancel Session")

    async def async_press(self) -> None:
        """Cancel swim session."""
        await self.coordinator.async_cancel_plonge()

    @property
    def available(self) -> bool:
        """Always available."""
        return True

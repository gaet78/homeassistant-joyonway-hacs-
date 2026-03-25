"""Select platform for Joyonway Spa — programme selection."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import JoyonwayCoordinator
from .entity import JoyonwayEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Joyonway select entities."""
    coordinator: JoyonwayCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([JoyonwayProgrammeSelect(coordinator)])


class JoyonwayProgrammeSelect(JoyonwayEntity, SelectEntity, RestoreEntity):
    """Select entity for spa programme."""

    _attr_icon = "mdi:playlist-play"

    def __init__(self, coordinator: JoyonwayCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator, "programme", "Programme")
        coordinator.register_programme_listener(self._on_programme_changed)

    async def async_added_to_hass(self) -> None:
        """Restore previous state."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in self.options:
                self.coordinator.programme = last_state.state

    @property
    def options(self) -> list[str]:
        """Return dynamic list of programme names."""
        return self.coordinator.programme_names

    @property
    def current_option(self) -> str:
        """Return the current programme."""
        return self.coordinator.programme

    async def async_select_option(self, option: str) -> None:
        """Apply selected programme."""
        await self.coordinator.async_apply_programme(option)
        self.async_write_ha_state()

    @callback
    def _on_programme_changed(self) -> None:
        """Called when coordinator changes programme (e.g. auto-detect Manuel)."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Programme select is always available."""
        return True

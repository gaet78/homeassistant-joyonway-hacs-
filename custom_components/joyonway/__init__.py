"""Joyonway Spa RS485 integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_PROGRAMMES, SEED_PROGRAMMES
from .coordinator import JoyonwayCoordinator

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Joyonway Spa from a config entry."""
    # Migration: seed default programmes on first load
    if CONF_PROGRAMMES not in entry.options:
        # Also migrate from old "custom_programmes" key if present
        old_custom = dict(entry.options.get("custom_programmes", {}))
        programmes = {**SEED_PROGRAMMES, **old_custom}
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, CONF_PROGRAMMES: programmes}
        )

    programmes = dict(entry.options.get(CONF_PROGRAMMES, {}))

    coordinator = JoyonwayCoordinator(
        hass,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        programmes=programmes,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — refresh programmes in coordinator."""
    coordinator: JoyonwayCoordinator = hass.data[DOMAIN][entry.entry_id]
    programmes = dict(entry.options.get(CONF_PROGRAMMES, {}))
    coordinator.update_programmes(programmes)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

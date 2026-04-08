"""Joyonway Spa RS485 integration for Home Assistant."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

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

    # Register domain services (once)
    if not hass.services.has_service(DOMAIN, "set_filtration"):

        async def handle_set_filtration(call: ServiceCall) -> None:
            """Handle joyonway.set_filtration service call."""
            slot = int(call.data["slot"])
            active = bool(call.data["active"])
            start_h = int(call.data.get("start_hour", 0))
            start_m = int(call.data.get("start_minute", 0))
            end_h = int(call.data.get("end_hour", 0))
            end_m = int(call.data.get("end_minute", 0))
            for coord in hass.data[DOMAIN].values():
                await coord.async_set_filtration(
                    slot, active, start_h, start_m, end_h, end_m
                )
                break

        hass.services.async_register(
            DOMAIN,
            "set_filtration",
            handle_set_filtration,
            schema=vol.Schema(
                {
                    vol.Required("slot"): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=2)
                    ),
                    vol.Required("active"): cv.boolean,
                    vol.Required("start_hour"): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=23)
                    ),
                    vol.Required("start_minute"): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=59)
                    ),
                    vol.Required("end_hour"): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=23)
                    ),
                    vol.Required("end_minute"): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=59)
                    ),
                }
            ),
        )

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

"""Config flow for Joyonway Spa RS485."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import DOMAIN, DEFAULT_HOST, DEFAULT_PORT
from .rs485 import read_spa


class JoyonwayConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Joyonway Spa."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            # Test connection
            result = await self.hass.async_add_executor_job(
                read_spa, host, port, 3
            )

            if result.get("status") == "offline":
                errors["base"] = "cannot_connect"
            elif result.get("status") == "no_data":
                errors["base"] = "no_data"
            else:
                # Prevent duplicate entries
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Joyonway Spa ({host})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            }),
            errors=errors,
        )

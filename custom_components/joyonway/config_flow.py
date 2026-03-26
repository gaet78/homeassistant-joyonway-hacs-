"""Config flow for Joyonway Spa RS485."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback

from .const import DOMAIN, DEFAULT_HOST, DEFAULT_PORT, CONF_PROGRAMMES


class JoyonwayConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Joyonway Spa."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> JoyonwayOptionsFlow:
        """Get the options flow handler."""
        return JoyonwayOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        from .rs485 import read_spa

        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            result = await self.hass.async_add_executor_job(
                read_spa, host, port, 3
            )

            if result.get("status") == "offline":
                errors["base"] = "cannot_connect"
            elif result.get("status") == "no_data":
                errors["base"] = "no_data"
            else:
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


class JoyonwayOptionsFlow(OptionsFlow):
    """Handle options for Joyonway Spa (programme management)."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize."""
        self._config_entry = config_entry
        self._edit_name: str | None = None

    def _get_programmes(self) -> dict:
        """Get all programmes from options."""
        return dict(self._config_entry.options.get(CONF_PROGRAMMES, {}))

    def _save(self, programmes: dict) -> ConfigFlowResult:
        """Save programmes to options."""
        return self.async_create_entry(
            title="",
            data={CONF_PROGRAMMES: programmes},
        )

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Main menu: add / edit / delete programme."""
        if user_input is not None:
            action = user_input["action"]
            if action == "add":
                return await self.async_step_add()
            if action == "edit":
                return await self.async_step_pick_edit()
            if action == "delete":
                return await self.async_step_pick_delete()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("action"): vol.In({
                    "add": "Ajouter un programme",
                    "edit": "Modifier un programme",
                    "delete": "Supprimer un programme",
                }),
            }),
        )

    # --- ADD ---

    async def async_step_add(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Add a new programme."""
        errors = {}
        if user_input is not None:
            name = user_input["name"].strip()
            if not name:
                errors["name"] = "name_empty"
            else:
                display_name = self._format_name(name, user_input)
                programmes = self._get_programmes()
                if display_name in programmes or display_name == "Manuel":
                    errors["name"] = "name_exists"
                else:
                    programmes[display_name] = self._build_prog_def(user_input)
                    return self._save(programmes)

        return self.async_show_form(
            step_id="add",
            data_schema=self._programme_schema(),
            errors=errors,
        )

    # --- EDIT ---

    async def async_step_pick_edit(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Pick which programme to edit."""
        programmes = self._get_programmes()
        if not programmes:
            return self.async_abort(reason="no_programmes")

        if user_input is not None:
            self._edit_name = user_input["programme"]
            return await self.async_step_edit()

        return self.async_show_form(
            step_id="pick_edit",
            data_schema=vol.Schema({
                vol.Required("programme"): vol.In(list(programmes.keys())),
            }),
        )

    async def async_step_edit(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Edit a programme."""
        errors = {}
        programmes = self._get_programmes()
        old_def = programmes.get(self._edit_name, {})

        if user_input is not None:
            new_name = user_input["name"].strip()
            if not new_name:
                errors["name"] = "name_empty"
            else:
                display_name = self._format_name(new_name, user_input)
                if display_name != self._edit_name and (
                    display_name in programmes or display_name == "Manuel"
                ):
                    errors["name"] = "name_exists"
                else:
                    if self._edit_name in programmes:
                        del programmes[self._edit_name]
                    programmes[display_name] = self._build_prog_def(user_input)
                    return self._save(programmes)

        # Pre-fill with current values
        defaults = {
            "name": self._extract_short_name(self._edit_name),
            "setpoint": old_def.get("setpoint", 30),
            "filtration1_active": old_def.get("filtration1", {}).get("active", True),
            "filtration1_start_h": old_def.get("filtration1", {}).get("start_h", 0),
            "filtration1_start_m": old_def.get("filtration1", {}).get("start_m", 0),
            "filtration1_end_h": old_def.get("filtration1", {}).get("end_h", 0),
            "filtration1_end_m": old_def.get("filtration1", {}).get("end_m", 0),
            "filtration2_active": old_def.get("filtration2", {}).get("active", False),
            "filtration2_start_h": old_def.get("filtration2", {}).get("start_h", 0),
            "filtration2_start_m": old_def.get("filtration2", {}).get("start_m", 0),
            "filtration2_end_h": old_def.get("filtration2", {}).get("end_h", 0),
            "filtration2_end_m": old_def.get("filtration2", {}).get("end_m", 0),
        }

        return self.async_show_form(
            step_id="edit",
            data_schema=self._programme_schema(defaults),
            errors=errors,
        )

    # --- DELETE ---

    async def async_step_pick_delete(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Pick which programme to delete."""
        programmes = self._get_programmes()
        if not programmes:
            return self.async_abort(reason="no_programmes")

        if user_input is not None:
            name = user_input["programme"]
            programmes.pop(name, None)
            return self._save(programmes)

        return self.async_show_form(
            step_id="pick_delete",
            data_schema=vol.Schema({
                vol.Required("programme"): vol.In(list(programmes.keys())),
            }),
        )

    # --- Helpers ---

    @staticmethod
    def _format_name(short_name: str, user_input: dict) -> str:
        """Format programme name with summary: 'Name (T°C, Hdeb-Hfin)'."""
        temp = user_input["setpoint"]
        f1_active = user_input["filtration1_active"]
        if f1_active:
            sh = user_input["filtration1_start_h"]
            sm = user_input["filtration1_start_m"]
            eh = user_input["filtration1_end_h"]
            em = user_input["filtration1_end_m"]
            start = f"{sh}h{sm:02d}" if sm else f"{sh}h"
            end = f"{eh}h{em:02d}" if em else f"{eh}h"
            return f"{short_name} ({temp}°C, {start}-{end})"
        return f"{short_name} ({temp}°C)"

    @staticmethod
    def _extract_short_name(display_name: str) -> str:
        """Extract short name from 'Name (T°C, ...)'."""
        idx = display_name.rfind(" (")
        if idx > 0 and display_name.endswith(")"):
            return display_name[:idx]
        return display_name

    @staticmethod
    def _build_prog_def(user_input: dict) -> dict:
        """Build a programme definition dict from form input."""
        return {
            "setpoint": user_input["setpoint"],
            "filtration1": {
                "active": user_input["filtration1_active"],
                "start_h": user_input["filtration1_start_h"],
                "start_m": user_input["filtration1_start_m"],
                "end_h": user_input["filtration1_end_h"],
                "end_m": user_input["filtration1_end_m"],
            },
            "filtration2": {
                "active": user_input["filtration2_active"],
                "start_h": user_input["filtration2_start_h"],
                "start_m": user_input["filtration2_start_m"],
                "end_h": user_input["filtration2_end_h"],
                "end_m": user_input["filtration2_end_m"],
            },
        }

    @staticmethod
    def _programme_schema(defaults: dict | None = None) -> vol.Schema:
        """Return the schema for a programme form."""
        d = defaults or {}
        return vol.Schema({
            vol.Required("name", default=d.get("name", "")): str,
            vol.Required("setpoint", default=d.get("setpoint", 30)): vol.All(
                int, vol.Range(min=11, max=39)
            ),
            vol.Required("filtration1_active", default=d.get("filtration1_active", True)): bool,
            vol.Required("filtration1_start_h", default=d.get("filtration1_start_h", 0)): vol.All(
                int, vol.Range(min=0, max=23)
            ),
            vol.Required("filtration1_start_m", default=d.get("filtration1_start_m", 0)): vol.All(
                int, vol.Range(min=0, max=59)
            ),
            vol.Required("filtration1_end_h", default=d.get("filtration1_end_h", 0)): vol.All(
                int, vol.Range(min=0, max=23)
            ),
            vol.Required("filtration1_end_m", default=d.get("filtration1_end_m", 0)): vol.All(
                int, vol.Range(min=0, max=59)
            ),
            vol.Required("filtration2_active", default=d.get("filtration2_active", False)): bool,
            vol.Required("filtration2_start_h", default=d.get("filtration2_start_h", 0)): vol.All(
                int, vol.Range(min=0, max=23)
            ),
            vol.Required("filtration2_start_m", default=d.get("filtration2_start_m", 0)): vol.All(
                int, vol.Range(min=0, max=59)
            ),
            vol.Required("filtration2_end_h", default=d.get("filtration2_end_h", 0)): vol.All(
                int, vol.Range(min=0, max=23)
            ),
            vol.Required("filtration2_end_m", default=d.get("filtration2_end_m", 0)): vol.All(
                int, vol.Range(min=0, max=59)
            ),
        })

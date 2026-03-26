"""DataUpdateCoordinator for Joyonway Spa."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, callback, CALLBACK_TYPE
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SESSION_DURATION,
    READ_DURATION,
    FLOOD_DURATION_EQUIPMENT,
    FLOOD_DURATION_SETPOINT,
    FLOOD_DURATION_FILTRATION,
    FLOOD_INTERVAL,
)
from .rs485 import read_spa, flood_cmd, cmd_setpoint, cmd_pump, cmd_light, cmd_filtration

_LOGGER = logging.getLogger(__name__)


class JoyonwayCoordinator(DataUpdateCoordinator[dict]):
    """Coordinator to poll spa status via RS485."""

    def __init__(self, hass: HomeAssistant, host: str, port: int,
                 programmes: dict | None = None) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name="Joyonway Spa",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.host = host
        self.port = port

        # All programmes from options (Manuel is always implicit)
        self._programmes: dict = programmes or {}

        # Soft state (managed by entities, persisted via RestoreEntity)
        self.programme: str = "Manuel"
        self.setpoint_target: float = 30.0
        self.session_duration: int = DEFAULT_SESSION_DURATION

        # Je plonge timer
        self._plonge_unsub: CALLBACK_TYPE | None = None
        self.plonge_end: datetime | None = None

        # Listeners for soft state changes
        self._programme_listeners: list = []
        self._setpoint_listeners: list = []

        # Cooldown: skip manual mode detection after programme change
        self._programme_changed_at: datetime | None = None
        self._programme_cooldown = timedelta(seconds=90)

    @property
    def programmes(self) -> dict:
        """Return all programmes (Manuel + user-defined)."""
        return {"Manuel": {}, **self._programmes}

    @property
    def programme_names(self) -> list[str]:
        """Return all programme names."""
        return list(self.programmes.keys())

    def update_programmes(self, programmes: dict) -> None:
        """Update programmes from options flow."""
        self._programmes = programmes
        # If current programme was deleted, switch to Manuel
        if self.programme not in self.programmes:
            self.programme = "Manuel"
        self._notify_programme_listeners()

    async def _async_update_data(self) -> dict:
        """Fetch data from RS485 bus."""
        try:
            data = await self.hass.async_add_executor_job(
                read_spa, self.host, self.port, READ_DURATION
            )
        except Exception as err:
            raise UpdateFailed(f"Error communicating with W610: {err}") from err

        if data.get("status") == "offline":
            raise UpdateFailed("W610 connection failed")

        # Skip RS485 sync and manual mode detection during cooldown
        # (programme commands are still being applied to the spa)
        in_cooldown = (
            self._programme_changed_at is not None
            and datetime.now() - self._programme_changed_at < self._programme_cooldown
        )

        if not in_cooldown:
            # Sync setpoint from RS485 if it differs (changed from physical panel)
            rs485_setpoint = data.get("setpoint")
            if rs485_setpoint is not None:
                if round(rs485_setpoint) != round(self.setpoint_target):
                    _LOGGER.info(
                        "RS485 setpoint %.1f differs from target %.1f, syncing",
                        rs485_setpoint, self.setpoint_target,
                    )
                    self.setpoint_target = round(rs485_setpoint)
                    self._notify_setpoint_listeners()

            # Auto-detect manual mode
            self._check_manual_mode(data)
        else:
            # Clear cooldown if expired on next check
            if datetime.now() - self._programme_changed_at >= self._programme_cooldown:
                self._programme_changed_at = None

        return data

    def _check_manual_mode(self, data: dict) -> None:
        """Switch to Manuel if settings diverge from active programme."""
        if self.programme == "Manuel":
            return

        prog_def = self.programmes.get(self.programme)
        if not prog_def:
            return

        # Check setpoint
        expected_setpoint = prog_def.get("setpoint")
        if expected_setpoint is not None and round(self.setpoint_target) != expected_setpoint:
            _LOGGER.info("Setpoint diverged from programme, switching to Manuel")
            self.programme = "Manuel"
            self._notify_programme_listeners()
            return

        # Check filtration 1
        f1 = prog_def.get("filtration1", {})
        if f1.get("active") is not None:
            rs485_f1_active = data.get("filtration1_active")
            if rs485_f1_active is not None and rs485_f1_active != f1["active"]:
                _LOGGER.info("Filtration 1 diverged from programme, switching to Manuel")
                self.programme = "Manuel"
                self._notify_programme_listeners()
                return

        # Check filtration 2
        f2 = prog_def.get("filtration2", {})
        if f2.get("active") is not None:
            rs485_f2_active = data.get("filtration2_active")
            if rs485_f2_active is not None and rs485_f2_active != f2["active"]:
                _LOGGER.info("Filtration 2 diverged from programme, switching to Manuel")
                self.programme = "Manuel"
                self._notify_programme_listeners()
                return

    def register_programme_listener(self, callback_fn) -> None:
        """Register a callback for programme changes."""
        self._programme_listeners.append(callback_fn)

    def register_setpoint_listener(self, callback_fn) -> None:
        """Register a callback for setpoint target changes."""
        self._setpoint_listeners.append(callback_fn)

    def _notify_programme_listeners(self) -> None:
        for cb in self._programme_listeners:
            cb()

    def _notify_setpoint_listeners(self) -> None:
        for cb in self._setpoint_listeners:
            cb()

    # --- RS485 commands ---

    async def async_set_setpoint(self, temp_c: float) -> None:
        """Send a temperature setpoint command."""
        self.setpoint_target = temp_c
        temp_f = round(temp_c * 9 / 5 + 32)

        # Check if in programme mode, exit first
        if self.data and self.data.get("mode") == "programme":
            _LOGGER.info("Spa in programme mode, exiting first")
            exit_cmd = cmd_setpoint(50)
            await self.hass.async_add_executor_job(
                flood_cmd, self.host, self.port, exit_cmd, 5, FLOOD_INTERVAL
            )
            await asyncio.sleep(1)

        cmd = cmd_setpoint(temp_f)
        await self.hass.async_add_executor_job(
            flood_cmd, self.host, self.port, cmd, FLOOD_DURATION_SETPOINT, FLOOD_INTERVAL
        )
        await asyncio.sleep(2)
        await self.async_request_refresh()

    async def async_set_pump(self, pump: int, on: bool) -> None:
        """Turn pump on/off. pump: 1 or 2."""
        mask = 0x04 if pump == 1 else 0x10
        cmd = cmd_pump(mask, on)
        await self.hass.async_add_executor_job(
            flood_cmd, self.host, self.port, cmd, FLOOD_DURATION_EQUIPMENT, FLOOD_INTERVAL
        )
        await asyncio.sleep(3)
        await self.async_request_refresh()

    async def async_set_light(self, on: bool) -> None:
        """Turn light on/off."""
        cmd = cmd_light(on)
        await self.hass.async_add_executor_job(
            flood_cmd, self.host, self.port, cmd, FLOOD_DURATION_EQUIPMENT, FLOOD_INTERVAL
        )
        await asyncio.sleep(3)
        await self.async_request_refresh()

    async def async_set_filtration(self, slot: int, active: bool,
                                   start_h: int = 0, start_m: int = 0,
                                   end_h: int = 0, end_m: int = 0) -> None:
        """Set filtration schedule."""
        cmd = cmd_filtration(slot, active, start_h, start_m, end_h, end_m)
        await self.hass.async_add_executor_job(
            flood_cmd, self.host, self.port, cmd, FLOOD_DURATION_FILTRATION, FLOOD_INTERVAL
        )
        await asyncio.sleep(2)
        await self.async_request_refresh()

    async def async_toggle_filtration(self, slot: int, active: bool) -> None:
        """Toggle filtration on/off, keeping current schedule times."""
        start_h, start_m, end_h, end_m = 0, 0, 0, 0
        if self.data:
            start_str = self.data.get(f"filtration{slot}_start", "00:00")
            end_str = self.data.get(f"filtration{slot}_end", "00:00")
            if start_str and ":" in start_str:
                parts = start_str.split(":")
                start_h, start_m = int(parts[0]), int(parts[1])
            if end_str and ":" in end_str:
                parts = end_str.split(":")
                end_h, end_m = int(parts[0]), int(parts[1])
        await self.async_set_filtration(slot, active, start_h, start_m, end_h, end_m)

    # --- Programme management ---

    async def async_apply_programme(self, name: str) -> None:
        """Apply a preset programme."""
        self.programme = name
        self._notify_programme_listeners()

        if name == "Manuel":
            return

        # Start cooldown to avoid false auto-Manuel detection
        self._programme_changed_at = datetime.now()

        prog_def = self.programmes.get(name)
        if not prog_def:
            return

        # Set setpoint
        setpoint = prog_def.get("setpoint")
        if setpoint is not None:
            self.setpoint_target = float(setpoint)
            self._notify_setpoint_listeners()

        # Set filtration 1
        f1 = prog_def.get("filtration1", {})
        if "active" in f1:
            await self.async_set_filtration(
                1, f1["active"],
                f1.get("start_h", 0), f1.get("start_m", 0),
                f1.get("end_h", 0), f1.get("end_m", 0),
            )

        # Set filtration 2
        f2 = prog_def.get("filtration2", {})
        if "active" in f2:
            await self.async_set_filtration(
                2, f2["active"],
                f2.get("start_h", 0), f2.get("start_m", 0),
                f2.get("end_h", 0), f2.get("end_m", 0),
            )

        # Always send setpoint via RS485 (even if value didn't change)
        await self.async_set_setpoint(self.setpoint_target)

    # --- Je plonge ---

    async def async_je_plonge(self) -> None:
        """Start a swim session: heat to 38°C, auto-return after session_duration."""
        # Cancel any existing timer
        if self._plonge_unsub:
            self._plonge_unsub()
            self._plonge_unsub = None

        # Direct RS485 commands: 38°C + filtration 10h-23h
        self.programme = "Manuel"
        self._notify_programme_listeners()
        self.setpoint_target = 38.0
        self._notify_setpoint_listeners()
        await self.async_set_filtration(1, True, 10, 0, 23, 0)
        await self.async_set_setpoint(38.0)

        # Start timer
        duration_seconds = self.session_duration * 3600
        self.plonge_end = datetime.now() + timedelta(seconds=duration_seconds)

        @callback
        def _plonge_timer_finished(_now):
            """Called when session timer expires."""
            self._plonge_unsub = None
            self.plonge_end = None
            self.hass.async_create_task(self._async_end_plonge())

        self._plonge_unsub = async_call_later(
            self.hass, duration_seconds, _plonge_timer_finished
        )
        _LOGGER.info("Je plonge! Session for %dh started", self.session_duration)

    async def _async_end_plonge(self) -> None:
        """End swim session: return to 30°C + filtration 12h-20h."""
        self.programme = "Manuel"
        self._notify_programme_listeners()
        self.setpoint_target = 30.0
        self._notify_setpoint_listeners()
        await self.async_set_filtration(1, True, 12, 0, 20, 0)
        await self.async_set_setpoint(30.0)
        _LOGGER.info("Plonge session ended, switched to 30°C")

        # Send notification via HA
        try:
            await self.hass.services.async_call(
                "script", "envoyer_notification",
                {
                    "title": "Spa : fin de session",
                    "message": "Session terminée — le spa repasse à 30°C.",
                    "priority": "info",
                    "tags": "hot_tub",
                },
                blocking=False,
            )
        except Exception:
            _LOGGER.warning("Could not send end-of-session notification")

    async def async_cancel_plonge(self) -> None:
        """Cancel swim session and return to 30°C."""
        if self._plonge_unsub:
            self._plonge_unsub()
            self._plonge_unsub = None
        self.plonge_end = None
        self.programme = "Manuel"
        self._notify_programme_listeners()
        self.setpoint_target = 30.0
        self._notify_setpoint_listeners()
        await self.async_set_filtration(1, True, 12, 0, 20, 0)
        await self.async_set_setpoint(30.0)
        _LOGGER.info("Plonge session cancelled")

    @property
    def plonge_active(self) -> bool:
        """Return True if a swim session is active."""
        return self._plonge_unsub is not None

    @property
    def plonge_remaining(self) -> str | None:
        """Return remaining time as HH:MM:SS string."""
        if self.plonge_end is None:
            return None
        remaining = self.plonge_end - datetime.now()
        if remaining.total_seconds() <= 0:
            return "00:00:00"
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

"""DataUpdateCoordinator for Joyonway Spa."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, READ_DURATION, FLOOD_DURATION_EQUIPMENT, FLOOD_DURATION_SETPOINT, FLOOD_DURATION_FILTRATION, FLOOD_INTERVAL
from .rs485 import read_spa, flood_cmd, cmd_setpoint, cmd_pump, cmd_light, cmd_filtration

_LOGGER = logging.getLogger(__name__)


class JoyonwayCoordinator(DataUpdateCoordinator[dict]):
    """Coordinator to poll spa status via RS485."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name="Joyonway Spa",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.host = host
        self.port = port

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

        return data

    async def async_set_setpoint(self, temp_c: float) -> None:
        """Send a temperature setpoint command."""
        temp_f = round(temp_c * 9 / 5 + 32)

        # Check if in programme mode, exit first
        if self.data and self.data.get("mode") == "programme":
            _LOGGER.info("Spa in programme mode, exiting first")
            exit_cmd = cmd_setpoint(50)  # 50°F = out of range, forces normal mode
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

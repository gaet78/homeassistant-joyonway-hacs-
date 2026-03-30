"""RS485 communication with Joyonway spa via USR-W610 TCP bridge."""

from __future__ import annotations

import asyncio
import logging
import socket
import time

_LOGGER = logging.getLogger(__name__)


def crc8(data: bytes, poly: int = 0x07, init: int = 0x71) -> int:
    """Calculate CRC-8 for Joyonway protocol."""
    crc = init
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ poly) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def make_frame(payload: bytes) -> bytes:
    """Build a complete frame with delimiter, length, and CRC."""
    length = len(payload) + 2
    crc = crc8(payload)
    return bytes([0x7E, length]) + payload + bytes([crc, 0x7E])


def extract_frame(data: bytes, cmd_byte: int) -> bytes | None:
    """Find the last valid F9 BF <cmd> broadcast frame in the data stream."""
    last_frame = None
    idx = 0
    while idx < len(data):
        pos = data.find(b'\x7e', idx)
        if pos == -1:
            break
        if (pos + 27 <= len(data) and
            data[pos + 1] == 0x1A and
            data[pos + 2] == 0xF9 and
            data[pos + 3] == 0xBF and
            data[pos + 4] == cmd_byte):
            last_frame = data[pos + 1:pos + 27]
        idx = pos + 1
    return last_frame


def parse_b4(frame: bytes) -> dict | None:
    """Parse a B4 status frame."""
    if frame is None or len(frame) < 22:
        return None

    temp_f = frame[9]
    setpoint_f = frame[16]
    pump_byte = frame[12]
    flag_byte = frame[14]
    mode_byte = frame[17]

    return {
        "temperature": round((temp_f - 32) * 5 / 9, 1),
        "temperature_f": temp_f,
        "setpoint": round((setpoint_f - 32) * 5 / 9, 1),
        "setpoint_f": setpoint_f,
        "pump1": bool(pump_byte & 0x04),
        "pump2": bool(pump_byte & 0x10),
        "heating": flag_byte != 0x20,
        "heating_mode": "pac_boiler" if flag_byte == 0x35
                        else "pac" if flag_byte == 0x21
                        else "off" if flag_byte == 0x20
                        else f"unknown_0x{flag_byte:02x}",
        "light": bool(mode_byte & 0x01),
        "mode": "normal" if mode_byte & 0xFE == 0x90
                else "programme" if mode_byte & 0xFE == 0x10
                else f"unknown_{mode_byte:#x}",
        "status": "ok",
    }


def parse_b5(frame_b4: bytes, frame_b5: bytes, result: dict) -> None:
    """Parse a B5 filtration frame and add data to result dict."""
    if frame_b5 is None or len(frame_b5) < 25:
        return

    # Heat pump output temperature from B4 byte 21
    b21 = frame_b4[21]
    result["temperature_pac"] = round((b21 - 32) * 5 / 9, 1)
    result["temperature_pac_f"] = b21

    # Filtration schedule 1
    b17 = frame_b5[17]
    result["filtration1_active"] = bool(b17 & 0xC0)
    result["filtration1_start"] = f"{b17 & 0x3F:02d}:{frame_b5[18]:02d}"
    result["filtration1_end"] = f"{frame_b5[19]:02d}:{frame_b5[20]:02d}"

    # Filtration schedule 2
    b21 = frame_b5[21]
    result["filtration2_active"] = bool(b21 & 0x40)
    result["filtration2_start"] = f"{b21 & 0x3F:02d}:{frame_b5[22]:02d}"
    result["filtration2_end"] = f"{frame_b5[23]:02d}:{frame_b5[24]:02d}"


def read_spa(host: str, port: int, duration: int = 3) -> dict:
    """Connect to W610, read bus for `duration` seconds, parse and return status."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        sock.settimeout(0.5)
    except socket.timeout:
        _LOGGER.warning(
            "W610 connection timeout: %s:%s — host may be unreachable or port filtered",
            host, port,
        )
        return {"status": "timeout"}
    except ConnectionRefusedError:
        _LOGGER.warning(
            "W610 connection refused: %s:%s — host reachable but port %s is closed",
            host, port, port,
        )
        return {"status": "refused"}
    except OSError as err:
        _LOGGER.warning(
            "W610 connection error: %s:%s — %s", host, port, err,
        )
        return {"status": "offline", "error": str(err)}

    _LOGGER.debug("W610 connected to %s:%s, listening for %ss…", host, port, duration)
    data = b''
    start = time.time()
    while time.time() - start < duration:
        try:
            chunk = sock.recv(2048)
            if chunk:
                data += chunk
                _LOGGER.debug("W610 received %d bytes (total: %d)", len(chunk), len(data))
        except socket.timeout:
            continue
    sock.close()
    _LOGGER.debug("W610 read complete: %d bytes total from %s:%s", len(data), host, port)

    frame_b4 = extract_frame(data, 0xB4)
    result = parse_b4(frame_b4)

    if result is None:
        return {"status": "no_data"}

    frame_b5 = extract_frame(data, 0xB5)
    parse_b5(frame_b4, frame_b5, result)
    return result


def flood_cmd(host: str, port: int, cmd: bytes, duration: float = 10, interval: float = 0.05) -> int:
    """Send a command in flood mode for `duration` seconds."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((host, port))
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sent = 0
    start = time.time()
    while time.time() - start < duration:
        sock.send(cmd)
        sent += 1
        time.sleep(interval)
    sock.close()
    return sent


# --- Command builders ---

def cmd_setpoint(temp_f: int) -> bytes:
    """Build setpoint command (A1 with 0x80 0x80 0x02 0x04 pattern)."""
    compl = 0xFF - temp_f
    return make_frame(bytes([
        0x20, 0xBF, 0xA1,
        0x01, 0x20, 0x00, 0xA1,
        0x00, 0x00, 0x80, 0x80,
        0x02, 0x04,
        compl, temp_f,
        0x00,
    ]))


def cmd_pump(pump_mask: int, on: bool) -> bytes:
    """Build pump command (A1 with mask/state pattern). mask: 0x04=pump1, 0x10=pump2."""
    return make_frame(bytes([
        0x20, 0xBF, 0xA1,
        0x01, 0x20, 0x00, 0xA1,
        pump_mask, pump_mask if on else 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ]))


def cmd_light(on: bool) -> bytes:
    """Build light command (AE)."""
    return make_frame(bytes([
        0x20, 0xBF, 0xAE,
        0x00, 0x11 if on else 0x00, 0x01,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ]))


# A4 filtration flags
_A4_FLAGS = {
    (1, True): 0x22,
    (1, False): 0x12,
    (2, True): 0x88,
    (2, False): 0x48,
}


def cmd_filtration(slot: int, active: bool,
                   start_h: int = 0, start_m: int = 0,
                   end_h: int = 0, end_m: int = 0) -> bytes:
    """Build filtration schedule command (A4)."""
    flag = _A4_FLAGS[(slot, active)]
    if slot == 1:
        p1 = [start_h, start_m, end_h, end_m]
        p2 = [0, 0, 0, 0]
    else:
        p1 = [0, 0, 0, 0]
        p2 = [start_h, start_m, end_h, end_m]
    return make_frame(bytes([
        0x20, 0xBF, 0xA4,
        0x01, 0x20, 0x00, 0xA1,
        flag,
    ] + p1 + p2))

# Joyonway Spa RS485 - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant custom integration for **Joyonway** (Balboa-like) spas via RS485 bus, using a **USR-W610** TCP/WiFi bridge.

## Features

- **Sensors**: Water temperature, setpoint, heat pump output temperature, operating mode, filtration schedules (2 slots)
- **Binary sensors**: Pump 1, Pump 2, Heating, Light status
- **Switches**: Pump 1, Pump 2, Light (on/off control)
- **Temperature setpoint**: Adjustable via service calls
- **Filtration schedule**: Configurable via service calls
- **UI config flow**: Add your spa from the Home Assistant UI — no YAML needed

## Hardware Required

| Component | Description |
|-----------|-------------|
| **Joyonway Spa** | With RS485 control board (Balboa-like protocol) |
| **USR-W610** | RS485 to WiFi/TCP bridge |

### USR-W610 Configuration

The W610 **must** be configured in **Transparent Mode** (not Modbus or AT command mode):

- **Protocol**: TCP Server
- **Baud rate**: 115200
- **Data bits**: 8, Stop bits: 1, Parity: None
- **Default port**: 8899

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the 3 dots menu → **Custom repositories**
3. Add this repository URL with category **Integration**
4. Search for "Joyonway" and install
5. Restart Home Assistant
6. Go to **Settings → Devices & Services → Add Integration → Joyonway Spa RS485**

### Manual

1. Copy the `custom_components/joyonway` folder to your Home Assistant `custom_components/` directory
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration → Joyonway Spa RS485**

## RS485 Protocol

This integration communicates with the spa's proprietary RS485 bus protocol:

- **Delimiter**: `0x7E`
- **CRC-8**: Polynomial `0x07`, init `0x71`
- **Status frames**: B4 (temperatures, pumps, heating, light, mode) and B5 (filtration schedules, heat pump output)
- **Command frames**: A1 (setpoint, pumps), AE (light), A4 (filtration)

Commands are sent using **flood mode** — the same frame is repeated for 1-10 seconds until the controller acknowledges it. This is required because there is no master/slave addressing; the W610 injects frames onto the shared bus.

### Temperature Resolution

The spa controller uses **Fahrenheit internally** with integer precision. This means temperature updates in Celsius appear in ~0.56°C steps, which is normal behavior.

For detailed protocol documentation, see the companion repository: [joyonway-rs485-ha](https://github.com/gaet78/joyonway-rs485-ha)

## Entities Created

### Sensors
| Entity | Description |
|--------|-------------|
| Water Temperature | Current water temperature (°C) |
| Setpoint | Target temperature (°C) |
| Heat Pump Output | Heat pump output water temperature (°C) |
| Mode | Operating mode (normal / programme) |
| Filtration 1 | Filtration schedule slot 1 (active/inactive + times) |
| Filtration 2 | Filtration schedule slot 2 (active/inactive + times) |

### Binary Sensors
| Entity | Description |
|--------|-------------|
| Pump 1 | Massage pump 1 status |
| Pump 2 | Massage pump 2 status |
| Heating | Heating active (PAC and/or boiler) |
| Light | Spa light status |

### Switches
| Entity | Description |
|--------|-------------|
| Pump 1 | Toggle massage pump 1 |
| Pump 2 | Toggle massage pump 2 |
| Light | Toggle spa light |

## Coordinator Services

The coordinator exposes methods that can be called from automations:

```python
# Set temperature setpoint (in °C, converted to °F internally)
await coordinator.async_set_setpoint(38.0)

# Control pumps (pump 1 or 2)
await coordinator.async_set_pump(1, True)   # Pump 1 ON
await coordinator.async_set_pump(2, False)  # Pump 2 OFF

# Control light
await coordinator.async_set_light(True)

# Set filtration schedule
await coordinator.async_set_filtration(slot=1, active=True, start_h=8, start_m=0, end_h=12, end_m=0)
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect" | Check W610 IP/port, ensure it's powered and on your network |
| "No RS485 data" | Check RS485 wiring (A/B), ensure W610 is in **Transparent Mode**, baud 115200 |
| Temperature updates slow | Normal — the spa controller broadcasts status every few seconds |
| Commands not working | Ensure no other device is sending on the RS485 bus simultaneously |

## License

MIT

"""Constants for the Joyonway Spa RS485 integration."""

DOMAIN = "joyonway"

CONF_HOST = "host"
CONF_PORT = "port"

DEFAULT_HOST = "192.168.1.11"
DEFAULT_PORT = 8899
DEFAULT_SCAN_INTERVAL = 30
READ_DURATION = 3
FLOOD_DURATION_EQUIPMENT = 1
FLOOD_DURATION_SETPOINT = 10
FLOOD_DURATION_FILTRATION = 10
FLOOD_INTERVAL = 0.05

DEFAULT_SESSION_DURATION = 6

DEFAULT_PROGRAMMES = {
    "Manuel": {},
    "Hors gel (11°C, 24/7)": {
        "setpoint": 11,
        "filtration1": {"active": True, "start_h": 0, "start_m": 0, "end_h": 23, "end_m": 59},
        "filtration2": {"active": False},
    },
    "Prêt à plonger (38°C, 10h-23h)": {
        "setpoint": 38,
        "filtration1": {"active": True, "start_h": 10, "start_m": 0, "end_h": 23, "end_m": 0},
        "filtration2": {"active": False},
    },
    "En repos (30°C, 12h-20h)": {
        "setpoint": 30,
        "filtration1": {"active": True, "start_h": 12, "start_m": 0, "end_h": 20, "end_m": 0},
        "filtration2": {"active": False},
    },
}

CONF_CUSTOM_PROGRAMMES = "custom_programmes"

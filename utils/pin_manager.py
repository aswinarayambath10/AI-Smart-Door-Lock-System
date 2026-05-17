"""
PIN Manager Utility
Handles PIN setup, verification, and storage for backup door access
"""

import os
import json
import hashlib
from datetime import datetime

PIN_FILE = "data/pin_config.json"


def _load_config():
    if not os.path.exists(PIN_FILE):
        return {"pin_hash": None, "enabled": False, "created_at": None}
    with open(PIN_FILE, "r") as f:
        return json.load(f)


def _save_config(config):
    os.makedirs(os.path.dirname(PIN_FILE), exist_ok=True)
    with open(PIN_FILE, "w") as f:
        json.dump(config, f, indent=2)


def _hash_pin(pin: str) -> str:
    """SHA-256 hash of the PIN for secure storage."""
    return hashlib.sha256(pin.strip().encode()).hexdigest()


def set_pin(pin: str) -> tuple:
    """
    Set a new PIN. Must be 4-8 digits.
    Returns: (success: bool, message: str)
    """
    pin = pin.strip()
    if not pin.isdigit():
        return False, "PIN must contain digits only (0-9)."
    if not (4 <= len(pin) <= 8):
        return False, "PIN must be 4 to 8 digits long."

    config = {
        "pin_hash": _hash_pin(pin),
        "enabled": True,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _save_config(config)
    return True, f"PIN set successfully! ({len(pin)}-digit PIN saved)"


def verify_pin(pin: str) -> bool:
    """Check if entered PIN matches stored PIN."""
    config = _load_config()
    if not config.get("enabled") or not config.get("pin_hash"):
        return False
    return _hash_pin(pin.strip()) == config["pin_hash"]


def is_pin_enabled() -> bool:
    """Check if a PIN has been configured."""
    config = _load_config()
    return config.get("enabled", False) and config.get("pin_hash") is not None


def disable_pin():
    """Disable PIN backup access."""
    config = _load_config()
    config["enabled"] = False
    _save_config(config)


def get_pin_info() -> dict:
    """Return PIN config info (without the hash)."""
    config = _load_config()
    return {
        "enabled": config.get("enabled", False),
        "created_at": config.get("created_at", "Not set"),
    }

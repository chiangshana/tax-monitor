import os
import sys
from pathlib import Path


APP_DIR_NAME = "TaxMonitor"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def is_frozen_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def user_data_root() -> Path:
    override = os.getenv("TAX_MONITOR_DATA_DIR")
    if override:
        return Path(override)

    if os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / APP_DIR_NAME


def data_dir() -> Path:
    override = os.getenv("TAX_MONITOR_DATA_DIR")
    if override:
        return Path(override)
    if is_frozen_app():
        return user_data_root() / "data"
    return PROJECT_ROOT / "data"


def output_dir(name: str) -> Path:
    return data_dir() / name

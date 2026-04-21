"""Windows-Autostart via HKCU\\...\\Run."""
from __future__ import annotations

import logging
import platform
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_APP_NAME = "fux-voice"
_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _get_current_exe_path() -> Optional[Path]:
    """Pfad zur aktuell laufenden .exe (PyInstaller) oder zu main.py (dev)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    script = Path(sys.argv[0]).resolve() if sys.argv else None
    return script


def is_autostart_enabled() -> bool:
    if not _is_windows():
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH) as key:
            value, _ = winreg.QueryValueEx(key, _APP_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except Exception:
        logger.exception("Autostart-Status konnte nicht gelesen werden")
        return False


def set_autostart(enabled: bool, exe_path: Optional[Path] = None) -> bool:
    """Setzt oder entfernt den Autostart-Eintrag. Returns True bei Erfolg."""
    if not _is_windows():
        logger.info("Autostart nur auf Windows verfuegbar")
        return False
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                target = exe_path or _get_current_exe_path()
                if target is None or not Path(target).exists():
                    logger.error("Autostart: Keine gueltige .exe gefunden (%s)", target)
                    return False
                value = f'"{target}"'
                winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, value)
                logger.info("Autostart aktiviert: %s", value)
            else:
                try:
                    winreg.DeleteValue(key, _APP_NAME)
                    logger.info("Autostart deaktiviert")
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        logger.exception("Autostart konnte nicht gesetzt werden")
        return False


def get_autostart_target() -> Optional[str]:
    if not _is_windows():
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH) as key:
            value, _ = winreg.QueryValueEx(key, _APP_NAME)
            return value
    except Exception:
        return None

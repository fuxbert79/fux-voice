"""Windows-Fokus-Management via Win32-API.

Zweck: Fenster-Fokus vor dem Paste wiederherstellen, damit Strg+V in der
App landet, in der der User vor der Aufnahme gearbeitet hat.

Standard-SetForegroundWindow unterliegt Windows-Restrictions. Workaround:
AttachThreadInput → BringWindowToTop + SetForegroundWindow → Detach.
"""
from __future__ import annotations

import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)

_ENABLED = sys.platform.startswith("win")


def get_foreground_hwnd() -> Optional[int]:
    """HWND des aktuell aktiven Fensters, oder None auf Non-Windows."""
    if not _ENABLED:
        return None
    try:
        import ctypes
        return int(ctypes.windll.user32.GetForegroundWindow())
    except Exception:
        logger.exception("GetForegroundWindow fehlgeschlagen")
        return None


def get_window_title(hwnd: int) -> str:
    """Title des Fensters (fuer Logging)."""
    if not _ENABLED or not hwnd:
        return ""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value
    except Exception:
        return ""


def force_set_foreground(hwnd: int) -> bool:
    """Aktiviert hwnd als Foreground-Fenster. True bei Erfolg.

    Nutzt AttachThreadInput-Trick, um die Windows-Restrictions bei
    SetForegroundWindow zu umgehen.
    """
    if not _ENABLED or not hwnd:
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        if not user32.IsWindow(hwnd):
            logger.debug("hwnd %x existiert nicht mehr", hwnd)
            return False

        current_fg = user32.GetForegroundWindow()
        if current_fg == hwnd:
            return True

        # Wenn minimiert → wiederherstellen
        SW_RESTORE = 9
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)

        # Thread-IDs
        current_thread = kernel32.GetCurrentThreadId()
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)
        foreground_thread = user32.GetWindowThreadProcessId(current_fg, None) if current_fg else 0

        # Input-Queues attachen
        attached_fg = False
        attached_target = False
        if foreground_thread and foreground_thread != current_thread:
            attached_fg = bool(user32.AttachThreadInput(current_thread, foreground_thread, True))
        if target_thread and target_thread != current_thread:
            attached_target = bool(user32.AttachThreadInput(current_thread, target_thread, True))

        try:
            user32.BringWindowToTop(hwnd)
            ok = bool(user32.SetForegroundWindow(hwnd))
        finally:
            if attached_fg:
                user32.AttachThreadInput(current_thread, foreground_thread, False)
            if attached_target:
                user32.AttachThreadInput(current_thread, target_thread, False)

        return ok
    except Exception:
        logger.exception("force_set_foreground fehlgeschlagen")
        return False

"""Globale Hotkeys mit Event-Suppression via keyboard-Library + Scan-Codes.

Warum dieser Ansatz?
- `keyboard.add_hotkey(..., suppress=True)` blockiert das Event → damit kein
  'ö' ins aktive Fenster geschrieben wird wenn Win+Ö als Hotkey dient.
- Scan-Codes (statt Strings) umgehen den Parser, der auf DE-Tastaturen mit
  Umlauten unzuverlaessig ist. Umlaute sind positional, also layout-stabil.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

import keyboard

logger = logging.getLogger(__name__)

# Windows Scan-Codes fuer DE-Tastatur (positional, layout-unabhaengig)
_UMLAUT_SCAN_CODES = {
    "ö": 39,   # 0x27
    "ä": 40,   # 0x28
    "ü": 26,   # 0x1A
    "ß": 12,   # 0x0C
}

_MODIFIER_ALIASES = {
    "ctrl": "ctrl", "control": "ctrl", "strg": "ctrl",
    "alt": "alt",
    "shift": "shift", "umschalt": "shift",
    "windows": "windows", "win": "windows", "cmd": "windows",
    "command": "windows", "meta": "windows", "super": "windows",
}


def _to_scan_code_steps(combo: str) -> list[tuple[int, ...]]:
    """'windows+ö' → [(91, 92), (39,)]

    Jedes Step ist ein Tuple gleichwertiger Scan-Codes (left/right Varianten).
    """
    parts = [p.strip() for p in combo.split("+") if p.strip()]
    steps: list[tuple[int, ...]] = []
    for part in parts:
        low = part.lower()
        if low in _MODIFIER_ALIASES:
            mod = _MODIFIER_ALIASES[low]
            codes = tuple(keyboard.key_to_scan_codes(mod))
            if not codes:
                raise ValueError(f"Keine Scan-Codes fuer Modifier '{mod}'")
            steps.append(codes)
        elif low in _UMLAUT_SCAN_CODES:
            steps.append((_UMLAUT_SCAN_CODES[low],))
        elif low.startswith("#") and low[1:].isdigit():
            steps.append((int(low[1:]),))
        elif len(low) == 1 or low in {"space", "enter", "tab", "esc", "escape",
                                       "backspace", "delete", "insert", "home", "end",
                                       "pageup", "pagedown", "up", "down", "left", "right",
                                       "pause", "caps lock", "num lock", "scroll lock"}:
            codes = tuple(keyboard.key_to_scan_codes(low))
            steps.append(codes if codes else ())
        elif low.startswith("f") and low[1:].isdigit():
            codes = tuple(keyboard.key_to_scan_codes(low))
            steps.append(codes if codes else ())
        else:
            codes = tuple(keyboard.key_to_scan_codes(low))
            steps.append(codes if codes else ())

    if not steps or any(not s for s in steps):
        raise ValueError(f"Kombi '{combo}' konnte nicht vollstaendig aufgeloest werden")
    return steps


class HotkeyListener:
    def __init__(
        self,
        on_start_stop: Callable[[], None],
        on_pause_resume: Callable[[], None],
        on_cancel: Callable[[], None],
        start_stop_combo: str = "windows+ö",
        pause_resume_combo: str = "windows+ä",
        cancel_combo: str = "esc",
    ) -> None:
        self._on_start_stop = on_start_stop
        self._on_pause_resume = on_pause_resume
        self._on_cancel = on_cancel
        self.start_stop_combo = start_stop_combo
        self.pause_resume_combo = pause_resume_combo
        self.cancel_combo = cancel_combo

        self._handles: list = []
        self._cancel_handle = None

    def _safe(self, fn: Callable[[], None], name: str) -> Callable[[], None]:
        def wrapped() -> None:
            logger.debug("Hotkey feuert: %s", name)
            try:
                fn()
            except Exception:
                logger.exception("Fehler im Hotkey-Handler %s", name)
        return wrapped

    def _register(self, combo: str, callback: Callable[[], None], name: str,
                  suppress: bool) -> None:
        try:
            steps = _to_scan_code_steps(combo)
        except Exception:
            logger.exception("Hotkey %s (%s) konnte nicht aufgeloest werden", name, combo)
            return

        try:
            handle = keyboard.add_hotkey(
                steps,
                self._safe(callback, name),
                suppress=suppress,
                trigger_on_release=False,
            )
        except Exception:
            logger.exception("Hotkey %s (%s) konnte nicht registriert werden", name, combo)
            return

        self._handles.append(handle)
        logger.info("Registriert: %-12s = %-18s suppress=%s steps=%s",
                    name, combo, suppress, steps)

    def start(self) -> None:
        # Haupt-Hotkeys MIT suppress → kein Zeichen-Echo ins aktive Fenster
        self._register(self.start_stop_combo, self._on_start_stop, "start_stop", suppress=True)
        self._register(self.pause_resume_combo, self._on_pause_resume, "pause_resume", suppress=True)
        logger.info("Hotkeys aktiv (Cancel %s wird nur waehrend Aufnahme registriert)",
                    self.cancel_combo)

    def enable_cancel(self) -> None:
        if self._cancel_handle is not None:
            return
        try:
            # ESC ohne suppress — sonst schluckt fux-voice ESC in allen Apps
            steps = _to_scan_code_steps(self.cancel_combo)
            self._cancel_handle = keyboard.add_hotkey(
                steps,
                self._safe(self._on_cancel, "cancel"),
                suppress=False,
                trigger_on_release=False,
            )
            logger.info("Cancel-Hotkey aktiv: %s", self.cancel_combo)
        except Exception:
            logger.exception("Cancel-Hotkey %s konnte nicht registriert werden",
                             self.cancel_combo)

    def disable_cancel(self) -> None:
        if self._cancel_handle is not None:
            try:
                keyboard.remove_hotkey(self._cancel_handle)
            except Exception:
                pass
            self._cancel_handle = None

    def stop(self) -> None:
        for h in self._handles:
            try:
                keyboard.remove_hotkey(h)
            except Exception:
                pass
        self._handles = []
        self.disable_cancel()
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

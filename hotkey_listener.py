"""Globale Hotkeys mit Event-Suppression via keyboard-Library.

Umlaute als Scan-Code-Syntax (`#NN`) — umgeht den fragilen keyboard-Parser,
der auf DE-Tastaturen Buchstaben wie 'ö' nicht zuverlaessig aufloest.

Beispiel: 'windows+ö' → 'windows+#39' (Scan-Code 39 = Ö auf DE-Layout)
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

import keyboard

logger = logging.getLogger(__name__)

# Windows Scan-Codes fuer DE-Tastatur (positional)
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


def _normalize_combo(combo: str):
    """'windows+ö' → ('windows', 39)

    Gibt einen TUPLE zurueck (hashable fuer keyboard._hotkeys dict).
    String-Parts (Modifier, Named Keys wie 'space', 'f9', 'esc') bleiben
    Strings; Umlaute werden zu ints (Scan-Codes) umgesetzt. Die
    keyboard-Library parst intern jeden Part via key_to_scan_codes():
    ints werden direkt als Scan-Code uebernommen, strings aufgeloest.
    """
    parts = [p.strip() for p in combo.split("+") if p.strip()]
    out: list = []
    for part in parts:
        low = part.lower()
        if low in _MODIFIER_ALIASES:
            out.append(_MODIFIER_ALIASES[low])
        elif low in _UMLAUT_SCAN_CODES:
            out.append(_UMLAUT_SCAN_CODES[low])  # int
        elif low.startswith("#") and low[1:].isdigit():
            out.append(int(low[1:]))  # int
        else:
            out.append(low)
    if not out:
        raise ValueError(f"Leerer Hotkey: '{combo}'")
    if len(out) == 1 and isinstance(out[0], str):
        return out[0]
    return tuple(out)


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
            normalized = _normalize_combo(combo)
        except Exception:
            logger.exception("Hotkey %s (%s) konnte nicht normalisiert werden", name, combo)
            return

        try:
            handle = keyboard.add_hotkey(
                normalized,
                self._safe(callback, name),
                suppress=suppress,
                trigger_on_release=False,
            )
        except Exception:
            logger.exception("Hotkey %s (%s → %r) konnte nicht registriert werden",
                             name, combo, normalized)
            return

        self._handles.append(handle)
        logger.info("Registriert: %-12s = %-18s → %r suppress=%s",
                    name, combo, normalized, suppress)

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
            normalized = _normalize_combo(self.cancel_combo)
            # ESC ohne suppress — sonst schluckt fux-voice ESC in allen Apps
            self._cancel_handle = keyboard.add_hotkey(
                normalized,
                self._safe(self._on_cancel, "cancel"),
                suppress=False,
                trigger_on_release=False,
            )
            logger.info("Cancel-Hotkey aktiv: %s → %r", self.cancel_combo, normalized)
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

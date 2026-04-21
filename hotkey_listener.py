"""Globale Hotkeys via keyboard.hook(suppress=True) mit selektivem Return.

Warum nicht keyboard.add_hotkey?
  Der interne String-Parser der keyboard-Library nutzt lokalisierte
  Key-Namen ('linke windows' statt 'left windows' auf deutschem Windows).
  Das fuehrt dazu, dass zwar add_hotkey ohne Fehler durchlaeuft, der
  interne Event-Matcher aber nie trifft.

Dieser Ansatz:
  Ein einziger Low-Level-Hook, selbst geschriebenes Matching gegen
  Scan-Codes. Suppress wird pro Event via Return-Value entschieden
  (True = event durchlassen, False = blockieren).
"""
from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

import keyboard

logger = logging.getLogger(__name__)

# Positionale Scan-Codes — layout-unabhaengig, gueltig auf Windows
_UMLAUT_SCAN_CODES = {
    "ö": 39,
    "ä": 40,
    "ü": 26,
    "ß": 12,
}

# Scan-Codes aller Modifier-Varianten (left/right)
_MODIFIER_SCAN_CODES = {
    "ctrl":    {29, 97},   # 97 ist der "extended" RCtrl
    "alt":     {56, 100},  # LAlt, RAlt (AltGr)
    "shift":   {42, 54},   # LShift, RShift
    "windows": {91, 92},   # LWin, RWin
}

_MODIFIER_ALIASES = {
    "ctrl": "ctrl", "control": "ctrl", "strg": "ctrl",
    "alt": "alt",
    "shift": "shift", "umschalt": "shift",
    "windows": "windows", "win": "windows", "cmd": "windows",
    "command": "windows", "meta": "windows", "super": "windows",
}

_NAMED_KEY_SCAN_CODES = {
    "esc": 1, "escape": 1,
    "space": 57,
    "enter": 28, "return": 28,
    "tab": 15,
    "backspace": 14,
    "delete": 83, "del": 83,
    "insert": 82, "ins": 82,
    "home": 71, "end": 79,
    "pageup": 73, "page_up": 73, "page up": 73,
    "pagedown": 81, "page_down": 81, "page down": 81,
    "up": 72, "down": 80, "left": 75, "right": 77,
    "pause": 69,
    "caps lock": 58, "caps_lock": 58,
    "scroll lock": 70, "scroll_lock": 70,
}
# F1..F12
for _i, _code in enumerate([59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 87, 88], 1):
    _NAMED_KEY_SCAN_CODES[f"f{_i}"] = _code


def _resolve_target(token: str) -> Optional[int]:
    """'ö' → 39, 'f9' → 67, '#39' → 39, 'a' → via keyboard lib."""
    low = token.lower()
    if low in _UMLAUT_SCAN_CODES:
        return _UMLAUT_SCAN_CODES[low]
    if low.startswith("#") and low[1:].isdigit():
        return int(low[1:])
    if low in _NAMED_KEY_SCAN_CODES:
        return _NAMED_KEY_SCAN_CODES[low]
    if len(low) == 1:
        try:
            codes = keyboard.key_to_scan_codes(low)
            return codes[0] if codes else None
        except Exception:
            return None
    return None


def _parse_combo(combo: str) -> tuple[set, int]:
    """'windows+ö' → ({'windows'}, 39)"""
    parts = [p.strip() for p in combo.split("+") if p.strip()]
    modifiers: set = set()
    target: Optional[int] = None
    for part in parts:
        low = part.lower()
        if low in _MODIFIER_ALIASES:
            modifiers.add(_MODIFIER_ALIASES[low])
        else:
            t = _resolve_target(part)
            if t is None:
                raise ValueError(f"Unbekannter Key: {part!r} in {combo!r}")
            target = t
    if target is None:
        raise ValueError(f"Kein Target-Key in {combo!r}")
    return modifiers, target


class _Binding:
    __slots__ = ("modifiers", "target_scan_code", "callback", "name", "suppress", "held")

    def __init__(self, modifiers: set, target: int,
                 callback: Callable[[], None], name: str, suppress: bool) -> None:
        self.modifiers = modifiers
        self.target_scan_code = target
        self.callback = callback
        self.name = name
        self.suppress = suppress
        self.held = False


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

        self._bindings: list[_Binding] = []
        self._cancel_binding: Optional[_Binding] = None
        self._modifiers_pressed: set = set()
        self._hook_handle = None

    def _active_bindings(self) -> list[_Binding]:
        if self._cancel_binding:
            return self._bindings + [self._cancel_binding]
        return self._bindings

    @staticmethod
    def _scancode_to_modifier(sc: int) -> Optional[str]:
        for name, codes in _MODIFIER_SCAN_CODES.items():
            if sc in codes:
                return name
        return None

    def _on_event(self, event) -> bool:
        """Return True = Event durchlassen, False = blockieren."""
        try:
            sc = event.scan_code
            etype = event.event_type

            # Modifier-State tracken (immer durchlassen)
            mod = self._scancode_to_modifier(sc)
            if mod:
                if etype == keyboard.KEY_DOWN:
                    self._modifiers_pressed.add(mod)
                elif etype == keyboard.KEY_UP:
                    self._modifiers_pressed.discard(mod)
                return True

            # KEY_UP: held-Flag zuruecksetzen
            if etype == keyboard.KEY_UP:
                for b in self._active_bindings():
                    if b.target_scan_code == sc:
                        b.held = False
                return True

            if etype != keyboard.KEY_DOWN:
                return True

            # KEY_DOWN: bindings checken
            for b in self._active_bindings():
                if b.target_scan_code != sc:
                    continue
                if not b.modifiers.issubset(self._modifiers_pressed):
                    # Richtiger Key, aber Modifier-Stand passt nicht
                    continue

                # Match — Auto-repeat nur suppressen, nicht nochmal feuern
                if b.held:
                    return not b.suppress

                b.held = True
                logger.info("Hotkey feuert: %s", b.name)
                # Callback in Thread ausfuehren, damit der Hook nicht blockiert
                threading.Thread(target=self._run_callback, args=(b,), daemon=True).start()

                return not b.suppress

            return True
        except Exception:
            logger.exception("Fehler in _on_event")
            return True

    def _run_callback(self, b: _Binding) -> None:
        try:
            b.callback()
        except Exception:
            logger.exception("Fehler im Hotkey-Handler %s", b.name)

    def _build_bindings(self) -> None:
        self._bindings = []
        for combo, cb, name, suppress in [
            (self.start_stop_combo, self._on_start_stop, "start_stop", True),
            (self.pause_resume_combo, self._on_pause_resume, "pause_resume", True),
        ]:
            try:
                mods, target = _parse_combo(combo)
                self._bindings.append(_Binding(mods, target, cb, name, suppress))
                logger.info(
                    "Registriert: %-12s = %-18s (mods=%s, scan_code=%d, suppress=%s)",
                    name, combo, sorted(mods), target, suppress,
                )
            except Exception:
                logger.exception("Hotkey %s=%s konnte nicht geparst werden", name, combo)

    def start(self) -> None:
        self._build_bindings()
        try:
            self._hook_handle = keyboard.hook(self._on_event, suppress=True)
            logger.info("Low-Level-Hook aktiv (selektives suppress)")
        except Exception:
            logger.exception("Hook konnte nicht installiert werden")

    def enable_cancel(self) -> None:
        if self._cancel_binding is not None:
            return
        try:
            mods, target = _parse_combo(self.cancel_combo)
            self._cancel_binding = _Binding(mods, target, self._on_cancel, "cancel", suppress=False)
            logger.info("Cancel-Hotkey aktiv: %s (scan_code=%d)", self.cancel_combo, target)
        except Exception:
            logger.exception("Cancel-Hotkey %s konnte nicht geparst werden", self.cancel_combo)

    def disable_cancel(self) -> None:
        self._cancel_binding = None

    def stop(self) -> None:
        self._bindings = []
        self._cancel_binding = None
        if self._hook_handle is not None:
            try:
                keyboard.unhook(self._hook_handle)
            except Exception:
                pass
            self._hook_handle = None


# -----------------------------------------------------------------------
# Diagnose-Hilfe
# -----------------------------------------------------------------------

def start_diagnostic(duration_s: int = 30) -> None:
    """Loggt alle KEY_DOWN-Events fuer N Sekunden (parallel zu HotkeyListener)."""
    logger.info("=" * 60)
    logger.info("HOTKEY-DIAGNOSE aktiv fuer %d Sekunden", duration_s)
    logger.info("Druecke deine Hotkey-Kombination")
    logger.info("=" * 60)

    stop_flag = {"stop": False}
    hook_ref = {"h": None}

    def diag_hook(event):
        if stop_flag["stop"]:
            return
        if event.event_type != keyboard.KEY_DOWN:
            return
        logger.info(
            "DIAG KEY_DOWN: scan_code=%-4s name=%-25r is_keypad=%s",
            event.scan_code, event.name, getattr(event, "is_keypad", None),
        )

    try:
        hook_ref["h"] = keyboard.hook(diag_hook)
    except Exception:
        logger.exception("Diag-Hook konnte nicht installiert werden")
        return

    def _stop() -> None:
        stop_flag["stop"] = True
        try:
            if hook_ref["h"]:
                keyboard.unhook(hook_ref["h"])
        except Exception:
            pass
        logger.info("HOTKEY-DIAGNOSE beendet")

    timer = threading.Timer(duration_s, _stop)
    timer.daemon = True
    timer.start()

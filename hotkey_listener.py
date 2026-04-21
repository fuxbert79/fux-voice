"""Globale Hotkey-Registrierung via pynput (whisper-writer Pattern).

Warum pynput statt keyboard?
- Robust auf deutschen Tastaturen (Umlaute funktionieren via VK-Code)
- Keine Admin-Rechte noetig
- Pressed-Set + Subset-Check statt fragiler String-Parser

Unterstuetzte Hotkey-Syntax:
  ctrl+shift+a       Modifier + Standard-Key
  windows+ö          Modifier + Umlaut (DE-Layout via VK)
  ctrl+f9            Modifier + F-Key
  windows+#220       Modifier + direkter VK-Code (Fallback)
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from pynput import keyboard as pk

logger = logging.getLogger(__name__)

# Windows Virtual-Key-Codes fuer deutsche Umlaute (DE-Layout)
_VK_UMLAUTE_WIN = {
    "ö": 0xC0,  # VK_OEM_3
    "ä": 0xDE,  # VK_OEM_7
    "ü": 0xBA,  # VK_OEM_1
    "ß": 0xDB,  # VK_OEM_4
}

_MODIFIER_ALIASES = {
    "ctrl": "ctrl", "control": "ctrl", "strg": "ctrl",
    "alt": "alt",
    "shift": "shift", "umschalt": "shift",
    "windows": "windows", "win": "windows", "cmd": "windows",
    "command": "windows", "meta": "windows", "super": "windows",
}

# Named special keys, die pynput direkt als pk.Key.* anbietet
_SPECIAL_KEYS: dict[str, object] = {
    "space": pk.Key.space,
    "enter": pk.Key.enter, "return": pk.Key.enter,
    "tab": pk.Key.tab,
    "esc": pk.Key.esc, "escape": pk.Key.esc,
    "backspace": pk.Key.backspace,
    "delete": pk.Key.delete, "del": pk.Key.delete,
    "insert": pk.Key.insert, "ins": pk.Key.insert,
    "home": pk.Key.home, "end": pk.Key.end,
    "page_up": pk.Key.page_up, "pageup": pk.Key.page_up,
    "page_down": pk.Key.page_down, "pagedown": pk.Key.page_down,
    "up": pk.Key.up, "down": pk.Key.down,
    "left": pk.Key.left, "right": pk.Key.right,
    "pause": pk.Key.pause,
    "caps_lock": pk.Key.caps_lock,
    "num_lock": pk.Key.num_lock,
    "scroll_lock": pk.Key.scroll_lock,
    "print_screen": pk.Key.print_screen,
}
for _i in range(1, 13):
    _SPECIAL_KEYS[f"f{_i}"] = getattr(pk.Key, f"f{_i}")


def _normalize_modifier(key) -> Optional[str]:
    """Pynput-Modifier → standardisierter Name oder None."""
    if not isinstance(key, pk.Key):
        return None
    if key in (pk.Key.ctrl_l, pk.Key.ctrl_r, pk.Key.ctrl):
        return "ctrl"
    if key in (pk.Key.alt_l, pk.Key.alt_r, pk.Key.alt):
        return "alt"
    alt_gr = getattr(pk.Key, "alt_gr", None)
    if alt_gr is not None and key == alt_gr:
        return "alt"
    if key in (pk.Key.shift_l, pk.Key.shift_r, pk.Key.shift):
        return "shift"
    if key in (pk.Key.cmd_l, pk.Key.cmd_r, pk.Key.cmd):
        return "windows"
    return None


class _ParsedCombo:
    """'windows+ö' → Modifiers-Set + Target-Matcher."""

    __slots__ = ("modifiers", "target_char", "target_key", "target_vk", "raw")

    def __init__(self, combo: str) -> None:
        self.raw = combo
        self.modifiers: set[str] = set()
        self.target_char: Optional[str] = None
        self.target_key = None
        self.target_vk: Optional[int] = None

        parts = [p.strip() for p in combo.split("+") if p.strip()]
        target: Optional[str] = None

        for part in parts:
            low = part.lower()
            if low in _MODIFIER_ALIASES:
                self.modifiers.add(_MODIFIER_ALIASES[low])
            else:
                target = part

        if target is None:
            raise ValueError(f"Kein Target-Key im Hotkey '{combo}'")

        low = target.lower()
        if low in _SPECIAL_KEYS:
            self.target_key = _SPECIAL_KEYS[low]
        elif low in _VK_UMLAUTE_WIN:
            self.target_char = low
            self.target_vk = _VK_UMLAUTE_WIN[low]
        elif low.startswith("#") and low[1:].isdigit():
            self.target_vk = int(low[1:])
        elif len(low) == 1:
            self.target_char = low
        else:
            self.target_char = low

    def matches(self, key) -> bool:
        if self.target_key is not None:
            return key == self.target_key

        if not isinstance(key, pk.KeyCode):
            return False

        if self.target_vk is not None and key.vk is not None and key.vk == self.target_vk:
            return True

        if self.target_char is not None and key.char is not None:
            if key.char.lower() == self.target_char:
                return True

        return False

    def describe(self) -> str:
        return (f"mods={sorted(self.modifiers)}, "
                f"char={self.target_char!r}, vk={self.target_vk}, "
                f"special={self.target_key}")


class _Binding:
    __slots__ = ("combo", "callback", "name", "held")

    def __init__(self, combo: _ParsedCombo, callback: Callable[[], None], name: str) -> None:
        self.combo = combo
        self.callback = callback
        self.name = name
        self.held = False


class HotkeyListener:
    """Public API — nutzt einen einzigen pynput Listener fuer alle Bindings."""

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

        self._modifiers_active: set[str] = set()
        self._main_bindings: list[_Binding] = []
        self._cancel_binding: Optional[_Binding] = None
        self._listener: Optional[pk.Listener] = None

    def _all_bindings(self) -> list[_Binding]:
        if self._cancel_binding is not None:
            return self._main_bindings + [self._cancel_binding]
        return self._main_bindings

    def _on_press(self, key) -> None:
        try:
            mod = _normalize_modifier(key)
            if mod:
                self._modifiers_active.add(mod)
                return

            for binding in self._all_bindings():
                if binding.held:
                    continue
                if not binding.combo.matches(key):
                    continue
                if not binding.combo.modifiers.issubset(self._modifiers_active):
                    continue

                binding.held = True
                logger.debug("Hotkey feuert: %s", binding.name)
                try:
                    binding.callback()
                except Exception:
                    logger.exception("Fehler im Callback %s", binding.name)
        except Exception:
            logger.exception("Fehler in _on_press")

    def _on_release(self, key) -> None:
        try:
            mod = _normalize_modifier(key)
            if mod:
                self._modifiers_active.discard(mod)
                return

            for binding in self._all_bindings():
                if binding.combo.matches(key):
                    binding.held = False
        except Exception:
            logger.exception("Fehler in _on_release")

    def _parse_main(self) -> None:
        self._main_bindings = []
        for combo, cb, name in [
            (self.start_stop_combo, self._on_start_stop, "start_stop"),
            (self.pause_resume_combo, self._on_pause_resume, "pause_resume"),
        ]:
            try:
                parsed = _ParsedCombo(combo)
                self._main_bindings.append(_Binding(parsed, cb, name))
                logger.info("Registriert: %-12s = %-20s (%s)", name, combo, parsed.describe())
            except Exception:
                logger.exception("Hotkey %s=%s konnte nicht geparst werden", name, combo)

    def start(self) -> None:
        self._parse_main()
        self._listener = pk.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()
        logger.info("pynput Listener aktiv (Cancel %s wird nur waehrend Aufnahme scharf geschaltet)",
                    self.cancel_combo)

    def enable_cancel(self) -> None:
        if self._cancel_binding is not None:
            return
        try:
            parsed = _ParsedCombo(self.cancel_combo)
            self._cancel_binding = _Binding(parsed, self._on_cancel, "cancel")
            logger.info("Cancel-Hotkey aktiv: %s", self.cancel_combo)
        except Exception:
            logger.exception("Cancel-Hotkey %s konnte nicht geparst werden", self.cancel_combo)

    def disable_cancel(self) -> None:
        self._cancel_binding = None

    def stop(self) -> None:
        self._main_bindings = []
        self._cancel_binding = None
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

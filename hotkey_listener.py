"""Registriert globale Hotkeys (Windows-weit, auch im Terminal)."""
from __future__ import annotations

import logging
from typing import Callable

import keyboard

logger = logging.getLogger(__name__)


class HotkeyListener:
    """Registriert Hotkeys und feuert Callbacks."""

    def __init__(
        self,
        on_start_stop: Callable[[], None],
        on_pause_resume: Callable[[], None],
        on_cancel: Callable[[], None],
        start_stop_combo: str = "ctrl+shift+space",
        pause_resume_combo: str = "ctrl+shift+p",
        cancel_combo: str = "esc",
    ) -> None:
        self._on_start_stop = on_start_stop
        self._on_pause_resume = on_pause_resume
        self._on_cancel = on_cancel
        self.start_stop_combo = start_stop_combo
        self.pause_resume_combo = pause_resume_combo
        self.cancel_combo = cancel_combo

        self._cancel_hotkey_handle = None

    def _safe(self, fn: Callable[[], None], name: str) -> Callable[[], None]:
        def wrapped() -> None:
            logger.debug("Hotkey ausgeloest: %s", name)
            try:
                fn()
            except Exception:
                logger.exception("Fehler im Hotkey-Handler %s", name)
        return wrapped

    def start(self) -> None:
        try:
            keyboard.add_hotkey(self.start_stop_combo, self._safe(self._on_start_stop, "start_stop"))
            logger.info("Registriert: Start/Stop = %s", self.start_stop_combo)
        except Exception:
            logger.exception("Hotkey %s konnte nicht registriert werden", self.start_stop_combo)

        try:
            keyboard.add_hotkey(self.pause_resume_combo, self._safe(self._on_pause_resume, "pause_resume"))
            logger.info("Registriert: Pause     = %s", self.pause_resume_combo)
        except Exception:
            logger.exception("Hotkey %s konnte nicht registriert werden", self.pause_resume_combo)

        logger.info("Hotkeys aktiv (Cancel %s nur waehrend Aufnahme)", self.cancel_combo)

    def enable_cancel(self) -> None:
        """ESC nur waehrend aktiver Aufnahme registrieren, sonst stoert es."""
        if self._cancel_hotkey_handle is None:
            self._cancel_hotkey_handle = keyboard.add_hotkey(
                self.cancel_combo, self._safe(self._on_cancel, "cancel")
            )

    def disable_cancel(self) -> None:
        if self._cancel_hotkey_handle is not None:
            keyboard.remove_hotkey(self._cancel_hotkey_handle)
            self._cancel_hotkey_handle = None

    def stop(self) -> None:
        keyboard.unhook_all_hotkeys()

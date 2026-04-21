"""Text-Injection via Clipboard + Strg+V (pynput Controller).

Funktioniert universell — auch in Terminals, Browsern, Editoren und
der Claude Code CLI. Die Zwischenablage wird nach dem Paste
wiederhergestellt.
"""
from __future__ import annotations

import logging
import time

import pyperclip
from pynput import keyboard as pk

logger = logging.getLogger(__name__)


class TextInjector:
    def __init__(
        self,
        paste_delay_ms: int = 50,
        restore_clipboard: bool = True,
        add_trailing_space: bool = True,
    ) -> None:
        self.paste_delay_s = paste_delay_ms / 1000.0
        self.restore_clipboard = restore_clipboard
        self.add_trailing_space = add_trailing_space
        self._controller = pk.Controller()

    def inject(self, text: str) -> None:
        if not text:
            return

        if self.add_trailing_space and not text.endswith((" ", "\n", "\t")):
            text = text + " "

        previous_clipboard: str | None = None
        if self.restore_clipboard:
            try:
                previous_clipboard = pyperclip.paste()
            except Exception:
                logger.exception("Zwischenablage-Backup fehlgeschlagen")

        pyperclip.copy(text)
        time.sleep(self.paste_delay_s)

        try:
            with self._controller.pressed(pk.Key.ctrl):
                self._controller.press("v")
                self._controller.release("v")
        except Exception:
            logger.exception("Strg+V konnte nicht gesendet werden")
            return

        if self.restore_clipboard and previous_clipboard is not None:
            time.sleep(self.paste_delay_s)
            try:
                pyperclip.copy(previous_clipboard)
            except Exception:
                logger.exception("Zwischenablage-Wiederherstellung fehlgeschlagen")

"""Text-Injection via Clipboard + Strg+V (keyboard-Library).

Funktioniert universell — auch in Terminals, Browsern, Editoren und
der Claude Code CLI. Die Zwischenablage wird nach dem Paste
wiederhergestellt.
"""
from __future__ import annotations

import logging
import time

import keyboard
import pyperclip

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

    def inject(self, text: str) -> None:
        if not text:
            logger.info("inject: leerer Text, ueberspringe")
            return

        if self.add_trailing_space and not text.endswith((" ", "\n", "\t")):
            text = text + " "

        logger.info("inject: %d Zeichen → Clipboard + Ctrl+V", len(text))

        previous_clipboard: str | None = None
        if self.restore_clipboard:
            try:
                previous_clipboard = pyperclip.paste()
            except Exception:
                logger.exception("Zwischenablage-Backup fehlgeschlagen")

        try:
            pyperclip.copy(text)
        except Exception:
            logger.exception("pyperclip.copy fehlgeschlagen — Text NICHT im Clipboard!")
            return

        time.sleep(self.paste_delay_s)

        try:
            keyboard.send("ctrl+v")
            logger.info("inject: Ctrl+V gesendet")
        except Exception:
            logger.exception("Strg+V konnte nicht gesendet werden")
            return

        if self.restore_clipboard and previous_clipboard is not None:
            time.sleep(self.paste_delay_s)
            try:
                pyperclip.copy(previous_clipboard)
            except Exception:
                logger.exception("Zwischenablage-Wiederherstellung fehlgeschlagen")

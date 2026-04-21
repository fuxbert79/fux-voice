"""Fuegt Text in das aktive Fenster ein via Clipboard + Strg+V.

Funktioniert universell — auch in Terminals, Browsern, Editoren und
der Claude Code CLI.
"""
from __future__ import annotations

import logging
import time

import keyboard
import pyperclip

logger = logging.getLogger(__name__)


class TextInjector:
    """Kapselt Clipboard-basiertes Einfuegen."""

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
        """Schreibt Text ins aktive Fenster."""
        if not text:
            return

        if self.add_trailing_space and not text.endswith((" ", "\n", "\t")):
            text = text + " "

        previous_clipboard: str | None = None
        if self.restore_clipboard:
            try:
                previous_clipboard = pyperclip.paste()
            except Exception:
                logger.exception("Konnte vorige Zwischenablage nicht lesen")

        pyperclip.copy(text)
        time.sleep(self.paste_delay_s)

        try:
            keyboard.send("ctrl+v")
        except Exception:
            logger.exception("Strg+V konnte nicht gesendet werden")
            return

        if self.restore_clipboard and previous_clipboard is not None:
            time.sleep(self.paste_delay_s)
            try:
                pyperclip.copy(previous_clipboard)
            except Exception:
                logger.exception("Zwischenablage konnte nicht wiederhergestellt werden")

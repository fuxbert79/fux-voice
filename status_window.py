"""Rechts-unten Status-Fenster waehrend aktiver Aufnahme.

Frameless tkinter-Toplevel, zeigt Status-Indikator, Statustext und
Lauf-Timer. Oeffnet bei Aufnahme-Start, schliesst sich bei IDLE.
"""
from __future__ import annotations

import logging
import threading
import time
import tkinter as tk
from typing import Optional

logger = logging.getLogger(__name__)

_BG_COLOR = "#1a1a1a"
_FG_COLOR = "#ffffff"
_SUB_COLOR = "#bbbbbb"
_BORDER_COLOR = "#303030"

_STATE_COLORS = {
    "recording": "#e64545",
    "paused": "#f0b500",
    "transcribing": "#3c82f0",
}

_STATE_LABELS = {
    "recording": "● Aufnahme läuft",
    "paused": "⏸ Pausiert",
    "transcribing": "⏳ Transkribiere …",
}


class StatusWindow:
    """Ein Floating-Fenster rechts unten, das den Aufnahme-Status anzeigt."""

    WIDTH = 280
    HEIGHT = 76
    MARGIN_RIGHT = 16
    MARGIN_BOTTOM = 70  # Platz fuer Taskleiste

    def __init__(self) -> None:
        self._root: Optional[tk.Tk] = None
        self._status_var: Optional[tk.StringVar] = None
        self._timer_var: Optional[tk.StringVar] = None
        self._indicator_canvas: Optional[tk.Canvas] = None
        self._indicator_circle = None
        self._thread: Optional[threading.Thread] = None
        self._ui_ready = threading.Event()
        self._current_state = "idle"
        self._recording_start: float = 0.0
        self._paused_accum: float = 0.0
        self._pause_start: float = 0.0
        self._running = False
        self._lock = threading.Lock()

    # -------------------------- Public API --------------------------

    def show(self, state: str = "recording") -> None:
        """Zeigt das Fenster (asynchron im UI-Thread)."""
        with self._lock:
            if self._root is None:
                self._recording_start = time.time()
                self._paused_accum = 0.0
                self._running = True
                self._thread = threading.Thread(target=self._run_ui, daemon=True)
                self._thread.start()
                self._ui_ready.wait(timeout=2.0)
        self.set_state(state)

    def set_state(self, state: str) -> None:
        """Aktualisiert Indikator + Status-Text."""
        self._current_state = state
        if self._root is None:
            return

        def _update() -> None:
            color = _STATE_COLORS.get(state, "#808080")
            label = _STATE_LABELS.get(state, state)
            if self._indicator_canvas and self._indicator_circle:
                self._indicator_canvas.itemconfig(self._indicator_circle, fill=color)
            if self._status_var:
                self._status_var.set(label)

            now = time.time()
            if state == "paused" and self._pause_start == 0.0:
                self._pause_start = now
            elif state == "recording" and self._pause_start > 0.0:
                self._paused_accum += now - self._pause_start
                self._pause_start = 0.0
            elif state == "transcribing":
                if self._timer_var:
                    self._timer_var.set("")

        try:
            self._root.after(0, _update)
        except Exception:
            pass

    def hide(self) -> None:
        """Schliesst das Fenster."""
        with self._lock:
            self._running = False
            if self._root is None:
                return
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass
            self._root = None
            self._ui_ready.clear()

    # -------------------------- Intern --------------------------

    def _run_ui(self) -> None:
        try:
            self._root = tk.Tk()
            self._root.overrideredirect(True)
            self._root.attributes("-topmost", True)
            try:
                self._root.attributes("-alpha", 0.96)
            except Exception:
                pass

            sw = self._root.winfo_screenwidth()
            sh = self._root.winfo_screenheight()
            x = sw - self.WIDTH - self.MARGIN_RIGHT
            y = sh - self.HEIGHT - self.MARGIN_BOTTOM
            self._root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

            # Aussen-Rahmen (simuliert duennen Border)
            outer = tk.Frame(self._root, bg=_BORDER_COLOR, bd=0)
            outer.pack(fill="both", expand=True)
            inner = tk.Frame(outer, bg=_BG_COLOR, bd=0)
            inner.pack(fill="both", expand=True, padx=1, pady=1)

            content = tk.Frame(inner, bg=_BG_COLOR)
            content.pack(fill="both", expand=True, padx=14, pady=10)

            # Status-Indikator-Kreis
            self._indicator_canvas = tk.Canvas(
                content, width=18, height=18,
                bg=_BG_COLOR, highlightthickness=0,
            )
            self._indicator_canvas.pack(side="left", padx=(0, 12))
            self._indicator_circle = self._indicator_canvas.create_oval(
                2, 2, 16, 16, fill=_STATE_COLORS["recording"], outline="",
            )

            # Text-Spalte
            text_col = tk.Frame(content, bg=_BG_COLOR)
            text_col.pack(side="left", fill="both", expand=True)

            self._status_var = tk.StringVar(value=_STATE_LABELS["recording"])
            tk.Label(
                text_col, textvariable=self._status_var,
                fg=_FG_COLOR, bg=_BG_COLOR,
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).pack(fill="x")

            self._timer_var = tk.StringVar(value="00:00")
            tk.Label(
                text_col, textvariable=self._timer_var,
                fg=_SUB_COLOR, bg=_BG_COLOR,
                font=("Consolas", 10),
                anchor="w",
            ).pack(fill="x", pady=(2, 0))

            # App-Label rechts
            tk.Label(
                content, text="fux-voice",
                fg="#606060", bg=_BG_COLOR,
                font=("Segoe UI", 8),
            ).pack(side="right", anchor="se")

            self._ui_ready.set()
            self._tick()
            self._root.mainloop()
        except Exception:
            logger.exception("Status-Fenster UI-Thread crashed")
            self._ui_ready.set()

    def _tick(self) -> None:
        if not self._running or self._root is None:
            return
        try:
            if self._current_state in ("recording", "paused"):
                now = time.time()
                running_time = now - self._recording_start - self._paused_accum
                if self._current_state == "paused" and self._pause_start > 0.0:
                    running_time -= (now - self._pause_start)
                running_time = max(0.0, running_time)
                mm, ss = divmod(int(running_time), 60)
                if self._timer_var:
                    self._timer_var.set(f"{mm:02d}:{ss:02d}")
            self._root.after(250, self._tick)
        except Exception:
            pass

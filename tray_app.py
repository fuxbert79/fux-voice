"""Tray-Icon + State-Machine fuer fux-voice.

Orchestriert: Hotkey → Recorder → Transcriber → TextInjector.
Icon-Farbe visualisiert den Zustand.
"""
from __future__ import annotations

import logging
import threading
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw
from pystray import Icon as TrayIcon
from pystray import Menu, MenuItem

from audio_recorder import AudioRecorder
from config import ENV_PATH, ASSETS_DIR
from config_dialog import show_config_dialog
from hotkey_listener import HotkeyListener
from text_injector import TextInjector
from transcriber import WhisperTranscriber

logger = logging.getLogger(__name__)


class State(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    TRANSCRIBING = "transcribing"


_STATE_COLORS = {
    State.IDLE: None,
    State.RECORDING: (220, 50, 50, 255),
    State.PAUSED: (240, 190, 40, 255),
    State.TRANSCRIBING: (60, 130, 230, 255),
}

_STATE_TOOLTIPS = {
    State.IDLE: "fux-voice — bereit",
    State.RECORDING: "fux-voice — Aufnahme laeuft",
    State.PAUSED: "fux-voice — pausiert",
    State.TRANSCRIBING: "fux-voice — transkribiere …",
}


class FuxVoiceTrayApp:
    """Haupt-Anwendung: Tray + State-Machine."""

    def __init__(self, config: dict, icon_path: Path) -> None:
        self.config = config
        self.icon_path = icon_path
        self._base_icon = Image.open(icon_path).convert("RGBA")

        self._state = State.IDLE
        self._state_lock = threading.Lock()
        self._work_lock = threading.Lock()

        self.recorder = AudioRecorder(
            sample_rate=config["audio"]["sample_rate"],
            channels=config["audio"]["channels"],
            device=config["audio"].get("device"),
        )
        self.transcriber: Optional[WhisperTranscriber] = None
        self._rebuild_transcriber()
        self._config_dialog_open = False
        self.injector = TextInjector(
            paste_delay_ms=config["output"]["paste_delay_ms"],
            restore_clipboard=config["output"]["restore_clipboard"],
            add_trailing_space=config["output"]["add_trailing_space"],
        )
        self.hotkeys = HotkeyListener(
            on_start_stop=self._on_hotkey_start_stop,
            on_pause_resume=self._on_hotkey_pause_resume,
            on_cancel=self._on_hotkey_cancel,
            start_stop_combo=config["hotkeys"]["start_stop"],
            pause_resume_combo=config["hotkeys"]["pause_resume"],
            cancel_combo=config["hotkeys"]["cancel"],
        )

        self._tray: Optional[TrayIcon] = None

    def _render_icon(self, state: State) -> Image.Image:
        """Basis-Icon mit Status-Rand-Overlay."""
        img = self._base_icon.copy()
        color = _STATE_COLORS[state]
        if color is None:
            return img

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        w, h = img.size
        border = max(2, min(w, h) // 10)
        for i in range(border):
            draw.rectangle(
                (i, i, w - 1 - i, h - 1 - i),
                outline=color,
            )
        return Image.alpha_composite(img, overlay)

    def _set_state(self, new_state: State) -> None:
        with self._state_lock:
            self._state = new_state
        if self._tray is not None:
            self._tray.icon = self._render_icon(new_state)
            self._tray.title = _STATE_TOOLTIPS[new_state]
        logger.info("State → %s", new_state.value)

    @property
    def state(self) -> State:
        with self._state_lock:
            return self._state

    def _rebuild_transcriber(self) -> None:
        api_key = self.config.get("_openai_api_key", "")
        if not api_key:
            self.transcriber = None
            logger.warning("Kein API-Key gesetzt — Transkription deaktiviert")
            return
        self.transcriber = WhisperTranscriber(
            api_key=api_key,
            model=self.config["whisper"]["model"],
            language=self.config["whisper"]["language"],
            prompt=self.config["whisper"].get("prompt"),
        )

    def _transcribe_and_paste(self, audio: Optional[np.ndarray]) -> None:
        if audio is None or len(audio) == 0:
            return
        if self.transcriber is None:
            logger.warning("Keine Transkription moeglich — API-Key fehlt")
            return
        try:
            text = self.transcriber.transcribe(audio, self.recorder.sample_rate)
        except Exception:
            logger.exception("Transkription fehlgeschlagen")
            return
        if text:
            self.injector.inject(text)

    def _on_hotkey_start_stop(self) -> None:
        with self._work_lock:
            current = self.state
            if current == State.IDLE:
                self._set_state(State.RECORDING)
                self.hotkeys.enable_cancel()
                self.recorder.start()
            elif current in (State.RECORDING, State.PAUSED):
                self.hotkeys.disable_cancel()
                self._set_state(State.TRANSCRIBING)
                audio = self.recorder.stop(discard=False)
                threading.Thread(
                    target=self._finalize,
                    args=(audio,),
                    daemon=True,
                ).start()

    def _finalize(self, audio: Optional[np.ndarray]) -> None:
        try:
            self._transcribe_and_paste(audio)
        finally:
            self._set_state(State.IDLE)

    def _on_hotkey_pause_resume(self) -> None:
        with self._work_lock:
            current = self.state
            if current == State.RECORDING:
                audio = self.recorder.pause_and_flush()
                self._set_state(State.PAUSED)
                threading.Thread(
                    target=self._transcribe_and_paste,
                    args=(audio,),
                    daemon=True,
                ).start()
            elif current == State.PAUSED:
                self.recorder.resume()
                self._set_state(State.RECORDING)

    def _on_hotkey_cancel(self) -> None:
        with self._work_lock:
            if self.state in (State.RECORDING, State.PAUSED):
                logger.info("Aufnahme verworfen (ESC)")
                self.recorder.stop(discard=True)
                self.hotkeys.disable_cancel()
                self._set_state(State.IDLE)

    def _menu_config(self, _icon: TrayIcon, _item) -> None:
        if self._config_dialog_open:
            logger.info("Konfigurations-Dialog bereits geoeffnet")
            return
        threading.Thread(target=self._open_config_dialog, daemon=True).start()

    def _open_config_dialog(self) -> None:
        self._config_dialog_open = True
        icon_path = ASSETS_DIR / "siegai.ico"
        try:
            show_config_dialog(
                env_path=ENV_PATH,
                on_saved=self._on_api_key_saved,
                icon_path=icon_path if icon_path.exists() else None,
            )
        except Exception:
            logger.exception("Konfig-Dialog konnte nicht geoeffnet werden")
        finally:
            self._config_dialog_open = False

    def _on_api_key_saved(self, new_key: str) -> None:
        logger.info("API-Key aktualisiert")
        self.config["_openai_api_key"] = new_key
        self._rebuild_transcriber()

    def _menu_quit(self, icon: TrayIcon, _item) -> None:
        logger.info("Beende fux-voice …")
        self.hotkeys.stop()
        if self.state != State.IDLE:
            self.recorder.stop(discard=True)
        icon.stop()

    def _menu_toggle(self, _icon: TrayIcon, _item) -> None:
        self._on_hotkey_start_stop()

    def _build_menu(self) -> Menu:
        hk = self.config["hotkeys"]
        return Menu(
            MenuItem(f"Aufnahme starten/stoppen  ({hk['start_stop']})", self._menu_toggle, default=True),
            MenuItem(f"Pause / Weiter  ({hk['pause_resume']})", lambda i, _: self._on_hotkey_pause_resume()),
            MenuItem(f"Verwerfen  ({hk['cancel']})", lambda i, _: self._on_hotkey_cancel()),
            Menu.SEPARATOR,
            MenuItem("Konfiguration …", self._menu_config),
            Menu.SEPARATOR,
            MenuItem("Beenden", self._menu_quit),
        )

    def run(self) -> None:
        self.hotkeys.start()
        self._tray = TrayIcon(
            "fux-voice",
            icon=self._render_icon(State.IDLE),
            title=_STATE_TOOLTIPS[State.IDLE],
            menu=self._build_menu(),
        )
        logger.info("Tray gestartet — Hotkey %s", self.config["hotkeys"]["start_stop"])
        self._tray.run()

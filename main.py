"""fux-voice — Windows Speech-to-Text Tray-Tool.

Entry Point. Laedt Config, initialisiert Logging und startet die Tray-App.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from config import ASSETS_DIR, APP_DIR, ENV_PATH, has_api_key, load_config
from config_dialog import show_config_dialog
from tray_app import FuxVoiceTrayApp


def _setup_logging() -> None:
    log_dir = APP_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "fux-voice.log", encoding="utf-8"),
        ],
    )


def main() -> int:
    _setup_logging()
    log = logging.getLogger("fux-voice")
    try:
        config = load_config()
    except Exception as exc:
        log.error("Konfigurationsfehler: %s", exc)
        return 1

    icon_path = ASSETS_DIR / "siegai.ico"
    if not icon_path.exists():
        icon_path = ASSETS_DIR / "siegai.png"
    if not icon_path.exists():
        log.error("Kein Icon gefunden in %s", ASSETS_DIR)
        return 1

    if not has_api_key(config):
        log.info("Kein API-Key gefunden — oeffne Konfigurations-Dialog")
        dialog_icon = ASSETS_DIR / "siegai.ico"
        saved = show_config_dialog(
            env_path=ENV_PATH,
            icon_path=dialog_icon if dialog_icon.exists() else None,
        )
        if saved:
            config = load_config()
        if not has_api_key(config):
            log.info("Kein API-Key gesetzt — App startet trotzdem (Transkription deaktiviert)")

    app = FuxVoiceTrayApp(config=config, icon_path=icon_path)
    try:
        app.run()
    except KeyboardInterrupt:
        log.info("Abbruch durch Benutzer")
    return 0


if __name__ == "__main__":
    sys.exit(main())

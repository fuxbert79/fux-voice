"""fux-voice — Windows Speech-to-Text Tray-Tool.

Entry Point. Laedt Config, initialisiert Logging und startet die Tray-App.
"""
from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path

from config import APP_DIR, ASSETS_DIR, ENV_PATH, LOG_DIR, RESOURCE_DIR, has_api_key, load_config
from config_dialog import show_config_dialog
from tray_app import FuxVoiceTrayApp


def _setup_logging() -> Path:
    """Setzt Logging auf. Gibt den verwendeten Log-Pfad zurueck."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOG_DIR / "fux-voice.log"
    except Exception:
        # Fallback: Logs neben der .exe direkt
        log_file = APP_DIR / "fux-voice.log"

    handlers: list[logging.Handler] = []
    try:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8", mode="a"))
    except Exception:
        pass

    # StreamHandler nur wenn stdout existiert (Windows GUI-Mode: sys.stdout ist None)
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
    return log_file


def main() -> int:
    log_file = _setup_logging()
    log = logging.getLogger("fux-voice")
    log.info("=" * 60)
    log.info("fux-voice startet")
    log.info("Python      : %s", sys.version.split()[0])
    log.info("Executable  : %s", sys.executable)
    log.info("Frozen      : %s", bool(getattr(sys, "frozen", False)))
    log.info("APP_DIR     : %s", APP_DIR)
    log.info("RESOURCE_DIR: %s", RESOURCE_DIR)
    log.info("LOG_DIR     : %s", LOG_DIR)
    log.info("Log-Datei   : %s", log_file)

    try:
        config = load_config()
    except Exception as exc:
        log.error("Konfigurationsfehler: %s", exc)
        log.error(traceback.format_exc())
        return 1

    icon_path = ASSETS_DIR / "siegai.ico"
    if not icon_path.exists():
        icon_path = ASSETS_DIR / "siegai.png"
    if not icon_path.exists():
        log.error("Kein Icon gefunden in %s", ASSETS_DIR)
        return 1

    if not has_api_key(config):
        log.info("Kein API-Key gefunden — oeffne Konfigurations-Dialog")
        saved = show_config_dialog(
            env_path=ENV_PATH,
            icon_path=icon_path if icon_path.exists() else None,
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
    except Exception:
        log.exception("Unbehandelte Exception im Tray-App-Loop")
        return 2
    log.info("fux-voice beendet")
    return 0


if __name__ == "__main__":
    sys.exit(main())

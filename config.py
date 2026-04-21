"""Konfigurations-Loader fuer fux-voice.

Wichtig — Pfade unter PyInstaller:
- `DATA_DIR` (wo .env, config.json, logs hinkommen): Ordner der **.exe**,
  NICHT das temporaere _MEIPASS-Verzeichnis.
- `RESOURCE_DIR` (gebundelte read-only Dateien wie config.json.example,
  assets/*): _MEIPASS bei PyInstaller, Source-Ordner im Dev-Modus.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

APP_NAME = "fux-voice"


def _get_data_dir() -> Path:
    """Persistenter User-Daten-Ordner — .env, config.json, logs.

    Bei PyInstaller-EXE: Ordner der .exe.
    Im Dev-Modus: Source-Root.
    Override via Env-Variable FUX_VOICE_HOME moeglich.
    """
    override = os.environ.get("FUX_VOICE_HOME", "").strip()
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _get_resource_dir() -> Path:
    """Read-only Ressourcen — config.json.example, assets/*.

    Bei PyInstaller: _MEIPASS (entpackter Bundle-Ordner).
    Sonst: Source-Root.
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _get_data_dir()
RESOURCE_DIR = _get_resource_dir()

CONFIG_PATH = APP_DIR / "config.json"
ENV_PATH = APP_DIR / ".env"
LOG_DIR = APP_DIR / "logs"

CONFIG_EXAMPLE_PATH = RESOURCE_DIR / "config.json.example"
ASSETS_DIR = RESOURCE_DIR / "assets"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Rekursives Merge zweier Dicts, override gewinnt."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict[str, Any]:
    """Laedt config.json, faellt auf config.json.example zurueck."""
    # override=True: nach Speichern im Dialog muss der NEUE Key in os.environ.
    # Ohne override behaelt dotenv den ersten (leeren) Wert.
    load_dotenv(ENV_PATH, override=True)
    logger.info("APP_DIR      = %s", APP_DIR)
    logger.info("RESOURCE_DIR = %s", RESOURCE_DIR)
    logger.info("ENV_PATH     = %s (exists=%s)", ENV_PATH, ENV_PATH.exists())
    logger.info("CONFIG_PATH  = %s (exists=%s)", CONFIG_PATH, CONFIG_PATH.exists())

    with CONFIG_EXAMPLE_PATH.open("r", encoding="utf-8") as f:
        defaults = json.load(f)

    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        config = _deep_merge(defaults, user_cfg)
    else:
        logger.info("Keine config.json gefunden — verwende Defaults")
        config = defaults

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key.startswith("sk-proj-...") or api_key.startswith("sk-..."):
        api_key = ""
    config["_openai_api_key"] = api_key
    return config


def has_api_key(config: dict[str, Any]) -> bool:
    return bool(config.get("_openai_api_key"))


def save_user_config(updates: dict[str, Any]) -> None:
    """Merged updates in die user config.json (atomar)."""
    APP_DIR.mkdir(parents=True, exist_ok=True)

    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            current = json.load(f)
    else:
        current = {}

    clean_updates = {k: v for k, v in updates.items() if not k.startswith("_")}
    merged = _deep_merge(current, clean_updates)

    tmp_path = CONFIG_PATH.with_name(CONFIG_PATH.name + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    tmp_path.replace(CONFIG_PATH)
    logger.info("config.json aktualisiert: %s", CONFIG_PATH)

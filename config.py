"""Konfigurations-Loader fuer fux-voice."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

APP_NAME = "fux-voice"
APP_DIR = Path(os.environ.get("FUX_VOICE_HOME", Path(__file__).parent))
CONFIG_PATH = APP_DIR / "config.json"
CONFIG_EXAMPLE_PATH = APP_DIR / "config.json.example"
ENV_PATH = APP_DIR / ".env"
ASSETS_DIR = APP_DIR / "assets"


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
    load_dotenv(ENV_PATH)

    with CONFIG_EXAMPLE_PATH.open("r", encoding="utf-8") as f:
        defaults = json.load(f)

    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        config = _deep_merge(defaults, user_cfg)
    else:
        logger.info("Keine config.json gefunden, verwende Defaults aus config.json.example")
        config = defaults

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key.startswith("sk-proj-...") or api_key.startswith("sk-..."):
        api_key = ""
    config["_openai_api_key"] = api_key
    return config


def has_api_key(config: dict[str, Any]) -> bool:
    return bool(config.get("_openai_api_key"))


def save_user_config(updates: dict[str, Any]) -> None:
    """Merged updates in die user config.json (atomar).

    `updates` ist ein (teilweises) Config-Dict, z.B.
    {"audio": {"device": "Mikrofon XY"}}.
    Interne Felder wie "_openai_api_key" werden ignoriert.
    """
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
    logger.info("config.json aktualisiert (Pfad: %s)", CONFIG_PATH)

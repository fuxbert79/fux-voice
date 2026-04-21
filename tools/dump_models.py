"""Exportiert die exakte Liste der OpenAI-Modelle deines Accounts als Markdown.

Verwendung:
    cd /opt/fux-voice
    python tools/dump_models.py

Schreibt nach: docs/OPENAI_MODELS_MY_ACCOUNT.md

Der API-Key wird aus .env gelesen (gleiche Datei wie fux-voice nutzt).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("Fehler: python-dotenv nicht installiert. Bitte: pip install python-dotenv")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("Fehler: openai-Library nicht installiert. Bitte: pip install openai")
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
OUTPUT_PATH = REPO_ROOT / "docs" / "OPENAI_MODELS_MY_ACCOUNT.md"


# Grobe Kategorisierung basierend auf Modell-ID-Prefix
CATEGORY_RULES = [
    ("Audio · Transkription", lambda m: "transcribe" in m or m == "whisper-1"),
    ("Audio · TTS",           lambda m: "tts" in m or m.startswith("gpt-4o-mini-tts")),
    ("Audio · Realtime/Audio",lambda m: "realtime" in m or "audio" in m),
    ("Reasoning · o-Serie",   lambda m: m.startswith("o1") or m.startswith("o3") or m.startswith("o4")),
    ("Chat · GPT-5.x",        lambda m: m.startswith("gpt-5")),
    ("Chat · GPT-4.1",        lambda m: m.startswith("gpt-4.1")),
    ("Chat · GPT-4o",         lambda m: m.startswith("gpt-4o") or m == "chatgpt-4o-latest"),
    ("Chat · GPT-4 Legacy",   lambda m: m.startswith("gpt-4")),
    ("Chat · GPT-3.5",        lambda m: m.startswith("gpt-3.5")),
    ("Embeddings",            lambda m: "embedding" in m),
    ("Image",                 lambda m: "dall-e" in m or "image" in m),
    ("Video",                 lambda m: m.startswith("sora")),
    ("Moderation",            lambda m: "moderation" in m),
    ("Codex / Coding",        lambda m: "codex" in m),
    ("Computer Use",          lambda m: "computer-use" in m),
    ("Open-Weight",           lambda m: m.startswith("gpt-oss")),
    ("Fine-Tunes",            lambda m: m.startswith("ft:")),
    ("Base",                  lambda m: m in {"babbage-002", "davinci-002"}),
]


def categorize(model_id: str) -> str:
    for cat, rule in CATEGORY_RULES:
        if rule(model_id):
            return cat
    return "Sonstige"


def main() -> int:
    load_dotenv(ENV_PATH)
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-proj-..."):
        print(f"Fehler: Kein gueltiger OPENAI_API_KEY in {ENV_PATH}")
        return 1

    print(f"Rufe models.list() mit Key {api_key[:10]}…{api_key[-5:]} ab …")
    client = OpenAI(api_key=api_key)
    models = client.models.list()
    entries = sorted(models.data, key=lambda m: m.id)
    print(f"  → {len(entries)} Modelle empfangen")

    grouped: dict[str, list] = {}
    for m in entries:
        grouped.setdefault(categorize(m.id), []).append(m)

    lines: list[str] = []
    lines.append("# OpenAI Modelle deines Accounts")
    lines.append("")
    lines.append(f"**Stand:** {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    lines.append(f"**Anzahl:** {len(entries)} Modelle")
    lines.append(f"**Generiert von:** `tools/dump_models.py`")
    lines.append("")
    lines.append("| Kategorie | Anzahl |")
    lines.append("|---|---|")
    for cat in sorted(grouped.keys()):
        lines.append(f"| {cat} | {len(grouped[cat])} |")
    lines.append("")

    for cat in sorted(grouped.keys()):
        lines.append(f"## {cat}")
        lines.append("")
        lines.append("| Modell-ID | Owned By | Created |")
        lines.append("|---|---|---|")
        for m in sorted(grouped[cat], key=lambda x: x.id):
            owner = getattr(m, "owned_by", "")
            created = getattr(m, "created", 0)
            try:
                created_str = datetime.fromtimestamp(created, tz=timezone.utc).strftime("%Y-%m-%d")
            except Exception:
                created_str = ""
            lines.append(f"| `{m.id}` | {owner} | {created_str} |")
        lines.append("")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  → Geschrieben: {OUTPUT_PATH}")
    print(f"  → {len(grouped)} Kategorien")
    return 0


if __name__ == "__main__":
    sys.exit(main())

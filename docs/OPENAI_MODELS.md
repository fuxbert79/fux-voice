# OpenAI Modell-Katalog (Referenz)

**Stand:** April 2026 · Recherche aus [developers.openai.com](https://developers.openai.com/api/docs/models) und offiziellen Release-Announcements.

**Für deine exakte, account-spezifische Liste** (inkl. Fine-Tunes, freigeschaltete Preview-Modelle):
```bash
python tools/dump_models.py
```

Erzeugt `docs/OPENAI_MODELS_MY_ACCOUNT.md` mit allen Modellen, die `OpenAI.models.list()` für deinen API-Key zurückgibt.

---

## Für fux-voice relevant: Speech-to-Text

| Modell-ID | Preis | Anwendung |
|---|---|---|
| **`gpt-4o-transcribe`** | $0.006/min | **Empfohlen** — beste Qualität |
| `gpt-4o-mini-transcribe` | $0.003/min | Günstiger, schneller |
| `gpt-4o-transcribe-diarize` | — | Mit Sprecher-Erkennung |
| `whisper-1` | $0.006/min | Legacy-Modell von 2022 |

---

## Reasoning / Frontier Chat (GPT-5 Familie)

| Model-ID | Kontext | Input $/1M | Output $/1M | Notes |
|---|---|---|---|---|
| `gpt-5.4` | 1M | 2.50 | 15.00 | Flagship, Release 2026-03-05 |
| `gpt-5.4-2026-03-05` | 1M | 2.50 | 15.00 | Dated Snapshot |
| `gpt-5.4-pro` | 272K | 30.00 | 180.00 | Pro-Variante |
| `gpt-5.4-mini` | 400K | 0.75 | 4.50 | Release 2026-03-17 |
| `gpt-5.4-mini-2026-03-17` | 400K | 0.75 | 4.50 | Dated Snapshot |
| `gpt-5.4-nano` | 400K | 0.20 | 1.25 | Release 2026-03-17 |
| `gpt-5.4-nano-2026-03-17` | 400K | 0.20 | 1.25 | Dated Snapshot |
| `gpt-5.3-chat-latest` | 400K | — | — | ChatGPT-Instant |
| `gpt-5.2` | 400K | — | — | Vorherige Frontier |
| `gpt-5.2-pro` | 400K | — | — | Pro-Variante |
| `gpt-5.2-chat-latest` | 400K | — | — | ChatGPT-Variante |
| `gpt-5.1` | 400K | — | — | Bestes Coding-Modell |
| `gpt-5.1-chat-latest` | 400K | — | — | ChatGPT-Variante |
| `gpt-5` | 400K | 1.25 | 10.00 | |
| `gpt-5-2025-08-07` | 400K | 1.25 | 10.00 | Dated Snapshot |
| `gpt-5-pro` | 400K | 15.00 | 120.00 | Mehr Compute |
| `gpt-5-mini` | 400K | 0.25 | 2.00 | Near-frontier |
| `gpt-5-mini-2025-08-07` | 400K | 0.25 | 2.00 | Dated Snapshot |
| `gpt-5-nano` | 400K | 0.05 | 0.40 | Schnellstes GPT-5 |
| `gpt-5-nano-2025-08-07` | 400K | 0.05 | 0.40 | Dated Snapshot |
| `gpt-5-chat-latest` | 400K | — | — | ChatGPT-Variante |

## Reasoning o-Serie

| Model-ID | Kontext | Input $/1M | Output $/1M | Notes |
|---|---|---|---|---|
| `o3` | 200K | 2.00 | 8.00 | |
| `o3-2025-04-16` | 200K | 2.00 | 8.00 | Dated Snapshot |
| `o3-pro` | 200K | 20.00 | 80.00 | |
| `o3-mini` | 200K | 1.10 | 4.40 | |
| `o3-deep-research` | 200K | — | — | Deep-Research-Modus |
| `o4-mini` | 200K | 1.10 | 4.40 | |
| `o4-mini-2025-04-16` | 200K | 1.10 | 4.40 | Dated Snapshot |
| `o4-mini-deep-research` | 200K | — | — | |
| `o1` | 200K | 15.00 | 60.00 | |
| `o1-pro` | 200K | 150.00 | 600.00 | |
| `o1-mini` | 128K | 3.00 | 12.00 | **Deprecated** |
| `o1-preview` | 128K | 15.00 | 60.00 | **Deprecated** |

## Chat GPT-4.1 Familie

| Model-ID | Kontext | Input $/1M | Output $/1M | Notes |
|---|---|---|---|---|
| `gpt-4.1` | 1M | 2.00 | 8.00 | Smartest non-reasoning |
| `gpt-4.1-2025-04-14` | 1M | 2.00 | 8.00 | Dated Snapshot |
| `gpt-4.1-mini` | 1M | 0.40 | 1.60 | |
| `gpt-4.1-mini-2025-04-14` | 1M | 0.40 | 1.60 | Dated Snapshot |
| `gpt-4.1-nano` | 1M | 0.10 | 0.40 | |
| `gpt-4.1-nano-2025-04-14` | 1M | 0.10 | 0.40 | Dated Snapshot |

## Chat GPT-4o Familie

| Model-ID | Kontext | Input $/1M | Output $/1M | Notes |
|---|---|---|---|---|
| `gpt-4o` | 128K | 2.50 | 10.00 | **API-Ende Feb 2026** |
| `gpt-4o-2024-08-06` | 128K | 2.50 | 10.00 | Dated Snapshot |
| `gpt-4o-2024-11-20` | 128K | 2.50 | 10.00 | Dated Snapshot |
| `gpt-4o-2024-05-13` | 128K | 5.00 | 15.00 | Älter |
| `gpt-4o-mini` | 128K | 0.15 | 0.60 | |
| `gpt-4o-mini-2024-07-18` | 128K | 0.15 | 0.60 | Dated Snapshot |
| `chatgpt-4o-latest` | 128K | — | — | **Deprecated 2026-02-17** |
| `gpt-4o-search-preview` | 128K | — | — | Web-Search |
| `gpt-4o-mini-search-preview` | 128K | — | — | |

## Audio / Realtime

| Model-ID | Notes |
|---|---|
| `gpt-realtime-1.5` | Bestes Voice-Modell, aktuell |
| `gpt-realtime` | Realtime Text + Audio |
| `gpt-realtime-mini` | Cost-efficient |
| `gpt-audio-1.5` | Audio mit Chat Completions |
| `gpt-audio` | Audio I/O |
| `gpt-audio-mini` | Cost-efficient |
| `gpt-4o-audio-preview` | **Deprecated 2026-05-07** |
| `gpt-4o-mini-audio-preview` | **Deprecated 2026-05-07** |
| `gpt-4o-realtime-preview` | **Deprecated 2026-05-07** |
| `gpt-4o-realtime-preview-2025-06-03` | **Deprecated** |
| `gpt-4o-realtime-preview-2024-12-17` | **Deprecated** |
| `gpt-4o-mini-realtime-preview` | **Deprecated 2026-05-07** |

## Transcription (Speech-to-Text)

| Model-ID | Notes |
|---|---|
| `gpt-4o-transcribe` | STT powered by GPT-4o |
| `gpt-4o-mini-transcribe` | Kleiner, günstiger |
| `gpt-4o-transcribe-diarize` | Mit Sprecher-Erkennung |
| `whisper-1` | Legacy, $0.006/min |

## Text-to-Speech (TTS)

| Model-ID | Notes |
|---|---|
| `gpt-4o-mini-tts` | Neueste Generation |
| `tts-1` | $15 / 1M chars |
| `tts-1-hd` | $30 / 1M chars, bessere Qualität |

## Embeddings

| Model-ID | Dim | $/1M Tokens |
|---|---|---|
| `text-embedding-3-large` | 3072 | 0.13 |
| `text-embedding-3-small` | 1536 | 0.02 |
| `text-embedding-ada-002` | 1536 | 0.10 |

## Image Generation

| Model-ID | Notes |
|---|---|
| `gpt-image-1.5` | State-of-the-art |
| `gpt-image-1` | Vorherige Generation |
| `gpt-image-1-mini` | Cost-efficient |
| `chatgpt-image-latest` | ChatGPT-Variante |
| `dall-e-3` | **Deprecated 2026-05-12** |
| `dall-e-2` | **Deprecated 2026-05-12** |

## Video Generation (Sora)

| Model-ID | Notes |
|---|---|
| `sora-2` | **Deprecated 2026-09-24** |
| `sora-2-pro` | **Deprecated 2026-09-24** |
| `sora-2-t2v` | Text-to-Video |
| `sora-2-i2v` | Image-to-Video |
| `sora-2-pro-t2v` | Pro T2V |
| `sora-2-pro-i2v` | Pro I2V |

## Moderation

| Model-ID | Notes |
|---|---|
| `omni-moderation-latest` | Text + Bild |
| `omni-moderation-2024-09-26` | Dated Snapshot |
| `text-moderation-latest` | **Deprecated** |
| `text-moderation-stable` | **Deprecated** |
| `text-moderation-007` | **Deprecated** |

## Coding / Codex

| Model-ID | Notes |
|---|---|
| `gpt-5.3-codex` | Aktuelles Top-Coding |
| `gpt-5.2-codex` | Long-horizon tasks |
| `gpt-5.1-codex` | Agentic coding |
| `gpt-5.1-codex-max` | Long-running |
| `gpt-5.1-codex-mini` | Kleiner Codex |
| `gpt-5-codex` | GPT-5 für Codex |
| `gpt-5-codex-mini` | Ersetzt `codex-mini-latest` |
| `codex-mini-latest` | **Deprecated 2026-02-12** |

## Tools / Spezialisiert

| Model-ID | Notes |
|---|---|
| `computer-use-preview` | Computer-Use-Agent |
| `computer-use-preview-2025-03-11` | Dated Snapshot |

## Open-Weight (via API)

| Model-ID | Notes |
|---|---|
| `gpt-oss-120b` | Fits auf einer H100 |
| `gpt-oss-20b` | Mittlere Größe, low latency |

## Chat GPT-4 Legacy

| Model-ID | Kontext | Notes |
|---|---|---|
| `gpt-4-turbo` | 128K | Input $10 / Output $30 |
| `gpt-4-turbo-2024-04-09` | 128K | Dated Snapshot |
| `gpt-4-turbo-preview` | 128K | **Deprecated** |
| `gpt-4-0125-preview` | 128K | **Deprecated 2026-03-26** |
| `gpt-4-1106-preview` | 128K | **Deprecated 2026-03-26** |
| `gpt-4` | 8K | Input $30 / Output $60 |
| `gpt-4-0613` | 8K | Dated Snapshot |
| `gpt-4-0314` | 8K | **Deprecated 2026-03-26** |
| `gpt-4.5-preview` | 128K | **Deprecated** |

## Chat GPT-3.5 Legacy

| Model-ID | Kontext | Notes |
|---|---|---|
| `gpt-3.5-turbo` | 16K | $0.50 / $1.50 |
| `gpt-3.5-turbo-0125` | 16K | Dated Snapshot |
| `gpt-3.5-turbo-1106` | 16K | **Deprecated 2026-09-28** |
| `gpt-3.5-turbo-instruct` | 4K | **Deprecated 2026-09-28** |
| `gpt-3.5-turbo-16k` | 16K | **Deprecated** |

## Base-Modelle (Deprecated)

| Model-ID | Notes |
|---|---|
| `babbage-002` | **Deprecated 2026-09-28** |
| `davinci-002` | **Deprecated 2026-09-28** |

---

## Umfang

Diese Referenz deckt **~115 dokumentierte Modell-IDs** ab. Deine `models.list()` meldet **126** — die Differenz erklärt sich typischerweise durch:
- Weitere Dated Snapshots (z.B. `gpt-4-turbo-2024-01-25`)
- Fine-tuned Modelle auf deinem Account (`ft:gpt-3.5-turbo:...`)
- Preview-Modelle, die account-spezifisch freigeschaltet sind
- Organisationsspezifische Deployments

Für die **exakte** Liste deines Accounts nutze das Dump-Skript:
```bash
cd /opt/fux-voice
python tools/dump_models.py
```

## Quellen

- [OpenAI All Models](https://developers.openai.com/api/docs/models/all)
- [OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations)
- [Introducing GPT-5.4](https://openai.com/index/introducing-gpt-5-4/)
- [Introducing GPT-5.2](https://openai.com/index/introducing-gpt-5-2/)

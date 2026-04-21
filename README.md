# fux-voice

Windows Speech-to-Text Tray-Tool mit SiegAI-Branding. Deutsches Diktat per globalem Hotkey in beliebige Apps — auch im Terminal und in der Claude Code CLI. Powered by OpenAI Whisper.

## Installation (Windows — ein Einzeiler)

Öffne **PowerShell** (kein Admin nötig) und führe aus:

```powershell
irm https://raw.githubusercontent.com/fuxbert79/fux-voice/main/install.ps1 | iex
```

Das Script:
- lädt die neueste `fux-voice.exe` aus den [GitHub Releases](https://github.com/fuxbert79/fux-voice/releases)
- verifiziert die SHA-256-Prüfsumme
- installiert nach `%LOCALAPPDATA%\fux-voice\`
- registriert Autostart (`HKCU\...\Run`)
- erstellt Startmenü-Verknüpfung
- startet die App direkt

Nach dem Start erscheint das SiegAI-Icon rechts unten im Tray. **Rechtsklick → Konfiguration …** öffnet den Dialog für den OpenAI API-Key.

### Upgrade

Derselbe Einzeiler — das Script überschreibt die installierte Version.

### Deinstallation

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/fuxbert79/fux-voice/main/install.ps1))) -Uninstall
```

### Spezifische Version

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/fuxbert79/fux-voice/main/install.ps1))) -Version "v0.1.0"
```

## Features

- **Tray-Icon** mit SiegAI-Logo, farbiger Status-Rand (grau / rot / gelb / blau)
- **Globale Hotkeys** (Defaults):
  - `Windows + Ö` — Aufnahme starten / finalisieren
  - `Windows + Ä` — **Pause = Paste**: fügt aktuellen Block sofort ein und nimmt weiter auf
  - `Esc` — Aufnahme verwerfen (nur während aktiver Aufnahme)
  - Anpassbar via `%LOCALAPPDATA%\fux-voice\config.json`
- **API-Key-Ampel** — Test-Button im Konfig-Dialog prüft sofort, ob der OpenAI-Key & Verbindung funktionieren
- **Mikrofon-Auswahl** — Dropdown aller Eingabegeräte + Pegel-Anzeige, Wechsel live ohne Neustart
- **Über-Dialog** — Tray-Menü → Version, Build-Datum, Credits
- **Konfiguration im Tray** — API-Key via Rechtsklick-Menü hinterlegen, kein Neustart
- **Clipboard-Paste** — universelles Einfügen, Zwischenablage wird wiederhergestellt
- **Deutsche Sprache fix** — kein Auto-Detect, höhere Genauigkeit
- **Funktioniert in jeder App** — auch Windows Terminal, PowerShell, Claude Code CLI

## Pause = Paste Workflow

Der Pause-Hotkey fügt den bisher aufgenommenen Text **sofort** im aktiven Fenster ein und setzt die Aufnahme mit leerem Buffer fort. So kannst du natürlich diktieren: Satz sprechen → Pause → Text erscheint → weitersprechen → finaler Hotkey.

## Anforderungen

- Windows 10 / 11
- Mikrofon
- OpenAI API-Key ([Erstellen](https://platform.openai.com/api-keys))
- Internet-Verbindung (Audio geht an Whisper API)

## Kosten

OpenAI Whisper API: **~0.006 USD / Minute** Audio. Typisch: 0–5 USD / Monat bei normaler Nutzung.

## Build aus den Sources

```cmd
git clone https://github.com/fuxbert79/fux-voice.git
cd fux-voice
installer\build.bat
```

Ergebnis: `dist\fux-voice.exe`. Danach `installer\install.ps1` für lokalen Install.

## Entwicklung

```cmd
git clone https://github.com/fuxbert79/fux-voice.git
cd fux-voice
copy .env.example .env
REM .env editieren, API-Key eintragen
dev\run_dev.bat
```

## Projektstruktur

```
fux-voice/
├── main.py              Entry Point
├── tray_app.py          Tray + State-Machine
├── config_dialog.py     Konfig-Dialog (tkinter)
├── hotkey_listener.py   Globale Hotkeys (keyboard)
├── audio_recorder.py    sounddevice + Pause/Flush
├── transcriber.py       OpenAI Whisper API
├── text_injector.py     Clipboard + Strg+V
├── config.py            Config-Loader
├── assets/              SiegAI-Icons
├── installer/           Build- & Lokal-Install-Skripte
├── install.ps1          Bootstrap-Installer (für irm | iex)
├── .github/workflows/   CI: baut .exe bei v*-Tag
└── dev/                 Dev-Helpers
```

## DSGVO-Hinweis

Audio wird **pro Aufnahme** an OpenAI gesendet (US-Server). Für einen vollständig lokalen Betrieb ist die Integration von [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) in `transcriber.py` vorbereitet (aktuell nicht aktiv).

## Release erstellen (Maintainer)

```bash
git tag v0.1.0
git push --tags
```

GitHub Actions baut die `.exe` auf `windows-latest`, berechnet SHA-256 und hängt beides ans Release.

## Teil des fux-framework

fux-voice ist Teil des [fux-framework](https://github.com/fuxbert79/fux-framework) Ökosystems.

## Lizenz

MIT — siehe [LICENSE](LICENSE).

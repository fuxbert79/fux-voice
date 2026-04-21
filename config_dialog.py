"""Konfigurations-Dialog (tkinter) mit API-Key-Test und Mikrofon-Auswahl."""
from __future__ import annotations

import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ============================================================
# .env Lesen/Schreiben
# ============================================================

def save_api_key_to_env(env_path: Path, api_key: str) -> None:
    """Schreibt/aktualisiert OPENAI_API_KEY in .env (atomar)."""
    key_line = f"OPENAI_API_KEY={api_key}"
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith("OPENAI_API_KEY="):
                lines[i] = key_line
                updated = True
                break
        if not updated:
            lines.append(key_line)
    else:
        lines = [
            "# OpenAI API-Key fuer Whisper-Transkription",
            key_line,
        ]

    tmp_path = env_path.with_name(env_path.name + ".tmp")
    tmp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp_path.replace(env_path)


def load_api_key_from_env(env_path: Path) -> str:
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def _mask_key(key: str) -> str:
    if not key or len(key) < 12:
        return "(nicht gesetzt)"
    return f"{key[:10]}…{key[-5:]}"


# ============================================================
# OpenAI-Test
# ============================================================

def test_api_key(api_key: str, timeout_s: float = 10.0) -> tuple[bool, str]:
    if not api_key or not api_key.strip():
        return False, "Kein Key eingegeben"
    try:
        from openai import OpenAI
    except Exception as exc:
        return False, f"openai-Library fehlt: {exc}"
    try:
        client = OpenAI(api_key=api_key.strip(), timeout=timeout_s)
        models = client.models.list()
        model_ids = [m.id for m in models.data] if hasattr(models, "data") else []
        has_whisper = any("whisper" in mid for mid in model_ids)
        if has_whisper:
            return True, f"Verbindung OK — Whisper erreichbar ({len(model_ids)} Modelle)"
        return True, f"Verbindung OK ({len(model_ids)} Modelle, Whisper nicht gelistet)"
    except Exception as exc:
        msg = str(exc)
        if "401" in msg or "invalid" in msg.lower() or "Incorrect API key" in msg:
            return False, "Ungueltiger API-Key (401)"
        if "429" in msg:
            return False, "Rate-Limit / Quota ueberschritten (429)"
        if "timeout" in msg.lower():
            return False, "Timeout — keine Verbindung zu OpenAI"
        if len(msg) > 120:
            msg = msg[:120] + "…"
        return False, f"Fehler: {msg}"


# ============================================================
# Audio-Device-Helfer
# ============================================================

def list_input_devices() -> list[dict[str, Any]]:
    """Alle Eingabe-Geraete via sounddevice."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        inputs = []
        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0:
                inputs.append({
                    "index": idx,
                    "name": dev["name"],
                    "channels": int(dev["max_input_channels"]),
                    "sample_rate": int(dev.get("default_samplerate", 0) or 0),
                })
        return inputs
    except Exception:
        logger.exception("sounddevice konnte Geraete nicht auflisten")
        return []


def record_peak(device: Optional[str | int], duration_s: float = 2.0, sample_rate: int = 16000) -> tuple[float, float]:
    """Nimmt kurz auf und gibt (peak, rms) zurueck (normalisiert 0..1)."""
    import sounddevice as sd
    import numpy as np

    frames = int(duration_s * sample_rate)
    audio = sd.rec(frames, samplerate=sample_rate, channels=1, device=device, dtype="float32")
    sd.wait()
    if audio.ndim > 1:
        audio = audio.flatten()
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    rms = float(np.sqrt(np.mean(audio ** 2))) if len(audio) else 0.0
    return peak, rms


# ============================================================
# Konstanten
# ============================================================

_LED_COLOR_IDLE = "#808080"
_LED_COLOR_TEST = "#f0b500"
_LED_COLOR_OK = "#28a745"
_LED_COLOR_FAIL = "#dc3545"

_DEFAULT_DEVICE_LABEL = "Standard-Geraet (Windows-Default)"

# Verfuegbare Transkriptions-Modelle (OpenAI)
_MODELS = [
    {
        "id": "gpt-4o-transcribe",
        "label": "gpt-4o-transcribe · beste Qualitaet · $0.006/min",
    },
    {
        "id": "gpt-4o-mini-transcribe",
        "label": "gpt-4o-mini-transcribe · schnell + guenstig · $0.003/min",
    },
    {
        "id": "whisper-1",
        "label": "whisper-1 · Legacy-Modell · $0.006/min",
    },
]


# ============================================================
# Dialog
# ============================================================

def show_config_dialog(
    env_path: Path,
    current_device: Optional[str] = None,
    current_model: Optional[str] = None,
    on_saved: Optional[Callable[[dict[str, Any]], None]] = None,
    icon_path: Optional[Path] = None,
) -> bool:
    """Modaler Konfigurations-Dialog. Gibt True zurueck wenn gespeichert."""
    saved_flag = {"value": False}
    last_tested_key = {"value": "", "ok": False}

    root = tk.Tk()
    root.title("fux-voice — Konfiguration")
    root.geometry("680x680")
    root.resizable(False, False)
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass

    if icon_path and icon_path.exists() and icon_path.suffix.lower() == ".ico":
        try:
            root.iconbitmap(str(icon_path))
        except Exception:
            logger.debug("Icon konnte nicht gesetzt werden")

    bg = root.cget("bg")

    main = ttk.Frame(root, padding=20)
    main.pack(fill="both", expand=True)

    # ------------------------------------------------------------
    # Sektion API-Key
    # ------------------------------------------------------------

    current_key = load_api_key_from_env(env_path)
    if current_key.startswith("sk-proj-...") or current_key == "":
        current_key = ""

    ttk.Label(main, text="OpenAI API-Key", font=("Segoe UI", 11, "bold")).pack(anchor="w")
    ttk.Label(main, text=f"Aktuell: {_mask_key(current_key)}", foreground="gray").pack(anchor="w", pady=(2, 8))

    key_frame = ttk.Frame(main)
    key_frame.pack(fill="x")
    key_var = tk.StringVar(value=current_key)
    entry = ttk.Entry(key_frame, textvariable=key_var, show="*", width=48)
    entry.pack(side="left", fill="x", expand=True)

    led_canvas = tk.Canvas(key_frame, width=22, height=22, highlightthickness=0, bg=bg, borderwidth=0)
    led_canvas.pack(side="left", padx=(8, 4))
    led_circle = led_canvas.create_oval(3, 3, 19, 19, fill=_LED_COLOR_IDLE, outline="#444444", width=1)

    show_var = tk.BooleanVar(value=False)
    def toggle_show() -> None:
        entry.config(show="" if show_var.get() else "*")
    ttk.Checkbutton(key_frame, text="Zeigen", variable=show_var, command=toggle_show).pack(side="left", padx=(4, 0))

    test_btn = ttk.Button(key_frame, text="Testen")
    test_btn.pack(side="left", padx=(8, 0))

    ttk.Label(
        main, text="Erhaeltlich unter https://platform.openai.com/api-keys", foreground="gray",
    ).pack(anchor="w", pady=(4, 0))

    key_status_var = tk.StringVar(value="Noch nicht getestet.")
    key_status_lbl = ttk.Label(main, textvariable=key_status_var, foreground="gray")
    key_status_lbl.pack(anchor="w", pady=(6, 0))

    def set_led(color: str, text: str, fg: str = "gray") -> None:
        led_canvas.itemconfig(led_circle, fill=color)
        key_status_var.set(text)
        key_status_lbl.config(foreground=fg)

    if current_key:
        set_led(_LED_COLOR_IDLE, "Bisher nicht getestet — Testen druecken.", "gray")
    else:
        set_led(_LED_COLOR_IDLE, "Kein Key hinterlegt.", "gray")

    def run_api_test() -> None:
        key = key_var.get().strip()
        if not key:
            set_led(_LED_COLOR_FAIL, "Kein Key eingegeben.", _LED_COLOR_FAIL)
            return
        set_led(_LED_COLOR_TEST, "Pruefe Verbindung zu OpenAI …", "#b08400")
        test_btn.config(state="disabled")

        def worker(tested_key: str) -> None:
            ok, msg = test_api_key(tested_key)
            def done() -> None:
                last_tested_key["value"] = tested_key
                last_tested_key["ok"] = ok
                if ok:
                    set_led(_LED_COLOR_OK, msg, _LED_COLOR_OK)
                else:
                    set_led(_LED_COLOR_FAIL, msg, _LED_COLOR_FAIL)
                test_btn.config(state="normal")
            root.after(0, done)

        threading.Thread(target=worker, args=(key,), daemon=True).start()

    test_btn.config(command=run_api_test)

    def on_key_change(*_args: Any) -> None:
        new = key_var.get().strip()
        if new != last_tested_key["value"]:
            if new:
                set_led(_LED_COLOR_IDLE, "Geaendert — zum Pruefen Testen druecken.", "gray")
            else:
                set_led(_LED_COLOR_IDLE, "Kein Key eingegeben.", "gray")
    key_var.trace_add("write", on_key_change)

    # ------------------------------------------------------------
    # Sektion Mikrofon
    # ------------------------------------------------------------

    ttk.Separator(main, orient="horizontal").pack(fill="x", pady=16)

    ttk.Label(main, text="Mikrofon", font=("Segoe UI", 11, "bold")).pack(anchor="w")

    devices = list_input_devices()
    device_labels: list[str] = [_DEFAULT_DEVICE_LABEL]
    device_values: list[Optional[str]] = [None]
    for d in devices:
        label = f"{d['name']}  ·  {d['channels']} ch"
        if d["sample_rate"]:
            label += f"  ·  {d['sample_rate']} Hz"
        device_labels.append(label)
        device_values.append(d["name"])

    # Aktuell gewaehltes Device finden
    initial_idx = 0
    if current_device:
        for i, v in enumerate(device_values):
            if v == current_device:
                initial_idx = i
                break

    ttk.Label(
        main,
        text=f"Aktuell: {device_labels[initial_idx] if initial_idx else _DEFAULT_DEVICE_LABEL}",
        foreground="gray",
    ).pack(anchor="w", pady=(2, 8))

    mic_frame = ttk.Frame(main)
    mic_frame.pack(fill="x")

    device_combo = ttk.Combobox(
        mic_frame,
        values=device_labels,
        width=55,
        state="readonly",
    )
    device_combo.current(initial_idx)
    device_combo.pack(side="left", fill="x", expand=True)

    mic_test_btn = ttk.Button(mic_frame, text="Mikro testen")
    mic_test_btn.pack(side="left", padx=(8, 0))

    # Level-Anzeige
    level_frame = ttk.Frame(main)
    level_frame.pack(fill="x", pady=(8, 0))

    level_var = tk.IntVar(value=0)
    level_bar = ttk.Progressbar(level_frame, variable=level_var, maximum=100, length=400, mode="determinate")
    level_bar.pack(side="left")

    mic_status_var = tk.StringVar(value="Nicht getestet.")
    mic_status_lbl = ttk.Label(level_frame, textvariable=mic_status_var, foreground="gray")
    mic_status_lbl.pack(side="left", padx=(8, 0))

    def set_mic_status(text: str, color: str = "gray") -> None:
        mic_status_var.set(text)
        mic_status_lbl.config(foreground=color)

    def run_mic_test() -> None:
        idx = device_combo.current()
        device = device_values[idx] if 0 <= idx < len(device_values) else None
        set_mic_status("Nimm 2s auf … bitte sprechen", "#b08400")
        level_var.set(0)
        mic_test_btn.config(state="disabled")

        def worker() -> None:
            try:
                peak, rms = record_peak(device, duration_s=2.0)
                def done() -> None:
                    pct = int(peak * 100)
                    level_var.set(pct)
                    if peak < 0.005:
                        set_mic_status(f"Kein Signal (Peak {peak:.4f}). Stumm-/Gain pruefen.", _LED_COLOR_FAIL)
                    elif peak < 0.03:
                        set_mic_status(f"Sehr leise (Peak {peak:.3f}). Lauter sprechen?", "#b08400")
                    else:
                        set_mic_status(f"OK — Peak {peak:.2f}, RMS {rms:.3f}", _LED_COLOR_OK)
                    mic_test_btn.config(state="normal")
                root.after(0, done)
            except Exception as exc:
                logger.exception("Mikro-Test fehlgeschlagen")
                def done_err() -> None:
                    set_mic_status(f"Fehler: {exc}", _LED_COLOR_FAIL)
                    mic_test_btn.config(state="normal")
                root.after(0, done_err)

        threading.Thread(target=worker, daemon=True).start()

    mic_test_btn.config(command=run_mic_test)

    # ------------------------------------------------------------
    # Sektion Transkriptions-Modell
    # ------------------------------------------------------------

    ttk.Separator(main, orient="horizontal").pack(fill="x", pady=16)

    ttk.Label(main, text="Transkriptions-Modell", font=("Segoe UI", 11, "bold")).pack(anchor="w")

    model_ids = [m["id"] for m in _MODELS]
    model_labels = [m["label"] for m in _MODELS]
    initial_model_idx = 0
    if current_model and current_model in model_ids:
        initial_model_idx = model_ids.index(current_model)

    model_combo = ttk.Combobox(main, values=model_labels, width=60, state="readonly")
    model_combo.current(initial_model_idx)
    model_combo.pack(fill="x", pady=(8, 0))

    ttk.Label(
        main,
        text="gpt-4o-transcribe ist empfohlen — beste Qualitaet bei gleichem Preis wie whisper-1.",
        foreground="gray",
    ).pack(anchor="w", pady=(4, 0))

    # ------------------------------------------------------------
    # Sektion Autostart
    # ------------------------------------------------------------

    ttk.Separator(main, orient="horizontal").pack(fill="x", pady=16)

    from autostart import get_autostart_target, is_autostart_enabled, set_autostart

    autostart_var = tk.BooleanVar(value=is_autostart_enabled())
    autostart_check = ttk.Checkbutton(
        main, text="fux-voice automatisch mit Windows starten",
        variable=autostart_var,
    )
    autostart_check.pack(anchor="w")

    _current_target = get_autostart_target()
    autostart_info = ttk.Label(
        main,
        text=(f"Aktuell: {_current_target}" if _current_target else
              "Nicht aktiviert — Haken setzen, dann Speichern."),
        foreground="gray",
    )
    autostart_info.pack(anchor="w", pady=(2, 0))

    # ------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------

    ttk.Separator(main, orient="horizontal").pack(fill="x", pady=16)

    btn_frame = ttk.Frame(main)
    btn_frame.pack(fill="x", side="bottom")

    def collect_device() -> Optional[str]:
        idx = device_combo.current()
        if 0 <= idx < len(device_values):
            return device_values[idx]
        return None

    def collect_model() -> str:
        idx = model_combo.current()
        if 0 <= idx < len(model_ids):
            return model_ids[idx]
        return model_ids[0]

    def do_save() -> None:
        new_key = key_var.get().strip()
        new_device = collect_device()
        new_model = collect_model()
        new_autostart = autostart_var.get()

        if not new_key:
            set_led(_LED_COLOR_FAIL, "API-Key darf nicht leer sein.", _LED_COLOR_FAIL)
            return

        if last_tested_key["value"] != new_key:
            if not messagebox.askyesno(
                "Nicht getestet",
                "Der API-Key wurde noch nicht auf Verbindung getestet.\n\nTrotzdem speichern?",
                parent=root,
            ):
                return
        elif not last_tested_key["ok"]:
            if not messagebox.askyesno(
                "Test fehlgeschlagen",
                "Der Verbindungstest ist fehlgeschlagen.\n\nTrotzdem speichern?",
                parent=root,
            ):
                return

        if not new_key.startswith("sk-"):
            if not messagebox.askyesno(
                "Warnung",
                "Der Key beginnt nicht mit 'sk-'. Trotzdem speichern?",
                parent=root,
            ):
                return

        try:
            save_api_key_to_env(env_path, new_key)
        except Exception as exc:
            logger.exception("API-Key Speichern fehlgeschlagen")
            set_led(_LED_COLOR_FAIL, f"Speichern fehlgeschlagen: {exc}", _LED_COLOR_FAIL)
            return

        # Autostart setzen
        try:
            set_autostart(new_autostart)
        except Exception:
            logger.exception("Autostart konnte nicht gesetzt werden")

        saved_flag["value"] = True
        if on_saved:
            try:
                on_saved({
                    "api_key": new_key,
                    "device": new_device,
                    "model": new_model,
                    "autostart": new_autostart,
                })
            except Exception:
                logger.exception("on_saved-Callback schlug fehl")
        root.destroy()

    def do_cancel() -> None:
        root.destroy()

    ttk.Button(btn_frame, text="Abbrechen", command=do_cancel).pack(side="right", padx=(8, 0))
    ttk.Button(btn_frame, text="Speichern", command=do_save).pack(side="right")

    entry.bind("<Return>", lambda _e: run_api_test())
    root.bind("<Control-s>", lambda _e: do_save())
    root.bind("<Escape>", lambda _e: do_cancel())

    entry.focus_set()
    entry.icursor("end")

    root.mainloop()
    return saved_flag["value"]

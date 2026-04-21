"""Konfigurations-Dialog (tkinter) mit API-Key-Verbindungstest.

Wird via Tray-Rechtsklick aufgerufen oder automatisch beim Erst-Start
falls noch kein API-Key hinterlegt ist.
"""
from __future__ import annotations

import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable, Optional

logger = logging.getLogger(__name__)


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


def test_api_key(api_key: str, timeout_s: float = 10.0) -> tuple[bool, str]:
    """Testet API-Key via OpenAI models.list().

    Returns: (success, kurze Statusnachricht)
    """
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


# Ampel-Farben
_LED_COLOR_IDLE  = "#808080"  # Grau
_LED_COLOR_TEST  = "#f0b500"  # Gelb/Orange
_LED_COLOR_OK    = "#28a745"  # Grün
_LED_COLOR_FAIL  = "#dc3545"  # Rot


def show_config_dialog(
    env_path: Path,
    on_saved: Optional[Callable[[str], None]] = None,
    icon_path: Optional[Path] = None,
) -> bool:
    """Zeigt modalen Konfigurations-Dialog. Gibt True zurueck wenn gespeichert."""
    saved_flag = {"value": False}
    last_tested_key = {"value": "", "ok": False}

    root = tk.Tk()
    root.title("fux-voice — Konfiguration")
    root.geometry("620x340")
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

    current_key = load_api_key_from_env(env_path)
    if current_key.startswith("sk-proj-...") or current_key == "":
        current_key = ""

    bg = root.cget("bg")

    main = ttk.Frame(root, padding=20)
    main.pack(fill="both", expand=True)

    ttk.Label(main, text="OpenAI API-Key", font=("Segoe UI", 11, "bold")).pack(anchor="w")
    ttk.Label(main, text=f"Aktuell: {_mask_key(current_key)}", foreground="gray").pack(anchor="w", pady=(2, 10))

    # Zeile: Entry + Ampel + Zeigen + Test-Button
    entry_frame = ttk.Frame(main)
    entry_frame.pack(fill="x")

    key_var = tk.StringVar(value=current_key)
    entry = ttk.Entry(entry_frame, textvariable=key_var, show="*", width=48)
    entry.pack(side="left", fill="x", expand=True)

    # Ampel
    led_canvas = tk.Canvas(entry_frame, width=22, height=22, highlightthickness=0, bg=bg, borderwidth=0)
    led_canvas.pack(side="left", padx=(8, 4))
    led_circle = led_canvas.create_oval(3, 3, 19, 19, fill=_LED_COLOR_IDLE, outline="#444444", width=1)

    show_var = tk.BooleanVar(value=False)
    def toggle_show() -> None:
        entry.config(show="" if show_var.get() else "*")
    ttk.Checkbutton(entry_frame, text="Zeigen", variable=show_var, command=toggle_show).pack(side="left", padx=(4, 0))

    test_btn = ttk.Button(entry_frame, text="Testen")
    test_btn.pack(side="left", padx=(8, 0))

    ttk.Label(
        main, text="Erhaeltlich unter https://platform.openai.com/api-keys", foreground="gray",
    ).pack(anchor="w", pady=(6, 0))

    ttk.Separator(main, orient="horizontal").pack(fill="x", pady=14)

    # Status-Zeile
    status_var = tk.StringVar(value="Noch nicht getestet.")
    status_color_var = tk.StringVar(value="gray")
    status_lbl = ttk.Label(main, textvariable=status_var, foreground="gray")
    status_lbl.pack(anchor="w")

    def set_led(color: str, status_text: str, fg: str = "gray") -> None:
        led_canvas.itemconfig(led_circle, fill=color)
        status_var.set(status_text)
        status_lbl.config(foreground=fg)

    # Initial-LED basierend auf bisherigem Key
    if current_key:
        set_led(_LED_COLOR_IDLE, "Bisher nicht getestet — Testen druecken.", "gray")
    else:
        set_led(_LED_COLOR_IDLE, "Kein Key hinterlegt.", "gray")

    def run_test() -> None:
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

    test_btn.config(command=run_test)

    # Button-Zeile
    btn_frame = ttk.Frame(main)
    btn_frame.pack(fill="x", side="bottom")

    def do_save() -> None:
        new_key = key_var.get().strip()
        if not new_key:
            set_led(_LED_COLOR_FAIL, "API-Key darf nicht leer sein.", _LED_COLOR_FAIL)
            return

        # Wenn dieser Key noch nicht getestet wurde ODER der Test fehlgeschlagen ist, warnen
        if last_tested_key["value"] != new_key:
            if not messagebox.askyesno(
                "Nicht getestet",
                "Der Key wurde noch nicht auf Verbindung getestet.\n\nTrotzdem speichern?",
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
            logger.exception("Speichern fehlgeschlagen")
            set_led(_LED_COLOR_FAIL, f"Speichern fehlgeschlagen: {exc}", _LED_COLOR_FAIL)
            return

        saved_flag["value"] = True
        if on_saved:
            try:
                on_saved(new_key)
            except Exception:
                logger.exception("on_saved-Callback schlug fehl")
        root.destroy()

    def do_cancel() -> None:
        root.destroy()

    ttk.Button(btn_frame, text="Abbrechen", command=do_cancel).pack(side="right", padx=(8, 0))
    ttk.Button(btn_frame, text="Speichern", command=do_save).pack(side="right")

    # Enter im Entry = Testen (bequem), Strg+S = Speichern
    entry.bind("<Return>", lambda _e: run_test())
    root.bind("<Control-s>", lambda _e: do_save())
    root.bind("<Escape>", lambda _e: do_cancel())

    # Ampel zuruecksetzen wenn Key editiert wird
    def on_key_change(*_args) -> None:
        new = key_var.get().strip()
        if new != last_tested_key["value"]:
            if new:
                set_led(_LED_COLOR_IDLE, "Geaendert — zum Pruefen Testen druecken.", "gray")
            else:
                set_led(_LED_COLOR_IDLE, "Kein Key eingegeben.", "gray")
    key_var.trace_add("write", on_key_change)

    entry.focus_set()
    entry.icursor("end")

    root.mainloop()
    return saved_flag["value"]

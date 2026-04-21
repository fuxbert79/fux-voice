"""Konfigurations-Dialog (tkinter).

Wird via Tray-Rechtsklick aufgerufen oder automatisch beim Erst-Start
falls noch kein API-Key hinterlegt ist.
"""
from __future__ import annotations

import logging
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


def show_config_dialog(
    env_path: Path,
    on_saved: Optional[Callable[[str], None]] = None,
    icon_path: Optional[Path] = None,
) -> bool:
    """Zeigt modalen Konfigurations-Dialog. Gibt True zurueck wenn gespeichert."""
    saved_flag = {"value": False}

    root = tk.Tk()
    root.title("fux-voice — Konfiguration")
    root.geometry("540x280")
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

    main = ttk.Frame(root, padding=20)
    main.pack(fill="both", expand=True)

    ttk.Label(
        main,
        text="OpenAI API-Key",
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w")

    ttk.Label(
        main,
        text=f"Aktuell: {_mask_key(current_key)}",
        foreground="gray",
    ).pack(anchor="w", pady=(2, 10))

    entry_frame = ttk.Frame(main)
    entry_frame.pack(fill="x")

    key_var = tk.StringVar(value=current_key)
    entry = ttk.Entry(entry_frame, textvariable=key_var, show="*", width=55)
    entry.pack(side="left", fill="x", expand=True)

    show_var = tk.BooleanVar(value=False)

    def toggle_show() -> None:
        entry.config(show="" if show_var.get() else "*")

    ttk.Checkbutton(
        entry_frame, text="Zeigen", variable=show_var, command=toggle_show
    ).pack(side="left", padx=(8, 0))

    ttk.Label(
        main,
        text="Erhaeltlich unter https://platform.openai.com/api-keys",
        foreground="gray",
    ).pack(anchor="w", pady=(6, 0))

    ttk.Separator(main, orient="horizontal").pack(fill="x", pady=14)

    status_var = tk.StringVar(value="")
    ttk.Label(main, textvariable=status_var, foreground="#c0392b").pack(anchor="w")

    btn_frame = ttk.Frame(main)
    btn_frame.pack(fill="x", side="bottom")

    def do_save() -> None:
        new_key = key_var.get().strip()
        if not new_key:
            status_var.set("API-Key darf nicht leer sein.")
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
            status_var.set(f"Speichern fehlgeschlagen: {exc}")
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
    save_btn = ttk.Button(btn_frame, text="Speichern", command=do_save)
    save_btn.pack(side="right")

    root.bind("<Return>", lambda _e: do_save())
    root.bind("<Escape>", lambda _e: do_cancel())
    entry.focus_set()
    entry.icursor("end")

    root.mainloop()
    return saved_flag["value"]

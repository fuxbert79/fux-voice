"""Ueber-Dialog (tkinter).

Zeigt Version, Build-Datum, Credits und SiegAI-Markenzeichen mit
klickbarem Link zur Landingpage.
"""
from __future__ import annotations

import logging
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk
from typing import Optional

from version import (
    ABOUT_URL,
    APP_NAME,
    APP_SUBTITLE,
    BRAND_COLOR,
    BRAND_HIGHLIGHT,
    BRAND_PREFIX,
    BUILD_DATE,
    ENGINEER,
    __version__,
)

logger = logging.getLogger(__name__)


def show_about_dialog(icon_path: Optional[Path] = None) -> None:
    """Zeigt den Ueber-Dialog modal."""
    root = tk.Tk()
    root.title(f"Über {APP_NAME}")
    root.geometry("440x360")
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

    main = ttk.Frame(root, padding=(30, 24, 30, 20))
    main.pack(fill="both", expand=True)

    # App-Name
    ttk.Label(main, text=APP_NAME, font=("Segoe UI", 20, "bold")).pack(anchor="center")
    ttk.Label(main, text=APP_SUBTITLE, foreground="gray").pack(anchor="center", pady=(2, 18))

    # Version + Datum Block
    info = ttk.Frame(main)
    info.pack()
    ttk.Label(info, text="Version:").grid(row=0, column=0, sticky="e", padx=(0, 10))
    ttk.Label(info, text=f"v{__version__}", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w")
    ttk.Label(info, text="Build:").grid(row=1, column=0, sticky="e", padx=(0, 10), pady=(4, 0))
    ttk.Label(info, text=BUILD_DATE).grid(row=1, column=1, sticky="w", pady=(4, 0))

    ttk.Separator(main, orient="horizontal").pack(fill="x", pady=20)

    # Credits
    ttk.Label(main, text="engineering by", foreground="gray").pack(anchor="center")
    ttk.Label(main, text=ENGINEER, font=("Segoe UI", 11, "bold")).pack(anchor="center", pady=(2, 12))

    # SiegAI (AI in grün, klickbar)
    brand_frame = tk.Frame(main, bg=bg)
    brand_frame.pack(anchor="center")

    sieg_lbl = tk.Label(
        brand_frame, text=BRAND_PREFIX,
        font=("Segoe UI", 12, "bold"),
        cursor="hand2", bg=bg, fg="#222222",
    )
    ai_lbl = tk.Label(
        brand_frame, text=BRAND_HIGHLIGHT,
        font=("Segoe UI", 12, "bold"),
        cursor="hand2", bg=bg, fg=BRAND_COLOR,
    )
    sieg_lbl.pack(side="left")
    ai_lbl.pack(side="left")

    def _open_url(_e: object = None) -> None:
        try:
            webbrowser.open(ABOUT_URL)
        except Exception:
            logger.exception("Link konnte nicht geoeffnet werden: %s", ABOUT_URL)

    def _on_enter(event: object) -> None:
        event.widget.config(font=("Segoe UI", 12, "bold underline"))

    def _on_leave(event: object) -> None:
        event.widget.config(font=("Segoe UI", 12, "bold"))

    for lbl in (sieg_lbl, ai_lbl):
        lbl.bind("<Button-1>", _open_url)
        lbl.bind("<Enter>", _on_enter)
        lbl.bind("<Leave>", _on_leave)

    # URL klein darunter
    ttk.Label(main, text=ABOUT_URL.replace("https://", ""), foreground="gray", cursor="hand2").pack(
        anchor="center", pady=(4, 0)
    )

    # Schließen-Button
    ttk.Button(main, text="Schließen", command=root.destroy).pack(side="bottom", pady=(16, 0))

    root.bind("<Escape>", lambda _e: root.destroy())
    root.bind("<Return>", lambda _e: root.destroy())

    root.mainloop()

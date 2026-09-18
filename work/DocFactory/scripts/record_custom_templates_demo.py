#!/usr/bin/env python3
"""Медленный UI-прогон для screen recording."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tkinter.messagebox as mb

mb.showinfo = lambda *a, **k: True  # type: ignore[assignment]
mb.showwarning = lambda *a, **k: True  # type: ignore[assignment]
mb.showerror = lambda *a, **k: True  # type: ignore[assignment]
mb.askyesno = lambda *a, **k: True  # type: ignore[assignment]

from app import DocFactoryApp
from docfactory.custom_templates import list_customs
from docfactory.generators import generate


def pause(app: DocFactoryApp, sec: float = 1.0) -> None:
    end = time.time() + sec
    while time.time() < end:
        app.update()
        time.sleep(0.03)


def main() -> None:
    app = DocFactoryApp()
    app.geometry("1080x780+60+40")
    pause(app, 1.2)
    nb = next(c for c in app.winfo_children() if c.winfo_class() == "TNotebook")

    # показать конструктор
    nb.select(app.tab_mine)
    pause(app, 1.5)

    app._builder_preset_otchet()
    app.b_title.set("Мой отчёт сплайн")
    app.b_heading.set("ОТЧЁТ О РАБОТЕ")
    app.b_filename.set("Moy_otchet_splajn.docx")
    app.b_desc.set("Пользовательский шаблон из конструктора")
    pause(app, 1.8)

    app._builder_save()
    pause(app, 1.5)

    tid = next(c.id for c in list_customs() if c.title == "Мой отчёт сплайн")
    nb.select(app.tab_gen)
    app._refresh_catalog(select_id=tid)
    pause(app, 1.8)

    for key, var in app.field_vars.items():
        if "фио" in key.lower():
            var.set("Руцкий В.А.")
            break
    import tkinter as tk

    for key, w in app.field_widgets.items():
        if isinstance(w, tk.Text) and not w.get("1.0", "end").strip():
            w.insert("1.0", "Проверка пользовательского шаблона")
            break
    pause(app, 1.5)

    out = generate(tid, app._collect(), Path(app.out_dir.get()))
    print("DOCX", out)
    pause(app, 2.0)
    app.destroy()


if __name__ == "__main__":
    main()

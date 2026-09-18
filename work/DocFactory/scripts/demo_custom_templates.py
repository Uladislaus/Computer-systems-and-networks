#!/usr/bin/env python3
"""Программный прогон вкладки «Мои шаблоны» + скриншоты (без ручных кликов)."""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ART = Path("/opt/cursor/artifacts")
ART.mkdir(parents=True, exist_ok=True)

# глушим модалки, чтобы сценарий не зависал
import tkinter.messagebox as mb

mb.showinfo = lambda *a, **k: True  # type: ignore[assignment]
mb.showwarning = lambda *a, **k: True  # type: ignore[assignment]
mb.showerror = lambda *a, **k: True  # type: ignore[assignment]
mb.askyesno = lambda *a, **k: True  # type: ignore[assignment]

from PIL import ImageGrab

from app import DocFactoryApp
from docfactory.custom_templates import list_customs, load_custom
from docfactory.generators import generate


def shot(app: DocFactoryApp, name: str) -> Path:
    app.update_idletasks()
    app.update()
    app.lift()
    app.focus_force()
    x = app.winfo_rootx()
    y = app.winfo_rooty()
    w = app.winfo_width()
    h = app.winfo_height()
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    path = ART / name
    img.save(path)
    print(f"SHOT {path} ({w}x{h})")
    return path


def main() -> None:
    app = DocFactoryApp()
    app.update()
    # найти Notebook
    nb = None
    for child in app.winfo_children():
        if child.winfo_class() == "TNotebook":
            nb = child
            break
    assert nb is not None, "Notebook not found"

    shot(app, "docfactory-templates-tab.webp")

    nb.select(1)  # Мои шаблоны
    app.update()
    shot(app, "docfactory-my-templates-empty.webp")

    app._builder_preset_otchet()
    app.b_title.set("Мой отчёт сплайн")
    app.b_heading.set("ОТЧЁТ О РАБОТЕ")
    app.b_filename.set("Moy_otchet_splajn.docx")
    app.b_desc.set("Пользовательский шаблон из конструктора")
    app.update()
    shot(app, "docfactory-builder-preset-otchet.webp")

    app._builder_save()
    app.update()
    customs = list_customs()
    assert any(c.title == "Мой отчёт сплайн" for c in customs), customs
    tid = next(c.id for c in customs if c.title == "Мой отчёт сплайн")
    print("SAVED", tid)
    shot(app, "docfactory-builder-saved.webp")

    nb.select(0)  # Шаблоны
    app._refresh_catalog(select_id=tid)
    app.update()
    # заполним пару полей
    if "fio" in app.field_vars:
        app.field_vars["fio"].set("Руцкий В.А.")
    elif "фио" in app.field_vars:
        app.field_vars["фио"].set("Руцкий В.А.")
    else:
        # ключи генерируются из подписей
        for key, var in app.field_vars.items():
            if "fio" in key or key.endswith("фио") or "fio" in key.lower():
                var.set("Руцкий В.А.")
                break
        else:
            # найти по label через widgets — проставим первое meta-поле после org
            for key, var in list(app.field_vars.items())[:4]:
                if not var.get().strip():
                    var.set("Руцкий В.А.")
                    break
    shot(app, "docfactory-fill-custom-template.webp")

    data = app._collect()
    out = generate(tid, data, Path(app.out_dir.get()))
    print("DOCX", out, out.stat().st_size)
    assert out.exists() and out.stat().st_size > 1000

    tmpl = load_custom(tid)
    assert tmpl is not None
    log = ART / "custom-template-demo.log"
    log.write_text(
        "\n".join(
            [
                f"template_id={tid}",
                f"title={tmpl.title}",
                f"fields={len(tmpl.fields)}",
                f"docx={out}",
                f"docx_size={out.stat().st_size}",
                f"sample_keys={list(data.keys())[:6]}",
                "OK",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(log.read_text(encoding="utf-8"))
    app.destroy()


if __name__ == "__main__":
    main()

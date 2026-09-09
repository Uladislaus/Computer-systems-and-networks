#!/usr/bin/env python3
"""Офлайн-генератор Word-документов (DocFactory). GUI на tkinter."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from docfactory.catalog import CATALOG, get_doc_type
from docfactory.generators import generate

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "output"


class DocFactoryApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("DocFactory — офлайн генератор Word-документов")
        self.geometry("980x720")
        self.minsize(860, 600)

        self.out_dir = tk.StringVar(value=str(DEFAULT_OUT))
        self.selected_id = tk.StringVar(value=CATALOG[0].id)
        self.field_vars: dict[str, tk.Variable] = {}
        self.field_widgets: dict[str, tk.Widget] = {}

        self._build()
        self._on_select()

    def _build(self) -> None:
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Тип документа:").pack(side=tk.LEFT)
        titles = [f"{d.category}: {d.title}" for d in CATALOG]
        self.id_by_title = {f"{d.category}: {d.title}": d.id for d in CATALOG}
        self.combo = ttk.Combobox(top, values=titles, state="readonly", width=60)
        self.combo.set(titles[0])
        self.combo.pack(side=tk.LEFT, padx=8)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self._on_select())

        ttk.Button(top, text="Сформировать DOCX", command=self._generate).pack(side=tk.RIGHT)
        ttk.Button(top, text="Папка…", command=self._pick_out).pack(side=tk.RIGHT, padx=6)

        path_row = ttk.Frame(self, padding=(8, 0))
        path_row.pack(fill=tk.X)
        ttk.Label(path_row, text="Сохранить в:").pack(side=tk.LEFT)
        ttk.Entry(path_row, textvariable=self.out_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        self.desc = ttk.Label(self, text="", wraplength=920, padding=8)
        self.desc.pack(fill=tk.X)

        wrap = ttk.Frame(self, padding=8)
        wrap.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(wrap, highlightthickness=0)
        scroll = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=canvas.yview)
        self.form = ttk.Frame(canvas)
        self.form.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.form, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas = canvas
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        tip = (
            "Подсказка: в табличных полях строки разделяйте Enter, колонки — символом | "
            "(пример: 20.08.2026 | Python | практика | выполнено | повторить)"
        )
        ttk.Label(self, text=tip, padding=8).pack(fill=tk.X)

    def _pick_out(self) -> None:
        path = filedialog.askdirectory(initialdir=self.out_dir.get() or str(DEFAULT_OUT))
        if path:
            self.out_dir.set(path)

    def _on_select(self) -> None:
        title = self.combo.get()
        doc_id = self.id_by_title[title]
        self.selected_id.set(doc_id)
        dtype = get_doc_type(doc_id)
        self.desc.configure(text=f"{dtype.description}")

        for child in self.form.winfo_children():
            child.destroy()
        self.field_vars.clear()
        self.field_widgets.clear()

        for i, f in enumerate(dtype.fields):
            ttk.Label(self.form, text=f.label).grid(row=i, column=0, sticky="nw", pady=4, padx=(0, 8))
            if f.multiline:
                txt = tk.Text(self.form, height=5, width=80, wrap=tk.WORD)
                txt.insert("1.0", f.default)
                txt.grid(row=i, column=1, sticky="ew", pady=4)
                self.field_widgets[f.key] = txt
            else:
                var = tk.StringVar(value=f.default)
                ent = ttk.Entry(self.form, textvariable=var, width=80)
                ent.grid(row=i, column=1, sticky="ew", pady=4)
                self.field_vars[f.key] = var
                self.field_widgets[f.key] = ent
        self.form.columnconfigure(1, weight=1)

    def _collect(self) -> dict:
        dtype = get_doc_type(self.selected_id.get())
        data: dict[str, str] = {}
        for f in dtype.fields:
            w = self.field_widgets[f.key]
            if isinstance(w, tk.Text):
                data[f.key] = w.get("1.0", "end").strip()
            else:
                data[f.key] = self.field_vars[f.key].get().strip()
        return data

    def _generate(self) -> None:
        try:
            out = Path(self.out_dir.get())
            path = generate(self.selected_id.get(), self._collect(), out)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", str(exc))
            return
        messagebox.showinfo("Готово", f"Документ сохранён:\n{path}")


def main() -> None:
    DEFAULT_OUT.mkdir(parents=True, exist_ok=True)
    app = DocFactoryApp()
    app.mainloop()


if __name__ == "__main__":
    main()

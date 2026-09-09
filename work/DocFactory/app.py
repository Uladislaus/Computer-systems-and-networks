#!/usr/bin/env python3
"""DocFactory — генератор и конвертер Word/PDF/Markdown (офлайн)."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from docfactory.catalog import CATALOG, get_doc_type
from docfactory.convert import ConvertError, backend_status, convert_auto
from docfactory.generators import generate

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "output"


class DocFactoryApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("DocFactory — документы и конвертация (офлайн)")
        self.geometry("1000x740")
        self.minsize(880, 620)

        self.out_dir = tk.StringVar(value=str(DEFAULT_OUT))
        self.selected_id = tk.StringVar(value=CATALOG[0].id)
        self.field_vars: dict[str, tk.Variable] = {}
        self.field_widgets: dict[str, tk.Widget] = {}

        self.src_file = tk.StringVar()
        self.dst_file = tk.StringVar()
        self.conv_mode = tk.StringVar(value="Авто по расширениям")

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tab_gen = ttk.Frame(nb)
        self.tab_conv = ttk.Frame(nb)
        nb.add(self.tab_gen, text="Шаблоны → DOCX")
        nb.add(self.tab_conv, text="Конвертация MD / DOCX / PDF")

        self._build_generator(self.tab_gen)
        self._build_converter(self.tab_conv)
        self._on_select()

    # ---- generator tab ----
    def _build_generator(self, parent: ttk.Frame) -> None:
        top = ttk.Frame(parent, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Тип документа:").pack(side=tk.LEFT)
        titles = [f"{d.category}: {d.title}" for d in CATALOG]
        self.id_by_title = {f"{d.category}: {d.title}": d.id for d in CATALOG}
        self.combo = ttk.Combobox(top, values=titles, state="readonly", width=58)
        self.combo.set(titles[0])
        self.combo.pack(side=tk.LEFT, padx=8)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self._on_select())

        ttk.Button(top, text="Сформировать DOCX", command=self._generate).pack(side=tk.RIGHT)
        ttk.Button(top, text="Папка…", command=self._pick_out).pack(side=tk.RIGHT, padx=6)

        path_row = ttk.Frame(parent, padding=(8, 0))
        path_row.pack(fill=tk.X)
        ttk.Label(path_row, text="Сохранить в:").pack(side=tk.LEFT)
        ttk.Entry(path_row, textvariable=self.out_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        self.desc = ttk.Label(parent, text="", wraplength=940, padding=8)
        self.desc.pack(fill=tk.X)

        wrap = ttk.Frame(parent, padding=8)
        wrap.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(wrap, highlightthickness=0)
        scroll = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=canvas.yview)
        self.form = ttk.Frame(canvas)
        self.form.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.form, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        ttk.Label(
            parent,
            text="Подсказка: в табличных полях строки — Enter, колонки — символ |",
            padding=8,
        ).pack(fill=tk.X)

    def _pick_out(self) -> None:
        path = filedialog.askdirectory(initialdir=self.out_dir.get() or str(DEFAULT_OUT))
        if path:
            self.out_dir.set(path)

    def _on_select(self) -> None:
        title = self.combo.get()
        doc_id = self.id_by_title[title]
        self.selected_id.set(doc_id)
        dtype = get_doc_type(doc_id)
        self.desc.configure(text=dtype.description)

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
            path = generate(self.selected_id.get(), self._collect(), Path(self.out_dir.get()))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", str(exc))
            return
        messagebox.showinfo("Готово", f"Документ сохранён:\n{path}")

    # ---- converter tab ----
    def _build_converter(self, parent: ttk.Frame) -> None:
        info = ttk.LabelFrame(parent, text="Доступные движки", padding=8)
        info.pack(fill=tk.X, padx=8, pady=8)
        status = backend_status()
        lines = (
            f"MD ↔ DOCX: {status['md_docx']} / {status['docx_md']}\n"
            f"DOCX → PDF: {status['docx_pdf']}\n"
            f"PDF → DOCX: {status['pdf_docx']}\n\n"
            "DOCX→PDF: установите LibreOffice (рекомендуется) или Word + pip install docx2pdf.\n"
            "PDF→DOCX: pip install pdf2docx (уже в requirements.txt)."
        )
        ttk.Label(info, text=lines, justify=tk.LEFT).pack(anchor="w")

        form = ttk.Frame(parent, padding=8)
        form.pack(fill=tk.X)

        ttk.Label(form, text="Исходный файл:").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.src_file, width=70).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(form, text="Обзор…", command=self._pick_src).grid(row=0, column=2)

        ttk.Label(form, text="Куда сохранить:").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.dst_file, width=70).grid(row=1, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(form, text="Обзор…", command=self._pick_dst).grid(row=1, column=2, pady=6)

        ttk.Label(form, text="Режим:").grid(row=2, column=0, sticky="w")
        modes = [
            "Авто по расширениям",
            "MD → DOCX",
            "DOCX → MD",
            "DOCX → PDF",
            "PDF → DOCX",
            "MD → PDF",
            "PDF → MD",
        ]
        ttk.Combobox(form, textvariable=self.conv_mode, values=modes, state="readonly", width=28).grid(
            row=2, column=1, sticky="w", padx=6
        )
        form.columnconfigure(1, weight=1)

        btns = ttk.Frame(parent, padding=8)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Конвертировать", command=self._convert).pack(side=tk.LEFT)
        ttk.Button(btns, text="Подставить имя результата", command=self._suggest_dst).pack(side=tk.LEFT, padx=8)

        tip = (
            "Примеры:\n"
            "• notes.md → notes.docx\n"
            "• plan.docx → plan.pdf (нужен LibreOffice или Word)\n"
            "• scan.pdf → scan.docx (pdf2docx; вёрстка может отличаться от оригинала)"
        )
        ttk.Label(parent, text=tip, padding=8, justify=tk.LEFT).pack(anchor="w")

    def _pick_src(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[
                ("Документы", "*.md *.docx *.pdf"),
                ("Markdown", "*.md"),
                ("Word", "*.docx"),
                ("PDF", "*.pdf"),
                ("Все файлы", "*.*"),
            ]
        )
        if path:
            self.src_file.set(path)
            self._suggest_dst()

    def _pick_dst(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[
                ("Word", "*.docx"),
                ("PDF", "*.pdf"),
                ("Markdown", "*.md"),
                ("Все файлы", "*.*"),
            ],
        )
        if path:
            self.dst_file.set(path)

    def _target_ext(self) -> str:
        mode = self.conv_mode.get()
        mapping = {
            "MD → DOCX": ".docx",
            "DOCX → MD": ".md",
            "DOCX → PDF": ".pdf",
            "PDF → DOCX": ".docx",
            "MD → PDF": ".pdf",
            "PDF → MD": ".md",
        }
        if mode in mapping:
            return mapping[mode]
        src = Path(self.src_file.get() or "file.docx")
        auto = {".md": ".docx", ".docx": ".pdf", ".pdf": ".docx"}
        return auto.get(src.suffix.lower(), ".docx")

    def _suggest_dst(self) -> None:
        src = self.src_file.get().strip()
        if not src:
            return
        p = Path(src)
        out_dir = Path(self.out_dir.get() or DEFAULT_OUT)
        out_dir.mkdir(parents=True, exist_ok=True)
        self.dst_file.set(str(out_dir / (p.stem + self._target_ext())))

    def _forced_dst(self, src: Path) -> Path:
        mode = self.conv_mode.get()
        dst_text = self.dst_file.get().strip()
        if dst_text:
            return Path(dst_text)
        return src.with_suffix(self._target_ext())

    def _convert(self) -> None:
        src_text = self.src_file.get().strip()
        if not src_text:
            messagebox.showwarning("Файл", "Выберите исходный файл.")
            return
        src = Path(src_text)
        if not src.exists():
            messagebox.showerror("Файл", f"Не найден:\n{src}")
            return
        dst = self._forced_dst(src)
        # If mode forces extension, align dst suffix
        if self.conv_mode.get() != "Авто по расширениям":
            dst = dst.with_suffix(self._target_ext())
            self.dst_file.set(str(dst))
        try:
            result = convert_auto(src, dst)
        except ConvertError as exc:
            messagebox.showerror("Конвертация", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", str(exc))
            return
        messagebox.showinfo("Готово", f"Сохранено:\n{result}")


def main() -> None:
    DEFAULT_OUT.mkdir(parents=True, exist_ok=True)
    app = DocFactoryApp()
    app.mainloop()


if __name__ == "__main__":
    main()

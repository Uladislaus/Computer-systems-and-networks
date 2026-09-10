#!/usr/bin/env python3
"""DocFactory — генератор и конвертер Word/PDF/Markdown (офлайн)."""
from __future__ import annotations

import warnings

warnings.filterwarnings("ignore", message=".*fitz.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from docfactory.catalog import CATALOG, get_doc_type
from docfactory.convert import ConvertError, backend_status, convert_auto
from docfactory.generators import generate

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "output"

# Минималистичная палитра (не purple / не cream AI-клише)
C_BG = "#F3F5F4"
C_SURFACE = "#FFFFFF"
C_INK = "#1A2330"
C_MUTED = "#5B6B73"
C_LINE = "#D7DEDA"
C_ACCENT = "#0F6B5C"
C_ACCENT_HOVER = "#0B5549"


class DocFactoryApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("DocFactory")
        self.geometry("1040x760")
        self.minsize(900, 640)
        self.configure(bg=C_BG)
        self._setup_style()

        self.lift()
        self.attributes("-topmost", True)
        self.after(350, lambda: self.attributes("-topmost", False))
        try:
            self.focus_force()
        except tk.TclError:
            pass

        self.out_dir = tk.StringVar(value=str(DEFAULT_OUT))
        self.selected_id = tk.StringVar(value=CATALOG[0].id)
        self.field_vars: dict[str, tk.Variable] = {}
        self.field_widgets: dict[str, tk.Widget] = {}
        self.src_file = tk.StringVar()
        self.dst_file = tk.StringVar()
        self.conv_mode = tk.StringVar(value="Авто по расширениям")

        self._build_header()
        nb = ttk.Notebook(self, style="Card.TNotebook")
        nb.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))
        self.tab_gen = ttk.Frame(nb, style="Card.TFrame")
        self.tab_conv = ttk.Frame(nb, style="Card.TFrame")
        nb.add(self.tab_gen, text="  Шаблоны  ")
        nb.add(self.tab_conv, text="  Конвертация  ")
        self._build_generator(self.tab_gen)
        self._build_converter(self.tab_conv)
        self._on_select()

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        font_ui = ("Segoe UI", 10)
        font_title = ("Segoe UI Semibold", 16)
        font_small = ("Segoe UI", 9)

        style.configure(".", background=C_BG, foreground=C_INK, font=font_ui)
        style.configure("TFrame", background=C_BG)
        style.configure("Card.TFrame", background=C_SURFACE)
        style.configure("Header.TFrame", background=C_BG)
        style.configure("Header.TLabel", background=C_BG, foreground=C_INK, font=font_title)
        style.configure("Muted.TLabel", background=C_SURFACE, foreground=C_MUTED, font=font_small)
        style.configure("Card.TLabel", background=C_SURFACE, foreground=C_INK, font=font_ui)
        style.configure(
            "Accent.TButton",
            background=C_ACCENT,
            foreground="#FFFFFF",
            padding=(14, 8),
            font=("Segoe UI Semibold", 10),
            borderwidth=0,
        )
        style.map(
            "Accent.TButton",
            background=[("active", C_ACCENT_HOVER), ("pressed", C_ACCENT_HOVER)],
            foreground=[("disabled", "#DDDDDD")],
        )
        style.configure("TButton", padding=(10, 6), font=font_ui)
        style.configure("TEntry", fieldbackground="#FFFFFF", padding=4)
        style.configure("TCombobox", padding=4, fieldbackground="#FFFFFF")
        style.configure("Card.TNotebook", background=C_BG, borderwidth=0)
        style.configure("Card.TNotebook.Tab", padding=(16, 8), font=font_ui)
        style.map(
            "Card.TNotebook.Tab",
            background=[("selected", C_SURFACE), ("!selected", C_BG)],
            foreground=[("selected", C_ACCENT)],
        )
        style.configure("Card.TLabelframe", background=C_SURFACE, bordercolor=C_LINE)
        style.configure("Card.TLabelframe.Label", background=C_SURFACE, foreground=C_MUTED, font=font_small)

    def _build_header(self) -> None:
        head = ttk.Frame(self, style="Header.TFrame", padding=(16, 14, 16, 8))
        head.pack(fill=tk.X)
        ttk.Label(head, text="DocFactory", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Label(
            head,
            text="шаблоны · отчёты · MD/DOCX/PDF · OCR",
            background=C_BG,
            foreground=C_MUTED,
            font=("Segoe UI", 10),
        ).pack(side=tk.LEFT, padx=12)

    def _build_generator(self, parent: ttk.Frame) -> None:
        top = ttk.Frame(parent, style="Card.TFrame", padding=14)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Тип документа", style="Card.TLabel").pack(side=tk.LEFT)
        titles = [f"{d.category}: {d.title}" for d in CATALOG]
        self.id_by_title = {f"{d.category}: {d.title}": d.id for d in CATALOG}
        self.combo = ttk.Combobox(top, values=titles, state="readonly", width=56)
        self.combo.set(titles[0])
        self.combo.pack(side=tk.LEFT, padx=10)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self._on_select())

        ttk.Button(top, text="Сформировать DOCX", style="Accent.TButton", command=self._generate).pack(side=tk.RIGHT)
        ttk.Button(top, text="Папка…", command=self._pick_out).pack(side=tk.RIGHT, padx=8)

        path_row = ttk.Frame(parent, style="Card.TFrame", padding=(14, 0, 14, 8))
        path_row.pack(fill=tk.X)
        ttk.Label(path_row, text="Сохранить в", style="Muted.TLabel").pack(side=tk.LEFT)
        ttk.Entry(path_row, textvariable=self.out_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

        self.desc = ttk.Label(parent, text="", style="Muted.TLabel", wraplength=960, padding=(14, 4))
        self.desc.pack(fill=tk.X)

        wrap = ttk.Frame(parent, style="Card.TFrame", padding=10)
        wrap.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(wrap, highlightthickness=0, bg=C_SURFACE)
        scroll = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=canvas.yview)
        self.form = ttk.Frame(canvas, style="Card.TFrame")
        self.form.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.form, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        ttk.Label(
            parent,
            text="Подсказка: в табличных полях строки — Enter, колонки — символ |   ·   отчёты и доклады — в категории «Отчёты» (вверху списка)",
            style="Muted.TLabel",
            padding=(14, 8),
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
            ttk.Label(self.form, text=f.label, style="Card.TLabel").grid(
                row=i, column=0, sticky="nw", pady=5, padx=(4, 10)
            )
            if f.multiline:
                txt = tk.Text(
                    self.form,
                    height=4,
                    width=78,
                    wrap=tk.WORD,
                    bg="#FAFBFA",
                    fg=C_INK,
                    relief=tk.FLAT,
                    highlightthickness=1,
                    highlightbackground=C_LINE,
                    highlightcolor=C_ACCENT,
                    font=("Segoe UI", 10),
                )
                txt.insert("1.0", f.default)
                txt.grid(row=i, column=1, sticky="ew", pady=5)
                self.field_widgets[f.key] = txt
            else:
                var = tk.StringVar(value=f.default)
                ent = ttk.Entry(self.form, textvariable=var, width=78)
                ent.grid(row=i, column=1, sticky="ew", pady=5)
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

    def _build_converter(self, parent: ttk.Frame) -> None:
        info = ttk.LabelFrame(parent, text=" Движки ", style="Card.TLabelframe", padding=12)
        info.pack(fill=tk.X, padx=14, pady=12)
        status = backend_status()
        lines = (
            f"MD ↔ DOCX: {status['md_docx']} / {status['docx_md']}\n"
            f"DOCX → PDF: {status['docx_pdf']}\n"
            f"PDF → DOCX: {status['pdf_docx']}\n"
            f"PDF OCR:    {status.get('pdf_ocr', '—')}\n\n"
            "Скан PDF без текста: выберите «PDF → DOCX (OCR)» или «PDF → MD (OCR)».\n"
            "Нужны Tesseract OCR (rus+eng) и pip: pytesseract Pillow."
        )
        ttk.Label(info, text=lines, style="Muted.TLabel", justify=tk.LEFT).pack(anchor="w")

        form = ttk.Frame(parent, style="Card.TFrame", padding=14)
        form.pack(fill=tk.X)

        ttk.Label(form, text="Исходный файл", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.src_file, width=70).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(form, text="Обзор…", command=self._pick_src).grid(row=0, column=2)

        ttk.Label(form, text="Куда сохранить", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=8)
        ttk.Entry(form, textvariable=self.dst_file, width=70).grid(row=1, column=1, sticky="ew", padx=8, pady=8)
        ttk.Button(form, text="Обзор…", command=self._pick_dst).grid(row=1, column=2, pady=8)

        ttk.Label(form, text="Режим", style="Card.TLabel").grid(row=2, column=0, sticky="w")
        modes = [
            "Авто по расширениям",
            "MD → DOCX",
            "DOCX → MD",
            "DOCX → PDF",
            "PDF → DOCX",
            "PDF → DOCX (OCR)",
            "PDF → MD",
            "PDF → MD (OCR)",
            "MD → PDF",
        ]
        ttk.Combobox(form, textvariable=self.conv_mode, values=modes, state="readonly", width=28).grid(
            row=2, column=1, sticky="w", padx=8
        )
        form.columnconfigure(1, weight=1)

        btns = ttk.Frame(parent, style="Card.TFrame", padding=14)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Конвертировать", style="Accent.TButton", command=self._convert).pack(side=tk.LEFT)
        ttk.Button(btns, text="Подставить имя результата", command=self._suggest_dst).pack(side=tk.LEFT, padx=10)

        ttk.Label(
            parent,
            text="DOCX → MD: режим «DOCX → MD».  ·  Сканы из кадров: только OCR-режимы дадут редактируемый текст.",
            style="Muted.TLabel",
            padding=(14, 8),
            justify=tk.LEFT,
        ).pack(anchor="w")

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
            "PDF → DOCX (OCR)": ".docx",
            "PDF → MD": ".md",
            "PDF → MD (OCR)": ".md",
            "MD → PDF": ".pdf",
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
        stem = p.stem + ("_ocr" if "OCR" in self.conv_mode.get() else "")
        self.dst_file.set(str(out_dir / (stem + self._target_ext())))

    def _forced_dst(self, src: Path) -> Path:
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
        mode = self.conv_mode.get()
        force_ocr = "OCR" in mode
        dst = self._forced_dst(src)
        if mode != "Авто по расширениям":
            dst = dst.with_suffix(self._target_ext())
            self.dst_file.set(str(dst))
        try:
            result = convert_auto(src, dst, force_ocr=force_ocr)
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

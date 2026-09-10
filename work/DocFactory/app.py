#!/usr/bin/env python3
"""DocFactory — генератор и конвертер Word/PDF/Markdown (офлайн)."""
from __future__ import annotations

import warnings

warnings.filterwarnings("ignore", message=".*fitz.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from docfactory.catalog import full_catalog, get_doc_type
from docfactory.convert import ConvertError, backend_status, convert_auto
from docfactory.custom_templates import (
    ROLE_BODY,
    ROLE_LABELS,
    ROLE_META,
    ROLE_SIGNATURE,
    CustomField,
    CustomTemplate,
    delete_custom,
    is_custom_id,
    list_customs,
    load_custom,
    new_template_id,
    save_custom,
)
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
        self.geometry("1080x780")
        self.minsize(920, 660)
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
        self.selected_id = tk.StringVar()
        self.field_vars: dict[str, tk.Variable] = {}
        self.field_widgets: dict[str, tk.Widget] = {}
        self.src_file = tk.StringVar()
        self.dst_file = tk.StringVar()
        self.conv_mode = tk.StringVar(value="Авто по расширениям")
        self.id_by_title: dict[str, str] = {}

        # конструктор
        self._builder_fields: list[dict] = []
        self._edit_id: str | None = None

        self._build_header()
        nb = ttk.Notebook(self, style="Card.TNotebook")
        nb.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))
        self.tab_gen = ttk.Frame(nb, style="Card.TFrame")
        self.tab_mine = ttk.Frame(nb, style="Card.TFrame")
        self.tab_conv = ttk.Frame(nb, style="Card.TFrame")
        nb.add(self.tab_gen, text="  Шаблоны  ")
        nb.add(self.tab_mine, text="  Мои шаблоны  ")
        nb.add(self.tab_conv, text="  Конвертация  ")
        self._build_generator(self.tab_gen)
        self._build_my_templates(self.tab_mine)
        self._build_converter(self.tab_conv)
        self._refresh_catalog(select_first=True)

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
            text="шаблоны · свои формы · MD/DOCX/PDF · OCR",
            background=C_BG,
            foreground=C_MUTED,
            font=("Segoe UI", 10),
        ).pack(side=tk.LEFT, padx=12)

    # ─── Вкладка шаблонов ───────────────────────────────────────────

    def _build_generator(self, parent: ttk.Frame) -> None:
        top = ttk.Frame(parent, style="Card.TFrame", padding=14)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Тип документа", style="Card.TLabel").pack(side=tk.LEFT)
        self.combo = ttk.Combobox(top, values=[], state="readonly", width=56)
        self.combo.pack(side=tk.LEFT, padx=10)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self._on_select())

        ttk.Button(top, text="Сформировать DOCX", style="Accent.TButton", command=self._generate).pack(side=tk.RIGHT)
        ttk.Button(top, text="Папка…", command=self._pick_out).pack(side=tk.RIGHT, padx=8)

        path_row = ttk.Frame(parent, style="Card.TFrame", padding=(14, 0, 14, 8))
        path_row.pack(fill=tk.X)
        ttk.Label(path_row, text="Сохранить в", style="Muted.TLabel").pack(side=tk.LEFT)
        ttk.Entry(path_row, textvariable=self.out_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

        self.desc = ttk.Label(parent, text="", style="Muted.TLabel", wraplength=980, padding=(14, 4))
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
            text="Подсказка: свои шаблоны — вкладка «Мои шаблоны». В табличных полях: строки — Enter, колонки — |",
            style="Muted.TLabel",
            padding=(14, 8),
        ).pack(fill=tk.X)

    def _refresh_catalog(self, select_id: str | None = None, select_first: bool = False) -> None:
        catalog = full_catalog()
        titles = [f"{d.category}: {d.title}" for d in catalog]
        self.id_by_title = {f"{d.category}: {d.title}": d.id for d in catalog}
        self.combo.configure(values=titles)
        if not titles:
            return
        target_title = None
        if select_id:
            for title, did in self.id_by_title.items():
                if did == select_id:
                    target_title = title
                    break
        if target_title is None and not select_first:
            cur = self.combo.get()
            if cur in self.id_by_title:
                target_title = cur
        if target_title is None:
            # предпочитаем первый встроенный, иначе любой
            target_title = titles[0]
            for t in titles:
                if not t.startswith("Мои шаблоны:"):
                    target_title = t
                    break
        self.combo.set(target_title)
        self._on_select()

    def _pick_out(self) -> None:
        path = filedialog.askdirectory(initialdir=self.out_dir.get() or str(DEFAULT_OUT))
        if path:
            self.out_dir.set(path)

    def _on_select(self) -> None:
        title = self.combo.get()
        if title not in self.id_by_title:
            return
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

    # ─── Вкладка «Мои шаблоны» ──────────────────────────────────────

    def _build_my_templates(self, parent: ttk.Frame) -> None:
        outer = ttk.Frame(parent, style="Card.TFrame", padding=12)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        left = ttk.Frame(outer, style="Card.TFrame")
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        ttk.Label(left, text="Сохранённые", style="Card.TLabel").pack(anchor="w")
        self.mine_list = tk.Listbox(
            left,
            height=18,
            width=28,
            activestyle="dotbox",
            bg="#FAFBFA",
            fg=C_INK,
            highlightthickness=1,
            highlightbackground=C_LINE,
            selectbackground=C_ACCENT,
            selectforeground="#FFFFFF",
            font=("Segoe UI", 10),
        )
        self.mine_list.pack(fill=tk.Y, pady=6)
        self.mine_list.bind("<<ListboxSelect>>", lambda e: self._on_mine_select())

        btns = ttk.Frame(left, style="Card.TFrame")
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Новый", command=self._builder_new).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Изменить", command=self._builder_edit_selected).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Удалить", command=self._builder_delete).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Заполнить →", command=self._builder_use).pack(fill=tk.X, pady=2)

        right = ttk.Frame(outer, style="Card.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(1, weight=1)

        ttk.Label(
            right,
            text="Конструктор шаблона — задайте заголовок и поля, сохраните, потом заполняйте на вкладке «Шаблоны».",
            style="Muted.TLabel",
            wraplength=640,
        ).grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.b_title = tk.StringVar()
        self.b_heading = tk.StringVar()
        self.b_filename = tk.StringVar(value="Moy_shablon.docx")
        self.b_desc = tk.StringVar()

        ttk.Label(right, text="Название в списке", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(right, textvariable=self.b_title, width=50).grid(row=1, column=1, columnspan=2, sticky="ew", pady=3)

        ttk.Label(right, text="Заголовок в DOCX", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(right, textvariable=self.b_heading, width=50).grid(row=2, column=1, columnspan=2, sticky="ew", pady=3)

        ttk.Label(right, text="Имя файла", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Entry(right, textvariable=self.b_filename, width=50).grid(row=3, column=1, columnspan=2, sticky="ew", pady=3)

        ttk.Label(right, text="Описание", style="Card.TLabel").grid(row=4, column=0, sticky="nw", pady=3)
        ttk.Entry(right, textvariable=self.b_desc, width=50).grid(row=4, column=1, columnspan=2, sticky="ew", pady=3)

        fields_box = ttk.LabelFrame(right, text=" Поля формы ", style="Card.TLabelframe", padding=8)
        fields_box.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=10)
        right.rowconfigure(5, weight=1)
        fields_box.columnconfigure(0, weight=1)

        hdr = ttk.Frame(fields_box, style="Card.TFrame")
        hdr.pack(fill=tk.X)
        for text, w in (
            ("Подпись поля", 28),
            ("Роль в документе", 18),
            ("Многострочное", 12),
            ("Значение по умолчанию", 24),
        ):
            ttk.Label(hdr, text=text, style="Muted.TLabel", width=w).pack(side=tk.LEFT, padx=2)

        scroll_wrap = ttk.Frame(fields_box, style="Card.TFrame")
        scroll_wrap.pack(fill=tk.BOTH, expand=True, pady=4)
        self.fields_canvas = tk.Canvas(scroll_wrap, height=260, highlightthickness=0, bg=C_SURFACE)
        fscroll = ttk.Scrollbar(scroll_wrap, orient=tk.VERTICAL, command=self.fields_canvas.yview)
        self.fields_inner = ttk.Frame(self.fields_canvas, style="Card.TFrame")
        self.fields_inner.bind(
            "<Configure>", lambda e: self.fields_canvas.configure(scrollregion=self.fields_canvas.bbox("all"))
        )
        self.fields_canvas.create_window((0, 0), window=self.fields_inner, anchor="nw")
        self.fields_canvas.configure(yscrollcommand=fscroll.set)
        self.fields_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        fscroll.pack(side=tk.RIGHT, fill=tk.Y)

        row_btns = ttk.Frame(fields_box, style="Card.TFrame")
        row_btns.pack(fill=tk.X)
        ttk.Button(row_btns, text="+ Поле", command=lambda: self._builder_add_field()).pack(side=tk.LEFT)
        ttk.Button(row_btns, text="Шаблон: записка", command=self._builder_preset_zapiska).pack(side=tk.LEFT, padx=6)
        ttk.Button(row_btns, text="Шаблон: отчёт", command=self._builder_preset_otchet).pack(side=tk.LEFT)

        save_row = ttk.Frame(right, style="Card.TFrame")
        save_row.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        ttk.Button(save_row, text="Сохранить шаблон", style="Accent.TButton", command=self._builder_save).pack(
            side=tk.LEFT
        )
        ttk.Button(save_row, text="Очистить форму", command=self._builder_new).pack(side=tk.LEFT, padx=8)
        self.b_status = ttk.Label(save_row, text="", style="Muted.TLabel")
        self.b_status.pack(side=tk.LEFT, padx=8)

        self._refresh_mine_list()
        self._builder_new()

    def _refresh_mine_list(self) -> None:
        self.mine_list.delete(0, tk.END)
        self._mine_ids: list[str] = []
        for t in list_customs():
            self.mine_list.insert(tk.END, t.title)
            self._mine_ids.append(t.id)

    def _selected_mine_id(self) -> str | None:
        sel = self.mine_list.curselection()
        if not sel:
            return None
        idx = int(sel[0])
        if 0 <= idx < len(self._mine_ids):
            return self._mine_ids[idx]
        return None

    def _on_mine_select(self) -> None:
        tid = self._selected_mine_id()
        if tid:
            self._builder_load(tid)

    def _builder_clear_fields_ui(self) -> None:
        for child in self.fields_inner.winfo_children():
            child.destroy()
        self._builder_fields.clear()

    def _builder_add_field(
        self,
        label: str = "",
        role: str = ROLE_BODY,
        multiline: bool = False,
        default: str = "",
    ) -> None:
        row = ttk.Frame(self.fields_inner, style="Card.TFrame")
        row.pack(fill=tk.X, pady=2)
        label_var = tk.StringVar(value=label)
        role_var = tk.StringVar(value=ROLE_LABELS.get(role, ROLE_LABELS[ROLE_BODY]))
        multi_var = tk.BooleanVar(value=multiline)
        default_var = tk.StringVar(value=default)

        ttk.Entry(row, textvariable=label_var, width=28).pack(side=tk.LEFT, padx=2)
        role_cb = ttk.Combobox(
            row,
            textvariable=role_var,
            values=list(ROLE_LABELS.values()),
            state="readonly",
            width=18,
        )
        role_cb.pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(row, variable=multi_var, text="да").pack(side=tk.LEFT, padx=8)
        ttk.Entry(row, textvariable=default_var, width=24).pack(side=tk.LEFT, padx=2)

        def _remove() -> None:
            row.destroy()
            self._builder_fields[:] = [f for f in self._builder_fields if f["frame"] is not row]

        ttk.Button(row, text="×", width=3, command=_remove).pack(side=tk.LEFT, padx=4)

        self._builder_fields.append(
            {
                "frame": row,
                "label": label_var,
                "role": role_var,
                "multiline": multi_var,
                "default": default_var,
            }
        )

    def _role_key(self, label: str) -> str:
        for k, v in ROLE_LABELS.items():
            if v == label:
                return k
        return ROLE_BODY

    def _builder_collect_fields(self) -> list[CustomField]:
        used: set[str] = set()
        out: list[CustomField] = []
        from docfactory.custom_templates import _safe_key

        for item in self._builder_fields:
            label = item["label"].get().strip()
            if not label:
                continue
            role = self._role_key(item["role"].get())
            multi = bool(item["multiline"].get())
            out.append(
                CustomField(
                    key=_safe_key(label, used),
                    label=label,
                    multiline=multi,
                    default=item["default"].get(),
                    role=role,
                )
            )
        return out

    def _builder_new(self) -> None:
        self._edit_id = None
        self.b_title.set("")
        self.b_heading.set("")
        self.b_filename.set("Moy_shablon.docx")
        self.b_desc.set("")
        self._builder_clear_fields_ui()
        self._builder_add_field("Организация", ROLE_META, False, 'ГУ «Белгидромет»')
        self._builder_add_field("Подразделение", ROLE_META, False, "Служба программного обеспечения")
        self._builder_add_field("Дата", ROLE_META, False, "«____» ______________ 202__ г.")
        self._builder_add_field("Содержание", ROLE_BODY, True, "")
        self._builder_add_field("Исполнитель", ROLE_SIGNATURE, False, "")
        self.b_status.configure(text="Новый шаблон (ещё не сохранён)")

    def _builder_preset_zapiska(self) -> None:
        self.b_title.set(self.b_title.get() or "Моя служебная записка")
        self.b_heading.set(self.b_heading.get() or "СЛУЖЕБНАЯ ЗАПИСКА")
        self.b_filename.set("Moya_sluzhebnaya_zapiska.docx")
        self._builder_clear_fields_ui()
        for label, role, multi, default in (
            ("Организация", ROLE_META, False, 'ГУ «Белгидромет»'),
            ("Кому", ROLE_META, False, ""),
            ("От кого", ROLE_META, False, ""),
            ("Дата", ROLE_META, False, "«____» ______________ 202__ г."),
            ("Тема", ROLE_META, False, ""),
            ("Текст", ROLE_BODY, True, ""),
            ("Просьба", ROLE_BODY, True, ""),
            ("Подпись", ROLE_SIGNATURE, False, ""),
        ):
            self._builder_add_field(label, role, multi, default)
        self.b_status.configure(text="Пресет «записка» — сохраните, чтобы пользоваться")

    def _builder_preset_otchet(self) -> None:
        self.b_title.set(self.b_title.get() or "Мой отчёт")
        self.b_heading.set(self.b_heading.get() or "ОТЧЁТ")
        self.b_filename.set("Moy_otchet.docx")
        self._builder_clear_fields_ui()
        for label, role, multi, default in (
            ("Организация", ROLE_META, False, 'ГУ «Белгидромет»'),
            ("Подразделение", ROLE_META, False, "Служба программного обеспечения"),
            ("ФИО", ROLE_META, False, ""),
            ("Должность", ROLE_META, False, ""),
            ("Период", ROLE_META, False, ""),
            ("Дата", ROLE_META, False, "«____» ______________ 202__ г."),
            ("Цель", ROLE_BODY, True, ""),
            ("Выполнено", ROLE_BODY, True, ""),
            ("Результаты", ROLE_BODY, True, ""),
            ("Выводы", ROLE_BODY, True, ""),
            ("Руководитель", ROLE_SIGNATURE, False, ""),
            ("Исполнитель", ROLE_SIGNATURE, False, ""),
        ):
            self._builder_add_field(label, role, multi, default)
        self.b_status.configure(text="Пресет «отчёт» — сохраните, чтобы пользоваться")

    def _builder_load(self, template_id: str) -> None:
        tmpl = load_custom(template_id)
        if tmpl is None:
            return
        self._edit_id = tmpl.id
        self.b_title.set(tmpl.title)
        self.b_heading.set(tmpl.doc_heading or tmpl.title)
        self.b_filename.set(tmpl.filename)
        self.b_desc.set(tmpl.description)
        self._builder_clear_fields_ui()
        for f in tmpl.fields:
            self._builder_add_field(f.label, f.role, f.multiline, f.default)
        self.b_status.configure(text=f"Редактирование: {tmpl.id}")

    def _builder_edit_selected(self) -> None:
        tid = self._selected_mine_id()
        if not tid:
            messagebox.showinfo("Мои шаблоны", "Выберите шаблон слева.")
            return
        self._builder_load(tid)

    def _builder_save(self) -> None:
        title = self.b_title.get().strip()
        if not title:
            messagebox.showwarning("Сохранение", "Укажите название шаблона.")
            return
        fields = self._builder_collect_fields()
        if not fields:
            messagebox.showwarning("Сохранение", "Добавьте хотя бы одно поле.")
            return
        tmpl = CustomTemplate(
            id=self._edit_id or new_template_id(),
            title=title,
            description=self.b_desc.get().strip(),
            filename=(self.b_filename.get().strip() or "Moy_shablon.docx"),
            doc_heading=self.b_heading.get().strip() or title,
            fields=fields,
        )
        if not tmpl.filename.lower().endswith(".docx"):
            tmpl.filename += ".docx"
        try:
            path = save_custom(tmpl)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", str(exc))
            return
        self._edit_id = tmpl.id
        self._refresh_mine_list()
        self._refresh_catalog(select_id=tmpl.id)
        # выделить в списке
        if tmpl.id in self._mine_ids:
            idx = self._mine_ids.index(tmpl.id)
            self.mine_list.selection_clear(0, tk.END)
            self.mine_list.selection_set(idx)
            self.mine_list.see(idx)
        self.b_status.configure(text=f"Сохранено: {path.name}")
        messagebox.showinfo(
            "Готово",
            f"Шаблон «{tmpl.title}» сохранён.\nОн появился в списке на вкладке «Шаблоны» (категория «Мои шаблоны»).",
        )

    def _builder_delete(self) -> None:
        tid = self._selected_mine_id() or self._edit_id
        if not tid or not is_custom_id(tid):
            messagebox.showinfo("Удаление", "Выберите сохранённый шаблон.")
            return
        tmpl = load_custom(tid)
        name = tmpl.title if tmpl else tid
        if not messagebox.askyesno("Удаление", f"Удалить шаблон «{name}»?"):
            return
        delete_custom(tid)
        self._refresh_mine_list()
        self._refresh_catalog(select_first=True)
        self._builder_new()
        self.b_status.configure(text="Шаблон удалён")

    def _builder_use(self) -> None:
        tid = self._selected_mine_id() or self._edit_id
        if not tid or not is_custom_id(tid):
            messagebox.showinfo("Заполнение", "Сначала сохраните и выберите шаблон.")
            return
        if load_custom(tid) is None:
            messagebox.showwarning("Заполнение", "Шаблон не найден на диске. Сохраните его.")
            return
        self._refresh_catalog(select_id=tid)
        messagebox.showinfo("Шаблоны", "Шаблон выбран на вкладке «Шаблоны» — заполните поля и нажмите «Сформировать DOCX».")

    # ─── Конвертация ────────────────────────────────────────────────

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

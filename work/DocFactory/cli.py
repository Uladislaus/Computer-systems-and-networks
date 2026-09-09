#!/usr/bin/env python3
"""CLI DocFactory: шаблоны и конвертация."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from docfactory.catalog import CATALOG, get_doc_type
from docfactory.convert import backend_status, convert_auto
from docfactory.generators import generate


def main() -> None:
    parser = argparse.ArgumentParser(description="DocFactory offline DOCX/PDF/MD tool")
    parser.add_argument("--list", action="store_true", help="Список типов документов")
    parser.add_argument("--type", dest="doc_type", help="ID типа документа")
    parser.add_argument("--data", help="JSON-файл с полями")
    parser.add_argument("--out", default="output", help="Папка вывода для шаблонов")
    parser.add_argument("--convert", metavar="SRC", help="Конвертировать файл (MD/DOCX/PDF)")
    parser.add_argument("--to", dest="convert_to", help="Путь результата конвертации")
    parser.add_argument("--engines", action="store_true", help="Статус движков конвертации")
    args = parser.parse_args()

    if args.engines:
        for k, v in backend_status().items():
            print(f"{k}: {v}")
        return

    if args.list:
        for d in CATALOG:
            print(f"{d.id:28} | {d.category:24} | {d.title}")
        return

    if args.convert:
        path = convert_auto(Path(args.convert), Path(args.convert_to) if args.convert_to else None)
        print(path)
        return

    if not args.doc_type:
        parser.error("укажите --type, --convert, --list или --engines")

    dtype = get_doc_type(args.doc_type)
    data = {f.key: f.default for f in dtype.fields}
    if args.data:
        data.update(json.loads(Path(args.data).read_text(encoding="utf-8")))

    path = generate(args.doc_type, data, Path(args.out))
    print(path)


if __name__ == "__main__":
    main()

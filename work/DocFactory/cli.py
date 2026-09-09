#!/usr/bin/env python3
"""CLI: python cli.py --list | python cli.py --type sluzhebnaya_zapiska --out output"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from docfactory.catalog import CATALOG, get_doc_type
from docfactory.generators import generate


def main() -> None:
    parser = argparse.ArgumentParser(description="DocFactory offline DOCX generator")
    parser.add_argument("--list", action="store_true", help="Список типов документов")
    parser.add_argument("--type", dest="doc_type", help="ID типа документа")
    parser.add_argument("--data", help="JSON-файл с полями")
    parser.add_argument("--out", default="output", help="Папка вывода")
    args = parser.parse_args()

    if args.list:
        for d in CATALOG:
            print(f"{d.id:28} | {d.category:24} | {d.title}")
        return

    if not args.doc_type:
        parser.error("укажите --type или --list")

    dtype = get_doc_type(args.doc_type)
    data = {f.key: f.default for f in dtype.fields}
    if args.data:
        data.update(json.loads(Path(args.data).read_text(encoding="utf-8")))

    path = generate(args.doc_type, data, Path(args.out))
    print(path)


if __name__ == "__main__":
    main()

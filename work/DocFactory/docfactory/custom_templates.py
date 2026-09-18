"""Пользовательские шаблоны: создание, хранение, загрузка (JSON)."""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from docfactory.catalog import DocType, Field

USER_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "user_templates"

# Роли полей в макете DOCX
ROLE_META = "meta"  # строка в таблице шапки
ROLE_BODY = "body"  # раздел документа
ROLE_SIGNATURE = "signature"  # блок подписи

ROLE_LABELS = {
    ROLE_META: "Шапка (таблица)",
    ROLE_BODY: "Раздел",
    ROLE_SIGNATURE: "Подпись",
}


@dataclass
class CustomField:
    key: str
    label: str
    multiline: bool = False
    default: str = ""
    role: str = ROLE_BODY

    def to_field(self) -> Field:
        return Field(self.key, self.label, self.multiline, self.default)


@dataclass
class CustomTemplate:
    id: str
    title: str
    description: str = ""
    filename: str = "Moy_shablon.docx"
    doc_heading: str = ""
    fields: list[CustomField] = field(default_factory=list)
    created: str = ""
    updated: str = ""

    def to_doc_type(self) -> DocType:
        return DocType(
            id=self.id,
            title=self.title,
            category="Мои шаблоны",
            description=self.description or "Пользовательский шаблон",
            fields=tuple(f.to_field() for f in self.fields),
            filename=self.filename or _safe_filename(self.title),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "filename": self.filename,
            "doc_heading": self.doc_heading,
            "fields": [asdict(f) for f in self.fields],
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CustomTemplate:
        fields = [
            CustomField(
                key=str(f.get("key") or "").strip() or f"field_{i}",
                label=str(f.get("label") or f.get("key") or f"Поле {i}"),
                multiline=bool(f.get("multiline", False)),
                default=str(f.get("default") or ""),
                role=str(f.get("role") or ROLE_BODY),
            )
            for i, f in enumerate(data.get("fields") or [], start=1)
        ]
        return cls(
            id=str(data.get("id") or ""),
            title=str(data.get("title") or "Без названия"),
            description=str(data.get("description") or ""),
            filename=str(data.get("filename") or "Moy_shablon.docx"),
            doc_heading=str(data.get("doc_heading") or ""),
            fields=fields,
            created=str(data.get("created") or ""),
            updated=str(data.get("updated") or ""),
        )


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_filename(title: str) -> str:
    name = re.sub(r"[^\w\-]+", "_", title.strip(), flags=re.UNICODE)
    name = re.sub(r"_+", "_", name).strip("_") or "Moy_shablon"
    if not name.lower().endswith(".docx"):
        name += ".docx"
    return name


def _safe_key(label: str, used: set[str]) -> str:
    base = re.sub(r"[^\w]+", "_", label.strip().lower(), flags=re.UNICODE)
    base = re.sub(r"_+", "_", base).strip("_") or "field"
    base = base[:40]
    key = base
    n = 2
    while key in used:
        key = f"{base}_{n}"
        n += 1
    used.add(key)
    return key


def ensure_dir() -> Path:
    USER_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    return USER_TEMPLATES_DIR


def template_path(template_id: str) -> Path:
    return ensure_dir() / f"{template_id}.json"


def is_custom_id(doc_id: str) -> bool:
    return doc_id.startswith("custom_")


def new_template_id() -> str:
    return f"custom_{uuid.uuid4().hex[:10]}"


def list_customs() -> list[CustomTemplate]:
    ensure_dir()
    items: list[CustomTemplate] = []
    for path in sorted(USER_TEMPLATES_DIR.glob("custom_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            tmpl = CustomTemplate.from_dict(data)
            if not tmpl.id:
                tmpl.id = path.stem
            items.append(tmpl)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    items.sort(key=lambda t: (t.title.lower(), t.id))
    return items


def load_custom(template_id: str) -> CustomTemplate | None:
    if not is_custom_id(template_id):
        return None
    path = template_path(template_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        tmpl = CustomTemplate.from_dict(data)
        tmpl.id = template_id
        return tmpl
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def save_custom(tmpl: CustomTemplate) -> Path:
    if not tmpl.id:
        tmpl.id = new_template_id()
    if not is_custom_id(tmpl.id):
        raise ValueError("ID пользовательского шаблона должен начинаться с custom_")
    now = _now()
    if not tmpl.created:
        tmpl.created = now
    tmpl.updated = now
    if not tmpl.filename:
        tmpl.filename = _safe_filename(tmpl.title)
    # нормализуем ключи полей
    used: set[str] = set()
    for f in tmpl.fields:
        if not f.key or f.key in used:
            f.key = _safe_key(f.label or f.key or "field", used)
        else:
            used.add(f.key)
        if f.role not in ROLE_LABELS:
            f.role = ROLE_BODY
    path = template_path(tmpl.id)
    path.write_text(json.dumps(tmpl.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def delete_custom(template_id: str) -> bool:
    path = template_path(template_id)
    if path.exists():
        path.unlink()
        return True
    return False


def fields_from_labels(
    rows: list[tuple[str, str, bool, str]],
) -> list[CustomField]:
    """rows: (label, role, multiline, default)."""
    used: set[str] = set()
    out: list[CustomField] = []
    for label, role, multiline, default in rows:
        label = (label or "").strip()
        if not label:
            continue
        out.append(
            CustomField(
                key=_safe_key(label, used),
                label=label,
                multiline=bool(multiline),
                default=default or "",
                role=role if role in ROLE_LABELS else ROLE_BODY,
            )
        )
    return out

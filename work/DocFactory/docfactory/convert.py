"""Офлайн-конвертеры: Markdown ↔ DOCX, DOCX ↔ PDF."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from docfactory.engine import add_para, new_document, save_doc


class ConvertError(RuntimeError):
    pass


def _set_run_font(run, size: int = 12, bold: bool = False, italic: bool = False) -> None:
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic


def _add_inline(p, text: str, size: int = 12, bold: bool = False, italic: bool = False) -> None:
    parts = re.split(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = p.add_run(part[2:-2])
            _set_run_font(run, size=size, bold=True)
        elif part.startswith("`") and part.endswith("`"):
            run = p.add_run(part[1:-1])
            _set_run_font(run, size=size)
            run.font.name = "Courier New"
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            run = p.add_run(part[1:-1])
            _set_run_font(run, size=size, italic=True)
        else:
            run = p.add_run(part)
            _set_run_font(run, size=size, bold=bold, italic=italic)


def _parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    i = start
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.startswith("|"):
            break
        stripped = re.sub(r"\s", "", line)
        if re.match(r"^\|[\-:|]+\|$", stripped):
            i += 1
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)
        i += 1
    return rows, i


def md_to_docx(src: Path, dst: Path | None = None) -> Path:
    """Markdown → DOCX (python-docx, офлайн)."""
    src = Path(src)
    if src.suffix.lower() != ".md":
        raise ConvertError("Ожидался файл .md")
    dst = Path(dst) if dst else src.with_suffix(".docx")
    lines = src.read_text(encoding="utf-8").splitlines()
    doc = new_document()
    i = 0
    while i < len(lines):
        raw = lines[i].rstrip()
        if not raw or raw.strip() == "---":
            i += 1
            continue
        if raw.startswith("# "):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(12)
            _add_inline(p, raw[2:].strip(), size=16, bold=True)
            # force bold on whole title
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(16)
            i += 1
            continue
        if raw.startswith("## "):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(8)
            _add_inline(p, raw[3:].strip(), size=14, bold=True)
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(14)
            i += 1
            continue
        if raw.startswith("### "):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(6)
            _add_inline(p, raw[4:].strip(), size=13, bold=True)
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(13)
            i += 1
            continue
        if raw.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(6)
            _add_inline(p, raw[2:].strip(), size=11, italic=True)
            for run in p.runs:
                run.italic = True
            i += 1
            continue
        if re.match(r"^[-*]\s+", raw):
            content = re.sub(r"^[-*]\s+", "", raw)
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.75)
            p.paragraph_format.space_after = Pt(3)
            _add_inline(p, "• " + content, size=12)
            i += 1
            continue
        m = re.match(r"^(\d+)\.\s+(.*)$", raw)
        if m:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.75)
            p.paragraph_format.space_after = Pt(3)
            _add_inline(p, f"{m.group(1)}. {m.group(2)}", size=12)
            i += 1
            continue
        if raw.startswith("|"):
            rows, next_i = _parse_table(lines, i)
            if rows:
                cols = max(len(r) for r in rows)
                table = doc.add_table(rows=len(rows), cols=cols)
                table.style = "Table Grid"
                for r_idx, row in enumerate(rows):
                    for c_idx in range(cols):
                        cell_text = row[c_idx] if c_idx < len(row) else ""
                        cell = table.rows[r_idx].cells[c_idx]
                        cell.text = ""
                        clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", cell_text)
                        clean = re.sub(r"`([^`]+)`", r"\1", clean)
                        run = cell.paragraphs[0].add_run(clean)
                        _set_run_font(run, size=10, bold=(r_idx == 0))
                doc.add_paragraph()
            i = next_i
            continue
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        _add_inline(p, raw, size=12)
        i += 1
    return save_doc(doc, dst)


def docx_to_md(src: Path, dst: Path | None = None) -> Path:
    """DOCX → Markdown (упрощённо: абзацы и таблицы)."""
    src = Path(src)
    if src.suffix.lower() != ".docx":
        raise ConvertError("Ожидался файл .docx")
    dst = Path(dst) if dst else src.with_suffix(".md")
    doc = Document(src)
    out: list[str] = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            out.append("")
            continue
        style = (p.style.name or "") if p.style else ""
        if style.startswith("Heading 1"):
            out.append(f"# {text}")
        elif style.startswith("Heading 2"):
            out.append(f"## {text}")
        elif style.startswith("Heading 3"):
            out.append(f"### {text}")
        else:
            out.append(text)
    for table in doc.tables:
        out.append("")
        grid = [[c.text.strip().replace("\n", " ") for c in row.cells] for row in table.rows]
        if not grid:
            continue
        cols = max(len(r) for r in grid)
        for r in grid:
            while len(r) < cols:
                r.append("")
        out.append("| " + " | ".join(grid[0]) + " |")
        out.append("| " + " | ".join(["---"] * cols) + " |")
        for row in grid[1:]:
            out.append("| " + " | ".join(row) + " |")
        out.append("")
    dst.write_text("\n".join(out).strip() + "\n", encoding="utf-8")
    return dst


def _find_libreoffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    # Common Windows installs
    candidates = [
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def docx_to_pdf(src: Path, dst: Path | None = None) -> Path:
    """DOCX → PDF через LibreOffice (предпочтительно) или docx2pdf (Word на Windows)."""
    src = Path(src).resolve()
    if src.suffix.lower() != ".docx":
        raise ConvertError("Ожидался файл .docx")
    dst = Path(dst).resolve() if dst else src.with_suffix(".pdf")
    dst.parent.mkdir(parents=True, exist_ok=True)

    lo = _find_libreoffice()
    if lo:
        with tempfile.TemporaryDirectory() as tmp:
            cmd = [
                lo,
                "--headless",
                "--nologo",
                "--nofirststartwizard",
                "--convert-to",
                "pdf",
                "--outdir",
                tmp,
                str(src),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                raise ConvertError(
                    "LibreOffice не смог конвертировать в PDF.\n"
                    f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
                )
            produced = Path(tmp) / (src.stem + ".pdf")
            if not produced.exists():
                pdfs = list(Path(tmp).glob("*.pdf"))
                if not pdfs:
                    raise ConvertError("LibreOffice отработал, но PDF не найден.")
                produced = pdfs[0]
            shutil.copy2(produced, dst)
        return dst

    # Fallback: docx2pdf (requires Microsoft Word on Windows)
    try:
        from docx2pdf import convert as docx2pdf_convert  # type: ignore
    except ImportError as exc:
        raise ConvertError(
            "Для DOCX→PDF нужен LibreOffice (soffice) или пакет docx2pdf + Microsoft Word.\n"
            "Установите LibreOffice: https://www.libreoffice.org/\n"
            "Либо: pip install docx2pdf  (только Windows с установленным Word)."
        ) from exc

    docx2pdf_convert(str(src), str(dst))
    if not dst.exists():
        raise ConvertError("docx2pdf завершился без создания PDF.")
    return dst


def pdf_to_docx(src: Path, dst: Path | None = None) -> Path:
    """PDF → DOCX через pdf2docx (офлайн-библиотека)."""
    src = Path(src)
    if src.suffix.lower() != ".pdf":
        raise ConvertError("Ожидался файл .pdf")
    dst = Path(dst) if dst else src.with_suffix(".docx")
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        from pdf2docx import Converter  # type: ignore
    except ImportError as exc:
        raise ConvertError(
            "Для PDF→DOCX установите зависимость: pip install pdf2docx"
        ) from exc

    cv = Converter(str(src))
    try:
        cv.convert(str(dst))
    finally:
        cv.close()
    if not dst.exists():
        raise ConvertError("pdf2docx не создал файл DOCX.")
    return dst


def convert_auto(src: Path, dst: Path | None = None) -> Path:
    """Автовыбор направления по расширениям src/dst."""
    src = Path(src)
    if dst is None:
        # sensible defaults
        mapping = {
            ".md": ".docx",
            ".docx": ".pdf",
            ".pdf": ".docx",
        }
        ext = mapping.get(src.suffix.lower())
        if not ext:
            raise ConvertError(f"Не знаю, во что конвертировать {src.suffix}")
        dst = src.with_suffix(ext)
    else:
        dst = Path(dst)

    pair = (src.suffix.lower(), dst.suffix.lower())
    if pair == (".md", ".docx"):
        return md_to_docx(src, dst)
    if pair == (".docx", ".md"):
        return docx_to_md(src, dst)
    if pair == (".docx", ".pdf"):
        return docx_to_pdf(src, dst)
    if pair == (".pdf", ".docx"):
        return pdf_to_docx(src, dst)
    if pair == (".pdf", ".md"):
        # via docx
        tmp = dst.with_suffix(".tmp.docx")
        pdf_to_docx(src, tmp)
        try:
            return docx_to_md(tmp, dst)
        finally:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
    if pair == (".md", ".pdf"):
        tmp = dst.with_suffix(".tmp.docx")
        md_to_docx(src, tmp)
        try:
            return docx_to_pdf(tmp, dst)
        finally:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
    raise ConvertError(f"Неподдерживаемая пара: {pair[0]} → {pair[1]}")


def backend_status() -> dict[str, str]:
    """Статус доступных бэкендов конвертации."""
    status = {
        "md_docx": "ok (python-docx)",
        "docx_md": "ok (python-docx)",
        "docx_pdf": "нет LibreOffice / docx2pdf",
        "pdf_docx": "нет pdf2docx",
    }
    if _find_libreoffice():
        status["docx_pdf"] = f"ok (LibreOffice: {_find_libreoffice()})"
    else:
        try:
            import docx2pdf  # noqa: F401

            status["docx_pdf"] = "ok (docx2pdf / нужен Word)"
        except ImportError:
            pass
    try:
        import pdf2docx  # noqa: F401

        status["pdf_docx"] = "ok (pdf2docx)"
    except ImportError:
        pass
    return status

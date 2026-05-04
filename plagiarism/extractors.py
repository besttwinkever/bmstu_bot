"""Извлечение сырого текста из файлов работ.

Поддерживаем форматы, которые реально встречаются в учебных работах:
`.txt`, `.docx`, `.pdf`. Неизвестный формат → `UnsupportedFormat`, вызов
сам решит: пропустить работу или отметить отчёт как несостоявшийся.
"""
from __future__ import annotations

import io
import os
from typing import Callable, Dict


class UnsupportedFormat(Exception):
    """Расширение файла не поддерживается для извлечения текста."""


def _from_txt(data: bytes) -> str:
    for encoding in ('utf-8', 'cp1251', 'latin-1'):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode('utf-8', errors='ignore')


def _from_docx(data: bytes) -> str:
    from docx import Document  # python-docx
    doc = Document(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs if p.text]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text:
                    parts.append(cell.text)
    return '\n'.join(parts)


def _from_pdf(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    return '\n'.join((page.extract_text() or '') for page in reader.pages)


_EXTRACTORS: Dict[str, Callable[[bytes], str]] = {
    '.txt': _from_txt,
    '.docx': _from_docx,
    '.pdf': _from_pdf,
}


def extract_text(file_name: str, data: bytes) -> str:
    ext = os.path.splitext(file_name)[1].lower()
    extractor = _EXTRACTORS.get(ext)
    if extractor is None:
        raise UnsupportedFormat(f'Cannot extract text from {ext} files')
    return extractor(data)


def supported_extensions() -> list[str]:
    return [ext.lstrip('.') for ext in _EXTRACTORS]

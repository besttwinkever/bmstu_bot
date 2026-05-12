"""Подготовка извлечённого текста к сравнению.

Титульные листы, оглавления и короткие заголовки сильно похожи у разных
учебных работ, но не являются содержательным доказательством плагиата.
"""
from __future__ import annotations

import re


MIN_CLEAN_WORDS = 20

_BOILERPLATE_FRAGMENTS = (
    'министерство',
    'образования',
    'федеральное государственное',
    'высшего образования',
    'московский государственный технический университет',
    'мгту',
    'им. н. э. баумана',
    'имени н. э. баумана',
    'кафедра',
    'факультет',
    'на правах рукописи',
    'студент',
    'обучающийся',
    'преподаватель',
    'руководитель',
    'консультант',
    'проверил',
    'выполнил',
    'группа',
    'нормоконтролер',
)

_HEADING_PHRASES = {
    'аннотация',
    'введение',
    'заключение',
    'содержание',
    'оглавление',
    'список литературы',
    'список использованных источников',
    'перечень сокращений',
    'приложение',
    'цель работы',
    'задачи работы',
}


def _words(text: str) -> list[str]:
    return re.findall(r'[a-zа-яё0-9]+', text.lower(), flags=re.IGNORECASE)


def _is_upper_heading(line: str) -> bool:
    letters = re.findall(r'[A-Za-zА-Яа-яЁё]', line)
    return bool(letters) and line == line.upper()


def _is_boilerplate_line(line: str) -> bool:
    normalized = re.sub(r'\s+', ' ', line.strip().lower().replace('ё', 'е'))
    if not normalized:
        return True
    if re.fullmatch(r'[\d\s.,:-]+', normalized):
        return True
    if re.search(r'\.{3,}\s*\d+$', normalized):
        return True
    if re.fullmatch(r'(г\.\s*)?москва[, ]*\d{4}', normalized):
        return True

    words = _words(normalized)
    if len(words) <= 14 and any(fragment in normalized for fragment in _BOILERPLATE_FRAGMENTS):
        return True
    if len(words) <= 5:
        if normalized.rstrip(':') in _HEADING_PHRASES:
            return True
        if normalized.startswith(('глава ', 'раздел ')):
            return True
        if re.fullmatch(r'\d+(\.\d+)*\.?\s+.+', normalized):
            return True
        if _is_upper_heading(line):
            return True
        if normalized.endswith(':'):
            return True

    return False


def prepare_text_for_comparison(text: str) -> str:
    lines = [
        re.sub(r'\s+', ' ', line).strip()
        for line in (text or '').splitlines()
    ]
    kept = [line for line in lines if not _is_boilerplate_line(line)]
    cleaned = '\n'.join(kept).strip()
    cleaned_words = _words(cleaned)
    if len(cleaned_words) >= MIN_CLEAN_WORDS:
        return cleaned

    original = (text or '').strip()
    if len(_words(original)) >= MIN_CLEAN_WORDS:
        return original
    return cleaned or original

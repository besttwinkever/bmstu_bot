"""Метод шинглов (Жаккар) — быстрая проверка точного совпадения."""
from __future__ import annotations

import re
from typing import Set


DEFAULT_SHINGLE_SIZE = 3


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text, flags=re.UNICODE)
    return [t for t in text.split() if t]


def get_shingles(text: str, shingle_size: int = DEFAULT_SHINGLE_SIZE) -> Set[str]:
    words = _tokenize(text)
    if len(words) < shingle_size:
        return set()
    return {
        ' '.join(words[i:i + shingle_size])
        for i in range(len(words) - shingle_size + 1)
    }


def jaccard_similarity(text1: str, text2: str, shingle_size: int = DEFAULT_SHINGLE_SIZE) -> float:
    """Процент совпадения шинглов (0.0–100.0) по формуле Жаккара."""
    set1 = get_shingles(text1, shingle_size)
    set2 = get_shingles(text2, shingle_size)
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return (intersection / union) * 100

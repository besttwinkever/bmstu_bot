"""Семантическое сравнение через SentenceTransformer (rubert-tiny2)."""
from __future__ import annotations

import logging
import threading
from typing import Optional

from django.conf import settings


logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()

DEFAULT_MODEL_NAME = 'cointegrated/rubert-tiny2'
DEFAULT_THRESHOLD = 0.7

# Длинные документы делим на «окна»: SentenceTransformer-ы режут вход
# по max_seq_length (обычно 256 токенов ≈ 1.5 кБ), и без чанкования мы
# сравниваем только начало работ — для рефератов это критично.
_CHUNK_SIZE_CHARS = 1500
_CHUNK_OVERLAP_CHARS = 200
_MAX_CHUNKS_PER_TEXT = 12


def _get_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        from sentence_transformers import SentenceTransformer

        model_name = getattr(settings, 'PLAGIARISM_BERT_MODEL', DEFAULT_MODEL_NAME)
        logger.info('Loading BERT model %s', model_name)
        _model = SentenceTransformer(model_name)
    return _model


def _split_into_chunks(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= _CHUNK_SIZE_CHARS:
        return [text]

    chunks: list[str] = []
    step = _CHUNK_SIZE_CHARS - _CHUNK_OVERLAP_CHARS
    pos = 0
    while pos < len(text) and len(chunks) < _MAX_CHUNKS_PER_TEXT:
        chunks.append(text[pos:pos + _CHUNK_SIZE_CHARS])
        pos += step
    return chunks


def encode_chunks(text: str):
    """Закодировать текст в эмбеддинги по чанкам. Возвращает тензор [N, dim] или None."""
    chunks = _split_into_chunks(text)
    if not chunks:
        return None
    model = _get_model()
    return model.encode(chunks, convert_to_tensor=True)


def _resolve_threshold(threshold: Optional[float]) -> float:
    if threshold is not None:
        return threshold
    return getattr(settings, 'PLAGIARISM_BERT_THRESHOLD', DEFAULT_THRESHOLD)


def _percent_from_cosine(raw: float, threshold: float) -> float:
    # cos_sim теоретически в [-1, 1], но численно может дать 1.0000001 —
    # клипуем, иначе процент превысит 100 и вылезет в шаблонах.
    raw = max(-1.0, min(1.0, raw))
    if raw < threshold:
        return 0.0
    if threshold >= 1.0:
        return 100.0 if raw >= 1.0 else 0.0
    return ((raw - threshold) / (1.0 - threshold)) * 100


def similarity_from_embeddings(
    emb1,
    emb2,
    threshold: Optional[float] = None,
) -> float:
    """Сходство (0..100) по уже закодированным чанкам.

    Берём максимум косинусной близости по парам чанков — для длинных
    документов это надёжнее, чем усреднение: один общий абзац уже
    сигнал, который не должен размываться остальным несовпадающим.
    """
    if emb1 is None or emb2 is None:
        return 0.0

    from sentence_transformers import util

    th = _resolve_threshold(threshold)
    raw = float(util.cos_sim(emb1, emb2).max().item())
    return _percent_from_cosine(raw, th)


def semantic_similarity(
    text1: str,
    text2: str,
    threshold: Optional[float] = None,
) -> float:
    """Сходство в процентах (0..100). Ниже threshold → 0, выше — линейный rescale.

    Совместимая обёртка: для разовых сравнений. В пакетной обработке
    эффективнее закешировать эмбеддинги через `encode_chunks` и
    использовать `similarity_from_embeddings`.
    """
    if not text1.strip() or not text2.strip():
        return 0.0
    emb1 = encode_chunks(text1)
    emb2 = encode_chunks(text2)
    return similarity_from_embeddings(emb1, emb2, threshold)

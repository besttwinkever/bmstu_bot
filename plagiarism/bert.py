"""Семантическое сравнение через SentenceTransformer (rubert-tiny2)."""
from __future__ import annotations

import logging
import threading
from typing import Optional

import torch
from django.conf import settings
from django.db import transaction
from sentence_transformers import SentenceTransformer, util

from .models import SubmissionEmbedding


logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()

DEFAULT_MODEL_NAME = 'cointegrated/rubert-tiny2'
DEFAULT_THRESHOLD = 0.82

# Длинные документы делим на «окна»: SentenceTransformer-ы режут вход
# по max_seq_length (обычно 256 токенов ≈ 1.5 кБ), и без чанкования мы
# сравниваем только начало работ — для дипломов/рефератов это критично.
_CHUNK_SIZE_CHARS = 1500
_CHUNK_OVERLAP_CHARS = 200
_MAX_CHUNKS_PER_TEXT = 100


def _get_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
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

    Берём среднее косинусной близости по лучшему совпадению каждого
    чанка первого текста — баланс между чувствительностью к совпадениям
    и устойчивостью к тематическому шуму.
    """
    if emb1 is None or emb2 is None:
        return 0.0

    th = _resolve_threshold(threshold)
    cos_matrix = util.cos_sim(emb1, emb2)
    # Для каждого чанка первого текста берём лучшее совпадение со вторым,
    # затем усредняем — это даёт устойчивую оценку без завышения от
    # одной случайно похожей пары.
    best_per_chunk = cos_matrix.max(dim=1).values
    raw = float(best_per_chunk.mean().item())
    return _percent_from_cosine(raw, th)


# ---------------------------------------------------------------------------
#  pgvector: персистентное хранение эмбеддингов
# ---------------------------------------------------------------------------

def store_embeddings(submission, text: str) -> None:
    """Закодировать текст BERT-ом и сохранить эмбеддинги чанков в PostgreSQL.

    Если эмбеддинги для этой работы уже есть — перезаписываются (идемпотентно).
    """
    chunks = _split_into_chunks(text)
    if not chunks:
        return

    model = _get_model()
    vectors = model.encode(chunks, convert_to_numpy=True)

    with transaction.atomic():
        SubmissionEmbedding.objects.filter(submission=submission).delete()
        SubmissionEmbedding.objects.bulk_create([
            SubmissionEmbedding(
                submission=submission,
                chunk_index=i,
                embedding=vec.tolist(),
            )
            for i, vec in enumerate(vectors)
        ])


def load_embeddings(submission):
    """Загрузить эмбеддинги из БД как тензор [N, dim]. None — если нет записей."""
    rows = list(
        SubmissionEmbedding.objects
        .filter(submission=submission)
        .order_by('chunk_index')
        .values_list('embedding', flat=True)
    )
    if not rows:
        return None
    return torch.tensor(rows, dtype=torch.float32)


def get_or_compute_embeddings(submission, text: str | None = None):
    """Загрузить эмбеддинги из pgvector или вычислить, сохранить и вернуть.

    Если text=None и в БД ничего нет — вернёт None (старая работа без
    текста «на руках»). При первом прогоне антиплагиата с текстом —
    эмбеддинги будут сохранены; все последующие проверки пойдут из БД.
    """
    emb = load_embeddings(submission)
    if emb is not None:
        return emb

    if text is None:
        return None

    store_embeddings(submission, text)
    return load_embeddings(submission)


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

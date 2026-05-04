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


def semantic_similarity(
    text1: str,
    text2: str,
    threshold: Optional[float] = None,
) -> float:
    """Сходство в процентах (0..100). Ниже threshold → 0, выше — линейный rescale."""
    if not text1.strip() or not text2.strip():
        return 0.0

    th = threshold if threshold is not None else getattr(
        settings, 'PLAGIARISM_BERT_THRESHOLD', DEFAULT_THRESHOLD
    )

    from sentence_transformers import util

    model = _get_model()
    emb1 = model.encode(text1, convert_to_tensor=True)
    emb2 = model.encode(text2, convert_to_tensor=True)
    raw = float(util.cos_sim(emb1, emb2).item())

    if raw < th:
        return 0.0
    return ((raw - th) / (1.0 - th)) * 100

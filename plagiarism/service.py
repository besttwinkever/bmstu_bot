"""Антиплагиат: шинглы + BERT, итоговый score = max обоих метрик."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Optional

from django.conf import settings

from bot_send_file.models import Submission

from .bert import semantic_similarity
from .extractors import UnsupportedFormat, extract_text
from .models import PlagiarismReport, Verdict
from .shingles import jaccard_similarity


logger = logging.getLogger(__name__)


@dataclass
class Match:
    submission: Submission
    shingle_score: float
    bert_score: float

    @property
    def final_score(self) -> float:
        return max(self.shingle_score, self.bert_score)


@dataclass
class PlagiarismConfig:
    shingle_size: int = 3
    bert_threshold: float = 0.7
    shingle_prefilter: float = 15.0
    suspicious_threshold: float = 30.0
    plagiarism_threshold: float = 70.0

    @classmethod
    def from_settings(cls) -> 'PlagiarismConfig':
        return cls(
            shingle_size=getattr(settings, 'PLAGIARISM_SHINGLE_SIZE', 3),
            bert_threshold=getattr(settings, 'PLAGIARISM_BERT_THRESHOLD', 0.7),
            shingle_prefilter=getattr(settings, 'PLAGIARISM_SHINGLE_PREFILTER', 15.0),
            suspicious_threshold=getattr(settings, 'PLAGIARISM_SUSPICIOUS_THRESHOLD', 30.0),
            plagiarism_threshold=getattr(settings, 'PLAGIARISM_PLAGIARISM_THRESHOLD', 70.0),
        )


def _verdict_for(score: float, cfg: PlagiarismConfig) -> str:
    if score >= cfg.plagiarism_threshold:
        return Verdict.PLAGIARISM
    if score >= cfg.suspicious_threshold:
        return Verdict.SUSPICIOUS
    return Verdict.ORIGINAL


def _candidate_submissions(submission: Submission) -> Iterable[Submission]:
    """Прошлые работы по той же дисциплине от других студентов.

    Why: сравниваем по дисциплине (а не только по типу), чтобы ловить
    переиспользование текста между смежными работами. Только submissions
    с created_at < нашего — иначе оригиналом становится тот, кто пришёл
    вторым. Кандидаты, помеченные как копия ранних работ того же автора,
    исключаются — это производное от собственного текста.
    """
    discipline = submission.submission_type.discipline
    qs = (
        Submission.objects
        .filter(submission_type__discipline=discipline)
        .exclude(pk=submission.pk)
        .filter(created_at__lt=submission.created_at)
        .select_related('user', 'submission_type', 'plagiarism_report')
    )

    debug_bypass = bool(
        getattr(settings, 'DEBUG', False)
        and getattr(settings, 'BOT_DEBUG_BYPASS_AUTH', False)
    )
    if not debug_bypass:
        qs = qs.exclude(user=submission.user)
    else:
        own_earlier_pks = list(
            Submission.objects
            .filter(
                user=submission.user,
                submission_type__discipline=discipline,
                created_at__lt=submission.created_at,
            )
            .exclude(pk=submission.pk)
            .values_list('pk', flat=True)
        )
        if own_earlier_pks:
            qs = qs.exclude(plagiarism_report__matched_with_id__in=own_earlier_pks)

    return qs


def _read_text(submission: Submission) -> Optional[str]:
    if not submission.file:
        return None
    try:
        data = submission.file.read()
    except FileNotFoundError:
        logger.warning('Submission file missing: %s', submission.file.name)
        return None
    finally:
        try:
            submission.file.close()
        except Exception:
            pass
    try:
        return extract_text(submission.file.name, data)
    except UnsupportedFormat:
        raise


def check_submission(submission: Submission) -> PlagiarismReport:
    """Запустить антиплагиат и сохранить отчёт."""
    cfg = PlagiarismConfig.from_settings()
    report, _ = PlagiarismReport.objects.get_or_create(submission=submission)

    try:
        suspect_text = _read_text(submission)
    except UnsupportedFormat as exc:
        report.verdict = Verdict.UNSUPPORTED
        report.details = str(exc)
        report.save()
        return report

    if not suspect_text or not suspect_text.strip():
        report.verdict = Verdict.UNSUPPORTED
        report.details = 'Текст не извлечён (пустой файл или неподдерживаемый формат)'
        report.save()
        return report

    best: Optional[Match] = None
    for candidate in _candidate_submissions(submission):
        try:
            original_text = _read_text(candidate)
        except UnsupportedFormat:
            continue
        if not original_text:
            continue

        shingle_score = jaccard_similarity(original_text, suspect_text, cfg.shingle_size)
        # Если шинглы уже за порогом плагиата — BERT не изменит max(), пропускаем.
        if shingle_score >= cfg.plagiarism_threshold:
            bert_score = 0.0
        else:
            bert_score = semantic_similarity(original_text, suspect_text, cfg.bert_threshold)

        match = Match(candidate, shingle_score, bert_score)
        if best is None or match.final_score > best.final_score:
            best = match

    if best is None:
        report.shingle_score = 0.0
        report.bert_score = 0.0
        report.verdict = Verdict.ORIGINAL
        report.details = 'Нет подходящих работ для сравнения'
        report.matched_with = None
    else:
        report.shingle_score = best.shingle_score
        report.bert_score = best.bert_score
        report.verdict = _verdict_for(best.final_score, cfg)
        if report.verdict == Verdict.ORIGINAL:
            report.matched_with = None
            report.details = 'Совпадений выше порога не найдено'
        else:
            report.matched_with = best.submission
            report.details = (
                f'Сравнение с работой {best.submission.submission_id} '
                f'(автор: {best.submission.user.get_full_name() or best.submission.user.username})'
            )

    report.save()
    return report

"""Антиплагиат: шинглы + BERT, итоговый score = max обоих метрик."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Optional

from django.conf import settings
from django.db.models import Q

from bot_send_file.models import Submission

from .bert import encode_chunks, similarity_from_embeddings
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
    bert_threshold: float = 0.82
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
    переиспользование текста между смежными работами. «Раньше нашей»
    определяем по (created_at, pk) — на одинаковых таймстампах
    (массовая загрузка, миграция) PK служит tiebreaker'ом: оригиналом
    считается работа с меньшим pk. Кандидаты, помеченные как копия
    ранних работ того же автора, исключаются — это производное от
    собственного текста.
    """
    discipline = submission.submission_type.discipline
    earlier = (
        Q(created_at__lt=submission.created_at)
        | Q(created_at=submission.created_at, pk__lt=submission.pk)
    )
    qs = (
        Submission.objects
        .filter(submission_type__discipline=discipline)
        .filter(earlier)
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
            )
            .filter(earlier)
            .values_list('pk', flat=True)
        )
        if own_earlier_pks:
            qs = qs.exclude(plagiarism_report__matched_with_id__in=own_earlier_pks)

    return qs


def _read_text(submission: Submission) -> Optional[str]:
    """Извлечь текст из файла submission. None — если файла нет/он пуст."""
    if not submission.file:
        return None
    try:
        with submission.file.open('rb') as fp:
            data = fp.read()
    except FileNotFoundError:
        logger.warning('Submission file missing: %s', submission.file.name)
        return None
    return extract_text(submission.file.name, data)


def check_submission(submission: Submission) -> PlagiarismReport:
    """Запустить антиплагиат и сохранить отчёт."""
    cfg = PlagiarismConfig.from_settings()
    report, _ = PlagiarismReport.objects.get_or_create(submission=submission)

    try:
        return _run_check(submission, report, cfg)
    except Exception:
        logger.exception('Plagiarism check failed for submission %s', submission.pk)
        report.verdict = Verdict.ERROR
        report.details = 'Внутренняя ошибка проверки. Обратитесь к администратору.'
        report.shingle_score = None
        report.bert_score = None
        report.matched_with = None
        report.save()
        return report


def _set_unsupported(report: PlagiarismReport, details: str) -> None:
    """Сбрасываем агрегаты — иначе при повторном запуске остаются прошлые."""
    report.verdict = Verdict.UNSUPPORTED
    report.details = details
    report.shingle_score = None
    report.bert_score = None
    report.matched_with = None


def _run_check(
    submission: Submission,
    report: PlagiarismReport,
    cfg: PlagiarismConfig,
) -> PlagiarismReport:
    try:
        suspect_text = _read_text(submission)
    except UnsupportedFormat as exc:
        _set_unsupported(report, str(exc))
        report.save()
        return report
    except Exception as exc:
        # Битый docx/pdf, нечитаемая кодировка txt — пишем в отчёт,
        # но не валим всю проверку (см. ERROR-обёртку в check_submission).
        logger.exception('Failed to read suspect file for submission %s', submission.pk)
        _set_unsupported(report, f'Не удалось прочитать файл работы: {exc}')
        report.save()
        return report

    if not suspect_text or not suspect_text.strip():
        _set_unsupported(report, 'Текст не извлечён (пустой файл или неподдерживаемый формат).')
        report.save()
        return report

    # Эмбеддинги суспект-текста кодируются один раз и переиспользуются
    # на каждом кандидате — иначе на крупном курсе тратим минуты впустую.
    suspect_embedding = None

    best: Optional[Match] = None
    for candidate in _candidate_submissions(submission):
        try:
            original_text = _read_text(candidate)
        except UnsupportedFormat:
            continue
        except Exception:
            # Битый файл одного кандидата не должен ронять всю проверку:
            # пропускаем его, остальные кандидаты остаются в оценке.
            logger.warning(
                'Skipping candidate submission %s due to read error',
                candidate.pk, exc_info=True,
            )
            continue
        if not original_text:
            continue

        shingle_score = jaccard_similarity(original_text, suspect_text, cfg.shingle_size)

        if shingle_score >= cfg.plagiarism_threshold:
            # Шинглы уже дали потолок — BERT не повысит max(), экономим.
            bert_score = 0.0
        else:
            if suspect_embedding is None:
                suspect_embedding = encode_chunks(suspect_text)
            try:
                candidate_embedding = encode_chunks(original_text)
                bert_score = similarity_from_embeddings(
                    suspect_embedding, candidate_embedding, cfg.bert_threshold
                )
            except Exception:
                logger.warning(
                    'BERT similarity failed for candidate %s', candidate.pk,
                    exc_info=True,
                )
                bert_score = 0.0

        match = Match(candidate, shingle_score, bert_score)
        if best is None or match.final_score > best.final_score:
            best = match

    if best is None:
        report.shingle_score = 0.0
        report.bert_score = 0.0
        report.verdict = Verdict.ORIGINAL
        report.details = 'Нет подходящих работ для сравнения.'
        report.matched_with = None
    else:
        report.shingle_score = best.shingle_score
        report.bert_score = best.bert_score
        report.verdict = _verdict_for(best.final_score, cfg)
        if report.verdict == Verdict.ORIGINAL:
            report.matched_with = None
            report.details = 'Совпадений выше порога не найдено.'
        else:
            report.matched_with = best.submission
            author = (
                best.submission.user.get_full_name()
                or best.submission.user.username
            )
            report.details = (
                f'Сравнение с работой {best.submission.submission_id} '
                f'(автор: {author}).'
            )

    report.save()
    return report

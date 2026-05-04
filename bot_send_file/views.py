"""Веб-интерфейс преподавателя: список работ, оценка, рассылки, CRUD заданий."""
from __future__ import annotations

import logging
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from bot_app.models import Discipline, Notification, TgUser
from bot_app.services import NotificationService

from .models import Submission, SubmissionType


logger = logging.getLogger(__name__)


def _teacher_required(view):
    """Пользователь должен быть преподавателем указанной дисциплины."""
    @login_required
    def wrapper(request, discipline_id=None, submission_id=None, *args, **kwargs):
        discipline = None
        if discipline_id is not None:
            discipline = get_object_or_404(Discipline, pk=discipline_id)
        elif submission_id is not None:
            submission = get_object_or_404(Submission, submission_id=submission_id)
            discipline = submission.submission_type.discipline
            kwargs['submission'] = submission
        if discipline is not None and not discipline.teachers.filter(pk=request.user.pk).exists():
            return HttpResponseForbidden('Нет прав')
        kwargs['discipline'] = discipline
        return view(request, *args, **kwargs)
    return wrapper


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


@login_required
def teacher_panel(request):
    disciplines = Discipline.objects.filter(teachers=request.user)
    return render(request, 'teacher/dashboard.html', {
        'disciplines': disciplines,
        'user': request.user,
    })


@_teacher_required
def discipline_submissions(request, discipline):
    submissions = (
        Submission.objects
        .filter(submission_type__discipline=discipline)
        .select_related('user', 'submission_type', 'plagiarism_report')
        .order_by('-created_at')
    )

    status_filter = request.GET.get('status')
    if status_filter:
        submissions = submissions.filter(status=status_filter)

    type_filter = request.GET.get('type')
    if type_filter:
        submissions = submissions.filter(submission_type_id=type_filter)

    date_filter = request.GET.get('date_filter')
    if date_filter == 'overdue':
        submissions = submissions.filter(is_late=True)
    elif date_filter == 'ontime':
        submissions = submissions.filter(is_late=False)

    student_filter = (request.GET.get('student') or '').strip()
    if student_filter:
        # Каждое слово ищется в любом из полей — порядок «Иван Петров» не важен.
        for token in student_filter.split():
            submissions = submissions.filter(
                Q(user__first_name__icontains=token)
                | Q(user__last_name__icontains=token)
                | Q(user__username__icontains=token)
            )

    return render(request, 'teacher/submissions.html', {
        'discipline': discipline,
        'submissions': submissions,
        'status_choices': Submission.CHOICES,
        'current_status': status_filter,
        'submission_types': SubmissionType.objects.filter(discipline=discipline),
        'current_type': int(type_filter) if type_filter else None,
        'current_date_filter': date_filter,
        'current_student': student_filter,
    })


@_teacher_required
def update_submission(request, submission, discipline):
    if request.method == 'POST':
        new_status = request.POST.get('status')
        comment = request.POST.get('comment')

        valid_statuses = [s[0] for s in Submission.CHOICES]
        if new_status in valid_statuses:
            submission.status = new_status
            if comment:
                submission.status_text = comment
            submission.updated_at = timezone.now()
            submission.save()
            _notify_student(submission, comment)

    return redirect('discipline_submissions', discipline_id=discipline.pk)


def _notify_student(submission: Submission, comment: str | None) -> None:
    tg_user = TgUser.objects.filter(user=submission.user).first()
    if tg_user is None or not tg_user.messenger_id:
        return

    status_label = dict(Submission.CHOICES).get(submission.status, submission.status)
    text = (
        f'*Обновлён статус работы*\n'
        f'Дисциплина: {submission.submission_type.discipline.name}\n'
        f'Работа: {submission.submission_type.name}\n'
        f'Статус: {status_label}'
    )
    if comment:
        text += f'\nКомментарий: {comment}'

    NotificationService().notify_user(tg_user, text)


@_teacher_required
def download_submission(request, submission, discipline):
    if not submission.file:
        return redirect('discipline_submissions', discipline_id=discipline.pk)
    try:
        return FileResponse(
            submission.file.open(),
            as_attachment=True,
            filename=submission.file.name.split('/')[-1],
        )
    except FileNotFoundError:
        return HttpResponseNotFound(
            'Файл физически отсутствует на сервере. '
            'Пожалуйста, попросите студента загрузить работу повторно.'
        )


@_teacher_required
def manage_assignments(request, discipline):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            name = request.POST.get('name')
            if name:
                SubmissionType.objects.create(
                    name=name,
                    discipline=discipline,
                    deadline=request.POST.get('deadline') or None,
                    accept_late=(request.POST.get('accept_late') == 'on'),
                    allowed_extensions=request.POST.get('allowed_extensions') or 'pdf,docx,doc,txt',
                    max_file_size_mb=int(request.POST.get('max_file_size_mb') or 20),
                )
        elif action == 'delete':
            SubmissionType.objects.filter(
                pk=request.POST.get('type_id'),
                discipline=discipline,
            ).delete()
        elif action == 'edit':
            st = get_object_or_404(
                SubmissionType,
                pk=request.POST.get('type_id'),
                discipline=discipline,
            )
            st.name = request.POST.get('name') or st.name
            st.deadline = request.POST.get('deadline') or None
            st.accept_late = (request.POST.get('accept_late') == 'on')
            st.allowed_extensions = request.POST.get('allowed_extensions') or st.allowed_extensions
            st.max_file_size_mb = int(request.POST.get('max_file_size_mb') or st.max_file_size_mb)
            st.save()
        return redirect('manage_assignments', discipline_id=discipline.pk)

    return render(request, 'teacher/assignments.html', {
        'discipline': discipline,
        'assignments': SubmissionType.objects.filter(discipline=discipline),
    })


@_teacher_required
def manage_notifications(request, discipline):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete':
            Notification.objects.filter(
                pk=request.POST.get('notification_id'),
                discipline=discipline,
            ).delete()
            return redirect('manage_notifications', discipline_id=discipline.pk)

        text = request.POST.get('text')
        scheduled_raw = request.POST.get('scheduled_at')
        is_delayed = request.POST.get('is_delayed') == 'on'
        if text:
            scheduled_at = _parse_datetime(scheduled_raw) if is_delayed else None
            NotificationService().schedule_or_send(discipline, text, scheduled_at)
        return redirect('manage_notifications', discipline_id=discipline.pk)

    return render(request, 'teacher/notifications.html', {
        'discipline': discipline,
        'notifications': Notification.objects.filter(discipline=discipline).order_by('-created_at'),
    })

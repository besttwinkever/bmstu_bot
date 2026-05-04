import secrets
from datetime import timedelta

from django.contrib.auth.models import Group
from django.db import models
from django.utils import timezone
from oauth.models import OauthUser

from messaging.constants import Platform


AUTH_TOKEN_TTL = timedelta(minutes=15)


class AuthToken(models.Model):
    """Одноразовый токен привязки мессенджера к OAuth-пользователю.

    Жизненный цикл: бот создаёт токен на /start и кладёт в URL SSO. После
    успешного OAuth-callback view проверяет токен и удаляет его,
    повторное использование невозможно.
    """

    class Meta:
        verbose_name = 'Токен авторизации бота'
        verbose_name_plural = 'Токены авторизации бота'

    token = models.CharField('Токен', max_length=64, unique=True, db_index=True)
    platform = models.CharField('Платформа', max_length=32, default=Platform.TELEGRAM)
    messenger_id = models.CharField('ID мессенджера', max_length=255)
    expires_at = models.DateTimeField('Действителен до')
    created_at = models.DateTimeField('Создан', default=timezone.now)

    def __str__(self):
        return f'Токен для {self.platform}-пользователя {self.messenger_id}'

    @classmethod
    def issue(cls, platform: str, messenger_id: str) -> 'AuthToken':
        platform = (platform or Platform.TELEGRAM).lower()
        return cls.objects.create(
            token=secrets.token_urlsafe(32),
            platform=platform,
            messenger_id=str(messenger_id),
            expires_at=timezone.now() + AUTH_TOKEN_TTL,
        )

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at


class TgUser(models.Model):
    class Meta:
        verbose_name = 'Пользователь мессенджера'
        verbose_name_plural = 'Пользователи мессенджера'
        constraints = [
            models.UniqueConstraint(
                fields=['platform', 'messenger_id'],
                name='unique_messenger_user',
            )
        ]

    platform = models.CharField('Платформа', max_length=32, default=Platform.TELEGRAM)
    messenger_id = models.CharField('ID мессенджера', max_length=255, null=True, blank=True)
    user = models.OneToOneField(
        OauthUser, on_delete=models.CASCADE, related_name='user',
        verbose_name='Пользователь',
    )

    def __str__(self):
        return self.user.username


class Discipline(models.Model):
    class Meta:
        verbose_name = 'Дисциплина'
        verbose_name_plural = 'Дисциплины'

    teachers = models.ManyToManyField(OauthUser, related_name='disciplines', verbose_name='Преподаватели')
    groups = models.ManyToManyField(Group, related_name='disciplines', verbose_name='Учебные группы')
    name = models.CharField('Название', max_length=255, unique=True, null=False)
    description = models.TextField('Описание', unique=False, null=True, blank=True)

    def __str__(self):
        groups_list = [g.name for g in self.groups.all()]
        suffix = f' ({", ".join(groups_list)})' if groups_list else ''
        return f'{self.name}{suffix}'


class Notification(models.Model):
    class Meta:
        verbose_name = 'Рассылка студентам'
        verbose_name_plural = 'Рассылки студентам'

    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE, verbose_name='Дисциплина')
    text = models.TextField('Текст сообщения')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    scheduled_at = models.DateTimeField('Запланировано на', null=True, blank=True)
    is_sent = models.BooleanField('Отправлено', default=False)

    def __str__(self):
        return f'Рассылка для дисциплины «{self.discipline.name}»'


class BotCommand(models.Model):
    class Meta:
        verbose_name = 'Команда бота'
        verbose_name_plural = 'Команды бота'

    name = models.CharField('Название кнопки', max_length=255, unique=True, null=False)
    applicable_groups = models.ManyToManyField(
        Group, blank=True,
        verbose_name='Кому показывать (роли)',
    )
    description = models.TextField('Описание')

    def __str__(self):
        return self.name

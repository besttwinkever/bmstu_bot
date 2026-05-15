"""Аутентификация и определение роли пользователя (студент / преподаватель / сторонний)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from bot_app.models import TgUser
from messaging.constants import Platform, UserGroup


logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    STUDENT = 'student'
    STAFF = 'staff'
    EXTERNAL = 'external'
    UNKNOWN = 'unknown'


_GROUP_TO_ROLE = {
    UserGroup.STUDENT: UserRole.STUDENT,
    UserGroup.STAFF: UserRole.STAFF,
    UserGroup.EXTERNAL: UserRole.EXTERNAL,
}


@dataclass
class AuthenticatedUser:
    tg_user: TgUser
    role: UserRole
    groups: list[str]

    @property
    def oauth_user(self):
        return self.tg_user.user

    @property
    def full_name(self) -> str:
        return self.oauth_user.get_full_name()


class AuthService:
    @staticmethod
    def role_group_names() -> set[str]:
        return set(_GROUP_TO_ROLE.keys())

    @staticmethod
    def academic_group_ids(user):
        return user.groups.exclude(name__in=AuthService.role_group_names()).values_list('pk', flat=True)

    @staticmethod
    def find_by_messenger_id(platform: str, messenger_id: str) -> Optional[AuthenticatedUser]:
        platform = (platform or Platform.TELEGRAM).lower()
        tg_user = TgUser.objects.select_related('user').filter(
            platform=platform,
            messenger_id=messenger_id,
        ).first()
        if tg_user is None:
            tg_user = AuthService._debug_user_for_platform(platform, messenger_id)
        if tg_user is None:
            return None
        return AuthService._wrap(tg_user)

    @staticmethod
    def find_by_telegram_id(telegram_id: str) -> Optional[AuthenticatedUser]:
        return AuthService.find_by_messenger_id(Platform.TELEGRAM, telegram_id)

    @staticmethod
    def is_authenticated(platform: str, messenger_id: str) -> bool:
        return AuthService.find_by_messenger_id(platform, messenger_id) is not None

    @staticmethod
    def _is_debug_bypass_enabled() -> bool:
        return bool(
            getattr(settings, 'DEBUG', False)
            and getattr(settings, 'BOT_DEBUG_BYPASS_AUTH', False)
        )

    @staticmethod
    def _debug_user_for_platform(platform: str, messenger_id: str) -> Optional[TgUser]:
        if not AuthService._is_debug_bypass_enabled():
            return None

        username = getattr(settings, 'BOT_DEBUG_USER_USERNAME', 'debug_student')
        password = getattr(settings, 'BOT_DEBUG_USER_PASSWORD', 'ChangeMe123!')
        first_name = getattr(settings, 'BOT_DEBUG_USER_FIRST_NAME', 'Debug')
        last_name = getattr(settings, 'BOT_DEBUG_USER_LAST_NAME', 'User')
        role_group_name = getattr(settings, 'BOT_DEBUG_USER_GROUP', UserGroup.STUDENT)
        academic_group_name = getattr(settings, 'BOT_DEBUG_ACADEMIC_GROUP', 'Демо учебная группа')

        try:
            user_model = get_user_model()
            oauth_user = user_model.objects.filter(username=username).first()
            if oauth_user is None:
                oauth_user = user_model.objects.create_user(
                    username=username,
                    password=password,
                )
                if hasattr(oauth_user, 'first_name'):
                    oauth_user.first_name = first_name
                if hasattr(oauth_user, 'last_name'):
                    oauth_user.last_name = last_name
                oauth_user.save()
                logger.info('Created debug bot user "%s"', username)

            tg_user, _ = TgUser.objects.get_or_create(
                user=oauth_user,
                defaults={
                    'platform': platform,
                    'messenger_id': messenger_id,
                },
            )
            updates = []
            if tg_user.platform != platform:
                tg_user.platform = platform
                updates.append('platform')
            if tg_user.messenger_id != messenger_id:
                tg_user.messenger_id = messenger_id
                updates.append('messenger_id')
            if updates:
                tg_user.save(update_fields=updates)

            role_group, _ = Group.objects.get_or_create(name=role_group_name)
            oauth_user.groups.add(role_group)

            academic_group, _ = Group.objects.get_or_create(name=academic_group_name)
            oauth_user.groups.add(academic_group)

            return tg_user
        except Exception:
            logger.exception('Failed to resolve debug bot user')
            return None

    @staticmethod
    def _wrap(tg_user: TgUser) -> AuthenticatedUser:
        groups = list(tg_user.user.groups.values_list('name', flat=True))
        role = UserRole.UNKNOWN
        for group_name in groups:
            if group_name in _GROUP_TO_ROLE:
                role = _GROUP_TO_ROLE[group_name]
                break
        return AuthenticatedUser(tg_user=tg_user, role=role, groups=groups)

    @staticmethod
    def link_messenger(platform: str, messenger_id: str, oauth_user) -> tuple[TgUser, bool]:
        platform = (platform or Platform.TELEGRAM).lower()
        existing = TgUser.objects.filter(user=oauth_user).first()
        if existing is not None:
            updates = []
            if existing.platform != platform:
                existing.platform = platform
                updates.append('platform')
            if existing.messenger_id != messenger_id:
                existing.messenger_id = messenger_id
                updates.append('messenger_id')
            if updates:
                existing.save(update_fields=updates)
            return existing, False
        tg_user, created = TgUser.objects.get_or_create(
            platform=platform,
            messenger_id=messenger_id,
            defaults={'user': oauth_user},
        )
        if not created and tg_user.user != oauth_user:
            tg_user.user = oauth_user
            tg_user.save(update_fields=['user'])
        return tg_user, created

    @staticmethod
    def link_telegram(telegram_id: str, oauth_user) -> tuple[TgUser, bool]:
        return AuthService.link_messenger(Platform.TELEGRAM, telegram_id, oauth_user)

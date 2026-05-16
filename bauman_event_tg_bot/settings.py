"""
Django settings for bauman_event_tg_bot project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from pytz import timezone

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-k(0p(+w4kaw$39tn05fdn-uaid!r_dgj%3z+7odhppmf-k@wa$')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

# Application definition

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'oauth',
    'bot_send_file',
    'bot_app',
    'plagiarism',
    'rest_framework',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bauman_event_tg_bot.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'bauman_event_tg_bot.settings.export_template_vars',
            ],
        },
    },
]

WSGI_APPLICATION = 'bauman_event_tg_bot.wsgi.application'


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'bot'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Cache & Session
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Middleware for sessions via DB
SESSION_ENGINE = "django.contrib.sessions.backends.db"
# SESSION_CACHE_ALIAS = "default"

# Настройки сессии
SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]


# Internationalization
LANGUAGE_CODE = 'ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'bauman_event_tg_bot', 'static'),
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# OAuth
OAUTH_ACCESS_TOKEN_URL = os.getenv('OAUTH_ACCESS_TOKEN_URL')
OAUTH_AUTHORIZE_URL = os.getenv("OAUTH_AUTHORIZE_URL")
OAUTH_PROFILE_URL = os.getenv("OAUTH_PROFILE_URL")

OAUTH_CREATE_GROUPS_IF_NOT_EXISTS = os.getenv('OAUTH_CREATE_GROUPS_IF_NOT_EXISTS', 'False') == 'True'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'oauth.OauthUser'

# --- Celery --------------------------------------------------------------
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Moscow'
CELERY_TASK_ALWAYS_EAGER = os.getenv('CELERY_TASK_ALWAYS_EAGER', 'False') == 'True'

# --- Messaging platform --------------------------------------------------
# "telegram" или "vk"
BOT_PLATFORM = os.getenv('BOT_PLATFORM', 'telegram')
VK_BOT_TOKEN = os.getenv('VK_BOT_TOKEN', '')
VK_GROUP_ID = int(os.getenv('VK_GROUP_ID', '0') or '0')

# Debug-bypass для локальной разработки бота.
# Включается только если одновременно DEBUG=True и BOT_DEBUG_BYPASS_AUTH=True.
# В production такая комбинация = критическая дыра: bypass даёт авто-логин
# и расслабляет правила антиплагиата (см. plagiarism/service._candidate_submissions).
BOT_DEBUG_BYPASS_AUTH = os.getenv('BOT_DEBUG_BYPASS_AUTH', 'False') == 'True'
if not DEBUG and BOT_DEBUG_BYPASS_AUTH:
    raise RuntimeError(
        'BOT_DEBUG_BYPASS_AUTH=True запрещён при DEBUG=False — '
        'это полностью отключает аутентификацию.'
    )
BOT_DEBUG_USER_USERNAME = os.getenv('BOT_DEBUG_USER_USERNAME', 'debug_student')
BOT_DEBUG_USER_PASSWORD = os.getenv('BOT_DEBUG_USER_PASSWORD', 'ChangeMe123!')
BOT_DEBUG_USER_GROUP = os.getenv('BOT_DEBUG_USER_GROUP', 'Студент')
BOT_DEBUG_ACADEMIC_GROUP = os.getenv('BOT_DEBUG_ACADEMIC_GROUP', 'Демо учебная группа')
BOT_DEBUG_USER_FIRST_NAME = os.getenv('BOT_DEBUG_USER_FIRST_NAME', 'Debug')
BOT_DEBUG_USER_LAST_NAME = os.getenv('BOT_DEBUG_USER_LAST_NAME', 'User')

# --- Plagiarism ---------------------------------------------------------
PLAGIARISM_BERT_MODEL = os.getenv('PLAGIARISM_BERT_MODEL', 'cointegrated/rubert-tiny2')
PLAGIARISM_BERT_THRESHOLD = float(os.getenv('PLAGIARISM_BERT_THRESHOLD', '0.82'))
PLAGIARISM_SHINGLE_SIZE = int(os.getenv('PLAGIARISM_SHINGLE_SIZE', '3'))
PLAGIARISM_SHINGLE_PREFILTER = float(os.getenv('PLAGIARISM_SHINGLE_PREFILTER', '15.0'))
PLAGIARISM_SUSPICIOUS_THRESHOLD = float(os.getenv('PLAGIARISM_SUSPICIOUS_THRESHOLD', '30.0'))
PLAGIARISM_PLAGIARISM_THRESHOLD = float(os.getenv('PLAGIARISM_PLAGIARISM_THRESHOLD', '70.0'))

# Security
# SECURE_PROXY_SSL_HEADER включаем только когда явно стоим за reverse-proxy:
# иначе клиент сам может прислать X-Forwarded-Proto: https и обмануть Django.
if os.getenv('USE_PROXY_SSL_HEADER', 'False') == 'True':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False') == 'True'
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False') == 'True'

if not DEBUG and SECRET_KEY.startswith('django-insecure-'):
    raise RuntimeError(
        'SECRET_KEY обязателен в production: задайте переменную окружения '
        'SECRET_KEY длинной случайной строкой.'
    )

CORS_ALLOW_HEADERS = [
    'x-telegram-webapp-data',
    'content-type'
]

CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1:8000').split(',')
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://127.0.0.1:8000').split(',')


APP_TZ = timezone('Europe/Moscow')
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
_AUTHORIZE_BASE = OAUTH_AUTHORIZE_URL or "https://science.iu5.bmstu.ru/sso/authorize"
API_URL = f"{_AUTHORIZE_BASE}?redirect_uri={BACKEND_URL}/bot-oauth/callback"

def export_template_vars(request):
    data = {}
    data['API_URL'] = API_URL
    return data

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'bot_app': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

LOGIN_URL = '/teacher/login/'
LOGIN_REDIRECT_URL = '/teacher/panel/'
LOGOUT_REDIRECT_URL = '/teacher/login/'

# Jazzmin settings
JAZZMIN_SETTINGS = {
    'site_title': 'Панель администратора',
    'site_header': 'Панель администратора',
    'site_brand': 'Панель администратора',
    'welcome_sign': 'Добро пожаловать в панель администратора',
    'copyright': 'МГТУ ИУ5',
    'order_with_respect_to': [
        'oauth', 'bot_app', 'bot_send_file', 'plagiarism', 'auth',
    ],
    'custom_css': 'admin/css/jazzmin_overrides.css',
    'icons': {
        'auth.Group': 'fas fa-users',
        'oauth.OauthUser': 'fas fa-user',
        'bot_app.TgUser': 'fas fa-comments',
        'bot_app.Discipline': 'fas fa-book',
        'bot_app.Notification': 'fas fa-bell',
        'bot_app.AuthToken': 'fas fa-key',
        'bot_send_file.SubmissionType': 'fas fa-tasks',
        'bot_send_file.Submission': 'fas fa-file-upload',
        'plagiarism.PlagiarismReport': 'fas fa-search',
    },
}

# Минимальный набор UI-настроек: оставляем дефолтные (синие) цвета Jazzmin,
# тему flatly не используем — она бирюзовая и расходится с Bootstrap-синью
# преподавательской панели. Дополнительная стилизация — в jazzmin_overrides.css.
JAZZMIN_UI_TWEAKS = {
    'no_navbar_border': True,
    'sidebar_nav_small_text': False,
    'button_classes': {
        'primary': 'btn-primary',
        'secondary': 'btn-secondary',
        'info': 'btn-info',
        'warning': 'btn-warning',
        'danger': 'btn-danger',
        'success': 'btn-success',
    },
}
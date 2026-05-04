# Установка
1. Для работы требуется библиотека [bmstu_oauth](https://gitlab.bmstu.ru).

2. Настроить **.env** файл

| Название                          | Обозначение                          | По-умолчанию |
|-----------------------------------|--------------------------------------|--------------|
| OAUTH_CREATE_GROUPS_IF_NOT_EXISTS | Создавать группы сервиса авторизаций | False        |
| TELEGRAM_BOT_TOKEN                | Токен бота                           | -            |
| DB_NAME                           | Название базы                        | tg-bot       |
| DB_USER                           | Пользователь базы                    | postgres     |
| DB_PASSWORD                       | Пароль базы                          | postgres     |
| DB_HOST                           | Хост базы                            | localhost    |
| DB_PORT                           | Порт базы                            | 5432         |


## Debug-режим бота без OAuth

Для локальной отладки можно включить режим, в котором бот автоматически
подставляет тестового пользователя вместо авторизации через сайт.

Добавьте в `.env`:

```env
DEBUG=True
BOT_DEBUG_BYPASS_AUTH=True
BOT_DEBUG_USER_USERNAME=debug_student
BOT_DEBUG_USER_PASSWORD=ChangeMe123!
BOT_DEBUG_USER_GROUP=Студент
BOT_DEBUG_ACADEMIC_GROUP=Демо учебная группа
BOT_DEBUG_USER_FIRST_NAME=Debug
BOT_DEBUG_USER_LAST_NAME=User
```

Важно: bypass работает только при одновременном выполнении двух условий:
`DEBUG=True` и `BOT_DEBUG_BYPASS_AUTH=True`.


# Создание админа(ов)

Команда django: 
```python
python manage.py bootstrap имя1,имя2...
```

Создает в базе админов django с именами имя1...2... и паролем ChangeMe123!
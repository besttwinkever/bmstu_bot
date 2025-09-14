# Установка
1. Для работы требуется библиотека [bmstu_oauth](https://gitlab.bmstu.ru).
```python
pip install bmstu_oauth  -i https://public:public@projects.iu5.bmstu.ru/repository/pip_all/simple
```

2. Созать **.env** файл

| Название                          | Обозначение                          | По-умолчанию |
|-----------------------------------|--------------------------------------|--------------|
| OAUTH_CREATE_GROUPS_IF_NOT_EXISTS | Создавать группы сервиса авторизаций | False        |
| TELEGRAM_BOT_TOKEN                | Токен бота                           | -            |
| DB_NAME                           | Название базы                        | tg-bot       |
| DB_USER                           | Пользователь базы                    | postgres     |
| DB_PASSWORD                       | Пароль базы                          | postgres     |
| DB_HOST                           | Хост базы                            | localhost    |
| DB_PORT                           | Порт базы                            | 5432         |


# Создание админа(ов)

Команда django: 
```python
python manage.py bootstrap имя1,имя2...
```

Создает в базе админов django с именами имя1...2... и паролем ChangeMe123!
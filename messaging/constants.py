"""Строковые константы пользовательского интерфейса бота."""


class ButtonLabel:
    CANCEL = 'Отмена'
    BACK = 'Назад'
    SEND_FILE = 'Отправить файл'
    MY_SUBMISSIONS = 'Мои работы'
    CALENDAR = 'Календарь'
    LOGOUT = 'Выйти'
    AUTHORIZE = 'Авторизоваться'


class CallbackData:
    SEND_FILE = 'send_file'
    MY_SUBMISSIONS = 'my_submissions'
    MY_SUBMISSIONS_PAGE_PREFIX = 'my_page:'  # my_page:<n>
    LOGOUT = 'logout'
    DELETE_SUBMISSION_PREFIX = 'del_sub:'    # del_sub:<submission_pk>


class UserGroup:
    STUDENT = 'Студент'
    STAFF = 'Сотрудник'
    EXTERNAL = 'Сторонний'


class FSMState:
    AWAITING_DISCIPLINE = 'upload:awaiting_discipline'
    AWAITING_SUBMISSION_TYPE = 'upload:awaiting_submission_type'
    AWAITING_FILE = 'upload:awaiting_file'


class Platform:
    TELEGRAM = 'telegram'
    VK = 'vk'

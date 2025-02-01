import os

from dotenv import load_dotenv


# Флаг для пути файла БД: True - в продакшене, False - разработка/тестирование
PROD_DB = False

# Имя БД
DATABASE_NAME = 'projects_report.db'

# Путь к БД для Docker
DATABASE_PROD_PATH = 'db/'

DATABASE_DEV_PATH = '../'

DATABASE = (DATABASE_PROD_PATH + DATABASE_NAME if PROD_DB
            else DATABASE_DEV_PATH + DATABASE_NAME)

# Файл с первоначальными данными для таблицы Проектов
INITIAL_DATA_PATH = '../fixtures/initial_data.csv'


# Подгрузка виртуального окружения
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
RECEIVERS_ID = os.getenv('RECEIVERS_ID')
GROUP_ID = os.getenv('GROUP_ID')

try:
    RECEIVERS_ID = RECEIVERS_ID.split(',')
except AttributeError:
    pass


# Количество обрабатываемых строк из сообщения с отчетом из ТГ по проекту
STRINGS_NUBER_CUT_FROM_TG_MESSAGE = 8

# Шаблон искомых параметров в сообщении
# 'ключевое слово для поиска': тип конечных данных
# при добавлении новых аргументов, нужно добавить соответствующие переменные в
# функцию report_data_updater, ну и с БД порешать по полям
REPORT_DATA_PARAMS = {
    'ИТР': int,
    'Рабочие': int,
    'Ночь': int,
    'ПП': float,
}
# список ключевых слов для поиска в сообщении
SEARCH_PARAMS_IN_MESSAGE = [pattern for pattern in REPORT_DATA_PARAMS]


# Настройки расписания сообщений
SLEEP_PERIOD_SCHEDULE = 20
# Время UTC+0 (для сервера) отправки отчета (первое время)
# и уведомлений о необходимости прислать отсутствующие данные по проектам
REPORT_SEND_TIMES = ['07:30', '08:00', '08:30', '09:00', '09:30', '10:00']

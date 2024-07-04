import os
import re
import sqlite3
import time
from datetime import datetime

import pandas as pd
import schedule
import telegram
from dotenv import load_dotenv
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from database import (create_new_report, get_active_projects_amount,
                      get_project_id, get_project_report_data,
                      get_projects_names, get_today_reports_amount,
                      program_first_start, today_report_exist_id,
                      update_report)


# Подгрузка виртуального окружения
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
RECEIVERS_ID = os.getenv('RECEIVERS_ID')
GROUP_ID = os.getenv('GROUP_ID')

try:
    RECEIVERS_ID = RECEIVERS_ID.split(',')
except AttributeError:
    pass


# Настройки расписания сообщений
SLEEP_PERIOD_SCHEDULE = 20
# Время UTC+0 отправки отчета (первое время)
# и уведомлений о необходимости прислать отсутствующие данные по проектам
REPORT_SEND_TIMES = ['07:30', '08:00', '08:30', '09:00', '09:30', '10:00']

# Количество обрабатываемых строк из сообщения с отчетом из ТГ по проекту
STRINGS_NUBER_CUT_FROM_TG_MESSAGE = 8

# Шаблон шапки отчета, ожидаемого в ТГ (без названия проекта)
REPORT_PATTERN = ('Строительная площадка "{project_search_name}"\n'
                  'ИТР - XX\n'
                  'Рабочие - XX: \n'
                  'из них:\n'
                  'Ночь - XX\n'
                  'Выполнение ПП - XX%')

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


# Тексты сообщений для отправки ботом в ТГ !!!! С АРГУМЕНТАМИ
NOT_VALID_DATA_RESPONSE = ('Данные по проекту {project_search_name} '
                           'некорректные.\n'
                           'Пожалуйста, направьте отчет повторно с шапкой '
                           'по шаблону:\n' + REPORT_PATTERN)

TEXT_HEADER_RESPONSE = (
    'Количество персонала на стройплощадках объектов Смарт Констракшн '
    'по состоянию на {today_date}\n\n'
    'Общее по объектам:\n'
    'ИТР - {all_engineers_number}; '
    'Рабочих - {all_workers_number}\n'
    'в т.ч:'
)

SHORT_TEXT_HEADER_RESPONSE = 'Отчёт по людям {today_date}'

TEXT_BODY_RESPONSE = (
    '{project_name}:\n'
    'ИТР - {engineer}; '
    'Рабочих - {worker}'
)

SHORT_TEXT_BODY_RESPONSE = (
    '• {short_name}: {people_sum} '
    '(из них {night_people} ночью)'
)


def generate_text_messages():
    """Подготовка текста сводного отчета полной и короткой форм
    для отправки в ТГ чат.
    Возвращает тест сообщений для полной и короткой форм,
    а также список названий проектов, по которым еще нет данных.
    По проектам, данных по которым нет, будут проставлены 0 в отчете."""
    today_date = datetime.today().strftime("%d.%m.%Y")
    text = ''
    short_text = ''

    # Получение списка кортежей всех отчетов за сегодня
    report_data_list = get_project_report_data(cursor, today_date)

    all_engineers_number = 0
    all_workers_number = 0
    missing_data_projects_names = []
    project_names_of_actual_reports = []
    for report in report_data_list:
        (project_name,
         short_name,
         engineer,
         worker,
         night_people,
         people_sum,
         progress) = report

        text += '\n\n' + TEXT_BODY_RESPONSE.format(
            project_name=project_name,
            engineer=engineer,
            worker=worker
        )
        short_text += '\n' + SHORT_TEXT_BODY_RESPONSE.format(
            short_name=short_name,
            people_sum=people_sum,
            night_people=night_people
        )
        all_engineers_number += engineer
        all_workers_number += worker
        project_names_of_actual_reports.append(project_name)

    active_projects_names = get_projects_names(cursor)
    active_projects_short_names = get_projects_names(cursor,
                                                     short_name=True)
    # Для проектов, по которым отсутствуют данные, проставляем 0.
    # Формируем список с названиями проектов, по которым нет данных
    for project_name, project_short_name in zip(
            active_projects_names, active_projects_short_names):
        if project_name not in project_names_of_actual_reports:
            text += '\n\n' + TEXT_BODY_RESPONSE.format(
                project_name=project_name,
                engineer=0,
                worker=0)
            short_text += '\n' + SHORT_TEXT_BODY_RESPONSE.format(
                short_name=project_short_name,
                people_sum=0,
                night_people=0
            )
            missing_data_projects_names.append(project_name)

    text = TEXT_HEADER_RESPONSE.format(
        today_date=today_date,
        all_engineers_number=all_engineers_number,
        all_workers_number=all_workers_number) + text
    short_text = SHORT_TEXT_HEADER_RESPONSE.format(
        today_date=today_date) + short_text

    return text, short_text, missing_data_projects_names


def message_text_handler(text_list):
    """Обработка текста отчета из ТГ, возвращение списка корректных данных,
    соответствующего типа, или None"""
    result = {}
    for string in text_list:
        for param in SEARCH_PARAMS_IN_MESSAGE:
            match = re.search(fr'{param}\D*(\d+(?:[.,]\d+)?)', string)
            if match:
                result[param] = match.group(1).replace(',', '.')
                break

    result_list = [REPORT_DATA_PARAMS[param](result[param])
                   if param in result else None
                   for param in SEARCH_PARAMS_IN_MESSAGE]
    return result_list


def switch_is_actual_reports(on=True):
    """Функция переключения Флага актуальности проекта
    Если on=False - то переключит is_actual_reports на False
    по умолчанию переключает на True"""
    global is_actual_reports
    if on:
        is_actual_reports = True
    else:
        is_actual_reports = False


def report_data_updater(search_name, message_text_list):
    """Получение всех данных по отчету для записи в БД,
    Проверка наличия отчета и обновление/запись в БД
    Возвращает True - данные корректные и записаны в БД,
    возвращает False - данные некорректные"""
    project_id = get_project_id(cursor, search_name)
    today_date = datetime.today().date().strftime('%d.%m.%Y')
    report_data_list = message_text_handler(message_text_list)
    for value in report_data_list:
        if value is None:
            return False
    (engineer, worker, night_people, progress) = report_data_list
    try:
        people_sum = engineer + worker
    except TypeError:
        return False

    # проверка наличия сегодняшнего отчета в БД
    # если есть вернет id соответствующей записи, если нет - 0
    report_id = today_report_exist_id(cursor, project_id, today_date)
    if report_id == 0:
        create_new_report(connection,
                          cursor,
                          project_id,
                          today_date,
                          engineer,
                          worker,
                          night_people,
                          people_sum,
                          progress)
    else:
        update_report(connection,
                      cursor,
                      report_id,
                      engineer,
                      worker,
                      night_people,
                      people_sum,
                      progress)
    return True


def send_message_to_several_receivers(bot, receivers_id, text):
    for receiver_id in receivers_id:
        try:
            bot.send_message(chat_id=receiver_id, text=text)
        except telegram.TelegramError:
            pass


def generate_reports(update, context):
    projects_search_names = get_projects_names(cursor, search_name=True)
    text = update.message.text
    for search_name in projects_search_names:
        if search_name in text:
            is_valid_data = report_data_updater(
                search_name,
                text.splitlines()[:STRINGS_NUBER_CUT_FROM_TG_MESSAGE])
            # Отправка сообщения, если данные были некорректные
            if not is_valid_data:
                context.bot.send_message(
                    chat_id=GROUP_ID,
                    text=NOT_VALID_DATA_RESPONSE.format(
                        project_search_name=search_name)
                )
                break
            # проверка наличия всех отчетов и отправка сводного отчета
            today_date = datetime.today().date().strftime('%d.%m.%Y')
            today_reports_amount = get_today_reports_amount(cursor,
                                                            today_date)
            active_projects_amount = get_active_projects_amount(cursor)
            if today_reports_amount == active_projects_amount:
                text, short_text, missing_projects = generate_text_messages()
                send_message_to_several_receivers(bot=context.bot,
                                                  receivers_id=RECEIVERS_ID,
                                                  text=text)
                send_message_to_several_receivers(bot=context.bot,
                                                  receivers_id=RECEIVERS_ID,
                                                  text=short_text)
                switch_is_actual_reports(on=True)
            break


def send_report_at_the_same_time(bot, report_time):
    if is_actual_reports:
        return

    text, short_text, missing_projects = generate_text_messages()
    if report_time == REPORT_SEND_TIMES[0]:
        send_message_to_several_receivers(bot=bot,
                                          receivers_id=RECEIVERS_ID,
                                          text=text)
        send_message_to_several_receivers(bot=bot,
                                          receivers_id=RECEIVERS_ID,
                                          text=short_text)
    if len(missing_projects) != 0:
        reminder_message = ('Для формирования полного сводного отчета '
                            'по Компании недостаточно данных по:')
        for project_name in missing_projects:
            reminder_message += f'\n• {project_name}'
        bot.send_message(chat_id=GROUP_ID, text=reminder_message)


def generate_and_send_table_report(update, context):
    chat = update.effective_chat

    # Чтение данных из базы данных в pandas DataFrame
    df = pd.read_sql_query(
        'SELECT * FROM Reports '
        'JOIN Projects ON Projects.id = Reports.project_id;',
        connection)
    # Запись данных в Excel
    try:
        df.to_excel('table_report.xlsx', index=False)
        context.bot.send_message(
            chat_id=chat.id,
            text='Полный сформированные отчет по людям в Excel:'
        )
        context.bot.send_document(chat_id=chat.id,
                                  document=open('table_report.xlsx', 'rb'))
    except Exception as e:
        context.bot.send_message(
            chat_id=chat.id,
            text=f'Произошла ошибка: {e}'
        )


# Инициализация кнопки start и добавление кнопки "Прислать Excel отчет"
def start_button(update, context):
    chat = update.effective_chat
    button = telegram.ReplyKeyboardMarkup(
        [[telegram.KeyboardButton('Прислать Excel отчет')]],
        resize_keyboard=True)

    context.bot.send_message(
        chat_id=chat.id,
        text='Можно запросить Excel отчет кнопкой "Прислать Excel отчет"',
        reply_markup=button
        )


def main():
    bot = telegram.Bot(token=BOT_TOKEN)
    updater = Updater(token=BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Подключение кнопок
    dispatcher.add_handler(CommandHandler('start', start_button))
    dispatcher.add_handler(
        MessageHandler(Filters.regex('Прислать Excel отчет'),
                       generate_and_send_table_report))

    # Подключение обработки входящих сообщений (основной функционал бота)
    dispatcher.add_handler(MessageHandler(Filters.text, generate_reports))

    updater.start_polling()

    # Добавление в расписание:
    # Смена флага актуальности отчета в конце дня
    # Уведомления в случае отсутствия данных по отчету UTC+0
    schedule.every().day.at('20:59').do(switch_is_actual_reports, on=False)
    for report_time in REPORT_SEND_TIMES:
        schedule.every().day.at(report_time).do(send_report_at_the_same_time,
                                                bot=bot,
                                                report_time=report_time)
    while True:
        schedule.run_pending()
        time.sleep(SLEEP_PERIOD_SCHEDULE)


if __name__ == '__main__':
    # флаг актуальности отчетов на сегодня:
    # True - все отчеты по проектам сегодня предоставлены,
    # False - все или часть отчетов не предоставлены
    is_actual_reports = False

    # Подключение базы данных и создание таблиц с проектами (если их нет)
    with sqlite3.connect('db/projects_report.db',
                         check_same_thread=False) as connection:
        connection.execute('PRAGMA foreign_keys = ON;')
        cursor = connection.cursor()
        program_first_start(connection, cursor)

        # выполнение основного кода с запуском ТГ бота
        main()

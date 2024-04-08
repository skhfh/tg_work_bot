import os
import re
import sqlite3
from datetime import datetime

from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import Updater, Filters, MessageHandler

from database import (create_new_report, get_active_projects_amount,
                      get_project_id, get_projects_names,
                      get_project_report_data, get_today_reports_amount,
                      program_first_start, today_report_exist_id,
                      update_report)

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

# Подгрузка виртуального окружения
load_dotenv()

# BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_TOKEN = os.getenv('BOT_TOKEN_TEST')
# RECEIVER_ID = os.getenv('EMIL_ID')
RECEIVER_ID = os.getenv('MY_ID')


# Текст сообщений для отправки ботом в ТГ !!!! С АРГУМЕНТАМИ
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


def generate_text_messages(projects_search_names):
    """Подготовка текста сводного отчета полной и короткой форм
    для отправки в ТГ чат"""
    today_date = datetime.today().strftime("%d.%m.%Y")
    text = ''
    short_text = ''
    all_engineers_number = 0
    all_workers_number = 0

    for search_name in projects_search_names:
        (project_name,
         short_name,
         engineer,
         worker,
         night_people,
         people_sum,
         progress) = get_project_report_data(cursor, search_name, today_date)

        text += '\n\n' + TEXT_BODY_RESPONSE.format(project_name=project_name,
                                                   engineer=engineer,
                                                   worker=worker)
        short_text += '\n' + SHORT_TEXT_BODY_RESPONSE.format(
            short_name=short_name,
            people_sum=people_sum,
            night_people=night_people
        )
        all_engineers_number += engineer
        all_workers_number += worker

    text = TEXT_HEADER_RESPONSE.format(
        today_date=today_date,
        all_engineers_number=all_engineers_number,
        all_workers_number=all_workers_number) + text
    short_text = SHORT_TEXT_HEADER_RESPONSE.format(
        today_date=today_date) + short_text

    return text, short_text


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


def generate_reports(update, context):
    projects_search_names = get_projects_names(cursor, search_name=True)
    chat = update.effective_chat
    text = update.message.text
    for search_name in projects_search_names:
        if search_name in text:
            is_valid_data = report_data_updater(
                search_name,
                text.splitlines()[:STRINGS_NUBER_CUT_FROM_TG_MESSAGE])
            # Отправка сообщения, если данные были некорректные
            if not is_valid_data:
                context.bot.send_message(
                    chat_id=RECEIVER_ID,
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
                text, short_text = generate_text_messages(
                    projects_search_names)
                # context.bot.send_message(chat_id=chat.id, text=text)
                # context.bot.send_message(chat_id=chat.id, text=short_text)
                context.bot.send_message(chat_id=RECEIVER_ID, text=text)
                context.bot.send_message(chat_id=RECEIVER_ID, text=short_text)
            break


def main():
    bot = Bot(token=BOT_TOKEN)
    updater = Updater(token=BOT_TOKEN)

    updater.dispatcher.add_handler(MessageHandler(Filters.text,
                                                  generate_reports))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    # Подключение базы данных и создание таблиц с проектами (если их нет)
    with sqlite3.connect('projects_report.db',
                         check_same_thread=False) as connection:
        connection.execute('PRAGMA foreign_keys = ON;')
        cursor = connection.cursor()
        program_first_start(connection, cursor)

        # выполнение основного кода с запуском ТГ бота
        main()

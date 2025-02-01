import datetime
import re

import telegram

from tg_work_bot.bot.message_templates import (SHORT_TEXT_BODY_RESPONSE,
                                               SHORT_TEXT_HEADER_RESPONSE,
                                               TEXT_BODY_RESPONSE,
                                               TEXT_HEADER_RESPONSE)
from tg_work_bot.config.config import actual_reports_flag
from tg_work_bot.config.settings import (GROUP_ID, RECEIVERS_ID,
                                         REPORT_DATA_PARAMS, REPORT_SEND_TIMES,
                                         SEARCH_PARAMS_IN_MESSAGE)
from tg_work_bot.models.models import Project, Report


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
    """Парсинг из сообщения всех данных по отчету для записи в БД,
    Проверка наличия отчета и обновление/запись в БД,
    возвращает True - данные корректные и записаны в БД,
    возвращает False - данные некорректные"""
    project = Project.get_or_none(search_name=search_name)
    if project is None:
        return False
    report_data_list = message_text_handler(message_text_list)

    for value in report_data_list:
        if value is None:
            return False
    (engineer, worker, night_people, progress) = report_data_list
    try:
        people_sum = engineer + worker
    except TypeError:
        return False
    current_date = datetime.date.today()

    # проверка наличия сегодняшнего отчета в БД
    # если есть - обновление записи, если нет - создание
    existing_report = Report.get_or_none(project=project, date=current_date)
    if existing_report:
        existing_report.engineer = engineer
        existing_report.worker = worker
        existing_report.night_people = night_people
        existing_report.people_sum = people_sum
        existing_report.progress = progress
        existing_report.save()
    else:
        Report.create(
            project_id=project,
            engineer=engineer,
            worker=worker,
            night_people=night_people,
            people_sum=people_sum,
            progress=progress
        )
    return True


def send_message_to_several_receivers(bot, receivers_id, text):
    for receiver_id in receivers_id:
        try:
            bot.send_message(chat_id=receiver_id, text=text)
        except telegram.TelegramError:
            pass


def generate_text_messages():
    """Подготовка текста сводного отчета полной и короткой форм
    для отправки в ТГ чат.
    Возвращает тест сообщений для полной и короткой форм,
    а также список названий проектов, по которым еще нет данных.
    По проектам, данных по которым нет, будут проставлены 0 в отчете."""
    current_date = datetime.date.today()
    text = ''
    short_text = ''

    # Получение списка кортежей всех отчетов за сегодня
    query = Report.select().where(Report.date == current_date).execute()
    report_data_list = [
        (
            report.project.name,
            report.project.short_name,
            report.engineer,
            report.worker,
            report.night_people,
            report.people_sum,
            report.progress
        )
        for report in query
    ]

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

    projects = (Project.select(Project.name, Project.short_name)
                .where(Project.status == True).execute())

    # Для проектов, по которым отсутствуют данные, проставляем 0.
    # Формируем список с названиями проектов, по которым нет данных
    for project in projects:
        if project.name not in project_names_of_actual_reports:
            text += '\n\n' + TEXT_BODY_RESPONSE.format(
                project_name=project.name,
                engineer=0,
                worker=0)
            short_text += '\n' + SHORT_TEXT_BODY_RESPONSE.format(
                short_name=project.short_name,
                people_sum=0,
                night_people=0
            )
            missing_data_projects_names.append(project.name)

    text = TEXT_HEADER_RESPONSE.format(
        today_date=current_date.strftime('%d.%m.%Y'),
        all_engineers_number=all_engineers_number,
        all_workers_number=all_workers_number) + text
    short_text = SHORT_TEXT_HEADER_RESPONSE.format(
        today_date=current_date.strftime('%d.%m.%Y')) + short_text

    return text, short_text, missing_data_projects_names


def send_report_at_the_same_time(bot, report_time):
    if actual_reports_flag.get_flag():
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

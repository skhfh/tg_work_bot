import datetime

import pandas as pd
import telegram

from tg_work_bot.bot.message_templates import NOT_VALID_DATA_RESPONSE
from tg_work_bot.bot.services import (generate_text_messages,
                                      report_data_updater,
                                      send_message_to_several_receivers)
from tg_work_bot.config.config import actual_reports_flag
from tg_work_bot.config.settings import (GROUP_ID, RECEIVERS_ID,
                                         STRINGS_NUBER_CUT_FROM_TG_MESSAGE)
from tg_work_bot.models.models import Project, Report


def start_button(update, context):
    """Инициализация кнопки start и добавление кнопки (Прислать Excel отчет)"""
    chat = update.effective_chat
    button = telegram.ReplyKeyboardMarkup(
        [[telegram.KeyboardButton('Прислать Excel отчет')]],
        resize_keyboard=True)

    context.bot.send_message(
        chat_id=chat.id,
        text='Можно запросить Excel отчет кнопкой "Прислать Excel отчет"',
        reply_markup=button
    )


def generate_and_send_table_report(update, context):
    """Генерация отчетных данных в Excel и отправка в чат"""
    chat = update.effective_chat
    data = Report.select(
        Report.id,
        Report.project,
        Project.name,
        Report.engineer,
        Report.worker,
        Report.night_people,
        Report.people_sum,
        Report.progress,
        Report.date
    ).join(Project).dicts()

    # Создаем DataFrame
    df = pd.DataFrame(data)
    df.rename(
        columns={
            'id': 'id',
            'project': 'id проекта',
            'name': 'Название проекта',
            'engineer': 'Кол-во ИТР',
            'worker': 'Кол-во рабочих',
            'night_people': 'Кол-во в ночь',
            'people_sum': 'Всего людей',
            'progress': 'Процент выполнения',
            'date': 'Дата'
        },
        inplace=True)

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


def generate_reports(update, context):
    """Обработка входящих отчетов по проектам
    Создание/обновление записей в БД и отправка сообщений:
    если данные переданы некорректно, если все отчеты по проектам получены
    """
    query = Project.select(Project.search_name).where(
        Project.status == True).tuples()
    projects_search_names = [row[0] for row in query]
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
            current_date = datetime.date.today()
            today_reports_amount = (
                Report.select().where(Report.date == current_date).count()
            )
            active_projects_amount = (
                Project.select().where(Project.status == True).count()
            )

            if today_reports_amount == active_projects_amount:
                text, short_text, missing_projects = generate_text_messages()
                send_message_to_several_receivers(bot=context.bot,
                                                  receivers_id=RECEIVERS_ID,
                                                  text=text)
                send_message_to_several_receivers(bot=context.bot,
                                                  receivers_id=RECEIVERS_ID,
                                                  text=short_text)
                actual_reports_flag.set_flag(True)
            break

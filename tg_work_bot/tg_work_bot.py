import os
import re
from dataclasses import dataclass
from datetime import datetime

from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import Updater, Filters, MessageHandler

load_dotenv()

# BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_TOKEN = os.getenv('BOT_TOKEN_TEST')
# RECEIVER_ID = os.getenv('EMIL_ID')
RECEIVER_ID = os.getenv('MY_ID')

PROJECTS_NAMES = {
    1: ['Технопарк', 'ТП'],
    2: ['Энергоцентр', 'ЭЦ'],
    3: ['Бублик', 'Бублик'],
    4: ['ЦОД ТМ7,8', 'ТМ7,8'],
    5: ['ЦОД Саратов', 'РЦОД'],
    6: ['ЦОД ЮП', 'ЮП'],
    7: ['ЦОД Новая Рига', 'Новая Рига'],
}


@dataclass
class Projects:
    """Объект проекта с его характеристиками"""
    name: str
    sort_name: str
    engineers_number: int = 0
    workers_number: int = 0
    night_people_number: int = 0
    program_execution: int = 0

    def get_people_sum(self):
        return self.engineers_number + self.workers_number

    def get_message(self) -> str:
        return (f'{self.name}:\n'
                f'ИТР - {self.engineers_number}; '
                f'Рабочих - {self.workers_number}')

    def get_sort_message(self) -> str:
        return (f'• {self.sort_name}: {self.get_people_sum()} '
                f'(из них {self.night_people_number} ночью)')


def project_text_handler(text_list):
    params_string_number = {
        'ИТР': 1,
        'Рабочие': 2,
        'Ночь': 4,
        'ПП': 5,
    }
    new_params_list = []
    for param in params_string_number:
        new_param = re.search(r'\d+',
                              text_list[params_string_number[param]])
        if new_param:
            new_param = int(new_param.group())
        else:
            new_param = None
        new_params_list.append(new_param)
    return new_params_list


def project_updater(project, text_list):
    (engineers_number,
     workers_number,
     night_people_number,
     program_execution) = project_text_handler(text_list)
    project.engineers_number = engineers_number
    project.workers_number = workers_number
    project.night_people_number = night_people_number
    project.program_execution = program_execution


def check_actual_dates(projects_codes):
    for project_code in projects_codes:
        if projects_codes[project_code][1] != datetime.today().date():
            return False
    return True


def generate_text_messages(projects_codes):
    today_date = datetime.today().strftime("%d.%m.%Y")
    text = ''
    short_text = ''
    all_engineers_number = 0
    all_workers_number = 0
    for project_code in projects_codes:
        project = projects_codes[project_code][0]
        text += '\n\n' + project.get_message()
        short_text += '\n' + project.get_sort_message()
        all_engineers_number += project.engineers_number
        all_workers_number += project.workers_number
    text = (f'Количество персонала на стройплощадках объектов Смарт '
            f'Констракшн по состоянию на {today_date}\n\n'
            f'Общее по объектам:\n'
            f'ИТР - {all_engineers_number}; '
            f'Рабочих - {all_workers_number}\n'
            f'в т.ч:' + text)
    short_text = f'Отчёт по людям {today_date}' + short_text
    return text, short_text


def main():
    tp_project = Projects(name=PROJECTS_NAMES[1][0],
                          sort_name=PROJECTS_NAMES[1][1])
    ec_project = Projects(name=PROJECTS_NAMES[2][0],
                          sort_name=PROJECTS_NAMES[2][1])
    bub_project = Projects(name=PROJECTS_NAMES[3][0],
                           sort_name=PROJECTS_NAMES[3][1])
    tm78_project = Projects(name=PROJECTS_NAMES[4][0],
                            sort_name=PROJECTS_NAMES[4][1])
    rcod_project = Projects(name=PROJECTS_NAMES[5][0],
                            sort_name=PROJECTS_NAMES[5][1])
    up_project = Projects(name=PROJECTS_NAMES[6][0],
                          sort_name=PROJECTS_NAMES[6][1])
    nr_project = Projects(name=PROJECTS_NAMES[7][0],
                          sort_name=PROJECTS_NAMES[7][1])

    projects_codes = {
        'ТЕХНОПАРК': [tp_project, None],
        'Энергоцентр': [ec_project, None],
        'Бублик': [bub_project, None],
        'ЦОД ТМ-7,8': [tm78_project, None],
        'РЦОД Саратов': [rcod_project, None],
        'МегаЦОД-3 ЮП': [up_project, None],
        'ЦОД Новая Рига': [nr_project, None],
    }

    def answer(update, context):
        chat = update.effective_chat
        text = update.message.text
        for project_code in projects_codes:
            if project_code in text:
                project = projects_codes[project_code][0]
                project_updater(project, text.splitlines()[:6])
                projects_codes[project_code][1] = datetime.today().date()
                if check_actual_dates(projects_codes):
                    text, short_text = generate_text_messages(projects_codes)
                    # context.bot.send_message(chat_id=chat.id, text=text)
                    # context.bot.send_message(chat_id=chat.id, text=short_text)
                    context.bot.send_message(chat_id=RECEIVER_ID, text=text)
                    context.bot.send_message(chat_id=RECEIVER_ID, text=short_text)
                break

    bot = Bot(token=BOT_TOKEN)
    updater = Updater(token=BOT_TOKEN)

    updater.dispatcher.add_handler(MessageHandler(Filters.text, answer))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

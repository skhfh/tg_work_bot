import csv

from peewee import SqliteDatabase

from tg_work_bot.config.settings import DATABASE, INITIAL_DATA_PATH
from tg_work_bot.models.models import Project, Report

db = SqliteDatabase(DATABASE)


def init_db():
    """Инициализация базы данных.
    Создание таблиц и наполнение первоначальными данными"""

    db.connect()
    db.create_tables([Project, Report])

    if Project.select().count() == 0:
        with open(INITIAL_DATA_PATH, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file, delimiter=';')
            next(csv_reader)
            projects_data = [{
                'name': row[0],
                'short_name': row[1],
                'search_name': row[2]
            } for row in csv_reader]
            Project.insert_many(projects_data).execute()

import csv

from peewee import SqliteDatabase

from models import Project, Report


db = SqliteDatabase('projects.db')

def init_db():
    """Инициализация базы данных.
    Создание таблиц и наполнение первоначальными данными"""

    db.connect()
    db.create_tables([Project, Report])

    if Project.select().count() == 0:
        with open('initial_data.csv', 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file, delimiter=';')
            next(csv_reader)
            projects_data = [{
                'name': row[0],
                'short_name': row[1],
                'search_name': row[2]
            } for row in csv_reader]
            Project.insert_many(projects_data).execute()


# init_db()

# Report.insert(project_id=3, engineer=1, worker=4, night_people=3, progress=0.6).execute()
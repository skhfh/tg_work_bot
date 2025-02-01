import datetime

from peewee import (SQL, BooleanField, CharField, DateField, FloatField,
                    ForeignKeyField, IntegerField, Model, SqliteDatabase)

from tg_work_bot.config.settings import DATABASE

db = SqliteDatabase(DATABASE)


class Project(Model):
    """Модель проектов"""
    name = CharField(unique=True,
                     null=False,
                     verbose_name='Название проекта')
    short_name = CharField(unique=True,
                           null=False,
                           verbose_name='Сокращенное название проекта')
    search_name = CharField(
        unique=True,
        null=False,
        verbose_name='Название проекта для поиска',
        help_text='Название проекта, по которому происходит '
                  'поиск данных в отчетах от проектных команд.'
    )
    status = BooleanField(default=True)

    class Meta:
        database = db
        table_name = 'projects'

    def __str__(self):
        return self.name


class Report(Model):
    """Модель отчетов"""
    project = ForeignKeyField(Project,
                              backref='reports',
                              on_delete='CASCADE')
    date = DateField(default=datetime.date.today,
                     verbose_name='Текущая дата отчета')
    engineer = IntegerField(verbose_name='Количество инженеров')
    worker = IntegerField(verbose_name='Количество рабочих')
    night_people = IntegerField(verbose_name='Количество людей в ночь')
    people_sum = IntegerField(verbose_name='Общее количество людей')
    progress = FloatField(verbose_name='Процент выполнения проекта')

    class Meta:
        database = db
        table_name = 'reports'
        constraints = [
            SQL('UNIQUE (project_id, date)')
        ]

    def __str__(self):
        return self.date + ' -- ' + str(self.project)

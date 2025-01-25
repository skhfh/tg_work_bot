import datetime
from peewee import SqliteDatabase, SQL
from peewee import Model, CharField, BooleanField, ForeignKeyField, DateField, IntegerField, FloatField

db = SqliteDatabase('projects.db')

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


class Report(Model):
    """Модель отчетов"""
    project_id = ForeignKeyField(Project,
                                 backref='reports',
                                 on_delete='CASCADE')
    date = DateField(default=datetime.date.today,
                     verbose_name='Текущая дата отчета')
    engineer = IntegerField(verbose_name='Количество инженеров')
    worker = IntegerField(verbose_name='Количество рабочих')
    night_people = IntegerField(verbose_name='Количество людей в ночь')
    people_sum = IntegerField(default=0, verbose_name='Общее количество людей')
    progress = FloatField(verbose_name='Процент выполнения проекта')

    class Meta:
        database = db
        table_name = 'reports'
        constraints = [
            SQL('UNIQUE (project_id, date)')
        ]

    @property
    def formatted_date(self):
        return self.date.strftime('%d-%m-%Y') if self.date else None

    def save(self, *args, **kwargs):
        # Автоматический расчет people_sum при сохранении
        self.people_sum = self.engineer + self.worker
        return super().save(*args, **kwargs)

    @classmethod
    def create(cls, **query):
        # Перехват create() и автоматический расчет people_sum
        query["people_sum"] = query.get("engineer", 0) + query.get("worker", 0)
        return super().create(**query)

    @classmethod
    def insert(cls, **query):
        # Перехват insert() и автоматический расчет people_sum
        query["people_sum"] = query.get("engineer", 0) + query.get("worker", 0)
        return super().insert(**query)
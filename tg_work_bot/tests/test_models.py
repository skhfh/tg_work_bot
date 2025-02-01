import datetime

import pytest
from peewee import IntegrityError

from tg_work_bot.models.models import Project, Report


def test_create_project(test_db):
    """Тест создания проекта"""
    project = Project.create(name='Project name',
                             short_name='Short',
                             search_name='Search')

    assert project.id == 1
    assert project.name == 'Project name'
    assert project.short_name == 'Short'
    assert project.search_name == 'Search'
    assert project.status is True


@pytest.mark.parametrize('field, kwargs', [
    ('name', {'short_name': 'Short', 'search_name': 'Search'}),
    ('short_name', {'name': 'Project', 'search_name': 'Search'}),
    ('search_name', {'name': 'Project', 'short_name': 'Short'}),
])
def test_project_fields_cannot_be_null(test_db, field, kwargs):
    """Тестируем, что каждое обязательное поле не может быть NULL"""
    with pytest.raises(IntegrityError) as ex:
        Project.create(**kwargs)

    assert f'{field}' in str(ex.value)


@pytest.mark.parametrize('field, kwargs', [
    ('name',
     {'name': 'Unique Project',
      'short_name': 'Short',
      'search_name': 'Search'}),
    ('short_name',
     {'name': 'Project',
      'short_name': 'Unique Short',
      'search_name': 'Search'}),
    ('search_name',
     {'name': 'Project',
      'short_name': 'Short',
      'search_name': 'Unique Search'}),
])
def test_project_name_must_be_unique(test_db, field, kwargs):
    """Проверяем уникальность поля `name`"""
    Project.create(name='Unique Project',
                   short_name='Unique Short',
                   search_name='Unique Search')
    with pytest.raises(IntegrityError) as ex:
        Project.create(**kwargs)

    assert f'{field}' in str(ex.value)


def test_create_report(test_db):
    """Тест создания записи отчета"""
    project = Project.create(name='Project name',
                             short_name='Short',
                             search_name='Search')
    report = Report.create(project=project,
                           engineer=1,
                           worker=2,
                           night_people=3,
                           people_sum=3,
                           progress=45.5)

    assert report.project == project
    assert report.engineer == 1
    assert report.worker == 2
    assert report.night_people == 3
    assert report.people_sum == 3
    assert report.progress == 45.5
    assert report.date == datetime.date.today()


@pytest.mark.parametrize('kwargs', [
    {'engineer': 1, 'worker': 2, 'night_people': 3, 'people_sum': 3,
     'progress': 45.5}
])
def test_report_fields_date_and_project_unique(test_db, kwargs):
    """Тест уникальности связки полей дата-проект"""
    project = Project.create(name='Project name',
                             short_name='Short',
                             search_name='Search')
    Report.insert(project=project, **kwargs).execute()
    with pytest.raises(IntegrityError) as ex:
        Report.create(project=project, **kwargs)

    assert 'UNIQUE constraint failed' in str(ex.value)

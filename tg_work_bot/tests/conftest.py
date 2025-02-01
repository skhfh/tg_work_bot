import pytest
from peewee import SqliteDatabase

from tg_work_bot.models.models import Project, Report

TEST_DB = SqliteDatabase(':memory:')


@pytest.fixture(scope='function')
def test_db():
    """Фикстура для тестирования моделей Peewee."""
    TEST_DB.bind([Project, Report])
    TEST_DB.connect()
    TEST_DB.create_tables([Project, Report])

    yield TEST_DB

    TEST_DB.close()

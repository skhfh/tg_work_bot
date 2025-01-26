from tg_work_bot.models.models import Project


def get_active_projects_amount():
    """Количество активных проектов"""
    return Project.select().where(Project.status == True).count()


def get_project_by_search_name(search_name):
    """Получение id проекта и таблицы Проектов в БД"""
    return Project.get_or_none(search_name=search_name)


def get_projects_names(short_name=False, search_name=False):
    """Получение наименований проектов
    short_name=True - получение сокращенных названий
    search_name=True - получение названий для поиска в сообщениях
    В остальных случаях - полные названия проектов"""
    projects = Project.select().where(Project.status == True).execute()
    if short_name and not search_name:
        return [project.short_name for project in projects]
    elif not short_name and search_name:
        return [project.search_name for project in projects]
    else:
        return [project.name for project in projects]

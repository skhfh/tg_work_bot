import datetime

from tg_work_bot.models.models import Report

current_date = datetime.date.today()


def create_or_update_report(project, engineer, worker, night_people,
                            progress):
    """Создание или обновление записи в таблице Отчеты БД"""
    existing_report = Report.get_or_none(project=project,
                                         date=current_date)
    if existing_report:
        existing_report.engineer = engineer
        existing_report.worker = worker
        existing_report.night_people = night_people
        existing_report.people_sum = engineer + worker
        existing_report.progress = progress
        existing_report.save()
    else:
        Report.create(
            project_id=project,
            engineer=engineer,
            worker=worker,
            night_people=night_people,
            people_sum=engineer + worker + night_people,
            progress=progress
        )


def get_today_reports_amount():
    """Количество, полученных отчетов сегодня"""
    return Report.select().where(Report.date == current_date).count()


def get_project_report_data():
    """Получение данных из БД для формирования сообщений сводных отчетов.
    Возвращаемый список кортежей данных по проектам на указанную дату:
    (имя проекта, короткое имя проекта, кол-во ИТР, рабочих, людей в ночь,
    всего людей, выполнение ПП)
    Или пустой список в случае если данных на этот день нет"""
    query = Report.select().where(Report.date == current_date).execute()
    return [
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

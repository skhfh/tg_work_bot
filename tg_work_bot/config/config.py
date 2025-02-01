import datetime

from peewee import OperationalError

from tg_work_bot.models.models import Project, Report


class ActualReportFlag:
    """Флаг актуальности отчетов на сегодня:
    True - все отчеты по проектам сегодня предоставлены,
    False - все или часть отчетов не предоставлены"""
    def __init__(self):
        try:
            today_reports_count = (
                Report.select()
                .where(Report.date == datetime.date.today())
                .count()
            )
            active_projects_count = (
                Project.select()
                .where(Project.status == True)
                .count()
            )
            if today_reports_count == active_projects_count:
                self.flag = True
            else:
                self.flag = False
        except OperationalError:
            self.flag = False

    def set_flag(self, value: bool):
        self.flag = value

    def get_flag(self):
        return self.flag


actual_reports_flag = ActualReportFlag()

import datetime

from peewee import OperationalError

from tg_work_bot.models.models import Project, Report


class ActualReportFlag:
    """Флаг актуальности отчетов на сегодня:
    True - все отчеты по проектам сегодня предоставлены,
    False - все или часть отчетов не предоставлены"""
    def __init__(self):
        try:
            if (
                    Report.select()
                            .where(Report.date == datetime.date.today())
                            .count()
                    == Project.select()
                    .where(Project.status == True)
                    .count()
            ):
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

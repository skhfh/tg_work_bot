import schedule
import time
import telegram
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from tg_work_bot.bot.handlers import (generate_and_send_table_report,
                                      generate_reports,
                                      start_button)
from tg_work_bot.bot.services import send_report_at_the_same_time
from tg_work_bot.config.config import actual_reports_flag
from tg_work_bot.config.settings import (BOT_TOKEN,
                                         REPORT_SEND_TIMES,
                                         SLEEP_PERIOD_SCHEDULE)
from tg_work_bot.models.base import init_db


def main():
    bot = telegram.Bot(token=BOT_TOKEN)
    updater = Updater(token=BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Подключение кнопок
    dispatcher.add_handler(CommandHandler('start', start_button))
    dispatcher.add_handler(
        MessageHandler(Filters.regex('Прислать Excel отчет'),
                       generate_and_send_table_report))
    # Подключение обработки входящих сообщений (основной функционал бота)
    dispatcher.add_handler(MessageHandler(Filters.text, generate_reports))

    updater.start_polling()

    # Добавление в расписание:
    # Смена флага актуальности отчета в конце дня
    # Уведомления в случае отсутствия данных по отчету UTC+0
    schedule.every().day.at('20:59').do(actual_reports_flag.set_flag,
                                        value=False)
    for report_time in REPORT_SEND_TIMES:
        schedule.every().day.at(report_time).do(send_report_at_the_same_time,
                                                bot=bot,
                                                report_time=report_time)
    while True:
        schedule.run_pending()
        time.sleep(SLEEP_PERIOD_SCHEDULE)

if __name__ == '__main__':
    #Инициализация БД и наполнение таблиц с проектами (если таблица пустая)
    init_db()

    # выполнение основного кода с запуском ТГ бота
    main()

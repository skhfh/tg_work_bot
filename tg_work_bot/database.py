# функции с запросами к БД

PROJECTS_START_PACK = [
    ('Технопарк', 'ТП', 'ТЕХНОПАРК'),
    ('Энергоцентр', 'ЭЦ', 'Энергоцентр'),
    ('Бублик', 'Бублик', 'Бублик'),
    ('ЦОД ТМ7,8', 'ТМ7,8', 'ЦОД ТМ-7,8'),
    ('ЦОД Саратов', 'РЦОД', 'РЦОД Саратов'),
    ('ЦОД ЮП', 'ЮП', 'МегаЦОД-3 ЮП'),
    ('ЦОД Новая Рига', 'Новая Рига', 'ЦОД Новая Рига'),
]


def program_first_start(conn, cur):
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS Projects(
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        short_name TEXT NOT NULL UNIQUE,
        search_name TEXT NOT NULL UNIQUE,
        responsible TEXT,
        status INTEGER DEFAULT 1 CHECK (status IN (0, 1))
    );

    CREATE TABLE IF NOT EXISTS Reports(
        id INTEGER PRIMARY KEY,
        project_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        engineer INTEGER,
        worker INTEGER,
        night_people INTEGER,
        people_sum INTEGER,
        progress REAL,
        FOREIGN KEY(project_id) REFERENCES Projects(id) ON DELETE CASCADE
        UNIQUE (project_id, date)
    );

    CREATE INDEX IF NOT EXISTS idx_date ON Reports(date);
    ''')

    if cur.execute('SELECT COUNT(*) FROM Projects').fetchone()[0] == 0:
        cur.executemany('''
            INSERT INTO Projects(name, short_name, search_name)
            VALUES(?, ?, ?)
            ''', PROJECTS_START_PACK)

    conn.commit()


def create_new_report(conn, cur, project_id, today_date, engineer, worker,
                      night_people, people_sum, progress):
    """Создание новой записи в таблице Отчеты БД"""
    cur.execute('''
        INSERT INTO Reports(project_id,
                            date,
                            engineer,
                            worker,
                            night_people,
                            people_sum,
                            progress)
        VALUES (?, ?, ?, ?, ?, ?, ?);''',
                (project_id,
                 today_date,
                 engineer,
                 worker,
                 night_people,
                 people_sum,
                 progress))
    conn.commit()


def get_active_projects_amount(cur):
    return cur.execute(
        'SELECT COUNT(*) FROM Projects WHERE status = 1'
    ).fetchone()[0]


def get_project_id(cur, search_name):
    """Получение id проекта и таблицы Проектов в БД"""
    return cur.execute(
        f'SELECT id FROM Projects WHERE search_name = "{search_name}"'
    ).fetchone()[0]


def get_project_report_data(cur, date):
    """Получение данных из БД для формирования сообщений сводных отчетов.
    Возвращаемый список кортежей данных по проектам на указанную дату:
    имя проекта, короткое имя проекта, кол-во ИТР, рабочих, людей в ночь,
    всего людей, выполнение ПП.
    Или пустой список в случае если данных на этот день нет"""
    result = cur.execute(f'''
        SELECT Projects.name,
               Projects.short_name,
               Reports.engineer,
               Reports.worker,
               Reports.night_people,
               Reports.people_sum,
               Reports.progress
        FROM Reports
        JOIN Projects ON Projects.id = Reports.project_id
        WHERE Reports.date = "{date}"
        ORDER BY Reports.project_id
        ''')
    return result.fetchall()


def get_projects_names(cur, short_name=False, search_name=False):
    """Если стоят флаги FALSE, то вернет полные названия проектов"""
    if short_name and not search_name:
        query = 'SELECT short_name FROM Projects WHERE status = 1'
    elif not short_name and search_name:
        query = 'SELECT search_name FROM Projects WHERE status = 1'
    else:
        query = 'SELECT name FROM Projects WHERE status = 1'
    result = cur.execute(query).fetchall()
    return [row[0] for row in result]


def get_today_reports_amount(cur, date):
    return cur.execute(
        f'SELECT COUNT(*) FROM Reports WHERE date = "{date}"'
    ).fetchone()[0]


def get_today_report_search_names(cur, date):
    return cur.execute(
        f'SELECT COUNT(*) FROM Reports WHERE date = "{date}"'
    ).fetchone()[0]


def today_report_exist_id(cur, project_id, date):
    """Проверка наличия сегодняшнего отчета и получения его ID.
    Если отчета нет, то вернет 0"""
    try:
        return cur.execute(
            f'SELECT id FROM Reports '
            f'WHERE project_id = "{project_id}" '
            f'AND date = "{date}"').fetchone()[0]
    except TypeError:
        return 0


def update_report(conn, cur, report_id, engineer, worker, night_people,
                  people_sum, progress):
    """Обновление записи в таблице Отчеты БД"""
    cur.execute('''UPDATE Reports
                   SET engineer = ?,
                       worker = ?,
                       night_people = ?,
                       people_sum = ?,
                       progress = ?
                   WHERE id = ?''', (
        engineer, worker, night_people, people_sum, progress, report_id
    ))
    conn.commit()

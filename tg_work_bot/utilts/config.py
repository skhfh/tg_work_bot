# Флаг для пути файла БД
PROD_DB = False

# Имя БД
DATABASE_NAME = 'projects_report.db'

# Путь к БД для Docker
DATABASE_PROD_PATH = 'db/'

DATABASE_DEV_PATH = '../'

DATABASE = (DATABASE_PROD_PATH + DATABASE_NAME if PROD_DB
            else DATABASE_DEV_PATH + DATABASE_NAME)

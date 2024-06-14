import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ.get('SECRET_KEY')

MYSQL_USER = os.getenv('MYSQL_USER', 'std_2392_bookify')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'std_2392_bookify')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '31415926')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'std-mysql.ist.mospolytech.ru')
ADMIN_ROLE_ID = 1
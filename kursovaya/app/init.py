from flask import Flask

from mysqldb import DBConnector

app = Flask(__name__, template_folder='templates')
application = app
app.config.from_pyfile('config.py')

db_connector = DBConnector(app)
from flask import g, current_app
import mysql.connector
from mysql.connector.errors import Error

class DBConnector:
    def __init__(self, app=None):
        self.app = app or current_app
        if app:
            app.teardown_appcontext(self.close)
        else:
            self.app.teardown_appcontext(self.close)

    def get_config(self):
        config = {
            'user': self.app.config['MYSQL_USER'],
            'password': self.app.config['MYSQL_PASSWORD'],
            'host': self.app.config['MYSQL_HOST'],
            'database': self.app.config['MYSQL_DATABASE']
        }
        return config

    def connect(self):
        if 'db' not in g:
            try:
                g.db = mysql.connector.connect(**self.get_config())
            except Error as err:
                current_app.logger.error(f"Database connection error: {err}")
                raise
        return g.db
    
    def close(self, e=None):
        db = g.pop('db', None)
        if db is not None:
            try:
                db.close()
            except Error as err:
                current_app.logger.error(f"Database close error: {err}")

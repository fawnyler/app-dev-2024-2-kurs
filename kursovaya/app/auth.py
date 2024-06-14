from flask import render_template, request, redirect, url_for, flash, Blueprint, current_app
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from app import db_connector
from users_policy import UsersPolicy
from functools import wraps

bp = Blueprint('auth', __name__, url_prefix='/auth')

class User(UserMixin):
    def __init__(self, user_id, login, role_id, user_name, user_surname, email):
        self.id = user_id
        self.login = login
        self.role_id = role_id
        self.user_name = user_name
        self.user_surname = user_surname
        self.email = email

    def is_admin(self):
        return self.role_id == current_app.config['ADMIN_ROLE_ID']
    
    def can(self, action, user=None):
        user_policy = UsersPolicy(user)
        method = getattr(user_policy, action, lambda: False)
        return method()

def can_user(action):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = None
            user_id = kwargs.get('user_id')
            if user_id:
                db = db_connector.connect()
                cursor = db.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
                user = cursor.fetchone()
                cursor.close()
                
            
            if not current_user.can(action, user):
                flash("У вас недостаточно прав для доступа к этой странице", category="warning")
                return redirect(url_for("index"))
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def init_login_manager(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Войдите, чтобы посмотреть содержимое страницы"
    login_manager.login_message_category = "warning"
    login_manager.user_loader(load_user)

def load_user(user_id):
    query = "SELECT user_id, login, role_id, user_name, user_surname, email FROM users WHERE user_id=%s"

    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (user_id,))
        user_data = cursor.fetchone()

    if user_data:
        return User(user_data.user_id, user_data.login, user_data.role_id, user_data.user_name, user_data.user_surname, user_data.email)
    
    return None

@bp.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template('auth.html')
    
    login = request.form.get("login", "")
    password = request.form.get("password", "")
    remember = request.form.get("remember") == "on"

    query = 'SELECT user_id, login, role_id, user_name, user_surname, email FROM users WHERE login=%s AND user_password=SHA2(%s, 256)'

    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (login, password))
        user = cursor.fetchone()

    if user is not None:
        login_user(User(user.user_id, user.login, user.role_id, user.user_name, user.user_surname, user.email), remember=remember)
        flash("Успешная авторизация", category="success")
        target_page = request.args.get("next", url_for("index"))
        return redirect(target_page)
    
    flash("Введены некорректные учетные данные пользователя", category="danger")
    return render_template('auth.html')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

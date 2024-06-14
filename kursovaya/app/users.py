from flask import Blueprint, current_app, render_template, flash, redirect, url_for, request, make_response
from flask_login import login_required, current_user
from mysqldb import DBConnector
from mysql.connector.errors import DatabaseError
import csv
from io import StringIO

from init import db_connector, app

bp = Blueprint('users', __name__, url_prefix='/users')

def get_user_info(user_id):
    db = db_connector.connect()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user_info = cursor.fetchone()
    cursor.close()
    return user_info

def update_user_info(db_connector, user_id, new_user_name, new_user_surname, new_user_midname, new_email):
    db = db_connector.connect()
    cursor = db.cursor()
    try:
        cursor.execute("""
            UPDATE users 
            SET user_name = %s, user_surname = %s, user_midname = %s, login = %s
            WHERE user_id = %s
        """, (new_user_name, new_user_surname, new_user_midname, new_email, user_id))
        db.commit()
    except DatabaseError as err:
        db.rollback()
        current_app.logger.error(f"Failed to update user info: {err}")
        raise
    finally:
        cursor.close()
        db.close()

def get_orders_history(user_id):
    db = db_connector.connect()
    cursor = db.cursor(dictionary=True)
    
    query = """
        SELECT orders.order_id, orders.date, orders.status,
               GROUP_CONCAT(book.title SEPARATOR ', ') AS book_titles,
               GROUP_CONCAT(order_item.amount SEPARATOR ', ') AS total_books,
               GROUP_CONCAT(order_item.amount * book.price SEPARATOR ', ') AS book_prices,
               SUM(order_item.amount * book.price) AS total_price
        FROM orders
        JOIN order_item ON orders.order_id = order_item.order_id
        JOIN book ON order_item.book_id = book.book_id
        WHERE orders.user_id = %s
        GROUP BY orders.order_id
    """
    cursor.execute(query, (user_id,))
    orders_history = cursor.fetchall()
    
    for order in orders_history:
        book_titles = order['book_titles'].split(', ')
        total_books = order['total_books'].split(', ')
        book_prices = order['book_prices'].split(', ')
        
        order['books_info'] = []
        for i in range(len(book_titles)):
            order['books_info'].append({
                'title': book_titles[i],
                'amount': total_books[i],
                'price': book_prices[i]
            })
    
    cursor.close()
    return orders_history

@bp.route('/export_orders_csv')
@login_required
def export_orders_csv():
    user_id = current_user.id
    orders_history = get_orders_history(user_id)
    
    csv_data = StringIO()
    csv_writer = csv.writer(csv_data)
    
    csv_writer.writerow(['Номер заказа', 'Дата', 'Статус', 'Книги', 'Количество книг', 'Цена за книгу', 'Общая сумма'])
    
    for order in orders_history:
        csv_writer.writerow([order['order_id'], order['date'], order['status'], order['book_titles'], order['total_books'], order['book_prices'], order['total_price']])
    
    response = make_response(csv_data.getvalue())
    
    response.headers['Content-Disposition'] = 'attachment; filename=orders.csv'
    response.headers['Content-type'] = 'text/csv'
    
    return response

@bp.route('/profile')
@login_required
def profile():
    user_id = current_user.id
    user_info = get_user_info(user_id)
    orders_history = get_orders_history(user_id)
    return render_template('profile.html', user_info=user_info, orders_history=orders_history)

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        new_user_name = request.form.get('user_name')
        new_user_surname = request.form.get('user_surname')
        new_user_midname = request.form.get('user_midname')
        new_email = request.form.get('login')
        
        try:
            update_user_info(db_connector, current_user.id, new_user_name, new_user_surname, new_user_midname, new_email)
            flash('Профиль успешно обновлен!', 'success')
            return redirect(url_for('users.profile'))
        except DatabaseError as e:
            flash(f'Ошибка при обновлении профиля: {e}', 'danger')
            return redirect(url_for('users.edit_profile'))

    else:  
        user_info = get_user_info(current_user.id)
        return render_template('edit_profile.html', user_info=user_info)
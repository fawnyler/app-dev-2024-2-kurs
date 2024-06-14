from flask import Blueprint, flash, redirect, request, url_for, render_template
from auth import can_user
from app import db_connector
from mysql.connector.errors import DatabaseError

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/add_book', methods=['GET', 'POST'])
@can_user('create')
def add_book():
    from app import get_genres

    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        price = request.form['price']
        release_date = request.form['release_date']
        genre_id = request.form['genre']  
        photo_url = request.form['photo_url'] 

        try:
            db = db_connector.connect()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO book (title, author, price, release_date, photo_url) VALUES (%s, %s, %s, %s, %s)",
                (title, author, price, release_date, photo_url)
            )
            book_id = cursor.lastrowid  

            cursor.execute(
                "INSERT INTO book_genre (book_id, genre_id) VALUES (%s, %s)",
                (book_id, genre_id)
            )

            db.commit()
            cursor.close()
            flash("Книга успешно добавлена", 'success')
            return redirect(url_for('index'))
        except DatabaseError as e:
            flash(f"Ошибка добавления книги: {str(e)}", 'danger')
            return redirect(url_for('index'))
    else:
        genres = get_genres()  
        print(genres)
        return render_template('add_book.html', genres=genres)


@bp.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
@can_user('edit')
def edit_book(book_id):
    db = db_connector.connect()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM book WHERE book_id = %s", (book_id,))
    book = cursor.fetchone()
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        price = request.form['price']
        cursor.execute("UPDATE book SET title = %s, author = %s, price = %s WHERE book_id = %s",
                       (title, author, price, book_id))
        db.commit()
        flash("Книга успешно обновлена", 'success')
        return redirect(url_for('index'))
    cursor.close()
    db.close()
    return render_template('edit_book.html', book=book)

@bp.route('/delete_book/<int:book_id>', methods=['POST'])
@can_user('delete')
def delete_book(book_id):
    try:
        db = db_connector.connect()
        cursor = db.cursor()
        
        cursor.execute("DELETE FROM order_item WHERE book_id=%s", (book_id,))
        
        cursor.execute("DELETE FROM book_genre WHERE book_id=%s", (book_id,))
        
        cursor.execute("DELETE FROM book WHERE book_id=%s", (book_id,))
        
        db.commit()
        cursor.close()
        flash("Книга успешно удалена", 'success')
        return redirect(url_for('index'))
    except DatabaseError as e:
        flash(f"Ошибка удаления книги: {str(e)}", 'danger')
        return redirect(url_for('index'))
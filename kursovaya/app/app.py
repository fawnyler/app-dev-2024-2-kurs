from flask import Flask, render_template, session, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from mysqldb import DBConnector
from mysql.connector.errors import DatabaseError
from datetime import datetime
from init import db_connector, app

app.config['DB_CONNECTOR'] = db_connector

from auth import bp as auth_bp, init_login_manager
app.register_blueprint(auth_bp)
init_login_manager(app)

from users import bp as users_bp
app.register_blueprint(users_bp)

from admin_function import bp as admin_bp
app.register_blueprint(admin_bp)

def get_genres():
    db = db_connector.connect()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT genre_id, genre_name FROM genre")
    genres = cursor.fetchall()
    cursor.close()
    return genres

@app.route('/genre/<string:genre_name>')
def genre_books(genre_name):
    try:
        db = db_connector.connect()
        cursor = db.cursor(dictionary=True)
        query = """
            SELECT 
                book.book_id,
                book.title, 
                book.author, 
                book.price,
                book.photo_url
            FROM 
                book 
            JOIN 
                book_genre ON book.book_id = book_genre.book_id 
            JOIN
                genre ON book_genre.genre_id = genre.genre_id
            WHERE 
                genre.genre_name = %s
        """
        cursor.execute(query, (genre_name,))
        books = cursor.fetchall()
        cursor.close()
        return render_template('genre_books.html', books=books, genre_name=genre_name) 
    except DatabaseError:
        flash("Ошибка получения книг выбранного жанра", category="danger")
        return redirect(url_for('index'))

def get_new_books():
    try:
        db = db_connector.connect()
        cursor = db.cursor(dictionary=True)
        query = """
            SELECT 
                book.book_id,
                book.title,  
                book.price, 
                book.author,
                book.photo_url,
                book.release_date
            FROM 
                book  
            ORDER BY 
                book.release_date DESC 
            LIMIT 8
        """
        cursor.execute(query)
        new_books = cursor.fetchall()
        cursor.close()
        return new_books
    except DatabaseError as e:
        flash(f"Ошибка получения новых книг: {str(e)}", category="danger")
        db_connector.connect().rollback()
        return []

def get_popular_authors():
    try:
        db = db_connector.connect()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM authors ORDER BY popularity DESC LIMIT 8")
        popular_authors = cursor.fetchall()
        cursor.close()
        return popular_authors
    except DatabaseError:
        flash("Ошибка получения популярных авторов", category="danger")
        db_connector.connect().rollback()

def get_wishlist_items(user_id):
    try:
        db = db_connector.connect()
        cursor = db.cursor(dictionary=True)  
        cursor.execute("""
            SELECT 
                book.book_id,
                book.title,
                book.author,
                book.price,
                COUNT(wishlist_book.book_id) AS amount
            FROM wishlist_book
            JOIN book ON wishlist_book.book_id = book.book_id
            JOIN wishlist ON wishlist_book.wishlist_id = wishlist.wishlist_id
            WHERE wishlist.user_id = %s
            GROUP BY book.book_id
        """, (user_id,))
        wishlist_items = cursor.fetchall()
        cursor.close()
        return wishlist_items
    except DatabaseError as e:
        flash("Ошибка получения элементов отложенного: " + str(e), category="danger")
        return []

def get_cart_items(user_id):
    try:
        db = db_connector.connect()
        cursor = db.cursor(dictionary=True) 
        cursor.execute("""
            SELECT 
                book.book_id,
                book.title,
                book.author,
                book.price,
                cart_book.amount,
                (cart_book.amount * book.price) as total
            FROM cart_book
            JOIN book ON cart_book.book_id = book.book_id
            JOIN cart ON cart_book.cart_id = cart.cart_id
            WHERE cart.user_id = %s
        """, (user_id,))
        cart_items = cursor.fetchall()
        cursor.close()
        return cart_items
    except DatabaseError:
        flash("Ошибка получения элементов корзины", category="danger")
        db_connector.connect().rollback()

def search_by_title(title):
    db = db_connector.connect()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM book WHERE title LIKE %s", ('%' + title + '%',))
    results = cursor.fetchall()
    cursor.close()
    print(f"Search by title '{title}': {results}")
    return results

def search_by_genre(genre):
    db = db_connector.connect()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT book.book_id, book.title, book.author, book.price, book.photo_url
        FROM book 
        JOIN book_genre ON book.book_id = book_genre.book_id 
        JOIN genre ON book_genre.genre_id = genre.genre_id 
        WHERE genre.genre_name LIKE %s
    """, ('%' + genre + '%',))
    results = cursor.fetchall()
    cursor.close()
    print(f"Search by genre '{genre}': {results}")
    return results

def search_by_author(author):
    db = db_connector.connect()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM book WHERE author LIKE %s", ('%' + author + '%',))
    results = cursor.fetchall()
    cursor.close()
    print(f"Search by author '{author}': {results}")
    return results

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'book_id' in request.form:
        book_id = request.form['book_id']
        try:
            db = db_connector.connect()
            cursor = db.cursor()
            
            cursor.execute("DELETE FROM cart_book WHERE book_id = %s", (book_id,))
            db.commit()
            
            flash('Товар успешно удален из корзины', 'success')
        except Exception as e:
            flash('Ошибка при удалении товара из корзины: ' + str(e), 'error')
            db.rollback()
        finally:
            cursor.close()
        
        return redirect(url_for('cart'))
    else:
        flash('Невозможно удалить товар из корзины: не указан ID книги', 'error')
        return redirect(url_for('cart'))
     
@app.route('/update_cart', methods=['POST'])
@login_required
def update_cart():
    user_id = current_user.id
    book_id = request.form.get('book_id')
    quantity = request.form.get('quantity', 1)  

    if not book_id or not book_id.isdigit():
        flash('Некорректное значение идентификатора книги', 'danger')
        return redirect(url_for('cart'))
    
    book_id = int(book_id)
    quantity = int(quantity)

    try:
        db = db_connector.connect()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("SELECT cart_id FROM cart WHERE user_id = %s", (user_id,))
        cart = cursor.fetchone()

        if cart:
            cart_id = cart['cart_id']
        else:
            cursor.execute("INSERT INTO cart (user_id) VALUES (%s)", (user_id,))
            db.commit()  
            cart_id = cursor.lastrowid

        cursor.execute("SELECT * FROM cart_book WHERE cart_id = %s AND book_id = %s", (cart_id, book_id))
        existing_book = cursor.fetchone()

        if existing_book:
            cursor.execute("UPDATE cart_book SET amount = amount + %s WHERE cart_id = %s AND book_id = %s", (quantity, cart_id, book_id))
        else:
            cursor.execute("INSERT INTO cart_book (cart_id, book_id, amount) VALUES (%s, %s, %s)", (cart_id, book_id, quantity))


        for key, value in request.form.items():
            if key.startswith('quantity_'):
                book_id = key.split('_')[1]
                quantity = int(value)
                
                if quantity > 0:
                    cursor.execute("""
                        UPDATE cart_book 
                        SET amount = %s 
                        WHERE cart_id = %s AND book_id = %s
                    """, (quantity, cart_id, book_id))
                else:
                    cursor.execute("""
                        DELETE FROM cart_book 
                        WHERE cart_id = %s AND book_id = %s
                    """, (cart_id, book_id))

        db.commit()

        flash('Корзина успешно обновлена', 'success')
    except DatabaseError as e:
        flash("Ошибка обновления корзины: " + str(e), category="danger")
        db.rollback()  
    finally:
        cursor.close()

    return redirect(url_for('cart'))

@app.route('/update_wishlist', methods=['POST'])
@login_required
def update_wishlist():
    user_id = current_user.id
    book_id = request.form.get('book_id')
    
    if not book_id or not book_id.isdigit():
        flash('Некорректное значение идентификатора книги', 'danger')
        return redirect(url_for('wishlist'))
    
    book_id = int(book_id)

    try:
        db = db_connector.connect()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("SELECT wishlist_id FROM wishlist WHERE user_id = %s", (user_id,))
        wishlist = cursor.fetchone()

        if wishlist is None:
            cursor.execute("INSERT INTO wishlist (user_id) VALUES (%s)", (user_id,))
            db.commit()
            wishlist_id = cursor.lastrowid
        else:
            wishlist_id = wishlist['wishlist_id']

        cursor.execute("INSERT INTO wishlist_book (wishlist_id, book_id) VALUES (%s, %s)", (wishlist_id, book_id))
        db.commit()
        
        cursor.execute("""
            UPDATE wishlist_book 
            SET amount = IFNULL(amount, 0) + 1 
            WHERE wishlist_id = %s AND book_id = %s
        """, (wishlist_id, book_id))
        db.commit()

        flash('Книга добавлена в отложенное', 'success')
    except DatabaseError as e:
        flash("Ошибка добавления книги в отложенное: " + str(e), category="danger")
        db.rollback()
    finally:
        cursor.close()

    return redirect (url_for('wishlist'))

@app.route('/move_to_wishlist', methods=['POST'])
def move_to_wishlist():
    if 'book_id' in request.form:
        book_id = request.form['book_id']
        try:
            db = db_connector.connect()
            cursor = db.cursor(dictionary=True)

            user_id = current_user.id
            
            cursor.execute("SELECT wishlist_id FROM wishlist WHERE user_id = %s", (user_id,))
            wishlist = cursor.fetchone()

            if wishlist is None:
                cursor.execute("INSERT INTO wishlist (user_id) VALUES (%s)", (user_id,))
                db.commit()
                wishlist_id = cursor.lastrowid
            else:
                wishlist_id = wishlist['wishlist_id']

            cursor.execute("DELETE FROM cart_book WHERE book_id = %s AND cart_id = (SELECT cart_id FROM cart WHERE user_id = %s)", (book_id, user_id))
            db.commit()

            cursor.execute("SELECT * FROM wishlist_book WHERE wishlist_id = %s AND book_id = %s", (wishlist_id, book_id))
            existing_book = cursor.fetchone()

            if existing_book:
                cursor.execute("UPDATE wishlist_book SET amount = amount + 1 WHERE wishlist_id = %s AND book_id = %s", (wishlist_id, book_id))
            else:
                cursor.execute("INSERT INTO wishlist_book (wishlist_id, book_id, amount) VALUES (%s, %s, 1)", (wishlist_id, book_id))

            db.commit()
            
            flash('Книга успешно перемещена в отложенное', 'success')
        except Exception as e:
            flash('Ошибка при перемещении книги в отложенное: ' + str(e), 'error')
            db.rollback()
        finally:
            cursor.close()
        
        return redirect(url_for('wishlist'))
    else:
        flash('Невозможно переместить книгу в отложенное: не указан ID книги', 'error')
        return redirect(url_for('wishlist'))

@app.route('/remove_from_wishlist', methods=['POST'])
@login_required
def remove_from_wishlist():
    user_id = current_user.id
    book_id = request.form.get('book_id')
    
    if not book_id or not book_id.isdigit():
        flash('Некорректное значение идентификатора книги', 'danger')
        return redirect(url_for('wishlist'))
    
    book_id = int(book_id)

    try:
        db = db_connector.connect()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("DELETE FROM wishlist_book WHERE wishlist_id IN (SELECT wishlist_id FROM wishlist WHERE user_id = %s) AND book_id = %s", (user_id, book_id))
        db.commit()
        
        flash('Книга успешно удалена из отложенного', 'success')
    except DatabaseError as e:
        flash("Ошибка удаления книги из отложенного: " + str(e), category="danger")
        db.rollback()
    finally:
        cursor.close()

    return redirect(url_for('wishlist'))

@app.route('/move_to_cart', methods=['POST'])
@login_required
def move_to_cart():
    user_id = current_user.id
    book_id = request.form.get('book_id')
    
    try:
        db = db_connector.connect()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("SELECT cart_id FROM cart WHERE user_id = %s", (user_id,))
        carts = cursor.fetchall()

        if carts:
            cart_id = carts[0]['cart_id']
        else:
            cursor.execute("INSERT INTO cart (user_id) VALUES (%s)", (user_id,))
            db.commit()
            cart_id = cursor.lastrowid

        cursor.execute("DELETE FROM wishlist_book WHERE book_id = %s", (book_id,))
        db.commit()
        
        cursor.execute("SELECT * FROM cart_book WHERE cart_id = %s AND book_id = %s", (cart_id, book_id))
        existing_book = cursor.fetchone()

        if existing_book:
            cursor.execute("UPDATE cart_book SET amount = amount + 1 WHERE cart_id = %s AND book_id = %s", (cart_id, book_id))
        else:
            cursor.execute("INSERT INTO cart_book (cart_id, book_id, amount) VALUES (%s, %s, 1)", (cart_id, book_id))
        
        db.commit()
        flash('Книга успешно перемещена в корзину', 'success')
    except DatabaseError as e:
        flash("Ошибка перемещения книги в корзину: " + str(e), category="danger")
        db.rollback()
    finally:
        cursor.close()

    return redirect(url_for('cart'))



@app.route('/')
def index():
    genres = get_genres()
    new_books = get_new_books()
    popular_authors = get_popular_authors()
    return render_template('index.html', genres=genres, new_books=new_books, popular_authors=popular_authors)

@app.route('/cart', methods=['GET', 'POST'])
@login_required
def cart():
    user_id = current_user.id
    cart_items = get_cart_items(user_id)
    total_sum = sum(item['total'] for item in cart_items)
    user_info = {
        'user_name': current_user.user_name,
        'user_surname': current_user.user_surname,
        'email': current_user.email
    }
    return render_template('cart.html', cart_items=cart_items, total_sum=total_sum, user_info=user_info)

@app.route('/wishlist')
@login_required
def wishlist():
    user_id = current_user.id
    wishlist_items = get_wishlist_items(user_id)
    return render_template('wishlist.html', wishlist_items=wishlist_items)

@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    user_id = current_user.id
    user_name = request.form.get('user_name')
    user_surname = request.form.get('user_surname')
    email = request.form.get('email')
    address = request.form.get('address')
    payment_method = request.form.get('payment_method')
    
    try:
        db = db_connector.connect()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("INSERT INTO orders (user_id, user_name, user_surname, email, address, payment_method, date) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
            (user_id, user_name, user_surname, email, address, payment_method, datetime.now()))
        
        order_id = cursor.lastrowid
        
        cart_id = get_cart_id(user_id)
        
        if not cart_id:
            flash("Ошибка: корзина не найдена", 'danger')
            return redirect(url_for('cart'))

        cursor.execute("SELECT book_id, amount FROM cart_book WHERE cart_id = %s", (cart_id,))
        cart_items = cursor.fetchall()
        
        if not cart_items:
            flash("Ваша корзина пуста", 'danger')
            return redirect(url_for('cart'))
        
        for item in cart_items:
            book_id = item['book_id']
            amount = item['amount']
            
            cursor.execute("""
                INSERT INTO order_item (order_id, book_id, amount)
                VALUES (%s, %s, %s)
            """, (order_id, book_id, amount))
        
        cursor.execute("DELETE FROM cart_book WHERE cart_id = %s", (cart_id,))
        
        db.commit()
        flash('Заказ успешно оформлен', 'success')
        return redirect(url_for('index'))
    
    except DatabaseError as e:
        flash('Ошибка оформления заказа: ' + str(e), 'error')
        db.rollback()
    
    finally:
        cursor.close()
    
    return redirect(url_for('cart'))

def get_cart_id(user_id):
    try:
        db = db_connector.connect()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT cart_id FROM cart WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            return result['cart_id']
        else:
            return None
    except DatabaseError as e:
        flash("Ошибка получения ID корзины: " + str(e), 'danger')
        return None

@app.route('/checkout/gift_card_form', methods=['GET', 'POST'])
@login_required
def checkout_gift_card_form():
    if request.method == 'POST':
        return redirect(url_for('index')) 
    else:
        return render_template('gift_card_form.html')

@app.route('/checkout/gift_card', methods=['POST'])
@login_required
def checkout_gift_card():
    recipient_name = request.form['recipient_name']
    recipient_email = request.form['recipient_email']
    amount = request.form['amount']
    sender_id = current_user.id
    
    try:
        db = db_connector.connect()
        cursor = db.cursor()

        cursor.execute(
            "INSERT INTO gift_cards (sender_id, recipient_name, recipient_email, amount) VALUES (%s, %s, %s, %s)",
            (sender_id, recipient_name, recipient_email, amount)
        )

        db.commit()
        cursor.close()
        flash("Подарочная карта успешно оформлена", 'success')
        return redirect(url_for('index'))

    except DatabaseError as e:
        flash("Ошибка оформления подарочной карты: " + str(e), category="danger")
        return redirect(url_for('index'))

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')
    
    if query:
        results = []
        
        title_results = search_by_title(query)
        genre_results = search_by_genre(query)
        author_results = search_by_author(query)
        
        print(f"Title results: {title_results}")
        print(f"Genre results: {genre_results}")
        print(f"Author results: {author_results}")
        
        results.extend(title_results)
        results.extend(genre_results)
        results.extend(author_results)
        
        results = [dict(t) for t in {tuple(d.items()) for d in results}]
        
        print(f"Combined results: {results}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(results=results)
        else:
            return render_template('search_results.html', results=results, search_query=query)
    
    return render_template('search_results.html', results=[], search_query=query)

if __name__ == "__main__":
    app.run(debug=True)
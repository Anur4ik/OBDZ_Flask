import random
from datetime import datetime
import pytz
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, g, current_app, redirect, url_for, request, session, flash

app = Flask(__name__)
app.secret_key = 'super_secret_key'
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("CALL register_user_proc(%s, %s)", (request.form['username'], request.form['password']))
            conn.commit()
            return redirect(url_for('login'))
        except Exception as e: flash(str(e))
        finally: conn.close()
    return render_template('login.html', mode='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT id, username ,is_admin FROM users WHERE username=%s AND password=%s",
                        (request.form['username'], request.form['password']))
            user = cur.fetchone()
        conn.close()
        if user:
            session['user_id'], session['username'],session['is_admin']= user[0], user[1],user[2]
            return redirect(url_for('index'))
    return render_template('login.html', mode='login')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))
@app.route('/')
def index():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, title, poster_url, price FROM movies ORDER BY title;")
    movies_list = cur.fetchall()
    cur.execute("SELECT balance FROM users WHERE id=%s", (session['user_id'],))
    balance = cur.fetchone()[0]
    conn.close()
    return render_template('index.html', movies=movies_list, balance=balance, username=session['username'],is_admin=session.get('is_admin'))


@app.route('/admin/add_movie', methods=['GET', 'POST'])
def add_movie():
    if not session.get('is_admin'): return "Access Denied"

    if request.method == 'POST':
        conn = get_db()
        try:
            with conn.cursor() as cur:
                # Отримуємо дані з форми
                title = request.form['title']
                poster = request.form['poster_url']
                price = request.form['price']
                rows = request.form['rows']
                seats = request.form['seats']
                cur.execute("CALL add_movie_proc(%s, %s, %s, %s, %s)",
                            (title, poster, price, rows, seats))
            conn.commit()
            flash(f'Фільм "{title}" додано з залою {rows}x{seats}!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            conn.rollback()
            flash(str(e), 'error')
        finally:
            conn.close()

    return render_template('add_movie.html')


@app.route('/admin/delete_movie', methods=['POST'])
def delete_movie():
    # 1. Перевірка на адміна
    if 'user_id' not in session or not session.get('is_admin'):
        return "Тільки для адмінів!"

    movie_id = request.form['movie_id']

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("CALL delete_movie_proc(%s)", (movie_id,))
        conn.commit()
        flash('Фільм успішно видалено!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Помилка видалення: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('index'))
@app.route('/movie/<int:movie_id>')
def open_movie_hall(movie_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db();
    cur = conn.cursor()

    cur.execute("SELECT id, title, price FROM movies WHERE id = %s", (movie_id,))
    info = cur.fetchone()
    cur.execute("""
        SELECT s.id, s.row_num, s.seat_num, 
               CASE WHEN b.is_paid THEN 'sold' WHEN b.id IS NOT NULL THEN 'booked' ELSE 'free' END
        FROM seats s 
        LEFT JOIN bookings b ON s.id = b.seat_id AND b.movie_id = %s
        WHERE s.movie_id = %s  
        ORDER BY s.row_num, s.seat_num
    """, (movie_id, movie_id))

    seats = cur.fetchall()
    conn.close()
    return render_template('hall.html', seats=seats, info=info)
@app.route('/action', methods=['POST'])
def action():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor()
    try:
        proc = "book_seat_proc" if request.form['type'] == 'book' else "buy_ticket_proc"
        cur.execute(f"CALL {proc}(%s, %s, %s)", (session['user_id'], request.form['movie_id'], request.form['seat_id']))
        conn.commit()
        flash('Успішно!', 'success')
    except Exception as e:
        conn.rollback(); flash(str(e), 'error')
    finally: conn.close()
    return redirect(url_for('open_movie_hall', movie_id=request.form['movie_id']))

@app.route('/admin/dump')
def dump_db():
    if not session.get('is_admin'): return "Access Denied"
    conn = get_db();
    cur = conn.cursor()

    # Виводимо останні дії з аудит-лога
    cur.execute("SELECT details,action_type,log_time FROM audit_log ORDER BY log_time DESC LIMIT 20")
    logs = cur.fetchall()

    # Виводимо всі бронювання
    cur.execute("""
        SELECT u.username, m.title, s.seat_num, b.is_paid 
        FROM bookings b JOIN users u ON b.user_id=u.id 
        JOIN movies m ON b.movie_id=m.id JOIN seats s ON b.seat_id=s.id
    """)
    books = cur.fetchall()
    conn.close()

    # Простий HTML прямо тут, щоб не створювати файл
    html = "<h1>Audit Log</h1><pre>" + "\n".join([str(r) for r in logs]) + "</pre>"
    html += "<h1>Bookings</h1><pre>" + "\n".join([str(r) for r in books]) + "</pre>"
    html += "<a href='/'>Back</a>"
    return html
# @app.route("/dump")
# def dump_entries():
#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute('select id, date, title, content from entries order by date')
#     rows = cursor.fetchall()
#     output = ""
#     for r in rows:
#         debug(str(dict(r)))
#         output += str(dict(r))
#         output += "\n"
#     return "SQL dump below:\n<pre>" + output + "</pre>"

# def dump_entries():
#     conn = get_db()
#     cur = conn.cursor()
#     cur.execute("select * from entries")
#     rows = cur.fetchall()
#     print("Here are the entries:")
#     print(rows)

def connect_db():
    debug("Connecting to DB.")
    conn = psycopg2.connect(host="localhost", user="postgres", password="admin", dbname="cinema",
                            cursor_factory=psycopg2.extras.DictCursor)
    return conn

def get_db():
    if "db" not in g:
        g.db = connect_db()
    return g.db
@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
        debug("Closing DB")
@app.cli.command("init")
def init_db():
    conn = get_db()
    cur = conn.cursor()
    with current_app.open_resource("schema.sql") as file:
        alltext = file.read()
        cur.execute(alltext)
    conn.commit()
    print("Initialized the database.")
@app.cli.command('populate')
def populate_db():
    conn = get_db()
    cur = conn.cursor()
    with current_app.open_resource("populate.sql") as file:
        alltext = file.read()
        cur.execute(alltext)
    conn.commit()
    print("Populated DB with sample data.")
    # dump_entries()

def debug(s):
    if app.config['DEBUG']:
        print(s)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

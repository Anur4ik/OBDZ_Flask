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
            cur.execute("SELECT id, username FROM users WHERE username=%s AND password=%s",
                        (request.form['username'], request.form['password']))
            user = cur.fetchone()
        conn.close()
        if user:
            session['user_id'], session['username'] = user[0], user[1]
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

    return render_template('index.html', movies=movies_list, balance=balance, username=session['username'])

@app.route("/browse")
def browse():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('select id, date, title, content from entries order by date')
    rowlist = cursor.fetchall()
    return render_template('browse.html', entries=rowlist)

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
    conn = psycopg2.connect(host="localhost", user="postgres", password="postgres", dbname="cinema",
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

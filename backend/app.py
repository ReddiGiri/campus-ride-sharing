from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = "campusride"


@app.route('/', methods=['GET', 'POST'])
def home():
    if 'user' not in session:
        return redirect(url_for('login'))

    connection = sqlite3.connect('rides.db')
    cursor = connection.cursor()

    if request.method == 'POST':

        name = request.form['name']
        destination = request.form['destination']
        seats = int(request.form['seats'])

        cursor.execute(
            "INSERT INTO rides (username, name, destination, seats) VALUES (?, ?, ?, ?)",
            (session['user'], name, destination, seats)
        )

        connection.commit()

    search = request.args.get('search')

    if search:

        cursor.execute(
            "SELECT * FROM rides WHERE destination LIKE ?",
            ('%' + search + '%',)
        )

    else:

        cursor.execute("SELECT * FROM rides")

    rides = cursor.fetchall()

    connection.close()

    return render_template(
        'index.html',
        rides=rides,
        user=session.get('user')
    )


@app.route('/book/<int:ride_id>')
def book_ride(ride_id):

    connection = sqlite3.connect('rides.db')
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE rides SET seats = seats - 1 WHERE id = ? AND seats > 0",
        (ride_id,)
    )

    connection.commit()
    connection.close()

    return redirect('/')


@app.route('/delete/<int:ride_id>')
def delete_ride(ride_id):

    connection = sqlite3.connect('rides.db')
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM rides WHERE id = ? AND username = ?",
        (ride_id, session['user'])
    )

    connection.commit()
    connection.close()

    return redirect('/')


@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        connection = sqlite3.connect('rides.db')
        cursor = connection.cursor()

        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed_password)
        )

        connection.commit()
        connection.close()

        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        connection = sqlite3.connect('rides.db')
        cursor = connection.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )

        user = cursor.fetchone()

        connection.close()

        if user and check_password_hash(user[2], password):

            session['user'] = username

            if username == "admin":

                session['admin'] = True

            return redirect('/')
        else:

            return "Invalid Username or Password"

    return render_template('login.html')

@app.route('/admin')
def admin():

    if 'admin' not in session:
        return redirect('/')

    connection = sqlite3.connect('rides.db')
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM rides")

    rides = cursor.fetchall()

    connection.close()

    return render_template(
        'admin.html',
        rides=rides
    )


@app.route('/logout')
def logout():

    session.pop('user', None)

    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True)
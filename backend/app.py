from flask import Flask, render_template, request, redirect, session, send_from_directory, flash
from flask_socketio import SocketIO, join_room
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "secret123"

socketio = SocketIO(app, cors_allowed_origins="*")

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def connect_db():
    return sqlite3.connect("rides.db")


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@socketio.on("join")
def handle_join(data):
    username = data["username"]
    join_room(username)
    print(username, "joined socket room")


@app.route("/", methods=["GET", "POST"])
def home():

    if "user" not in session:
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor()

    if request.method == "POST":
        username = session["user"]
        name = request.form["name"]
        from_location = request.form["from_location"]
        destination = request.form["destination"]
        seats = request.form["seats"]
        time = request.form["time"]
        vehicle = request.form["vehicle"]
        phone = request.form["phone"]

        cursor.execute("""
            INSERT INTO rides
            (username, name, from_location, destination, seats, time, vehicle, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, name, from_location, destination, seats, time, vehicle, phone))

        conn.commit()

    search = request.args.get("search")

    if search:
        cursor.execute("""
            SELECT rides.id,
                   rides.username,
                   rides.name,
                   rides.from_location,
                   rides.destination,
                   rides.seats,
                   rides.time,
                   rides.vehicle,
                   rides.phone,
                   rides.rating,
                   users.image,
                   users.college_id
            FROM rides
            JOIN users ON rides.username = users.username
            WHERE rides.destination LIKE ?
            AND rides.seats > 0
            AND rides.completed = 0
        """, ('%' + search + '%',))
    else:
        cursor.execute("""
            SELECT rides.id,
                   rides.username,
                   rides.name,
                   rides.from_location,
                   rides.destination,
                   rides.seats,
                   rides.time,
                   rides.vehicle,
                   rides.phone,
                   rides.rating,
                   users.image,
                   users.college_id
            FROM rides
            JOIN users ON rides.username = users.username
            WHERE rides.seats > 0
            AND rides.completed = 0
        """)

    rides = cursor.fetchall()
    conn.close()

    return render_template("index.html", rides=rides, user=session["user"])


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        college_id = request.form["college_id"]
        email = request.form["email"]
        image = request.files["image"]

        if college_id.strip() == "" or email.strip() == "":
            return "College ID and College Email are required"

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return "Username already exists"

        image.save(os.path.join(app.config["UPLOAD_FOLDER"], image.filename))

        hashed_password = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO users (username, password, image, college_id, email)
            VALUES (?, ?, ?, ?, ?)
        """, (username, hashed_password, image.filename, college_id, email))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(user[2], password):
            session["user"] = username
            return redirect("/")
        else:
            return "Invalid username or password"

    return render_template("login.html")


@app.route("/profile")
def profile():

    if "user" not in session:
        return redirect("/login")

    username = session["user"]

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT username, image, college_id, email FROM users WHERE username=?",
        (username,)
    )
    user = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM rides WHERE username=?", (username,))
    total_rides = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM rides WHERE username=? AND completed=1", (username,))
    completed_rides = cursor.fetchone()[0]

    active_rides = total_rides - completed_rides

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        total_rides=total_rides,
        completed_rides=completed_rides,
        active_rides=active_rides
    )


@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():

    if "user" not in session:
        return redirect("/login")

    username = session["user"]

    conn = connect_db()
    cursor = conn.cursor()

    if request.method == "POST":
        email = request.form["email"]
        college_id = request.form["college_id"]
        image = request.files["image"]

        if image and image.filename != "":
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], image.filename))

            cursor.execute("""
                UPDATE users
                SET email=?, college_id=?, image=?
                WHERE username=?
            """, (email, college_id, image.filename, username))

        else:
            cursor.execute("""
                UPDATE users
                SET email=?, college_id=?
                WHERE username=?
            """, (email, college_id, username))

        conn.commit()
        conn.close()

        return redirect("/profile")

    cursor.execute(
        "SELECT username, image, college_id, email FROM users WHERE username=?",
        (username,)
    )

    user = cursor.fetchone()

    conn.close()

    return render_template("edit_profile.html", user=user)


@app.route("/myrides")
def myrides():

    if "user" not in session:
        return redirect("/login")

    username = session["user"]

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM rides WHERE username=? ORDER BY id DESC",
        (username,)
    )

    rides = cursor.fetchall()

    conn.close()

    return render_template("myrides.html", rides=rides)


@app.route("/mybookings")
def mybookings():

    if "user" not in session:
        return redirect("/login")

    passenger = session["user"]

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT rides.id,
               rides.username,
               rides.name,
               rides.from_location,
               rides.destination,
               rides.seats,
               rides.time,
               rides.vehicle,
               rides.phone,
               rides.rating,
               rides.completed
        FROM bookings
        JOIN rides ON bookings.ride_id = rides.id
        WHERE bookings.passenger=?
    """, (passenger,))

    my_rides = cursor.fetchall()

    conn.close()

    return render_template("mybookings.html", my_rides=my_rides)


@app.route("/book/<int:id>")
def book(id):

    if "user" not in session:
        return redirect("/login")

    passenger = session["user"]

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM bookings WHERE ride_id=? AND passenger=?",
        (id, passenger)
    )
    already_booked = cursor.fetchone()

    if already_booked:
        conn.close()
        flash("You already booked this ride")
        return redirect("/")

    cursor.execute("SELECT username, seats FROM rides WHERE id=?", (id,))
    ride = cursor.fetchone()

    if ride:
        ride_owner = ride[0]
        seats = ride[1]

        if passenger == ride_owner:
            conn.close()
            flash("You cannot book your own ride")
            return redirect("/")

        if seats > 0:
            cursor.execute(
                "UPDATE rides SET seats = seats - 1 WHERE id=?",
                (id,)
            )

            cursor.execute(
                "INSERT INTO bookings (ride_id, passenger) VALUES (?, ?)",
                (id, passenger)
            )

            conn.commit()

            socketio.emit(
                "booking_alert",
                {"message": passenger + " booked your ride 🚗"},
                room=ride_owner
            )

            flash("Ride booked successfully ✅")

    conn.close()

    return redirect("/")


@app.route("/cancel_booking/<int:ride_id>")
def cancel_booking(ride_id):

    if "user" not in session:
        return redirect("/login")

    passenger = session["user"]

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM bookings WHERE ride_id=? AND passenger=?",
        (ride_id, passenger)
    )

    if cursor.rowcount > 0:
        cursor.execute(
            "UPDATE rides SET seats = seats + 1 WHERE id=?",
            (ride_id,)
        )

    conn.commit()
    conn.close()

    return redirect("/mybookings")


@app.route("/complete_ride/<int:ride_id>")
def complete_ride(ride_id):

    if "user" not in session:
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE rides SET completed=1 WHERE id=? AND username=?",
        (ride_id, session["user"])
    )

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/delete/<int:id>")
def delete(id):

    if "user" not in session:
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM rides WHERE id=? AND username=?",
        (id, session["user"])
    )

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/rate/<int:id>/<int:value>")
def rate(id, value):

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE rides SET rating=? WHERE id=?",
        (value, id)
    )

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


@app.route("/admin")
def admin():

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    conn.close()

    return render_template("admin.html", users=users)


if __name__ == "__main__":
    socketio.run(app, debug=True)
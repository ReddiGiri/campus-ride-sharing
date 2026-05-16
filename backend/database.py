import sqlite3

connection = sqlite3.connect('rides.db')

cursor = connection.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS rides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    name TEXT,
    destination TEXT,
    seats INTEGER
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT
)
''')

connection.commit()

connection.close()

print("Database created successfully")
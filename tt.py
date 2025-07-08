import sqlite3

conn = sqlite3.connect('data/users.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT,
    password TEXT NOT NULL,
    name TEXT,
    avatar TEXT,
    is_verified INTEGER DEFAULT 0,
    category TEXT DEFAULT 'Без категорії',
    city TEXT,
    description TEXT,
    visible INTEGER DEFAULT 1,
    last_seen TEXT
)
''')

conn.commit()
conn.close()
print("✅ Таблиця users створена або вже існує.")

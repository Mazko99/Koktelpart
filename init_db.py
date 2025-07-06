import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT,
    receiver TEXT,
    message TEXT,
    room TEXT,
    media_urls TEXT,
    timestamp TEXT
);
""")

conn.commit()
conn.close()

print("✅ Таблиця messages створена або вже існує.")

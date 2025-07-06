import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE shared_messages ADD COLUMN sender TEXT")
    print("✅ Колонка 'sender' успішно додана.")
except sqlite3.OperationalError as e:
    print(f"⚠️ Помилка: {e}")

conn.commit()
conn.close()

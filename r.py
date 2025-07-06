import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

columns = {
    "reply_to_id": "INTEGER",
    "timestamp": "TEXT",
    "is_read": "INTEGER DEFAULT 0"
}

for column, column_type in columns.items():
    try:
        cursor.execute(f"ALTER TABLE messages ADD COLUMN {column} {column_type}")
        print(f"Колонка '{column}' успішно додана.")
    except sqlite3.OperationalError as e:
        print(f"Помилка або колонка '{column}' вже існує:", e)

conn.commit()
conn.close()

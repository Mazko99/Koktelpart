import sqlite3
import os

def get_db_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'users.db')

def ensure_message_columns():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(messages)")
    columns = [col[1] for col in cursor.fetchall()]

    columns_to_add = {
        "media_urls": "TEXT",
        "status": "TEXT",
        "reply_to": "TEXT",
        "timestamp": "TEXT"
    }

    for col, col_type in columns_to_add.items():
        if col not in columns:
            print(f"➕ Додаємо колонку: {col}")
            cursor.execute(f"ALTER TABLE messages ADD COLUMN {col} {col_type}")
        else:
            print(f"✅ Колонка вже є: {col}")

    conn.commit()
    conn.close()
    print("✅ Усі колонки перевірено. Готово!")

if __name__ == "__main__":
    ensure_message_columns()


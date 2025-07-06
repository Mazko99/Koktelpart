import sqlite3

# Підключення до бази
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Додаємо колонку sender, якщо вона ще не існує
try:
    cursor.execute("ALTER TABLE shared_messages ADD COLUMN sender TEXT")
    print("[+] Додано колонку 'sender'")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e) or "already exists" in str(e):
        print("[=] Колонка 'sender' вже існує")
    else:
        print("[!] Помилка при додаванні 'sender':", e)

# Додаємо колонку timestamp, якщо вона ще не існує
try:
    cursor.execute("ALTER TABLE shared_messages ADD COLUMN timestamp TEXT")
    print("[+] Додано колонку 'timestamp'")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e) or "already exists" in str(e):
        print("[=] Колонка 'timestamp' вже існує")
    else:
        print("[!] Помилка при додаванні 'timestamp':", e)

conn.commit()
conn.close()

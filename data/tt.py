import sqlite3

# Підключення до локальної бази
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Оновлення категорій
cursor.execute("""
    UPDATE users
    SET category = 'Індивідуалки – ' || TRIM(city)
    WHERE category = 'Індивідуалки' AND city IS NOT NULL AND city != ''
""")
conn.commit()

# Отримуємо результат
cursor.execute("SELECT id, username, category, city FROM users WHERE category LIKE 'Індивідуалки – %'")
rows = cursor.fetchall()

# Вивід результату
print("Оновлені користувачі:")
print("-" * 50)
for row in rows:
    print(f"ID: {row[0]} | Username: {row[1]} | Категорія: {row[2]} | Місто: {row[3]}")

conn.close()

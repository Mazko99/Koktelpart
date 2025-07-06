import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    verified INTEGER DEFAULT 0
)
''')

# Створимо тестових користувачів
users = [
    ('Петро Іванов', 'petro@example.com', 0),
    ('Марія Коваленко', 'maria@example.com', 1)
]
c.executemany('INSERT INTO users (name, email, verified) VALUES (?, ?, ?)', users)

conn.commit()
conn.close()
print("Базу даних створено!")

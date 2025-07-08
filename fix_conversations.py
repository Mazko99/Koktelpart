import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("SELECT sender, receiver, message FROM messages")
rows = cursor.fetchall()

if rows:
    for r in rows:
        print(f"ВІД: {r[0]} → ДО: {r[1]} | ТЕКСТ: {r[2]}")
else:
    print("❌ Повідомлень взагалі немає в базі.")

conn.close()

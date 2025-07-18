from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit, join_room
import sqlite3
import os
                

app = Flask(__name__)
app.secret_key = 'supersecretkey123'
app.permanent_session_lifetime = timedelta(days=7)
socketio = SocketIO(app)

def get_db():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'users.db')
    if not os.path.exists(db_path):
        raise FileNotFoundError("❌ База users.db не знайдена в папці data/")
    return sqlite3.connect(db_path)

def ensure_message_columns():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(messages)")
    columns = [col[1] for col in cursor.fetchall()]
    if "reply_to" not in columns:
        cursor.execute("ALTER TABLE messages ADD COLUMN reply_to TEXT")
    conn.commit()
    conn.close()

ensure_message_columns()


@app.before_request
def update_last_seen():
    session.permanent = True
    if "username" in session:
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET last_seen = ? WHERE username = ?", (datetime.utcnow().isoformat(), session["username"]))
        conn.commit()
        conn.close()

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    error = False

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['username'] = username
            if username == "admin" and password == "adminpass":
                return redirect(url_for('admin_panel'))
            return redirect('/home')
        else:
            message = 'Невірний логін або пароль'
            error = True
            return render_template('login.html',
                                   message=message,
                                   error=error,
                                   request=request)  # щоб значення залишались

    return render_template('login.html', request=request)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].lower()
        password = request.form['password']
        name = request.form['name']
        default_avatar = 'static/Sample_User_Icon.png'

        if 'admin' in username:
            return render_template('register.html', error='❌ Заборонено використовувати "admin" у логіні')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        if cursor.fetchone():
            conn.close()
            return render_template('register.html', error='❌ Користувач з таким логіном вже існує')
        
        cursor.execute("INSERT INTO users (username, password, name, avatar, is_verified) VALUES (?, ?, ?, ?, ?)",
                       (username, password, name, default_avatar, 0))
        conn.commit()
        conn.close()
        return render_template('register.html', success='✅ Акаунт створено! Тепер увійдіть.')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect('/login')
    return render_template('home.html', username=session['username'])

@app.route('/profiles')
def profiles():
    if 'username' not in session:
        return redirect('/login')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, name, avatar, is_verified FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template('profiles.html', users=users)

@app.route('/category/1')
def virtual_models():
    if 'username' not in session:
        return redirect('/login')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, avatar, username, is_verified FROM users WHERE category=? AND visible=1", ("Віртуальні моделі",))
    models = cursor.fetchall()
    conn.close()
    return render_template('virtual_models.html', models=models)

@app.route('/category/2')
def real_models():
    if 'username' not in session:
        return redirect('/login')

    selected_city = request.args.get('city')
    conn = get_db()
    cursor = conn.cursor()

    # Отримати список міст
    cursor.execute("""
        SELECT TRIM(city), COUNT(*) 
        FROM users 
        WHERE category LIKE 'Індивідуалки%' AND visible=1 AND city IS NOT NULL AND city != ''
        GROUP BY TRIM(city)
    """)
    cities_data = cursor.fetchall()

    if selected_city:
        cursor.execute("""
            SELECT id, name, avatar, TRIM(city), is_verified 
            FROM users 
            WHERE category LIKE 'Індивідуалки%' 
              AND visible=1 AND LOWER(TRIM(city)) = LOWER(?)
        """, (selected_city,))
    else:
        cursor.execute("""
            SELECT id, name, avatar, TRIM(city), is_verified 
            FROM users 
            WHERE category LIKE 'Індивідуалки%' 
              AND visible=1
        """)

    models = cursor.fetchall()
    conn.close()
    return render_template('category_real.html', models=models, cities=cities_data, selected_city=selected_city)


@app.route('/profile')
def my_profile():
    if 'username' not in session:
        return redirect('/login')
    return redirect(f"/profile/{session['username']}")

@app.route('/profile/<int:user_id>')
def profile_by_id(user_id):
    if 'username' not in session:
        return redirect('/login')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return "Користувача не знайдено", 404
    username = user[1]
    cursor.execute("SELECT id, title, description, price, image_filename, currency FROM products WHERE user_id=?", (user_id,))
    products = cursor.fetchall()
    conn.close()
    user_folder = os.path.join('static', 'uploads', username)
    photos = os.listdir(user_folder) if os.path.exists(user_folder) else []
    return render_template('profile.html', user=user, username=username, photos=photos, products=products)

@app.route('/profile/<username>')
def profile(username):
    if 'username' not in session:
        return redirect('/login')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return "Користувача не знайдено", 404
    cursor.execute("SELECT id FROM users WHERE username=?", (username,))
    user_id = cursor.fetchone()[0]
    cursor.execute("SELECT id, title, description, price, image_filename, currency FROM products WHERE user_id=?", (user_id,))
    products = cursor.fetchall()
    conn.close()
    user_folder = os.path.join('static', 'uploads', username)
    photos = os.listdir(user_folder) if os.path.exists(user_folder) else []
    return render_template('profile.html', user=user, username=username, photos=photos, products=products)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        return redirect('/login')

    username = session['username']
    description = request.form.get('description', '')
    category = request.form.get('category', 'Без категорії')
    city = request.form.get('city', '')
    visible = int(request.form.get('visible', 1))
    avatar_file = request.files.get('avatar')

    # Якщо категорія — індивідуалки, то додаємо місто до категорії
    if category == 'Індивідуалки' and city:
        full_category = f"Індивідуалки – {city}"
    else:
        full_category = category

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users SET description = ?, category = ?, city = ?, visible = ? 
        WHERE username = ?
    """, (description, full_category, city, visible, username))

    if avatar_file and avatar_file.filename:
        avatar_path = f"static/uploads/{username}_avatar.png"
        os.makedirs(os.path.dirname(avatar_path), exist_ok=True)
        avatar_file.save(avatar_path)
        cursor.execute("UPDATE users SET avatar = ? WHERE username = ?", (avatar_path, username))

    conn.commit()
    conn.close()

    return redirect(f"/profile/{username}")

@app.route('/upload_media', methods=['POST'])
def upload_media():
    if 'username' not in session:
        return redirect('/login')

    username = session['username']
    user_folder = os.path.join('static', 'uploads', username)
    os.makedirs(user_folder, exist_ok=True)

    uploaded_files = request.files.getlist('media_files')
    for file in uploaded_files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(user_folder, filename))

    return redirect(f"/profile/{username}")

@app.route('/delete_photo', methods=['POST'])
def delete_photo():
    if 'username' not in session:
        return redirect('/login')

    username = session['username']
    filename = request.form.get('filename')
    if not filename:
        return "Файл не вказано", 400

    file_path = os.path.join('static', 'uploads', username, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    return redirect(f"/profile/{username}")

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'username' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = request.form['price']
        currency = request.form['currency']
        user = session['username']

        # Отримати ID користувача
        cursor.execute("SELECT id FROM users WHERE username=?", (user,))
        user_id = cursor.fetchone()[0]

        # Завантаження фото
        image = request.files['image']
        if image:
            filename = secure_filename(image.filename)
            image_path = f"static/uploads/{user}/{filename}"
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image.save(image_path)
        else:
            filename = ""

        cursor.execute("""
            INSERT INTO products (user_id, title, description, price, image_filename, currency)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, title, description, price, filename, currency))
        conn.commit()
        conn.close()
        return redirect(f"/profile/{user}")

    return render_template('add_product.html')

@app.route('/delete_product', methods=['POST'])
def delete_product():
    if 'username' not in session:
        return redirect('/login')

    product_id = request.form.get('product_id')
    if not product_id:
        return "Missing product ID", 400

    conn = get_db()
    cursor = conn.cursor()

    # Отримуємо ім'я файлу зображення, щоб видалити його
    cursor.execute("SELECT image_filename FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    if row and row[0]:
        try:
            os.remove(row[0])
        except:
            pass

    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

    return redirect(f"/profile/{session['username']}")

@app.route('/shared_chat')
def shared_chat():
    if not session.get('username'):
        return redirect('/login')
    return render_template('shared_chat.html', username=session['username'])


@app.route('/admin/shared_chat')
def admin_shared_chat():
    if session.get('username') != 'admin':
        return redirect('/login')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, sender, text, reply_to, media_urls FROM shared_messages ORDER BY timestamp ASC")
    messages = [{"id": row[0], "sender": row[1], "text": row[2], "reply_to": row[3], "media_urls": row[4]} for row in cursor.fetchall()]
    conn.close()
    return render_template("admin/shared_chat.html", username=session['username'], messages=messages)

@app.route('/admin/delete_shared_message/<int:msg_id>')
def delete_shared_message(msg_id):
    if session.get('username') != 'admin':
        return redirect('/login')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shared_messages WHERE id=?", (msg_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_shared_chat'))

@app.route('/upload_media_chat', methods=['POST'])
def upload_media_chat():
    uploaded_files = request.files.getlist("files[]")
    urls = []
    username = session['username']
    folder = os.path.join("static", "chat_uploads", username)
    os.makedirs(folder, exist_ok=True)
    for file in uploaded_files:
        filename = secure_filename(file.filename)
        path = os.path.join(folder, filename)
        file.save(path)
        urls.append(f"/{path}")
    return jsonify({"urls": urls})

@socketio.on("join_shared")
def handle_join_shared():
    join_room("shared")

@socketio.on("send_shared")
def handle_send_shared(data):
    username = session.get("username", "Unknown")
    message = data.get("message", "")
    reply_to = data.get("reply_to", "")
    media_urls = ",".join(data.get("media_urls", []))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO shared_messages (sender, text, reply_to, media_urls, timestamp) VALUES (?, ?, ?, ?, ?)",
                   (username, message, reply_to, media_urls, datetime.utcnow()))
    conn.commit()
    conn.close()
    emit("receive_shared", {
        "username": username,
        "message": message,
        "reply_to": reply_to,
        "media_urls": data.get("media_urls", [])
    }, room="shared")
@app.route('/chat_with/<username>', methods=['GET', 'POST'])
def chat_with(username):
    if 'username' not in session:
        return redirect('/login')
    if username == session['username']:
        return redirect('/profile')

    # Функція для додавання відсутніх колонок
    def add_missing_columns():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(messages)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        if "media_urls" not in existing_columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN media_urls TEXT")
        if "status" not in existing_columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN status TEXT")
        if "reply" not in existing_columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN reply TEXT")
        if "timestamp" not in existing_columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN timestamp TEXT")
        conn.commit()
        conn.close()

    # Додаємо відсутні колонки, якщо треба
    add_missing_columns()

    conn = get_db()
    cursor = conn.cursor()

    # Перевірка чи існує користувач
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return "Користувача не знайдено", 404

    # Отримуємо всі повідомлення між двома користувачами
    cursor.execute("""
        SELECT sender, content, media_urls, status, reply
        FROM messages
        WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
        ORDER BY id ASC
    """, (session['username'], username, username, session['username']))
    messages = cursor.fetchall()
    conn.close()

    # Формуємо унікальну кімнату для двох
    room = "_".join(sorted([session['username'], username]))

    return render_template("private_chat.html",
                           username=username,
                           my_username=session['username'],
                           messages=messages,
                           room=room)

@app.route('/admin')
def admin_panel():
    if session.get('username') != 'admin':
        return redirect('/login')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, name, city, category, is_verified FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template('admin/index.html', users=users)

@app.route('/admin/add_user', methods=['GET', 'POST'])
def add_user():
    if session.get('username') != 'admin':
        return redirect('/login')
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO users (username, email, password, name, avatar, is_verified) VALUES (?, ?, ?, ?, ?, ?)",
                  (username, email, password, name, 'static/Sample_User_Icon.png', 0))
        conn.commit()
        conn.close()
        return redirect('/admin')
    return render_template('admin/add_user.html')

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if session.get('username') != 'admin':
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        cursor.execute("UPDATE users SET name = ?, password = ? WHERE id = ?", (name, password, user_id))
        conn.commit()
        conn.close()
        return redirect('/admin')

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    return render_template('admin/edit_user.html', user=user)

@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    if session.get('username') != 'admin':
        return redirect('/login')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/verify_user/<int:user_id>')
def verify_user(user_id):
    if session.get('username') != 'admin':
        return redirect('/login')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_verified=1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/unverify_user/<int:user_id>')
def unverify_user(user_id):
    if session.get('username') != 'admin':
        return redirect('/login')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_verified=0 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/chats')
def admin_chats():
    if session.get('username') != 'admin':
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT 
            CASE WHEN sender < receiver THEN sender ELSE receiver END AS user1,
            CASE WHEN sender > receiver THEN sender ELSE receiver END AS user2
        FROM messages
        WHERE sender != receiver
    """)
    pairs = cursor.fetchall()
    conn.close()

    return render_template("admin_chats.html", pairs=pairs)

@app.route('/admin/chat/<user1>/<user2>')
def admin_view_chat(user1, user2):
    if session.get('username') != 'admin':
        return redirect('/login')

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sender, content, media_urls, status, reply_to
        FROM messages
        WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
        ORDER BY id ASC
    """, (user1, user2, user2, user1))
    messages = cursor.fetchall()
    conn.close()

    return render_template("admin/admin_view_chat.html", user1=user1, user2=user2, messages=messages)

@app.route('/admin/messages')
def view_messages():
    if session.get('username') != 'admin':
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()
    
    # Витягуємо унікальні пари користувачів, які між собою спілкувались
    cursor.execute("""
        SELECT DISTINCT 
            CASE 
                WHEN sender < receiver THEN sender 
                ELSE receiver 
            END AS user1,
            CASE 
                WHEN sender < receiver THEN receiver 
                ELSE sender 
            END AS user2
        FROM messages
        WHERE sender != receiver
    """)
    dialogs = cursor.fetchall()
    conn.close()

    return render_template("admin/messages.html", dialogs=dialogs)

@socketio.on('join')
def handle_join(data):
    room = data['room']
    join_room(room)

@socketio.on('send_message')
def handle_send_message(data):
    sender = session.get('username')
    receiver = data['receiver']
    message = data['message']
    media_urls = ','.join(data.get('media_urls', [])) if data.get('media_urls') else None
    reply = data.get('reply')

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    room = data['room']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (sender, receiver, content, media_urls, status, reply_to, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (sender, receiver, message, media_urls, 'delivered', reply, timestamp))
    conn.commit()
    conn.close()

    emit('receive_message', {
        'username': sender,
        'message': message,
        'media_urls': data.get('media_urls', []),
        'reply': reply,
        'timestamp': timestamp
    }, room=room)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
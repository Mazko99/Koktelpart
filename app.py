from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit, join_room
import sqlite3, os

app = Flask(__name__)
app.secret_key = 'supersecretkey123'
app.permanent_session_lifetime = timedelta(days=7)
socketio = SocketIO(app)

def get_db():
    return sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.db'))

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
            if username == "admin" and password == "admin123":
                return redirect(url_for('admin_panel'))
            return redirect('/home')
        else:
            return render_template('login.html', error='Невірний логін або пароль')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        default_avatar = 'static/Sample_User_Icon.png'
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        if cursor.fetchone():
            conn.close()
            return render_template('register.html', error='Користувач вже існує.')
        cursor.execute("INSERT INTO users (username, password, name, avatar, is_verified) VALUES (?, ?, ?, ?, ?)",
                       (username, password, name, default_avatar, 0))
        conn.commit()
        conn.close()
        return redirect('/login')
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
    cursor.execute("""
        SELECT city, COUNT(*) 
        FROM users 
        WHERE (category='Реальні моделі' OR category='Індивідуалки') AND visible=1 
        GROUP BY city
    """)
    cities_data = cursor.fetchall()
    if selected_city:
        cursor.execute("""
            SELECT id, name, avatar, city, is_verified 
            FROM users 
            WHERE (category='Реальні моделі' OR category='Індивідуалки') 
              AND city=? AND visible=1
        """, (selected_city,))
    else:
        cursor.execute("""
            SELECT id, name, avatar, city, is_verified 
            FROM users 
            WHERE (category='Реальні моделі' OR category='Індивідуалки') 
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
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET description=?, category=?, city=?, visible=? WHERE username=?",
                   (description, category, city, visible, username))
    if avatar_file and avatar_file.filename:
        avatar_path = f"static/uploads/{username}_avatar.png"
        os.makedirs(os.path.dirname(avatar_path), exist_ok=True)
        avatar_file.save(avatar_path)
        cursor.execute("UPDATE users SET avatar=? WHERE username=?", (avatar_path, username))
    conn.commit()
    conn.close()
    return redirect(f"/profile/{username}")

@app.route('/shared_chat')
def shared_chat():
    if 'username' not in session:
        return redirect('/login')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, sender, text, reply_to, media_urls FROM shared_messages ORDER BY timestamp ASC")
    messages = [{"id": row[0], "sender": row[1], "text": row[2], "reply_to": row[3], "media_urls": row[4]} for row in cursor.fetchall()]
    conn.close()
    return render_template("shared_chat.html", username=session['username'], messages=messages)

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
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return "Користувача не знайдено", 404
    if request.method == 'POST':
        message = request.form.get('message', '')
        if message:
            cursor.execute("INSERT INTO messages (sender, receiver, content) VALUES (?, ?, ?)",
                           (session['username'], username, message))
            conn.commit()
    conn.close()
    return render_template('private_chat.html', username=session['username'], target_username=username)

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
        password = request.form['password']
        name = request.form['name']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password, name, avatar, is_verified) VALUES (?, ?, ?, ?, ?)",
                       (username, password, name, 'static/Sample_User_Icon.png', 0))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_panel'))
    return render_template('admin/add_user.html')

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if session.get('username') != 'admin':
        return redirect('/login')
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        city = request.form['city']
        cursor.execute("UPDATE users SET name=?, city=? WHERE id=?", (name, city, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_panel'))
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
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

@app.route('/admin/messages')
def view_messages():
    if session.get('username') != 'admin':
        return redirect('/login')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT sender, receiver, content FROM messages ORDER BY id DESC")
    messages = cursor.fetchall()
    conn.close()
    return render_template('admin/messages.html', messages=messages)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

@app.before_first_request
def create_admin_if_not_exists():
    conn = get_db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, name TEXT, avatar TEXT, is_verified INTEGER DEFAULT 0, last_seen TEXT)")
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, name, avatar, is_verified) VALUES (?, ?, ?, ?, ?)",
                  ('admin', 'admin123', 'Адміністратор', 'static/Sample_User_Icon.png', 1))
        conn.commit()
    conn.close()

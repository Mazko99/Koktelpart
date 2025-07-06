from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3

admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates')

# 🔌 Підключення до БД
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# 🔒 Захист усіх маршрутів адмінки
@admin_bp.before_request
def restrict_admin():
    allowed_routes = ['admin.login', 'admin.logout']
    if not session.get("is_admin") and request.endpoint not in allowed_routes:
        return redirect(url_for("admin.login"))

# 🔐 Вхід
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            session['is_admin'] = True
            return redirect(url_for('admin.index'))
        else:
            flash("Невірний логін або пароль", "danger")
    return render_template('admin/login.html')

# 🚪 Вихід
@admin_bp.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin.login'))

# 🏠 Головна: список користувачів
@admin_bp.route('/')
def index():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return render_template('admin/index.html', users=users)

# ➕ Додавання користувача
@admin_bp.route('/add', methods=('GET', 'POST'))
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
            (username, email, password)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('admin.index'))
    return render_template('admin/add.html')

# ✏️ Редагування користувача
@admin_bp.route('/edit/<int:id>', methods=('GET', 'POST'))
def edit_user(id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (id,)).fetchone()
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        conn.execute(
            'UPDATE users SET username = ?, email = ? WHERE id = ?',
            (username, email, id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('admin.index'))
    conn.close()
    return render_template('admin/edit.html', user=user)

# 🗑️ Видалення користувача
@admin_bp.route('/delete/<int:id>')
def delete_user(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin.index'))

# ✅ Верифікація
@admin_bp.route('/verify/<int:id>')
def verify_user(id):
    conn = get_db_connection()
    conn.execute('UPDATE users SET is_verified = 1 WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin.index'))

# ❌ Зняти верифікацію
@admin_bp.route('/unverify/<int:id>')
def unverify_user(id):
    conn = get_db_connection()
    conn.execute('UPDATE users SET is_verified = 0 WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin.index'))

# 💬 Перелік діалогів
@admin_bp.route('/messages')
def messages():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT 
            CASE WHEN sender < receiver THEN sender ELSE receiver END AS user1,
            CASE WHEN sender < receiver THEN receiver ELSE sender END AS user2
        FROM private_messages
        ORDER BY user1, user2
    """)
    dialogs = cursor.fetchall()
    conn.close()
    return render_template('admin/messages.html', dialogs=dialogs)

# 📬 Перегляд діалогу
@admin_bp.route('/messages/<user1>/<user2>')
def view_dialog(user1, user2):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT rowid, sender, msg FROM private_messages
        WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)
        ORDER BY rowid ASC
    """, (user1, user2, user2, user1))
    messages = cursor.fetchall()
    conn.close()
    return render_template('admin/view_dialog.html', user1=user1, user2=user2, messages=messages)

# ❌ Видалення повідомлення з особистого чату
@admin_bp.route('/delete_message/<int:msg_id>', methods=['POST'])
def delete_private_message(msg_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM private_messages WHERE rowid = ?', (msg_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('admin.messages'))

# 🌐 Перегляд спільного чату
@admin_bp.route('/shared')
def shared():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, sender, message, media_urls, timestamp FROM shared_messages ORDER BY id DESC")
    messages = cursor.fetchall()
    conn.close()
    return render_template('admin/shared.html', messages=messages)

# ❌ Видалення повідомлення зі спільного чату
@admin_bp.route('/delete_shared/<int:msg_id>', methods=['POST'])
def delete_shared(msg_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM shared_messages WHERE id = ?', (msg_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin.shared'))

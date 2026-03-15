from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from database import register_user, login_user
import hashlib
import secrets
import datetime
import sqlite3

app = Flask(__name__)
CORS(app)

# Главная страница - перенаправляем на регистрацию
@app.route('/')
def index():
    return render_template('signup.html')

# Страница регистрации
@app.route('/signup')
def signup_page():
    return render_template('signup.html')

# Страница входа
@app.route('/signin')
def signin_page():
    return render_template('signin.html')

# Страница профиля (dashboard)
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Обработка регистрации
@app.route('/register', methods=['POST'])
def register():
    try:
        # Получаем данные из формы
        data = request.form
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        # Валидация на сервере
        if not username or len(username) < 3:
            return jsonify({
                'success': False,
                'error': 'Имя пользователя должно быть минимум 3 символа'
            }), 400
            
        if not email or '@' not in email:
            return jsonify({
                'success': False,
                'error': 'Введите корректный email'
            }), 400
            
        if not password or len(password) < 8:
            return jsonify({
                'success': False,
                'error': 'Пароль должен быть минимум 8 символов'
            }), 400
        
        # Регистрируем пользователя
        result = register_user(username, email, password, "пусто")
        
        if result:
            # Получаем ID нового пользователя
            conn = sqlite3.connect('test.db')
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM users WHERE email = ?", (email,))
            user_id = cur.fetchone()[0]
            
            # Создаем токен
            token = hashlib.sha256(f"{user_id}{secrets.token_hex(8)}".encode()).hexdigest()
            
            # Создаем таблицу сессий если ее нет
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Устанавливаем срок действия (30 дней)
            expires = datetime.datetime.now() + datetime.timedelta(days=30)
            
            # Удаляем старые сессии этого пользователя
            cur.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            
            # Сохраняем новый токен
            cur.execute(
                "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user_id, token, expires)
            )
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Регистрация успешна!',
                'user': {
                    'username': username,
                    'email': email
                },
                'token': token,
                'user_id': user_id
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Этот email уже занят или произошла ошибка базы данных'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Обработка входа
@app.route('/login', methods=['POST'])
def login():
    try:
        # Получаем данные из формы
        data = request.form
        
        email = data.get('email')
        password = data.get('password')
        remember = data.get('remember') == 'true'
        
        # Валидация на сервере
        if not email or '@' not in email:
            return jsonify({
                'success': False,
                'error': 'Введите корректный email'
            }), 400
            
        if not password:
            return jsonify({
                'success': False,
                'error': 'Введите пароль'
            }), 400
        
        # Проверяем логин
        user_id = login_user(email, password)
        
        if user_id:
            # Создаем токен
            token = hashlib.sha256(f"{user_id}{secrets.token_hex(8)}".encode()).hexdigest()
            
            # Сохраняем токен в базу данных сессий
            conn = sqlite3.connect('test.db')
            cur = conn.cursor()
            
            # Создаем таблицу сессий если ее нет
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Устанавливаем срок действия
            if remember:
                expires = datetime.datetime.now() + datetime.timedelta(days=30)
            else:
                expires = datetime.datetime.now() + datetime.timedelta(days=1)
            
            # Удаляем старые сессии этого пользователя
            cur.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            
            # Сохраняем новый токен
            cur.execute(
                "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user_id, token, expires)
            )
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Вход выполнен успешно!',
                'user_id': user_id,
                'token': token
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Неверный email или пароль'
            }), 401
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Получение данных пользователя
@app.route('/user/<int:user_id>')
def get_user(user_id):
    # Проверяем токен в заголовке
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'success': False, 'error': 'Токен не предоставлен'}), 401
    
    # Проверяем токен в базе
    conn = sqlite3.connect('test.db')
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id FROM sessions WHERE token = ? AND expires_at > ?",
        (token, datetime.datetime.now())
    )
    session = cur.fetchone()
    
    if not session or session[0] != user_id:
        conn.close()
        return jsonify({'success': False, 'error': 'Недействительный токен'}), 401
    
    # Получаем данные пользователя
    cur.execute(
        "SELECT user_nickname, email FROM users WHERE user_id = ?",
        (user_id,)
    )
    user = cur.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'success': True,
            'username': user[0],
            'email': user[1],
            'user_id': user_id
        })
    else:
        return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

# Проверка токена
@app.route('/check-auth', methods=['GET'])
def check_auth():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'authenticated': False}), 401
    
    conn = sqlite3.connect('test.db')
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id FROM sessions WHERE token = ? AND expires_at > ?",
        (token, datetime.datetime.now())
    )
    session = cur.fetchone()
    conn.close()
    
    if session:
        return jsonify({'authenticated': True, 'user_id': session[0]})
    else:
        return jsonify({'authenticated': False}), 401

# Запуск сервера
if __name__ == '__main__':
    app.run(debug=True, port=5000)
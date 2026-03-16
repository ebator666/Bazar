from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from database import register_user, login_user, save_session, get_user_token, create_db
import hashlib
import secrets
import datetime

app = Flask(__name__)
CORS(app)

#создаем бд
create_db()
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
            #получаем айди из бд
            user_id = login_user(email, password)
            
            if user_id:
                #генерируем токен
                token = hashlib.sha256(f"{user_id}{secrets.token_hex(8)}".encode()).hexdigest()
                
                save_session(user_id, token, 30)
                
                return jsonify({
                    'success': True,
                    'message': 'Регистрация успешна!',
                    'user_id': user_id,
                    'token': token,
                    'user': {
                        'username': username,
                        'email': email
                    }
                }), 200
        
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
            remember = request.form.get('remember') == 'true'
            days = 30 if remember else 1

            # Создаем токен
            token = hashlib.sha256(f"{user_id}{secrets.token_hex(8)}".encode()).hexdigest()
            
            # сохраняем сессию
            if save_session(user_id, token, days):   
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
    
    #возвращаем жанные пользователя, если токен совпадает и не просрочен
    user_data = get_user_token(token)
    
    if user_data:
        # Сравниваем ID из токена (user_data[0]) с ID из URL (user_id)
        if user_data[0] == user_id:
            return jsonify({
                'success': True,
                'username': user_data[1],
                'email': user_data[2],
                'user_id': user_data[0]
            })
        else:
            return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403
            
    return jsonify({'success': False, 'error': 'Сессия истекла или неверна'}), 401

# Проверка токена
@app.route('/check-auth', methods=['GET'])
def check_auth():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'authenticated': False}), 401
    
    #возвращаем данные пользователя, если токен совпадает и не просрочен
    user_data = get_user_token(token)
    
    if user_data:
        return jsonify({'authenticated': True, 'user_id': user_data[0]}), 200
    else:
        return jsonify({'authenticated': False}), 401

# Запуск сервера
if __name__ == '__main__':
    app.run(debug=True, port=5000)
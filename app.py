from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from database import (
    register_user, login_user, save_session, get_user_token, create_db,
    create_ad, get_user_ads, get_ad_by_id, update_ad, delete_ad,
    add_photo, get_ad_photos, delete_ad_photos, PHOTO_FOLDER,
    get_all_ads, get_ad_with_seller
)
import hashlib
import secrets
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Настройки загрузки фото
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = PHOTO_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

create_db()

# ============= СТРАНИЦЫ =============

@app.route('/')
def index():
    return render_template('marketplace.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/signin')
def signin_page():
    return render_template('signin.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/ad/<int:ad_id>')
def ad_detail(ad_id):
    return render_template('ad_detail.html', ad_id=ad_id)

# ============= API МАРШРУТЫ =============

# Получение всех объявлений для главной страницы
@app.route('/api/all-ads', methods=['GET'])
def get_all_ads_route():
    try:
        ads = get_all_ads()
        result = []
        for ad in ads:
            photos = get_ad_photos(ad[0])
            first_photo = photos[0][1] if photos else None
            
            result.append({
                'id': ad[0],
                'title': ad[1],
                'price': ad[2],
                'description': ad[3],
                'category': ad[4],
                'seller_name': ad[5],
                'created_at': ad[6],
                'first_photo': first_photo
            })
        return jsonify({'success': True, 'ads': result})
    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Получение детальной информации об объявлении
@app.route('/api/ad/<int:ad_id>', methods=['GET'])
def get_ad_detail_route(ad_id):
    try:
        ad = get_ad_with_seller(ad_id)
        if not ad:
            return jsonify({'success': False, 'error': 'Объявление не найдено'}), 404
        
        photos = get_ad_photos(ad_id)
        photo_list = [{'id': p[0], 'url': p[1], 'order': p[2]} for p in photos]
        
        return jsonify({
            'success': True,
            'ad': {
                'id': ad[0],
                'title': ad[1],
                'price': ad[2],
                'description': ad[3],
                'category': ad[4],
                'seller_id': ad[5],
                'seller_name': ad[6],
                'seller_email': ad[7],
                'seller_geolocation': ad[8],
                'created_at': ad[9],
                'photos': photo_list
            }
        })
    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Получение объявлений пользователя
@app.route('/api/ads', methods=['GET'])
def get_ads():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401
    
    user_data = get_user_token(token)
    if not user_data:
        return jsonify({'success': False, 'error': 'Сессия истекла'}), 401
    
    ads = get_user_ads(user_data[0])
    
    result = []
    for ad in ads:
        photos = get_ad_photos(ad[0])
        first_photo = photos[0][1] if photos else None
        
        result.append({
            'id': ad[0],
            'title': ad[1],
            'price': ad[2],
            'description': ad[3],
            'category': ad[4],
            'created_at': ad[5],
            'first_photo': first_photo
        })
    
    return jsonify({'success': True, 'ads': result})

# Получение фото объявления
@app.route('/api/ads/<int:ad_id>/photos', methods=['GET'])
def get_ad_photos_route(ad_id):
    photos = get_ad_photos(ad_id)
    result = [{'id': p[0], 'url': p[1], 'order': p[2]} for p in photos]
    return jsonify({'success': True, 'photos': result})

# Создание объявления
@app.route('/api/ads', methods=['POST'])
def create_ad_route():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401
    
    user_data = get_user_token(token)
    if not user_data:
        return jsonify({'success': False, 'error': 'Сессия истекла'}), 401
    
    title = request.form.get('title', '').strip()
    price = request.form.get('price')
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()
    
    if not title or len(title) < 3:
        return jsonify({'success': False, 'error': 'Название должно быть минимум 3 символа'}), 400
    
    if not price or not str(price).isdigit() or int(price) <= 0:
        return jsonify({'success': False, 'error': 'Введите корректную цену'}), 400
    
    if not category:
        return jsonify({'success': False, 'error': 'Выберите категорию'}), 400
    
    ad_id = create_ad(
        user_data[0],
        user_data[3] or "не указана",
        title,
        int(price),
        description,
        category
    )
    
    if not ad_id:
        return jsonify({'success': False, 'error': 'Ошибка при создании объявления'}), 500
    
    uploaded_photos = []
    files = request.files.getlist('photos')
    
    for i, file in enumerate(files[:5]):
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            photo_url = f"/uploads/{filename}"
            add_photo(ad_id, photo_url, i)
            uploaded_photos.append(photo_url)
    
    return jsonify({
        'success': True,
        'message': 'Объявление создано!',
        'ad': {'id': ad_id, 'title': title, 'price': price}
    }), 201

# Обновление объявления
@app.route('/api/ads/<int:ad_id>', methods=['PUT'])
def update_ad_route(ad_id):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401
    
    user_data = get_user_token(token)
    if not user_data:
        return jsonify({'success': False, 'error': 'Сессия истекла'}), 401
    
    ad = get_ad_by_id(ad_id)
    if not ad or ad[1] != user_data[0]:
        return jsonify({'success': False, 'error': 'Объявление не найдено'}), 404
    
    data = request.json
    title = data.get('title', '').strip()
    price = data.get('price')
    description = data.get('description', '').strip()
    category = data.get('category', '').strip()
    
    if not title or len(title) < 3:
        return jsonify({'success': False, 'error': 'Название должно быть минимум 3 символа'}), 400
    
    if not price or not str(price).isdigit() or int(price) <= 0:
        return jsonify({'success': False, 'error': 'Введите корректную цену'}), 400
    
    if not category:
        return jsonify({'success': False, 'error': 'Выберите категорию'}), 400
    
    if update_ad(ad_id, title, int(price), description, category):
        return jsonify({'success': True, 'message': 'Объявление обновлено!'})
    
    return jsonify({'success': False, 'error': 'Ошибка при обновлении'}), 500

# Удаление объявления
@app.route('/api/ads/<int:ad_id>', methods=['DELETE'])
def delete_ad_route(ad_id):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401
    
    user_data = get_user_token(token)
    if not user_data:
        return jsonify({'success': False, 'error': 'Сессия истекла'}), 401
    
    photos = get_ad_photos(ad_id)
    for photo in photos:
        try:
            filename = photo[1].split('/')[-1]
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass
    
    if delete_ad(ad_id, user_data[0]):
        return jsonify({'success': True, 'message': 'Объявление удалено!'})
    
    return jsonify({'success': False, 'error': 'Объявление не найдено'}), 404

# Проверка токена
@app.route('/check-auth', methods=['GET'])
def check_auth():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'authenticated': False}), 401
    
    user_data = get_user_token(token)
    
    if user_data:
        return jsonify({'authenticated': True, 'user_id': user_data[0]})
    return jsonify({'authenticated': False}), 401

# Получение данных пользователя
@app.route('/user/<int:user_id>')
def get_user(user_id):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'success': False, 'error': 'Токен не предоставлен'}), 401
    
    user_data = get_user_token(token)
    
    if user_data and user_data[0] == user_id:
        return jsonify({
            'success': True,
            'username': user_data[1],
            'email': user_data[2],
            'geolocation': user_data[3],
            'user_id': user_data[0]
        })
    
    return jsonify({'success': False, 'error': 'Сессия истекла или неверна'}), 401

# Обработка регистрации
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.form
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or len(username) < 3:
            return jsonify({'success': False, 'error': 'Имя пользователя должно быть минимум 3 символа'}), 400
            
        if not email or '@' not in email:
            return jsonify({'success': False, 'error': 'Введите корректный email'}), 400
            
        if not password or len(password) < 8:
            return jsonify({'success': False, 'error': 'Пароль должен быть минимум 8 символов'}), 400
        
        result = register_user(username, email, password, "не указана")
        
        if result:
            user_id = login_user(email, password)
            
            if user_id:
                token = hashlib.sha256(f"{user_id}{secrets.token_hex(8)}".encode()).hexdigest()
                save_session(user_id, token, 30)
                
                return jsonify({
                    'success': True,
                    'message': 'Регистрация успешна!',
                    'user_id': user_id,
                    'token': token,
                    'user': {'username': username, 'email': email}
                }), 200
        
        return jsonify({'success': False, 'error': 'Этот email уже занят'}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Обработка входа
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.form
        email = data.get('email')
        password = data.get('password')
        remember = data.get('remember') == 'true'

        if not email or '@' not in email:
            return jsonify({'success': False, 'error': 'Введите корректный email'}), 400
            
        if not password:
            return jsonify({'success': False, 'error': 'Введите пароль'}), 400
        
        user_id = login_user(email, password)
        
        if user_id:
            days = 30 if remember else 1
            token = hashlib.sha256(f"{user_id}{secrets.token_hex(8)}".encode()).hexdigest()
            
            if save_session(user_id, token, days):   
                return jsonify({
                    'success': True,
                    'message': 'Вход выполнен успешно!',
                    'user_id': user_id,
                    'token': token
                }), 200
        
        return jsonify({'success': False, 'error': 'Неверный email или пароль'}), 401
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Раздача загруженных фото
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
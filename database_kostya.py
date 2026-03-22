import bcrypt
import sqlite3 as sq
import datetime

def create_db():
    with sq.connect("test.db", check_same_thread=False) as con:
        cur = con.cursor()
        cur.execute("PRAGMA foreign_keys = ON")

        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_nickname TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            user_geolocation TEXT NOT NULL
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS ads (
            ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            seller_geolocation TEXT NOT NULL,
            title TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            image_path TEXT DEFAULT 'default.jpg',
            FOREIGN KEY (seller_id) REFERENCES users (user_id)
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )""")

def register_user(nickname, email, password, geo):
    if len(password) < 8:
            print("Слишком короткий пароль. Минимум 8 символов")
            return False
            
    if len(password) > 24:
        print("Слишком длинный пароль. Максимум 24 символа")
        return False
        
    if "@" not in email or "." not in email:
        print("Ошибка: Почта введена неверно.")
        return False
        
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            hash = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(password.encode("UTF-8"), hash)
            cur.execute("INSERT INTO users (user_nickname, email, password, user_geolocation) VALUES (?, ?, ?, ?)", (nickname, email, hashed_password, geo))
            con.commit()
            print(f"Пользователь {nickname} добавлен в базу данных")
            return True
    
    except sq.IntegrityError:
        print("Ошибка: почта занята другим пользователем")
        return False

def login_user(email, password):
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON") 
            cur.execute("SELECT user_id, password FROM users WHERE email = ?", (email,))
            result = cur.fetchone()
            if result is not None:
                if bcrypt.checkpw(password.encode("UTF-8"), result[1]):
                    print("Вы успешно авторизировались!")
                    return result[0]
                else:
                    print("Ошибка: Неверный логин или пароль.")
                    return False
            else:
                print("Ошибка: Неверный логин или пароль.")
                return False
            
    except sq.Error as e:
        print(f"Ошибка: {e}")
        return False

def save_session(user_id, token, days = 30):
    try:
        expires = datetime.datetime.now() + datetime.timedelta(days=30)
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            cur.execute("INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",(user_id, token, expires))
            con.commit()
            return True
    except sq.Error as e:
        print(f"Ошибка сохранения сессии: {e}")
        return False
    
def get_user_token(token):
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute("SELECT user_id FROM sessions WHERE token = ? AND expires_at > ?",(token, datetime.datetime.now()))
            session = cur.fetchone()
            if session:
                cur.execute("SELECT user_nickname, email FROM users WHERE user_id = ?", (session[0],))
                user = cur.fetchone()
                return (session[0], user[0], user[1])
            return None
    except sq.Error:
        return None

def create_ad(seller_id, seller_geolocation, title, price, description, category, image_path="default.jpg"):
    if not title or len(title) < 3 or len(title) > 50:
        print("Ошибка: название товара должно быть от 3 до 50 символов")
        return False
    
    if price < 0:
        print("Ошибка: цена не может быть отрицательной")
        return False
    
    if len(description) < 10:
        print("Ошибка: описание слишком короткое")
        return False

    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute("INSERT INTO ads (seller_id, seller_geolocation, title, price, description, category, image_path) VALUES (?, ?, ?, ?, ?, ?, ?)", 
            (seller_id, seller_geolocation, title, price, description, category, image_path))
            con.commit()
            
            print(f"Объявление '{title}' успешно создано.")
            return True
            
    except sq.Error as e:
        print(f"Ошибка базы данных: {e}")
        return False 

def delete_ad(ad_id, user_id):
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute("DELETE FROM ads WHERE ad_id = ? AND seller_id = ?", (ad_id, user_id))
            con.commit()

            if cur.rowcount > 0:
                print(f"Объявление {ad_id} удалено владельцем {user_id}")
                return True
            else:
                print(f"Объявление {ad_id} не найдено или доступ запрещен")
                return False
        
    except sq.Error as e:
        print(f"Ошибка при удалении: {e}")
        return False

def update_ad(ad_id, user_id, title, price, description, category, image_path="default.jpg"):
    if not title or price < 0 or len(description) < 10:
        print("Ошибка валидации: проверьте корректность данных")
        return False

    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute("UPDATE ads SET title = ?, price = ?, description = ?, category = ?, image_path = ? WHERE ad_id = ? AND seller_id = ?", 
            (title, price, description, category, image_path, ad_id, user_id))
            con.commit()

            if cur.rowcount > 0:
                print(f"Объявление {ad_id} успешно обновлено")
                return True
            else:
                print("Ошибка: объявление не найдено или у вас нет прав на его редактирование")
                return False
                
    except sq.Error as e:
        print(f"Ошибка базы данных при обновлении: {e}")
        return False

def get_user_ads(user_id):
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON") 
            cur.execute("SELECT * FROM ads WHERE seller_id = ? ORDER BY ad_id DESC", (user_id,))
            
            return cur.fetchall() 
            
    except sq.Error as e:
        print(f"Ошибка при получении объявлений: {e}")
        return []

def get_all_ads():
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute("SELECT * FROM ads ORDER BY ad_id DESC")

            return cur.fetchall()
            
    except sq.Error as e:
        print(f"Ошибка при получении всех объявлений: {e}")
        return []

def get_one_ad(ad_id):
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute("SELECT * FROM ads WHERE ad_id = ?", (ad_id,))

            return cur.fetchone()
        
    except sq.Error as e:
        print(f"Ошибка при получении объявления {ad_id}: {e}")
        return None
    
create_db()
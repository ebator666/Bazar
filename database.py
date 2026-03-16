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
            description TEXT,
            category TEXT NOT NULL,
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
            cur.execute("SELECT user_id FROM sessions WHERE token = ? AND expires_at > ?",(token, datetime.datetime.now()))
            session = cur.fetchone()
            if session:
                cur.execute("SELECT user_nickname, email FROM users WHERE user_id = ?", (session[0],))
                user = cur.fetchone()
                return (session[0], user[0], user[1])
            return None
    except sq.Error:
        return None
    

create_db()

        





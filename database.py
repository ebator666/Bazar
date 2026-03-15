import bcrypt
import sqlite3 as sq

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

create_db()

        





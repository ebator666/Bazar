import bcrypt
import sqlite3 as sq
import datetime
import os

PHOTO_FOLDER = 'static/uploads'
os.makedirs(PHOTO_FOLDER, exist_ok=True)

def create_db():
    with sq.connect("test.db", check_same_thread=False) as con:
        cur = con.cursor()
        cur.execute("PRAGMA foreign_keys = ON")

        # Таблица пользователей
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_nickname TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            user_geolocation TEXT NOT NULL,
            age INTEGER,
            direction TEXT,
            student_group TEXT,
            dormitory TEXT,
            phone TEXT
        )""")

        # Таблица КАТЕГОРИЙ (главное изменение)
        cur.execute("""CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            parent_id INTEGER REFERENCES categories(id),
            type TEXT NOT NULL  -- goods, housing, services, exchange, study, work, transport, events
        )""")

        # Таблица объявлений (ссылка на категорию, не строка)
        cur.execute("""CREATE TABLE IF NOT EXISTS ads (
            ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL,
            seller_geolocation TEXT NOT NULL,
            title TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT,
            category_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (seller_id) REFERENCES users (user_id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE RESTRICT
        )""")

        # Таблица фото объявлений
        cur.execute("""CREATE TABLE IF NOT EXISTS ad_photos (
            photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_id INTEGER NOT NULL,
            photo_url TEXT NOT NULL,
            order_num INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ad_id) REFERENCES ads (ad_id) ON DELETE CASCADE
        )""")
#  НОВАЯ ТАБЛИЦА profile_photos 
        cur.execute("""
            CREATE TABLE IF NOT EXISTS profile_photos (
                photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                original_name TEXT,
                mime_type TEXT,
                size INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        # Таблица сессий
        cur.execute("""CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )""")

def create_initial_categories():
    parents = [
        ("Товары", "goods", "goods"),
        ("Жильё", "housing", "housing"),
        ("Услуги", "services", "services"),
        ("Обмен", "exchange", "exchange"),
        ("Учеба", "study", "study"),
        ("Работа / Подработка", "work", "work"),
        ("Транспорт", "transport", "transport"),
        ("События", "events", "events"),
    ]

    children = {
        "goods": [
            ("Техника", "electronics"),
            ("Одежда", "clothes"),
            ("Мебель", "furniture"),
            ("Книги", "books"),
            ("Другое", "other"),
        ],
        "housing": [
            ("Поиск соседей", "search_roommate"),
            ("Аренда комнаты", "room_rent"),
        ],
        "services": [
            ("Репетиторство", "tutoring"),
            ("Программирование", "programming"),
            ("Помощь с курсовыми", "coursework_help"),
        ],
        "exchange": [
            ("Обмен вещами", "item_exchange"),
            ("Отдам даром", "giveaway"),
        ],
        "study": [
            ("Конспекты", "notes"),
            ("Учебники", "textbooks"),
            ("Подготовка к экзаменам", "exam_prep"),
        ],
        "work": [
            ("Стажировки", "internship"),
            ("Волонтёрство", "volunteer"),
            ("Вакансии", "vacancy"),
        ],
        "transport": [
            ("Авто", "car"),
            ("Велосипеды", "bicycle"),
        ],
        "events": [
            ("Мероприятия", "event"),
            ("Студклубы", "club"),
        ],
    }

    with sq.connect("test.db", check_same_thread=False) as con:
        cur = con.cursor()
        cur.execute("PRAGMA foreign_keys = ON")

        for name, slug, cat_type in parents:
            cur.execute(
                "INSERT OR IGNORE INTO categories (name, slug, parent_id, type) VALUES (?, ?, ?, ?)",
                (name, slug, None, cat_type),
            )

        con.commit()

        cur.execute("SELECT id, slug FROM categories WHERE parent_id IS NULL")
        parent_rows = cur.fetchall()
        parent_map = {slug: cat_id for cat_id, slug in parent_rows}

        for parent_slug, items in children.items():
            parent_id = parent_map.get(parent_slug)
            if not parent_id:
                continue
            for name, slug in items:
                cur.execute(
                    "INSERT OR IGNORE INTO categories (name, slug, parent_id, type) VALUES (?, ?, ?, ?)",
                    (name, slug, parent_id, parent_slug),
                )

        con.commit()  

# Создаем папку для фото
PHOTO_FOLDER = 'static/uploads'
os.makedirs(PHOTO_FOLDER, exist_ok=True)


# ============= ФУНКЦИИ РЕГИСТРАЦИИ И ВХОДА =============

def register_user(nickname, email, password, geo):
    """Регистрация нового пользователя"""
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
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(password.encode("UTF-8"), salt)
            cur.execute("""INSERT INTO users (user_nickname, email, password, user_geolocation) 
                           VALUES (?, ?, ?, ?)""", 
                       (nickname, email, hashed_password, geo))
            con.commit()
            print(f"Пользователь {nickname} добавлен в базу данных")
            return True
    
    except sq.IntegrityError:
        print("Ошибка: почта занята другим пользователем")
        return False
    except Exception as e:
        print(f"Ошибка регистрации: {e}")
        return False


def login_user(email, password):
    """Вход пользователя, возвращает user_id или False"""
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


# ============= ФУНКЦИИ СЕССИЙ =============

def save_session(user_id, token, days=30):
    """Сохраняет токен сессии в БД"""
    try:
        expires = datetime.datetime.now() + datetime.timedelta(days=days)
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            # Удаляем старые сессии этого пользователя
            cur.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            cur.execute("""INSERT INTO sessions (user_id, token, expires_at) 
                           VALUES (?, ?, ?)""", 
                       (user_id, token, expires))
            con.commit()
            return True
    except sq.Error as e:
        print(f"Ошибка сохранения сессии: {e}")
        return False

def get_user_token(token):
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("""SELECT user_id FROM sessions 
                           WHERE token = ? AND expires_at > ?""",
                        (token, datetime.datetime.now()))
            session = cur.fetchone()
            if session:
                user_id = session[0]
                cur.execute("""SELECT user_nickname, email, user_geolocation, 
                                      age, direction, student_group, dormitory, phone
                               FROM users WHERE user_id = ?""",
                            (user_id,))
                user = cur.fetchone()
                if user:
                    # user = (nickname, email, geo, age, direction, student_group, dormitory, phone)
                    return (user_id, *user)   # возвращает: (id, name, email, geo, age, ...)
                return None
            return None
    except sq.Error:
        return None


# ============= ФУНКЦИИ ДЛЯ РАБОТЫ С ОБЪЯВЛЕНИЯМИ =============

def create_ad(seller_id, seller_geolocation, title, price, description, category_id):
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute("""
                INSERT INTO ads (seller_id, seller_geolocation, title, price, description, category_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (seller_id, seller_geolocation, title, price, description, category_id))
            con.commit()
            return cur.lastrowid
    except sq.Error as e:
        print(f"Ошибка создания объявления: {e}")
        return None


def get_user_ads(user_id):
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("""
                SELECT 
                    a.ad_id, a.title, a.price, a.description,
                    c.name AS category_name,
                    COALESCE(a.created_at, datetime('now')) as created_at
                FROM ads a
                JOIN categories c ON a.category_id = c.id
                WHERE a.seller_id = ?
                ORDER BY a.created_at DESC
            """, (user_id,))
            return cur.fetchall()
    except sq.Error as e:
        print(f"Ошибка получения объявлений: {e}")
        return []


def get_all_ads():
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("""
                SELECT 
                    a.ad_id, a.title, a.price, a.description,
                    c.name AS category_name, c.slug AS category_slug, c.type AS category_type,
                    u.user_nickname AS seller_name,
                    COALESCE(a.created_at, datetime('now')) AS created_at
                FROM ads a
                JOIN categories c ON a.category_id = c.id
                JOIN users u ON a.seller_id = u.user_id
                ORDER BY a.created_at DESC
            """)
            return cur.fetchall()
    except sq.Error as e:
        print(f"Ошибка получения всех объявлений: {e}")
        return []


def get_ad_by_id(ad_id):
    """Получает объявление по ID"""
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("""
                SELECT 
                    a.ad_id,
                    a.seller_id,
                    a.title,
                    a.price,
                    a.description,
                    a.category_id,
                    c.name AS category_name,
                    c.slug AS category_slug,
                    c.type AS category_type,
                    COALESCE(a.created_at, datetime('now')) AS created_at
                FROM ads a
                JOIN categories c ON a.category_id = c.id
                WHERE a.ad_id = ?
            """, (ad_id,))
            return cur.fetchone()
    except sq.Error as e:
        print(f"Ошибка получения объявления: {e}")
        return None


def get_ad_with_seller(ad_id):
    """Получает объявление с данными продавца"""
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("""
                SELECT 
                    a.ad_id,
                    a.title,
                    a.price,
                    a.description,
                    a.category_id,
                    c.name AS category_name,
                    c.slug AS category_slug,
                    c.type AS category_type,
                    a.seller_id,
                    u.user_nickname,
                    u.email,
                    u.user_geolocation,
                    COALESCE(a.created_at, datetime('now')) AS created_at
                FROM ads a
                JOIN users u ON a.seller_id = u.user_id
                JOIN categories c ON a.category_id = c.id
                WHERE a.ad_id = ?
            """, (ad_id,))
            return cur.fetchone()
    except sq.Error as e:
        print(f"Ошибка получения объявления с продавцом: {e}")
        return None


def update_ad(ad_id, title, price, description, category_id):
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("""
                UPDATE ads
                SET title = ?, price = ?, description = ?, category_id = ?
                WHERE ad_id = ?
            """, (title, price, description, category_id, ad_id))
            con.commit()
            return cur.rowcount > 0
    except sq.Error as e:
        print(f"Ошибка обновления объявления: {e}")
        return False


def delete_ad(ad_id, seller_id):
    """Удаляет объявление (фото удаляются каскадно)"""
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            # Фото удалятся автоматически из-за ON DELETE CASCADE
            cur.execute("DELETE FROM ads WHERE ad_id = ? AND seller_id = ?", (ad_id, seller_id))
            con.commit()
            return cur.rowcount > 0
    except sq.Error as e:
        print(f"Ошибка удаления объявления: {e}")
        return False


# ============= ФУНКЦИИ ДЛЯ РАБОТЫ С ФОТО =============

def add_photo(ad_id, photo_url, order_num):
    """Добавляет фото к объявлению"""
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO ad_photos (ad_id, photo_url, order_num)
                VALUES (?, ?, ?)
            """, (ad_id, photo_url, order_num))
            con.commit()
            return cur.lastrowid
    except sq.Error as e:
        print(f"Ошибка добавления фото: {e}")
        return None


def get_ad_photos(ad_id):
    """Получает все фото объявления"""
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("""
                SELECT photo_id, photo_url, order_num
                FROM ad_photos
                WHERE ad_id = ?
                ORDER BY order_num ASC
            """, (ad_id,))
            return cur.fetchall()
    except sq.Error as e:
        print(f"Ошибка получения фото: {e}")
        return []


def delete_ad_photos(ad_id):
    """Удаляет все фото объявления"""
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("DELETE FROM ad_photos WHERE ad_id = ?", (ad_id,))
            con.commit()
            return True
    except sq.Error as e:
        print(f"Ошибка удаления фото: {e}")
        return False


#  функции:
def update_user_profile(user_id, nickname, email, age=None, direction=None, student_group=None, dormitory=None, phone=None):
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("""
                UPDATE users
                SET user_nickname = ?,
                    email = ?,
                    age = ?,
                    direction = ?,
                    student_group = ?,
                    dormitory = ?,
                    phone = ?
                WHERE user_id = ?
            """, (nickname, email, age, direction, student_group, dormitory, phone, user_id))
            con.commit()
            return cur.rowcount > 0
    except Exception as e:
        print("DB Error update_user_profile:", e)
        return False



def get_profile_photo(user_id):
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("SELECT filename FROM profile_photos WHERE user_id = ? ORDER BY photo_id DESC LIMIT 1", (user_id,))
            result = cur.fetchone()
            return f"/uploads/{result[0]}" if result else None
    except:
        return None

def add_profile_photo(user_id, filename, original_name, mime_type, size):
    try:
        with sq.connect("test.db", check_same_thread=False) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO profile_photos (user_id, filename, original_name, mime_type, size)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, filename, original_name, mime_type, size))
            con.commit()
        return True
    except:
        return False

# Инициализация
create_db()
print("✅ База данных инициализирована")

# Создаём начальные категории (1 раз при запуске)
create_initial_categories()
print("✅ Начальные категории созданы")
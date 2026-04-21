import express from "express";
import sqlite3 from "sqlite3";
import cors from "cors";
import session from "express-session";
import path from "path";
import fs from "fs";
import fileUpload from "express-fileupload"; // npm install express-fileupload

const app = express();
app.use(express.json());
app.use(cors({ origin: "*" }));
app.use(
  session({
    secret: "profile-secret",
    resave: false,
    saveUninitialized: false,
  }),
);

//  ФАЙЛЫ (multer аналог)
app.use(
  fileUpload({
    createParentPath: true,
    limits: { fileSize: 5 * 1024 * 1024 }, // 5MB
    abortOnLimit: true,
  }),
);

app.use(express.static("public"));

app.get("/", (req, res) => {
  res.sendFile(path.resolve("public/profile.html"));
});

const db = new sqlite3.Database("users.db");

//  ТАБЛИЦЫ
db.run(`CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  name TEXT, age TEXT, student_group TEXT, direction TEXT,
  dormitory TEXT, phone TEXT, email TEXT
)`);

db.run(`CREATE TABLE IF NOT EXISTS profile_photos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER DEFAULT 1,
  filename TEXT NOT NULL,
  original_name TEXT,
  mime_type TEXT,
  size INTEGER,
  uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
)`);

//  Создаем папку uploads
const UPLOAD_DIR = path.join(process.cwd(), "public", "uploads");
fs.mkdirSync(UPLOAD_DIR, { recursive: true });

//  PROFILE с ФОТО
app.get("/api/profile", (req, res) => {
  db.get("SELECT * FROM users WHERE id=1", (err, user) => {
    if (err) return res.status(500).json({ error: err.message });

    const profile = user || {
      id: 1,
      name: "",
      age: "",
      student_group: "",
      direction: "",
      dormitory: "",
      phone: "",
      email: "",
    };

    //  Получаем последнее фото
    db.get(
      "SELECT filename FROM profile_photos WHERE user_id=1 ORDER BY uploaded_at DESC LIMIT 1",
      (err, photo) => {
        profile.profile_photo = photo ? `/uploads/${photo.filename}` : null;
        res.json(profile);
      },
    );
  });
});

//  UPDATE ПРОФИЛЬ
app.patch("/api/profile", (req, res) => {
  const { name, age, student_group, direction, dormitory, phone, email } =
    req.body;

  db.run(
    `UPDATE users SET name=?, age=?, student_group=?, direction=?, 
     dormitory=?, phone=?, email=? WHERE id=1`,
    [name, age, student_group, direction, dormitory, phone, email],
    function (err) {
      if (err) return res.status(500).json({ error: err.message });

      if (this.changes === 0) {
        db.run(
          `INSERT INTO users (id, name, age, student_group, direction, dormitory, phone, email)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?)`,
          [name, age, student_group, direction, dormitory, phone, email],
          function (err2) {
            if (err2) return res.status(500).json({ error: err2.message });
            return res.json({ success: true, created: true });
          },
        );
      } else {
        db.get("SELECT * FROM users WHERE id=1", (err2, row) => {
          res.json({ success: true, updated: true, profile: row });
        });
      }
    },
  );
});

//  ЗАГРУЗКА ФОТО
app.post("/api/profile/photo", (req, res) => {
  if (!req.files || !req.files.photo) {
    return res.status(400).json({ error: "Нет файла" });
  }

  const file = req.files.photo;

  // Безопасное имя файла
  const filename = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}-${file.name}`;
  const filepath = path.join(UPLOAD_DIR, filename);

  //  Сохраняем файл
  file.mv(filepath, (err) => {
    if (err) return res.status(500).json({ error: err.message });

    //  Сохраняем в БД
    db.run(
      `INSERT INTO profile_photos (user_id, filename, original_name, mime_type, size)
       VALUES (1, ?, ?, ?, ?)`,
      [filename, file.name, file.mimetype, file.size],
      function (err) {
        if (err) return res.status(500).json({ error: err.message });
        res.json({
          success: true,
          photo_url: `/uploads/${filename}`,
          id: this.lastID,
        });
      },
    );
  });
});

app.listen(3000, () => console.log(" Backend: http://localhost:3000"));

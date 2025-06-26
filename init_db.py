import sqlite3

# 建立或連接到 SQLite 資料庫檔案 app.db
conn = sqlite3.connect("app.db")
cursor = conn.cursor()

# 1. 使用者表
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# 2. 目標表（每人兩個目標）
cursor.execute('''
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    goal_text TEXT,
    tone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')

# 3. 每日回報 check-in 表
cursor.execute('''
CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    goal_id INTEGER,
    date DATE,
    completed BOOLEAN,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(goal_id) REFERENCES goals(id)
)
''')

# 4. 對話記錄表
cursor.execute('''
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    goal_id INTEGER,
    tone TEXT,
    email TEXT,
    user_input TEXT,
    gpt_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(goal_id) REFERENCES goals(id)
)
''')

conn.commit()
conn.close()

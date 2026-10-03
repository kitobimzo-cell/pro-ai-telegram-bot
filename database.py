import sqlite3

DB_NAME = "bot_memory.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # История сообщений с привязкой к пользователю
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            user_name TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # База пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            PRIMARY KEY (chat_id, user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def save_user(chat_id, user_id, username="", first_name=""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (chat_id, user_id, username, first_name)
        VALUES (?, ?, ?, ?)
    ''', (chat_id, user_id, username or "", first_name or ""))
    conn.commit()
    conn.close()

def add_message(chat_id, user_id, user_name, role, content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO chat_history (chat_id, user_id, user_name, role, content)
        VALUES (?, ?, ?, ?, ?)
    ''', (chat_id, user_id, user_name, role, content))
    conn.commit()
    conn.close()

def get_chat_history(chat_id, limit=6):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_name, role, content FROM chat_history 
        WHERE chat_id = ? 
        ORDER BY id DESC LIMIT ?
    ''', (chat_id, limit))
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for user_name, role, content in reversed(rows):
        prefix = f"[{user_name}]: " if role == "user" and user_name else ""
        history.append({"role": role, "parts": [{"text": f"{prefix}{content}"}]})
    return history

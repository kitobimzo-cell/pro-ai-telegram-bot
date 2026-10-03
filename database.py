import sqlite3

DB_NAME = "bot_memory.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Suhbatlar xotirasi (Context)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Foydalanuvchilar va guruhlar ro'yxati
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            chat_type TEXT,
            username TEXT,
            first_name TEXT,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_user(chat_id, chat_type, username="", first_name=""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (chat_id, chat_type, username, first_name)
        VALUES (?, ?, ?, ?)
    ''', (chat_id, chat_type, username, first_name))
    conn.commit()
    conn.close()

def add_message(chat_id, role, content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO chat_history (chat_id, role, content)
        VALUES (?, ?, ?)
    ''', (chat_id, role, content))
    conn.commit()
    conn.close()

def get_chat_history(chat_id, limit=6):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT role, content FROM chat_history 
        WHERE chat_id = ? 
        ORDER BY id DESC LIMIT ?
    ''', (chat_id, limit))
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for role, content in reversed(rows):
        history.append({"role": role, "parts": [{"text": content}]})
    return history

import sqlite3

DB_NAME = "bot_memory.db"

def get_connection():
    # timeout=20.0 ma'lumotlar bazasi band bo'lganda 20 soniya kutishga imkon beradi
    conn = sqlite3.connect(DB_NAME, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;") # Baza tezligini oshiradi
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            PRIMARY KEY (chat_id, user_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            user_name TEXT,
            role TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_user(chat_id, user_id, username, first_name):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (chat_id, user_id, username, first_name)
            VALUES (?, ?, ?, ?)
        ''', (chat_id, user_id, username, first_name))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB save_user error: {e}")

def add_message(chat_id, user_id, user_name, role, message):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chat_history (chat_id, user_id, user_name, role, message)
            VALUES (?, ?, ?, ?, ?)
        ''', (chat_id, user_id, user_name, role, message))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB add_message error: {e}")

def get_chat_history(chat_id, limit=6):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_name, role, message FROM chat_history
            WHERE chat_id = ?
            ORDER BY id DESC LIMIT ?
        ''', (chat_id, limit))
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in reversed(rows):
            u_name, role, text = row
            if role == "user":
                history.append({"role": "user", "parts": [{"text": f"[{u_name}]: {text}"}]})
            else:
                history.append({"role": "model", "parts": [{"text": text}]})
        return history
    except Exception as e:
        print(f"DB get_chat_history error: {e}")
        return []

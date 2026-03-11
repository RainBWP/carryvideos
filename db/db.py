import sqlite3
import hashlib
import os

# db folder
DB_DIR = "db"
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

DB_PATH = os.path.join(DB_DIR, 'bot_database.db')
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    is_whitelisted INTEGER DEFAULT 0,
                    download_count INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    url TEXT,
                    file_size_bytes INTEGER,
                    sha256 TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id))''')
    
    conn.commit()
    conn.close()

def check_user(user_id: int, username: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT is_whitelisted FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (user_id, username, is_whitelisted) VALUES (?, ?, 0)", (user_id, username))
        conn.commit()
        authorized = False
    else:
        c.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
        conn.commit()
        authorized = bool(row[0])
    conn.close()
    return authorized

def record_download(user_id: int, url: str, filepath: str):
    size = os.path.getsize(filepath)
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    sha = sha256_hash.hexdigest()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO downloads (user_id, url, file_size_bytes, sha256) VALUES (?, ?, ?, ?)", (user_id, url, size, sha))
    c.execute("UPDATE users SET download_count = download_count + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_user_to_whitelist(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET is_whitelisted = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
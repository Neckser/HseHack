import sqlite3
import os

DB_PATH = "tiktok.db"

def init():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        avatar_color TEXT DEFAULT '#ff0050',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS videos (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        video_url TEXT NOT NULL,
        thumbnail_url TEXT,
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        shares INTEGER DEFAULT 0,
        duration INTEGER DEFAULT 60,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS video_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        video_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, video_id),
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (video_id) REFERENCES videos (id)
    )
    ''')
    
    # ========================
    # ТАБЛИЦА КОММЕНТАРИЕВ
    # ========================
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        video_id TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (video_id) REFERENCES videos (id)
    )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hashtags (
            video_id TEXT,
            tag TEXT
        )
    ''')
    
    # Создаем демо-пользователя
    cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (1, 'hacker')")
    
    # Создаем демо-видео если их нет
    cursor.execute("SELECT COUNT(*) FROM videos")
    if cursor.fetchone()[0] == 0:
        demo_videos = [
            ('vid1', 1, 'Горы', 'Красивый закат', 
             'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4'),
            ('vid2', 1, 'Котик', 'Смешной котик',
             'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4'),
            ('vid3', 1, 'Путешествие', 'Япония',
             'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4')
        ]
        
        cursor.executemany("""
            INSERT INTO videos (id, user_id, title, description, video_url, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now', ?))
        """, [
            (vid_id, uid, title, desc, url, f'-{i} hours') 
            for i, (vid_id, uid, title, desc, url) in enumerate(demo_videos)
        ])
        
        # Добавляем демо хештеги
        demo_hashtags = [
            ('vid1', 'горы'),
            ('vid1', 'закат'),
            ('vid2', 'котик'),
            ('vid2', 'животные'),
            ('vid3', 'путешествия'),
            ('vid3', 'япония')
        ]
        cursor.executemany("INSERT INTO hashtags (video_id, tag) VALUES (?, ?)", demo_hashtags)
    
    connection.commit()
    connection.close()
    print("✅ База данных инициализирована")



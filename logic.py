import sqlite3
from typing import List, Dict
import database

DB_PATH = database.DB_PATH

def _rows_to_video_list(rows, user_id=None) -> List[Dict]:
    videos = []
    for row in rows:
        v = dict(row)
        # удаляем хештеги
        v.pop('hashtags_list', None)

        # author info
        v['author'] = {
            'id': v.get('user_id'),
            'username': v.get('author_username') or f'user{v.get("user_id")}',
            'avatar_color': v.get('author_avatar') or '#ff0050'
        }

        # liked_by_user
        if user_id:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM video_likes WHERE user_id=? AND video_id=?", (user_id, v['id']))
            v['liked_by_user'] = bool(cur.fetchone())
            conn.close()
        else:
            v['liked_by_user'] = False

        videos.append(v)
    return videos


def get_all_videos():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            v.*,
            u.username as author_username,
            u.avatar_color as author_avatar
        FROM videos v
        LEFT JOIN users u ON v.user_id=u.id
        ORDER BY v.created_at DESC
    """)

    rows = cur.fetchall()
    conn.close()
    return _rows_to_video_list(rows)


def get_video_by_id(video_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            v.*,
            u.username as author_username,
            u.avatar_color as author_avatar
        FROM videos v
        LEFT JOIN users u ON v.user_id=u.id
        WHERE v.id=?
    """, (video_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return _rows_to_video_list([row])[0]


def like_video(video_id, user_id=1):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id FROM videos WHERE id=?", (video_id,))
    if not cur.fetchone():
        conn.close()
        return {"error": "Video not found"}

    cur.execute("SELECT 1 FROM video_likes WHERE user_id=? AND video_id=?", (user_id, video_id))
    if cur.fetchone():
        cur.execute("DELETE FROM video_likes WHERE user_id=? AND video_id=?", (user_id, video_id))
        liked = False
    else:
        cur.execute("INSERT INTO video_likes (user_id, video_id) VALUES (?,?)", (user_id, video_id))
        liked = True

    conn.commit()
    conn.close()
    return {"liked": liked}


def get_liked_videos(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            v.*,
            u.username as author_username,
            u.avatar_color as author_avatar
        FROM videos v
        JOIN video_likes vl ON vl.video_id=v.id AND vl.user_id=?
        LEFT JOIN users u ON v.user_id=u.id
        ORDER BY v.created_at DESC
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()
    return _rows_to_video_list(rows, user_id=user_id)

import sqlite3
from typing import List, Dict
import database

DB_PATH = database.DB_PATH

def _rows_to_video_list(rows, user_id=None) -> List[Dict]:
    videos = []
    for row in rows:
        v = dict(row)
        hashtags_str = v.pop('hashtags_list', '')
        v['hashtags'] = hashtags_str.split(',') if hashtags_str else []
        # author fields may be None if user missing; provide defaults
        v['author'] = {
            'id': v.get('user_id'),
            'username': v.pop('author_username', f'user{v.get("user_id")}'),
            'avatar_color': v.pop('author_avatar', '#ff0050')
        }

        # добавляем liked_by_user
        if user_id is not None:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM video_likes WHERE user_id = ? AND video_id = ?", (user_id, v['id']))
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
            u.avatar_color as author_avatar,
            GROUP_CONCAT(h.tag) as hashtags_list
        FROM videos v
        LEFT JOIN users u ON v.user_id = u.id
        LEFT JOIN hashtags h ON v.id = h.video_id
        GROUP BY v.id
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
            u.avatar_color as author_avatar,
            GROUP_CONCAT(h.tag) as hashtags_list
        FROM videos v
        LEFT JOIN users u ON v.user_id = u.id
        LEFT JOIN hashtags h ON v.id = h.video_id
        WHERE v.id = ?
        GROUP BY v.id
    """, (video_id,))

    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return _rows_to_video_list([row])[0]


def like_video(video_id, user_id=1):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id FROM videos WHERE id = ?", (video_id,))
    if not cur.fetchone():
        conn.close()
        return {"error": "Video not found"}

    cur.execute("SELECT 1 FROM video_likes WHERE user_id = ? AND video_id = ?", (user_id, video_id))
    if cur.fetchone():
        # убрать лайк
        cur.execute("DELETE FROM video_likes WHERE user_id = ? AND video_id = ?", (user_id, video_id))
        cur.execute("UPDATE videos SET likes = MAX(likes - 1, 0) WHERE id = ?", (video_id,))
        liked = False
    else:
        cur.execute("INSERT INTO video_likes (user_id, video_id) VALUES (?, ?)", (user_id, video_id))
        cur.execute("UPDATE videos SET likes = likes + 1 WHERE id = ?", (video_id,))
        liked = True

    cur.execute("SELECT likes FROM videos WHERE id = ?", (video_id,))
    res = cur.fetchone()
    likes = res[0] if res else 0

    conn.commit()
    conn.close()

    return {"liked": liked, "likes": likes}


def increment_views(video_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE videos SET views = views + 1 WHERE id = ?", (video_id,))
    conn.commit()
    conn.close()
    return True

def get_liked_videos(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            v.*,
            u.username as author_username,
            u.avatar_color as author_avatar,
            GROUP_CONCAT(h.tag) as hashtags_list
        FROM videos v
        LEFT JOIN users u ON v.user_id = u.id
        LEFT JOIN hashtags h ON v.id = h.video_id
        GROUP BY v.id
        ORDER BY v.created_at DESC
    """)

    rows = cur.fetchall()
    conn.close()

    # только те видео, которые лайкнул пользователь
    videos = _rows_to_video_list(rows, user_id=user_id)
    liked_videos = [v for v in videos if v['liked_by_user']]
    return liked_videos


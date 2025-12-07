import os
import random
import subprocess
import time
import json
import uuid
import sqlite3

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import database


# =========================
# НАСТРОЙКИ
# =========================

DOWNLOAD_DIR = r"D:\2\rutube_clips"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

HEADLESS = True
CLIP_DURATION_SEC = 10
MAX_START_SEC = 60

MIN_RUTUBE_CLIPS = 25
MAX_RUTUBE_CLIPS = 50
FETCH_INTERVAL = 5

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =========================
# SELENIUM (НОВАЯ ВЕРСИЯ)
# =========================

def create_driver():
    opts = Options()
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    if HEADLESS:
        opts.add_argument("--headless=new")

    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=opts)  # <---- Selenium Manager сам найдёт chromedriver
    return driver


# =========================
# ГЛАВНАЯ RUTUBE → video_id
# =========================

def get_video_ids(driver):
    driver.get("https://rutube.ru/")
    print("[*] Открыта главная Rutube...")

    try:
        videos = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR,
                 "a.wdp-link-module__link.wdp-card-poster-module__posterWrapper")
            )
        )
    except Exception:
        print("[-] Не удалось найти карточки видео")
        return []

    ids = []
    for v in videos:
        href = v.get_attribute("href")
        if href and "/video/" in href:
            ids.append(href.split("/video/")[1].split("/")[0])

    print(f"[+] Найдено {len(ids)} видео")
    return ids


# =========================
# NETWORK → m3u8 / mp4
# =========================

def find_stream_url_in_logs(driver):
    logs = driver.get_log("performance")

    for entry in logs:
        try:
            msg = json.loads(entry["message"])["message"]
            if msg.get("method") != "Network.responseReceived":
                continue

            response = msg.get("params", {}).get("response", {})
            url = response.get("url", "")
            mime = response.get("mimeType", "").lower()

            if ".m3u8" in url:
                return url

            if url.endswith(".mp4") or mime == "video/mp4":
                return url

        except:
            pass

    return None


def get_stream_url_for_video(driver, video_id):
    url = f"https://rutube.ru/video/{video_id}/"
    print(f"\n[*] Открываю видео: {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "video, div[data-player]"))
        )
    except:
        pass

    time.sleep(3)

    stream = find_stream_url_in_logs(driver)
    if stream:
        print(f"[+] Поток найден: {stream}")
    else:
        print("[-] Не нашли поток")

    return stream


# =========================
# FFmpeg режет 10 секунд
# =========================

def cut_clip(stream_url, video_id):
    start = random.randint(0, MAX_START_SEC)
    out = os.path.join(DOWNLOAD_DIR, f"{video_id}_clip.mp4")

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-t", str(CLIP_DURATION_SEC),
        "-i", stream_url,
        "-c", "copy",
        out
    ]

    print("[FFMPEG]", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
        print(f"[+] Клип сохранён {out}")
        return out
    except:
        print("[-] Ошибка ffmpeg")
        return None


# =========================
# БД
# =========================

def get_rutube_count():
    database.init()
    conn = sqlite3.connect(database.DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*)
        FROM videos v
        JOIN hashtags h ON v.id = h.video_id
        WHERE h.tag = 'rutube'
    """)
    count = cur.fetchone()[0]
    conn.close()
    return count


def cleanup_rutube_clips(max_count):
    database.init()
    conn = sqlite3.connect(database.DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT v.id, v.video_url
        FROM videos v
        JOIN hashtags h ON v.id = h.video_id
        WHERE h.tag = 'rutube'
        ORDER BY v.created_at ASC
    """)

    rows = cur.fetchall()
    if len(rows) <= max_count:
        conn.close()
        return

    to_delete = len(rows) - max_count
    print(f"[CLEANUP] удаляем {to_delete} старых клипов")

    for i in range(to_delete):
        video_id, url = rows[i]
        if url.startswith("/uploads/"):
            path = os.path.join(UPLOAD_DIR, url.split("/uploads/")[1])
            if os.path.exists(path):
                os.remove(path)

        cur.execute("DELETE FROM video_likes WHERE video_id=?", (video_id,))
        cur.execute("DELETE FROM comments WHERE video_id=?", (video_id,))
        cur.execute("DELETE FROM hashtags WHERE video_id=?", (video_id,))
        cur.execute("DELETE FROM videos WHERE id=?", (video_id,))

    conn.commit()
    conn.close()


def save_clip_to_db(clip_path):
    database.init()

    new_name = f"{uuid.uuid4().hex}.mp4"
    dest = os.path.join(UPLOAD_DIR, new_name)

    with open(clip_path, "rb") as src, open(dest, "wb") as dst:
        dst.write(src.read())

    conn = sqlite3.connect(database.DB_PATH)
    cur = conn.cursor()

    video_id = uuid.uuid4().hex[:8]
    url = f"/uploads/{new_name}"

    cur.execute("""
        INSERT INTO videos (id, user_id, title, description, video_url, duration)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (video_id, 1, f"Rutube {video_id}", "", url, CLIP_DURATION_SEC))

    cur.execute("INSERT INTO hashtags (video_id, tag) VALUES (?, 'rutube')", (video_id,))
    conn.commit()
    conn.close()

    print(f"[DB] Добавлен клип: {video_id} → {url}")


# =========================
# MAIN
# =========================

def main():
    database.init()
    driver = create_driver()

    try:
        while True:
            cleanup_rutube_clips(MAX_RUTUBE_CLIPS)

            count = get_rutube_count()
            print(f"[INFO] В БД rutube-клипов: {count}")

            if count < MIN_RUTUBE_CLIPS:
                print("[STATE] Включаем подкачку…")
            else:
                print("[STATE] Подкачка не нужна.")
                time.sleep(FETCH_INTERVAL)
                continue

            ids = get_video_ids(driver)
            random.shuffle(ids)

            for vid in ids:
                stream = get_stream_url_for_video(driver, vid)
                if not stream:
                    continue

                clip = cut_clip(stream, vid)
                if not clip:
                    continue

                save_clip_to_db(clip)
                break

            time.sleep(FETCH_INTERVAL)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()

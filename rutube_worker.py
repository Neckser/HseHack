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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

HEADLESS = True
CLIP_DURATION_SEC = 10
MAX_START_SEC = 60

MIN_RUTUBE_CLIPS = 25
MAX_RUTUBE_CLIPS = 50
FETCH_INTERVAL = 5

os.makedirs(UPLOAD_DIR, exist_ok=True)


# =========================
# SELENIUM
# =========================

def create_driver():
    opts = Options()
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    if HEADLESS:
        opts.add_argument("--headless=new")

    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=opts)
    return driver


# =========================
# Rutube → video_id
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
# Network → m3u8 / mp4
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

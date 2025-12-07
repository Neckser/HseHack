from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os, uuid, sqlite3

import database, logic

import subprocess
import sys
import time

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

database.init()


@app.get("/", response_class=FileResponse)
def root():
    return FileResponse("index.html")


@app.get("/api/videos_seq")
def api_videos_seq():
    return logic.get_all_videos()


@app.get("/api/videos_seq/{index}")
def api_video_by_index(index: int):
    videos = logic.get_all_videos()
    if not videos:
        raise HTTPException(status_code=404, detail="No videos")
    index = max(0, min(index, len(videos) - 1))
    video = videos[index]
    video["index"] = index
    return video


@app.get("/api/videos/{video_id}")
def api_get_video(video_id: str):
    video = logic.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@app.post("/api/videos/{video_id}/like")
def api_like_video(video_id: str, user_id: int = Form(1)):
    result = logic.like_video(video_id, user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/api/upload")
async def api_upload_video(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    user_id: int = Form(1),
):
    ext = os.path.splitext(file.filename)[1] or ".mp4"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    video_id = uuid.uuid4().hex[:8]
    video_url = f"/uploads/{filename}"

    conn = sqlite3.connect(database.DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO videos (id, user_id, title, description, video_url)
        VALUES (?, ?, ?, ?, ?)
    """,
        (video_id, user_id, title, description, video_url),
    )
    conn.commit()
    conn.close()

    return {"success": True, "video_id": video_id, "file_url": video_url}


@app.get("/profile")
def profile():
    return FileResponse("profile.html")


@app.get("/api/videos/liked")
def api_liked_videos(user_id: int = 1):
    return logic.get_liked_videos(user_id)


# ======================================================
#            АВТОЗАПУСК rutube_worker.py
# ======================================================

_worker_process = None


def start_worker():
    """
    Запускает rutube_worker.py как отдельный процесс.
    Вызывается один раз при старте приложения.
    """
    global _worker_process

    # если воркер уже запущен и живой — ничего не делаем
    if _worker_process is not None and _worker_process.poll() is None:
        return

    worker_path = os.path.join(os.path.dirname(__file__), "rutube_worker.py")

    if not os.path.exists(worker_path):
        print("[WORKER] rutube_worker.py не найден рядом с main.py — воркер не запущен")
        return

    print("[WORKER] Запускаем rutube_worker.py ...")

    # stdout/stderr наследуем от текущего процесса, чтобы логи были в той же консоли
    _worker_process = subprocess.Popen([sys.executable, worker_path])

    time.sleep(0.5)
    print("[WORKER] Воркер запущен, pid =", _worker_process.pid)


@app.on_event("startup")
async def on_startup():
    """
    При старте FastAPI (и при uvicorn main:app) автоматически поднимаем воркер.
    """
    start_worker()

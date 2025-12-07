from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from datetime import datetime

import database
import logic
import sqlite3

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()

# Статические файлы (включая загруженные видео)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# CORS (для фронтенда)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация БД (создаёт файл и таблицы при первом запуске)
database.init()

# Корневая страница — отдаём index.html (предполагается, что он в той же папке)
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
    if index < 0:
        index = 0
    if index >= len(videos):
        index = 0
    video = videos[index]
    video["index"] = index
    return video


@app.get("/api/videos/{video_id}")
def api_get_video(video_id: str):
    video = logic.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    # увеличить просмотры
    logic.increment_views(video_id)
    video['views'] = video.get('views', 0) + 1
    return video


@app.post("/api/videos/{video_id}/like")
def api_like_video(video_id: str, user_id: int = Form(1)):
    result = logic.like_video(video_id, user_id=user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/api/upload")
async def api_upload_video(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    hashtags: str = Form(""),
    user_id: int = Form(1),
):
    # Сохраняем файл
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
    cur.execute("""
        INSERT INTO videos (id, user_id, title, description, video_url)
        VALUES (?, ?, ?, ?, ?)
    """, (video_id, user_id, title, description, video_url))

    if hashtags:
        tags = [t.strip() for t in hashtags.split(",") if t.strip()]
        for tag in tags:
            cur.execute("INSERT INTO hashtags (video_id, tag) VALUES (?, ?)", (video_id, tag))

    conn.commit()
    conn.close()

    return {"success": True, "video_id": video_id, "file_url": video_url}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "endpoints": ["/api/videos_seq", "/api/videos_seq/{index}", "/api/upload"]
    }

@app.get('/profile')
def profile():
    return FileResponse('profile.html')


@app.get("/api/videos/liked")
def liked_videos(user_id: int = 1):
    return logic.get_liked_videos(user_id)

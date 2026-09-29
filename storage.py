"""Работа с MinIO: ссылки на файлы, список файлов в бакете, загрузка."""
import os
from urllib.parse import quote

from minio import Minio

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000")
MINIO_USER = os.getenv("MINIO_USER", "admin")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD", "password123")
BUCKET = os.getenv("MINIO_BUCKET", "galaxies.media")

# медиа «по умолчанию» тоже лежат в MinIO (их кладёт сервис minio-init)
DEFAULT_IMAGE = "default.jpg"
DEFAULT_VIDEO = "default.mp4"

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")
VIDEO_EXT = (".mp4", ".webm", ".mov")

MEDIA_BASE = f"{MINIO_PUBLIC_URL}/{BUCKET}/"

client = Minio(MINIO_ENDPOINT, access_key=MINIO_USER, secret_key=MINIO_PASSWORD, secure=False)


def media_url(key, default=DEFAULT_IMAGE):
    """Публичная ссылка на объект. Пробелы и кириллица кодируются."""
    return f"{MINIO_PUBLIC_URL}/{BUCKET}/{quote(key or default)}"


def is_video(key):
    return bool(key) and key.lower().endswith(VIDEO_EXT)


def _list_keys():
    try:
        return sorted(obj.object_name for obj in client.list_objects(BUCKET))
    except Exception:
        return []


def list_images():
    keys = [k for k in _list_keys() if k.lower().endswith(IMAGE_EXT)]
    return keys or [DEFAULT_IMAGE]


def list_videos():
    # gif тоже подходит как «видео» (анимация)
    keys = [k for k in _list_keys() if k.lower().endswith(VIDEO_EXT + (".gif",))]
    return keys or [DEFAULT_VIDEO]


def upload(file):
    """Загружает UploadFile в бакет и возвращает ключ объекта."""
    name = os.path.basename(file.filename or "").strip()
    if not name:
        raise ValueError("Пустое имя файла")
    client.put_object(
        BUCKET, name, file.file, length=-1, part_size=10 * 1024 * 1024,
        content_type=file.content_type or "application/octet-stream",
    )
    return name

import json
import mimetypes
from pathlib import Path

MEDIA_DIR = Path(__file__).parent / "minio" / "media"


def init_storage():
    """При запуске приложения: создаёт бакет, открывает его на чтение
    и загружает файлы из папки minio/media (в т.ч. default.jpg и default.mp4)."""
    try:
        if not client.bucket_exists(BUCKET):
            client.make_bucket(BUCKET)

        # публичный доступ только на чтение (скачивание файлов)
        policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{BUCKET}/*"],
            }],
        }
        client.set_bucket_policy(BUCKET, json.dumps(policy))

        existing = {obj.object_name for obj in client.list_objects(BUCKET)}
        for path in MEDIA_DIR.iterdir():
            if path.is_file() and (path.name not in existing or path.name.startswith("default.")):
                content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                client.fput_object(BUCKET, path.name, str(path), content_type=content_type)

        print(f"MinIO: бакет {BUCKET} готов")
    except Exception as e:
        print(f"MinIO недоступен: {e}")

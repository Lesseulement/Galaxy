"""MinIO: ссылки на файлы, загрузка файлов, начальная настройка бакета."""
import json
import mimetypes
import os
import re
import uuid
from pathlib import Path
from urllib.parse import quote

from minio import Minio

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000")
MINIO_USER = os.getenv("MINIO_USER", "admin")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD", "password123")
BUCKET = os.getenv("MINIO_BUCKET", "galaxies.media")

DEFAULT_IMAGE = "default.jpg"
DEFAULT_VIDEO = "default.mp4"
MEDIA_DIR = Path(__file__).parent / "minio" / "media"

client = Minio(MINIO_ENDPOINT, access_key=MINIO_USER, secret_key=MINIO_PASSWORD, secure=False)


def media_url(key, default=DEFAULT_IMAGE):
    return f"{MINIO_PUBLIC_URL}/{BUCKET}/{quote(key or default)}"


def upload(file, prefix):
    """Сохраняет файл в MinIO под сгенерированным латинским именем
    (например image_3f9a1c....jpg) и возвращает это имя."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,5}", ext):
        ext = mimetypes.guess_extension(file.content_type or "") or ""
    key = f"{prefix}_{uuid.uuid4().hex}{ext}"
    client.put_object(
        BUCKET, key, file.file, length=-1, part_size=10 * 1024 * 1024,
        content_type=file.content_type or "application/octet-stream",
    )
    return key


def init_storage():
    """Создаёт бакет, открывает его на чтение и загружает файлы из minio/media."""
    try:
        if not client.bucket_exists(BUCKET):
            client.make_bucket(BUCKET)
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

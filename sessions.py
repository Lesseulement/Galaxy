"""Сессии пользователей в Redis.

При входе создаётся сессия: случайный id -> {user_id, username}.
id сессии уходит клиенту в куке session_id. Ключ в Redis живёт SESSION_TTL секунд.
"""
import json
import os
import secrets
from typing import Optional

import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
SESSION_TTL = int(os.getenv("SESSION_TTL", str(24 * 60 * 60)))  # сутки
COOKIE_NAME = "session_id"

client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def _key(session_id: str) -> str:
    return f"session:{session_id}"


def create(user_id: int, username: str) -> str:
    session_id = secrets.token_urlsafe(32)
    client.setex(_key(session_id), SESSION_TTL, json.dumps({"user_id": user_id, "username": username}))
    return session_id


def get(session_id: Optional[str]) -> Optional[dict]:
    if not session_id:
        return None
    raw = client.get(_key(session_id))
    return json.loads(raw) if raw else None


def delete(session_id: str) -> None:
    client.delete(_key(session_id))

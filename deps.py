"""Текущий пользователь — из сессии в Redis по куке session_id.

current_user          — для методов создателя: без входа 401.
current_user_optional — для методов чтения: гость получает None.
"""
from typing import Optional

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyCookie

import sessions

# схема для Swagger: замочек у методов, которым нужна авторизация
cookie_scheme = APIKeyCookie(name=sessions.COOKIE_NAME, auto_error=False,
                             description="Кука сессии, выдаётся методом POST /api/users/login")


def current_user(session_id: Optional[str] = Security(cookie_scheme)) -> int:
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=401)
    return session["user_id"]


def current_user_optional(request: Request) -> Optional[int]:
    session = sessions.get(request.cookies.get(sessions.COOKIE_NAME))
    return session["user_id"] if session else None

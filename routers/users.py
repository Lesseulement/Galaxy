"""Домен пользователь: регистрация, аутентификация, деавторизация (3 метода).

Авторизация — через сессии в Redis: при входе создаётся сессия,
её id отдаётся клиенту в куке session_id (HttpOnly).
"""
import hashlib
import hmac
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, Security
from sqlalchemy.orm import Session

import sessions
from database import get_db
from deps import cookie_scheme
from models import User
from schemas import UserIn, UserOut

router = APIRouter(prefix="/users", tags=["Пользователи"])


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return f"{salt.hex()}${digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 100_000)
    return hmac.compare_digest(digest.hex(), digest_hex)


# 8. Регистрация. Пароль хранится только в виде хэша
@router.post(
    "/register", response_model=UserOut, status_code=201,
    summary="Регистрация",
    description="Создаёт пользователя. Пароль хранится в БД только в виде хэша. Доступно без входа.",
    responses={409: {"description": "Логин занят"}},
)
def register(body: UserIn, db: Session = Depends(get_db)):
    username = body.username.strip()
    if db.query(User).filter(User.username == username).first() is not None:
        raise HTTPException(status_code=409)
    user = User(username=username, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(id=user.id, username=user.username)


# 9. Аутентификация: проверка пароля, создание сессии в Redis, кука session_id
@router.post(
    "/login", response_model=UserOut,
    summary="Аутентификация (вход)",
    description="Проверяет логин и пароль, создаёт сессию в Redis и возвращает куку `session_id`. "
                "Браузер (и Swagger) дальше отправляет куку сам.",
    responses={401: {"description": "Неверный логин или пароль"}},
)
def login(body: UserIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username.strip()).first()
    if user is None or not check_password(body.password, user.password_hash):
        raise HTTPException(status_code=401)
    session_id = sessions.create(user.id, user.username)
    response.set_cookie(
        key=sessions.COOKIE_NAME, value=session_id,
        max_age=sessions.SESSION_TTL, httponly=True, samesite="lax", path="/",
    )
    return UserOut(id=user.id, username=user.username)


# 10. Деавторизация: удаление сессии из Redis и куки
@router.post(
    "/logout",
    summary="Деавторизация (выход)",
    description="Удаляет сессию из Redis и куку `session_id`. Требуется вход.",
    responses={200: {"description": "Выход выполнен"}, 401: {"description": "Не выполнен вход"}},
)
def logout(session_id: Optional[str] = Security(cookie_scheme)):
    if sessions.get(session_id) is None:
        raise HTTPException(status_code=401)
    sessions.delete(session_id)
    response = Response(status_code=200)
    response.delete_cookie(sessions.COOKIE_NAME, path="/")
    return response

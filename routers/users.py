"""Домен пользователь: регистрация, аутентификация и деавторизация."""
import hashlib
import os

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import UserIn, UserOut

router = APIRouter(prefix="/users", tags=["Пользователи"])


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return f"{salt.hex()}${digest.hex()}"


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: UserIn, db: Session = Depends(get_db)):
    """Регистрация нового пользователя. Пароль хранится только в виде хэша."""
    username = body.username.strip()
    if db.query(User).filter(User.username == username).first() is not None:
        raise HTTPException(status_code=409)  # логин занят
    user = User(username=username, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(id=user.id, username=user.username)


@router.post("/login")
def login():
    """Аутентификация — заглушка, будет реализована в ЛР4."""
    return Response(status_code=200)


@router.post("/logout")
def logout():
    """Деавторизация — заглушка, будет реализована в ЛР4."""
    return Response(status_code=200)

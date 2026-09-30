"""Сериализаторы (Pydantic-схемы) запросов и ответов.

Ответ по галактике всегда содержит один и тот же набор полей:
если поле ещё не заполнено, оно приходит как null.
Статус и системные поля наружу не отдаются и с клиента не принимаются.
"""
from typing import Optional

from pydantic import BaseModel, Field


class GalaxyOut(BaseModel):
    id: int
    title: Optional[str]
    description: Optional[str]
    supernova: Optional[str]
    magnitude: Optional[float]
    distance_mpc: Optional[float]
    image_url: str
    video_url: str
    likes_count: int
    is_liked: int   
    is_mine: int   

class LikeIn(BaseModel):
    like: int = Field(ge=0, le=1) 


class LikeOut(BaseModel):
    likes_count: int
    is_liked: int


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str

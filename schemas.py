"""Сериализаторы (Pydantic-схемы) запросов и ответов.

Ответ по галактике всегда содержит один и тот же набор полей:
незаполненное поле приходит как null. Статус, создатель и даты
наружу не отдаются и с клиента не принимаются.
"""
from typing import Optional

from pydantic import BaseModel, Field


class GalaxyOut(BaseModel):
    id: int
    title: str
    supernova: Optional[str]
    apparent_magnitude: Optional[float]
    distance_mpc: Optional[float]
    description: Optional[str]
    image_url: str
    video_url: str
    likes_count: int
    is_liked: int   # 0/1 — текущий пользователь поставил лайк
    is_mine: int    # 0/1 — создатель совпадает с текущим пользователем


class PublishIn(BaseModel):
    """Поля, которые вводятся перед кнопкой «Опубликовать»."""
    supernova: str = Field(min_length=1, max_length=30, examples=["SN 2002fk"])
    apparent_magnitude: float = Field(examples=[13.2])
    distance_mpc: float = Field(gt=0, examples=[29.4])
    description: Optional[str] = Field(None, examples=["Спиральная галактика в созвездии Эридан"])


class LikeIn(BaseModel):
    like: int = Field(ge=0, le=1, examples=[1])  # 1 — поставить лайк, 0 — отменить


class LikeOut(BaseModel):
    likes_count: int
    is_liked: int


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=50, examples=["veronika"])
    password: str = Field(min_length=6, max_length=128, examples=["password123"])


class UserOut(BaseModel):
    id: int
    username: str

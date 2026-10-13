"""Сериализаторы (Pydantic-схемы) запросов и ответов."""
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
    is_liked: int  
    is_mine: int    
class PublishIn(BaseModel):
    """Поля, которые вводятся перед кнопкой «Опубликовать»."""
    supernova: str = Field(min_length=1, max_length=30)
    apparent_magnitude: float
    distance_mpc: float = Field(gt=0)
    description: Optional[str] = None
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

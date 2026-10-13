"""ORM-модели. Таблицы и все ограничения создаёт db/01_schema.sql."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship

from database import Base

GalaxyStatus = ENUM("draft", "published", "deleted", name="galaxy_status", create_type=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)

    galaxies = relationship("Galaxy", back_populates="creator")
    likes = relationship("GalaxyLike", back_populates="user")


class Galaxy(Base):
    """Услуга — галактика со сверхновой типа Ia."""
    __tablename__ = "galaxies"

    id = Column(Integer, primary_key=True)

    # кнопка «Далее» (POST) — обязательные
    title = Column(String(100), nullable=False)
    image_key = Column(String(255), nullable=False, server_default="default.jpg")
    video_key = Column(String(255), nullable=False, server_default="default.mp4")

    status = Column(GalaxyStatus, nullable=False, server_default="draft")
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # кнопка «Опубликовать» (PUT)
    supernova = Column(String(30))
    apparent_magnitude = Column(Numeric(5, 2, asdecimal=False)) 
    distance_mpc = Column(Numeric(8, 2, asdecimal=False))       
    description = Column(Text)

    creator = relationship("User", back_populates="galaxies")
    likes = relationship("GalaxyLike", back_populates="galaxy")


class GalaxyLike(Base):
    __tablename__ = "galaxy_likes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    galaxy_id = Column(Integer, ForeignKey("galaxies.id"), nullable=False)

    user = relationship("User", back_populates="likes")
    galaxy = relationship("Galaxy", back_populates="likes")

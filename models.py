"""ORM-модели. Таблицы и ограничения создаёт db/schema.sql."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship

from database import Base

ServiceStatus = ENUM("draft", "published", "deleted", name="service_status", create_type=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255))

    services = relationship("GalaxyService", back_populates="creator")
    likes = relationship("GalaxyLike", back_populates="user")


class GalaxyService(Base):
    """Услуга = галактика со сверхновой типа Ia."""
    __tablename__ = "galaxy_services"

    id = Column(Integer, primary_key=True)
    image_key = Column(String(255), nullable=False, server_default="default.jpg")
    video_key = Column(String(255), nullable=False, server_default="default.mp4")
    status = Column(ServiceStatus, nullable=False, server_default="draft")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String(100))
    description = Column(Text)
    supernova = Column(String(30))
    magnitude = Column(Numeric(5, 2, asdecimal=False))
    distance_mpc = Column(Numeric(8, 2, asdecimal=False))

    creator = relationship("User", back_populates="services")
    likes = relationship("GalaxyLike", back_populates="service")


class GalaxyLike(Base):
    __tablename__ = "galaxy_likes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("galaxy_services.id"), nullable=False)

    user = relationship("User", back_populates="likes")
    service = relationship("GalaxyService", back_populates="likes")

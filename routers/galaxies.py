"""Домен услуги: галактики со сверхновыми типа Ia."""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session, selectinload

import storage
from database import get_db
from deps import current_user_id
from models import GalaxyLike, GalaxyService
from schemas import GalaxyOut, LikeIn, LikeOut

router = APIRouter(prefix="/galaxies", tags=["Галактики"])


def to_out(g: GalaxyService, uid: int) -> GalaxyOut:
    return GalaxyOut(
        id=g.id,
        title=g.title,
        description=g.description,
        supernova=g.supernova,
        magnitude=g.magnitude,
        distance_mpc=g.distance_mpc,
        image_url=storage.media_url(g.image_key, storage.DEFAULT_IMAGE),
        video_url=storage.media_url(g.video_key, storage.DEFAULT_VIDEO),
        likes_count=len(g.likes),
        is_liked=int(any(like.user_id == uid for like in g.likes)),
        is_mine=int(g.creator_id == uid),
    )


def published(db: Session):
    return (
        db.query(GalaxyService)
        .options(selectinload(GalaxyService.likes))
        .filter(GalaxyService.status == "published")
    )


def get_draft(db: Session, uid: int) -> Optional[GalaxyService]:
    return (
        db.query(GalaxyService)
        .options(selectinload(GalaxyService.likes))
        .filter(GalaxyService.creator_id == uid, GalaxyService.status == "draft")
        .first()
    )


@router.get("", response_model=List[GalaxyOut])
def list_galaxies(
    search: Optional[str] = None,
    dist_min: Optional[float] = None,
    dist_max: Optional[float] = None,
    db: Session = Depends(get_db),
    uid: int = Depends(current_user_id),
):
    """Список опубликованных галактик с фильтрацией по названию и расстоянию."""
    query = published(db)
    if search:
        query = query.filter(GalaxyService.title.ilike(f"%{search.strip()}%"))
    if dist_min is not None:
        query = query.filter(GalaxyService.distance_mpc >= dist_min)
    if dist_max is not None:
        query = query.filter(GalaxyService.distance_mpc <= dist_max)
    return [to_out(g, uid) for g in query.order_by(GalaxyService.id)]


@router.get("/feed", response_model=GalaxyOut)
def feed(
    item_id: Optional[int] = Query(None, alias="id"),
    next_item: bool = Query(False, alias="next"),
    db: Session = Depends(get_db),
    uid: int = Depends(current_user_id),
):
    """Лента: без id — первая галактика, с id — эта галактика,
    с id и next=true — следующая после неё (по кругу)."""
    query = published(db).order_by(GalaxyService.id)
    if item_id is None:
        item = query.first()
    elif next_item:
        item = query.filter(GalaxyService.id > item_id).first() or query.first()
    else:
        item = query.filter(GalaxyService.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404)
    return to_out(item, uid)


@router.get("/draft", response_model=GalaxyOut)
def read_draft(db: Session = Depends(get_db), uid: int = Depends(current_user_id)):
    """Черновик текущего пользователя (не больше одного), id не указывается."""
    draft = get_draft(db, uid)
    if draft is None:
        raise HTTPException(status_code=404)
    return to_out(draft, uid)


@router.post("", response_model=GalaxyOut, status_code=201)
def create_galaxy(
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    supernova: Optional[str] = Form(None),
    magnitude: Optional[float] = Form(None),
    distance_mpc: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    uid: int = Depends(current_user_id),
):
    """Добавление галактики: создаётся черновик, фото и видео — файлами в MinIO."""
    if get_draft(db, uid) is not None:
        raise HTTPException(status_code=409)  # черновик уже есть
    if not (image.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400)
    if not (video.content_type or "").startswith("video/"):
        raise HTTPException(status_code=400)
    if distance_mpc is not None and distance_mpc <= 0:
        raise HTTPException(status_code=400)

    draft = GalaxyService(
        title=(title or "").strip() or None,
        description=(description or "").strip() or None,
        supernova=(supernova or "").strip() or None,
        magnitude=magnitude,
        distance_mpc=distance_mpc,
        image_key=storage.upload(image, "image"),
        video_key=storage.upload(video, "video"),
        status="draft",
        creator_id=uid,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return to_out(draft, uid)


@router.put("/draft/publish", response_model=GalaxyOut)
def publish_draft(db: Session = Depends(get_db), uid: int = Depends(current_user_id)):
    """Публикация черновика: смена статуса draft -> published.
    Вернуть опубликованную галактику в черновик нельзя."""
    draft = get_draft(db, uid)
    if draft is None:
        raise HTTPException(status_code=404)
    if not (draft.title and draft.supernova and draft.magnitude is not None and draft.distance_mpc is not None):
        raise HTTPException(status_code=400)  # не заполнены обязательные поля
    draft.status = "published"
    db.commit()
    db.refresh(draft)
    return to_out(draft, uid)


@router.delete("/{galaxy_id}")
def delete_galaxy(galaxy_id: int, db: Session = Depends(get_db), uid: int = Depends(current_user_id)):
    """Мягкое удаление (статус deleted). Удалять можно только свои галактики."""
    galaxy = (
        db.query(GalaxyService)
        .filter(GalaxyService.id == galaxy_id, GalaxyService.status != "deleted")
        .first()
    )
    if galaxy is None:
        raise HTTPException(status_code=404)
    if galaxy.creator_id != uid:
        raise HTTPException(status_code=403)
    galaxy.status = "deleted"
    db.commit()
    return Response(status_code=200)


@router.post("/{galaxy_id}/like", response_model=LikeOut)
def like_galaxy(
    galaxy_id: int,
    body: LikeIn,
    db: Session = Depends(get_db),
    uid: int = Depends(current_user_id),
):
    """Лайк от текущего пользователя: like=1 ставит, like=0 отменяет."""
    galaxy = published(db).filter(GalaxyService.id == galaxy_id).first()
    if galaxy is None:
        raise HTTPException(status_code=404)

    existing = (
        db.query(GalaxyLike)
        .filter(GalaxyLike.service_id == galaxy_id, GalaxyLike.user_id == uid)
        .first()
    )
    if body.like == 1 and existing is None:
        db.add(GalaxyLike(service_id=galaxy_id, user_id=uid))
    elif body.like == 0 and existing is not None:
        db.delete(existing)
    db.commit()

    count = db.query(GalaxyLike).filter(GalaxyLike.service_id == galaxy_id).count()
    return LikeOut(likes_count=count, is_liked=body.like)

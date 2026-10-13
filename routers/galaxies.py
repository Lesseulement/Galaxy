"""Домен услуги: галактики со сверхновыми типа Ia (7 методов)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session, selectinload

import storage
from database import get_db
from deps import current_user_id
from models import Galaxy, GalaxyLike
from schemas import GalaxyOut, LikeIn, LikeOut, PublishIn

router = APIRouter(prefix="/galaxies", tags=["Галактики"])


def to_out(g: Galaxy, uid: int) -> GalaxyOut:
    return GalaxyOut(
        id=g.id,
        title=g.title,
        supernova=g.supernova,
        apparent_magnitude=g.apparent_magnitude,
        distance_mpc=g.distance_mpc,
        description=g.description,
        image_url=storage.media_url(g.image_key, storage.DEFAULT_IMAGE),
        video_url=storage.media_url(g.video_key, storage.DEFAULT_VIDEO),
        likes_count=len(g.likes),
        is_liked=int(any(like.user_id == uid for like in g.likes)),
        is_mine=int(g.creator_id == uid),
    )


def published(db: Session):
    return db.query(Galaxy).options(selectinload(Galaxy.likes)).filter(Galaxy.status == "published")


def get_draft(db: Session, uid: int) -> Optional[Galaxy]:
    return (
        db.query(Galaxy)
        .options(selectinload(Galaxy.likes))
        .filter(Galaxy.creator_id == uid, Galaxy.status == "draft")
        .first()
    )


# 1. Плитка: список опубликованных с фильтрацией по видимой звёздной величине
@router.get("", response_model=List[GalaxyOut])
def list_galaxies(
    magnitude_from: Optional[float] = None,
    magnitude_to: Optional[float] = None,
    title: Optional[str] = None,
    db: Session = Depends(get_db),
    uid: int = Depends(current_user_id),
):
    query = published(db)
    if magnitude_from is not None:
        query = query.filter(Galaxy.apparent_magnitude >= magnitude_from)
    if magnitude_to is not None:
        query = query.filter(Galaxy.apparent_magnitude <= magnitude_to)
    if title:
        query = query.filter(Galaxy.title.ilike(f"%{title.strip()}%"))
    return [to_out(g, uid) for g in query.order_by(Galaxy.id)]


# 2. Лента: без id — первая галактика; ?id=N — эта; ?id=N&next=true — следующая (по кругу)
@router.get("/feed", response_model=GalaxyOut)
def feed(
    item_id: Optional[int] = Query(None, alias="id"),
    next_item: bool = Query(False, alias="next"),
    db: Session = Depends(get_db),
    uid: int = Depends(current_user_id),
):
    query = published(db).order_by(Galaxy.id)
    if item_id is None:
        item = query.first()
    elif next_item:
        item = query.filter(Galaxy.id > item_id).first() or query.first()
    else:
        item = query.filter(Galaxy.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404)
    return to_out(item, uid)


# 3. Добавление: поля черновика текущего пользователя (не больше одного), id не указывается
@router.get("/draft", response_model=GalaxyOut)
def read_draft(db: Session = Depends(get_db), uid: int = Depends(current_user_id)):
    draft = get_draft(db, uid)
    if draft is None:
        raise HTTPException(status_code=404)
    return to_out(draft, uid)



@router.post("", response_model=GalaxyOut, status_code=201)
def create_draft(
    title: str = Form(..., min_length=1, max_length=100),
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
    uid: int = Depends(current_user_id),
):
    if get_draft(db, uid) is not None:
        raise HTTPException(status_code=409)  
    if not title.strip():
        raise HTTPException(status_code=400)
    if not (image.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400)
    if not (video.content_type or "").startswith("video/"):
        raise HTTPException(status_code=400)

    draft = Galaxy(
        title=title.strip(),
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
def publish_draft(body: PublishIn, db: Session = Depends(get_db), uid: int = Depends(current_user_id)):
    draft = get_draft(db, uid)
    if draft is None:
        raise HTTPException(status_code=404)
    draft.supernova = body.supernova.strip()
    draft.apparent_magnitude = body.apparent_magnitude
    draft.distance_mpc = body.distance_mpc
    draft.description = (body.description or "").strip() or None
    draft.status = "published"  
    db.commit()
    db.refresh(draft)
    return to_out(draft, uid)


@router.delete("/{galaxy_id}")
def delete_galaxy(galaxy_id: int, db: Session = Depends(get_db), uid: int = Depends(current_user_id)):
    galaxy = db.query(Galaxy).filter(Galaxy.id == galaxy_id, Galaxy.status != "deleted").first()
    if galaxy is None:
        raise HTTPException(status_code=404)
    if galaxy.creator_id != uid:
        raise HTTPException(status_code=403)
    galaxy.status = "deleted"
    db.commit()
    return Response(status_code=200)


# 7. Сердечко в ленте: like=1 ставит лайк, like=0 отменяет
@router.post("/{galaxy_id}/like", response_model=LikeOut)
def like_galaxy(
    galaxy_id: int,
    body: LikeIn,
    db: Session = Depends(get_db),
    uid: int = Depends(current_user_id),
):
    galaxy = published(db).filter(Galaxy.id == galaxy_id).first()
    if galaxy is None:
        raise HTTPException(status_code=404)

    existing = (
        db.query(GalaxyLike)
        .filter(GalaxyLike.galaxy_id == galaxy_id, GalaxyLike.user_id == uid)
        .first()
    )
    if body.like == 1 and existing is None:
        db.add(GalaxyLike(galaxy_id=galaxy_id, user_id=uid))
    elif body.like == 0 and existing is not None:
        db.delete(existing)
    db.commit()

    count = db.query(GalaxyLike).filter(GalaxyLike.galaxy_id == galaxy_id).count()
    return LikeOut(likes_count=count, is_liked=body.like)

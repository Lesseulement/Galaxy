"""Домен услуги: галактики со сверхновыми типа Ia (7 методов).

Чтение (список, лента) доступно всем. Методы создателя требуют входа:
без куки сессии — 401, чужая галактика — 403.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session, selectinload

import storage
from database import get_db
from deps import current_user, current_user_optional
from models import Galaxy, GalaxyLike
from schemas import GalaxyOut, LikeIn, LikeOut, PublishIn

router = APIRouter(prefix="/galaxies", tags=["Галактики"])

NEED_AUTH = {401: {"description": "Не выполнен вход"}}


def to_out(g: Galaxy, uid: Optional[int]) -> GalaxyOut:
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
        is_liked=int(uid is not None and any(like.user_id == uid for like in g.likes)),
        is_mine=int(uid is not None and g.creator_id == uid),
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
@router.get(
    "", response_model=List[GalaxyOut],
    summary="Список галактик (плитка)",
    description="Только опубликованные галактики. Фильтр по видимой звёздной величине "
                "`magnitude_from`–`magnitude_to`, необязательный поиск по названию `title`. "
                "Доступно без входа; для вошедшего пользователя заполняются `is_liked` и `is_mine`.",
)
def list_galaxies(
    magnitude_from: Optional[float] = Query(None, description="Видимая звёздная величина от"),
    magnitude_to: Optional[float] = Query(None, description="Видимая звёздная величина до"),
    title: Optional[str] = Query(None, description="Часть названия"),
    db: Session = Depends(get_db),
    uid: Optional[int] = Depends(current_user_optional),
):
    query = published(db)
    if magnitude_from is not None:
        query = query.filter(Galaxy.apparent_magnitude >= magnitude_from)
    if magnitude_to is not None:
        query = query.filter(Galaxy.apparent_magnitude <= magnitude_to)
    if title:
        query = query.filter(Galaxy.title.ilike(f"%{title.strip()}%"))
    return [to_out(g, uid) for g in query.order_by(Galaxy.id)]


# 2. Лента: без id — первая; ?id=N — эта; ?id=N&next=true — следующая (по кругу)
@router.get(
    "/feed", response_model=GalaxyOut,
    summary="Лента",
    description="Без `id` — первая опубликованная галактика; `id` — эта галактика; "
                "`id` и `next=true` — следующая после неё (по кругу). Доступно без входа.",
    responses={404: {"description": "Нет опубликованных галактик"}},
)
def feed(
    item_id: Optional[int] = Query(None, alias="id", description="id текущей галактики"),
    next_item: bool = Query(False, alias="next", description="true — следующая после id"),
    db: Session = Depends(get_db),
    uid: Optional[int] = Depends(current_user_optional),
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
@router.get(
    "/draft", response_model=GalaxyOut,
    summary="Поля черновика",
    description="Черновик текущего пользователя (у пользователя не больше одного). Требуется вход.",
    responses={**NEED_AUTH, 404: {"description": "Черновика нет"}},
)
def read_draft(db: Session = Depends(get_db), uid: int = Depends(current_user)):
    draft = get_draft(db, uid)
    if draft is None:
        raise HTTPException(status_code=404)
    return to_out(draft, uid)


# 4. Кнопка «Далее»: создаёт черновик — название, фото и видео (файлы в MinIO)
@router.post(
    "", response_model=GalaxyOut, status_code=201,
    summary="Кнопка «Далее»: создать черновик",
    description="Передаются название и файлы фото и видео. Файлы сохраняются в MinIO под латинскими "
                "именами. Создатель проставляется автоматически из сессии. Требуется вход.",
    responses={**NEED_AUTH, 400: {"description": "Неверные данные"}, 409: {"description": "Черновик уже есть"}},
)
def create_draft(
    title: str = Form(..., min_length=1, max_length=100, description="Название галактики"),
    image: UploadFile = File(..., description="Файл фото"),
    video: UploadFile = File(..., description="Файл видео"),
    db: Session = Depends(get_db),
    uid: int = Depends(current_user),
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
        creator_id=uid,  # автозаполнение создателя из сессии
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return to_out(draft, uid)


# 5. Кнопка «Опубликовать»: сохраняет поля формы и меняет статус draft -> published
@router.put(
    "/draft/publish", response_model=GalaxyOut,
    summary="Кнопка «Опубликовать»",
    description="Сохраняет поля формы (сверхновая, видимая звёздная величина, расстояние, описание) "
                "и меняет статус черновика на published. Требуется вход.",
    responses={**NEED_AUTH, 400: {"description": "Не заполнены поля"}, 404: {"description": "Черновика нет"}},
)
def publish_draft(body: PublishIn, db: Session = Depends(get_db), uid: int = Depends(current_user)):
    draft = get_draft(db, uid)
    if draft is None:
        raise HTTPException(status_code=404)
    draft.supernova = body.supernova.strip()
    draft.apparent_magnitude = body.apparent_magnitude
    draft.distance_mpc = body.distance_mpc
    draft.description = (body.description or "").strip() or None
    draft.status = "published"  # обратно в черновик вернуть нельзя
    db.commit()
    db.refresh(draft)
    return to_out(draft, uid)


# 6. Кнопки «Удалить» (плитка) и «Удалить черновик»: мягкое удаление, только свои
@router.delete(
    "/{galaxy_id}",
    summary="Кнопка «Удалить»",
    description="Мягкое удаление (статус deleted). Удалять можно только свои галактики. Требуется вход.",
    responses={200: {"description": "Удалено"}, **NEED_AUTH, 403: {"description": "Чужая галактика"},
               404: {"description": "Не найдена"}},
)
def delete_galaxy(galaxy_id: int, db: Session = Depends(get_db), uid: int = Depends(current_user)):
    galaxy = db.query(Galaxy).filter(Galaxy.id == galaxy_id, Galaxy.status != "deleted").first()
    if galaxy is None:
        raise HTTPException(status_code=404)
    if galaxy.creator_id != uid:
        raise HTTPException(status_code=403)
    galaxy.status = "deleted"
    db.commit()
    return Response(status_code=200)


# 7. Сердечко в ленте: like=1 ставит лайк, like=0 отменяет
@router.post(
    "/{galaxy_id}/like", response_model=LikeOut,
    summary="Сердечко: лайк",
    description="`like`: 1 — поставить лайк, 0 — отменить. Лайк ставится от текущего пользователя. Требуется вход.",
    responses={**NEED_AUTH, 404: {"description": "Галактика не найдена"}},
)
def like_galaxy(
    galaxy_id: int,
    body: LikeIn,
    db: Session = Depends(get_db),
    uid: int = Depends(current_user),
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

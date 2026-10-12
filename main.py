import math
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

import storage
from database import engine, get_db
from models import Galaxy, GalaxyLike

app = FastAPI(title="Галактики: расстояние по сверхновым Ia")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

CURRENT_USER_ID = 1  # авторизации пока нет, работаем от пользователя veronika


def fmt(value):
    """12.80 -> 12.8, None -> —"""
    return "—" if value is None else f"{value:g}"


templates.env.globals.update(media_url=storage.media_url, is_video=storage.is_video, fmt=fmt)
templates.env.globals["DEFAULT_VIDEO"] = storage.DEFAULT_VIDEO
storage.init_storage()  # настройка MinIO при запуске


def render(request, name, status_code=200, **context):
    return templates.TemplateResponse(request=request, name=name, context=context, status_code=status_code)


def not_found(request, message):
    return render(request, "message.html", status_code=404, message=message, active=None)


def current_draft(db):
    return (
        db.query(Galaxy)
        .filter(Galaxy.creator_id == CURRENT_USER_ID, Galaxy.status == "draft")
        .first()
    )


def start_page(request, status_code=200, error=None, title=""):
    """Окно «Далее»: выбор названия, фото и видео."""
    return render(
        request, "add_start.html", status_code=status_code, active="add",
        images=storage.list_images(), videos=storage.list_videos(),
        default_image=storage.DEFAULT_IMAGE, default_video=storage.DEFAULT_VIDEO,
        media_base=storage.MEDIA_BASE, error=error, title=title,
    )


# ------------------------------------------------------------------ ПЛИТКА
@app.get("/", response_class=HTMLResponse)
def grid(
    request: Request,
    mag_min: Optional[float] = None,
    mag_max: Optional[float] = None,
    db: Session = Depends(get_db),
):
    """Фильтрация по видимой звёздной величине: слайдеры «от» и «до» + кнопка «Найти»."""
    low, high = (
        db.query(func.min(Galaxy.apparent_magnitude), func.max(Galaxy.apparent_magnitude))
        .filter(Galaxy.status == "published")
        .one()
    )
    slider_min = math.floor(low) if low is not None else 0
    slider_max = math.ceil(high) if high is not None else 20

    lo = float(slider_min) if mag_min is None else mag_min
    hi = float(slider_max) if mag_max is None else mag_max
    if lo > hi:
        lo, hi = hi, lo

    items = (
        db.query(Galaxy)
        .options(selectinload(Galaxy.likes))
        .filter(Galaxy.status == "published", Galaxy.apparent_magnitude.between(lo, hi))
        .order_by(Galaxy.id)
        .all()
    )
    return render(
        request, "grid.html", active="grid", items=items,
        mag_min=lo, mag_max=hi, slider_min=slider_min, slider_max=slider_max,
    )


# ------------------------------------------------------------------ ЛЕНТА
@app.get("/feed")
def feed_start(request: Request, db: Session = Depends(get_db)):
    first = db.query(Galaxy).filter(Galaxy.status == "published").order_by(Galaxy.id).first()
    if not first:
        return render(request, "message.html", message="В ленте пока нет опубликованных галактик", active="feed")
    return RedirectResponse(url=f"/feed/{first.id}", status_code=303)


@app.get("/feed/{item_id}", response_class=HTMLResponse)
def feed(request: Request, item_id: int, db: Session = Depends(get_db)):
    item = db.query(Galaxy).filter(Galaxy.id == item_id, Galaxy.status == "published").first()
    if not item:
        return not_found(request, "Галактика удалена или не существует")

    likes_count = db.query(GalaxyLike).filter(GalaxyLike.galaxy_id == item.id).count()
    is_liked = (
        db.query(GalaxyLike)
        .filter(GalaxyLike.galaxy_id == item.id, GalaxyLike.user_id == CURRENT_USER_ID)
        .first()
        is not None
    )
    return render(request, "feed.html", active="feed", item=item, likes_count=likes_count, is_liked=is_liked)


@app.get("/feed/{item_id}/next")
def feed_next(item_id: int, db: Session = Depends(get_db)):
    published = db.query(Galaxy).filter(Galaxy.status == "published")
    nxt = published.filter(Galaxy.id > item_id).order_by(Galaxy.id).first()
    if not nxt:  # дошли до конца — начинаем сначала
        nxt = published.order_by(Galaxy.id).first()
    return RedirectResponse(url=f"/feed/{nxt.id}" if nxt else "/feed", status_code=303)


@app.post("/feed/{item_id}/like")
def toggle_like(item_id: int, db: Session = Depends(get_db)):
    """Лайк хранится в таблице galaxy_likes. Повторное нажатие снимает лайк."""
    like = (
        db.query(GalaxyLike)
        .filter(GalaxyLike.galaxy_id == item_id, GalaxyLike.user_id == CURRENT_USER_ID)
        .first()
    )
    if like:
        db.delete(like)
    else:
        db.add(GalaxyLike(galaxy_id=item_id, user_id=CURRENT_USER_ID))
    db.commit()
    return RedirectResponse(url=f"/feed/{item_id}", status_code=303)


# ------------------------------------------------------------------ ДОБАВЛЕНИЕ
@app.get("/add", response_class=HTMLResponse)
def add_page(request: Request, db: Session = Depends(get_db)):
    draft = current_draft(db)
    if draft is None:
        return start_page(request)  # черновика нет -> окно с кнопкой «Далее»
    return render(request, "add_form.html", active="add", draft=draft, form={}, error=None)


@app.post("/add/next")
def add_next(
    request: Request,
    title: str = Form(""),
    image_key: str = Form(storage.DEFAULT_IMAGE),
    video_key: str = Form(storage.DEFAULT_VIDEO),
    image_file: Optional[UploadFile] = File(None),
    video_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Кнопка «Далее»: создаёт черновик. Заполняются название, фото, видео
    и системные поля (статус, автор, даты). Остальные поля пока NULL."""
    if current_draft(db) is None:
        if not title.strip():
            return start_page(request, status_code=400, error="Введите название галактики")
        if image_file is not None and image_file.filename:
            image_key = storage.upload(image_file)
        if video_file is not None and video_file.filename:
            video_key = storage.upload(video_file)

        db.add(Galaxy(
            title=title.strip(),
            image_key=image_key or storage.DEFAULT_IMAGE,
            video_key=video_key or storage.DEFAULT_VIDEO,
            status="draft",
            creator_id=CURRENT_USER_ID,
        ))
        try:
            db.commit()
        except IntegrityError:  # второй черновик запрещён уникальным индексом в БД
            db.rollback()
    return RedirectResponse(url="/add", status_code=303)


@app.post("/add/publish")
def add_publish(
    request: Request,
    supernova: str = Form(""),
    apparent_magnitude: str = Form(""),
    distance_mpc: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    """Кнопка «Опубликовать»: сохраняет поля формы и меняет статус draft -> published."""
    draft = current_draft(db)
    if draft is None:
        return RedirectResponse(url="/add", status_code=303)

    form = dict(supernova=supernova, apparent_magnitude=apparent_magnitude,
                distance_mpc=distance_mpc, description=description)
    error = None
    try:
        mag = float(apparent_magnitude.replace(",", "."))
        dist = float(distance_mpc.replace(",", "."))
    except ValueError:
        mag = dist = None
        error = "Видимая звёздная величина и расстояние должны быть числами"
    if not supernova.strip():
        error = "Заполните обозначение сверхновой"
    elif dist is not None and dist <= 0:
        error = "Расстояние должно быть больше нуля"

    if error:
        return render(request, "add_form.html", status_code=400, active="add",
                      draft=draft, form=form, error=error)

    draft.supernova = supernova.strip()
    draft.apparent_magnitude = mag
    draft.distance_mpc = dist
    draft.description = description.strip() or None
    draft.status = "published"
    db.commit()
    return RedirectResponse(url=f"/feed/{draft.id}", status_code=303)


# ------------------------------------------------------------------ УДАЛЕНИЕ (SQL без ORM)
@app.post("/delete/{item_id}")
def delete_galaxy(item_id: int, back: str = Form("/")):
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE galaxies SET status = 'deleted' WHERE id = :id AND status <> 'deleted'"),
            {"id": item_id},
        )
    return RedirectResponse(url=back if back in ("/", "/add") else "/", status_code=303)

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
from models import GalaxyLike, GalaxyService

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
        db.query(GalaxyService)
        .filter(GalaxyService.creator_id == CURRENT_USER_ID, GalaxyService.status == "draft")
        .first()
    )



@app.get("/", response_class=HTMLResponse)
def grid(
    request: Request,
    search: Optional[str] = None,
    dist_min: Optional[float] = None,
    dist_max: Optional[float] = None,
    db: Session = Depends(get_db),
):
    published = db.query(GalaxyService).filter(GalaxyService.status == "published")

    # границы слайдера берём из данных
    max_in_db = db.query(func.max(GalaxyService.distance_mpc)).filter(GalaxyService.status == "published").scalar()
    slider_max = math.ceil(max_in_db or 50)

    lo = 0.0 if dist_min is None else max(0.0, dist_min)
    hi = float(slider_max) if dist_max is None else dist_max
    if lo > hi:
        lo, hi = hi, lo

    query = published.options(selectinload(GalaxyService.likes))
    if search:
        query = query.filter(GalaxyService.title.ilike(f"%{search.strip()}%"))
    query = query.filter(GalaxyService.distance_mpc.between(lo, hi))
    items = query.order_by(GalaxyService.id).all()

    return render(
        request, "grid.html", active="grid", items=items,
        search=search or "", dist_min=lo, dist_max=hi, slider_max=slider_max,
    )


@app.get("/feed")
def feed_start(request: Request, db: Session = Depends(get_db)):
    first = (
        db.query(GalaxyService).filter(GalaxyService.status == "published").order_by(GalaxyService.id).first()
    )
    if not first:
        return render(request, "message.html", message="В ленте пока нет опубликованных галактик", active="feed")
    return RedirectResponse(url=f"/feed/{first.id}", status_code=303)


@app.get("/feed/{item_id}", response_class=HTMLResponse)
def feed(request: Request, item_id: int, db: Session = Depends(get_db)):
    item = (
        db.query(GalaxyService)
        .filter(GalaxyService.id == item_id, GalaxyService.status == "published")
        .first()
    )
    if not item:
        return not_found(request, "Галактика удалена или не существует")

    likes_count = db.query(GalaxyLike).filter(GalaxyLike.service_id == item.id).count()
    is_liked = (
        db.query(GalaxyLike)
        .filter(GalaxyLike.service_id == item.id, GalaxyLike.user_id == CURRENT_USER_ID)
        .first()
        is not None
    )
    return render(request, "feed.html", active="feed", item=item, likes_count=likes_count, is_liked=is_liked)


@app.get("/feed/{item_id}/next")
def feed_next(item_id: int, db: Session = Depends(get_db)):
    published = db.query(GalaxyService).filter(GalaxyService.status == "published")
    nxt = published.filter(GalaxyService.id > item_id).order_by(GalaxyService.id).first()
    if not nxt:  # дошли до конца — начинаем сначала
        nxt = published.order_by(GalaxyService.id).first()
    return RedirectResponse(url=f"/feed/{nxt.id}" if nxt else "/feed", status_code=303)


@app.post("/feed/{item_id}/like")
def toggle_like(item_id: int, db: Session = Depends(get_db)):
    """Лайк хранится в таблице galaxy_likes. Повторное нажатие снимает лайк."""
    like = (
        db.query(GalaxyLike)
        .filter(GalaxyLike.service_id == item_id, GalaxyLike.user_id == CURRENT_USER_ID)
        .first()
    )
    if like:
        db.delete(like)
    else:
        db.add(GalaxyLike(service_id=item_id, user_id=CURRENT_USER_ID))
    db.commit()
    return RedirectResponse(url=f"/feed/{item_id}", status_code=303)



@app.get("/add", response_class=HTMLResponse)
def add_page(request: Request, db: Session = Depends(get_db)):
    draft = current_draft(db)
    if draft is None:
        return render(
            request, "add_start.html", active="add",
            images=storage.list_images(), videos=storage.list_videos(),
            default_image=storage.DEFAULT_IMAGE, default_video=storage.DEFAULT_VIDEO,
            media_base=storage.MEDIA_BASE,
        )
    return render(request, "add_form.html", active="add", draft=draft, form={}, error=None)


@app.post("/add/next")
def add_next(
    image_key: str = Form(storage.DEFAULT_IMAGE),
    video_key: str = Form(storage.DEFAULT_VIDEO),
    image_file: Optional[UploadFile] = File(None),
    video_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Кнопка «Далее»: создаёт черновик. Заполняются только фото, видео,
    статус, автор и дата создания — остальные поля пока NULL."""
    if current_draft(db) is None:
        if image_file is not None and image_file.filename:
            image_key = storage.upload(image_file)
        if video_file is not None and video_file.filename:
            video_key = storage.upload(video_file)

        db.add(GalaxyService(
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
    title: str = Form(""),
    supernova: str = Form(""),
    magnitude: str = Form(""),
    distance_mpc: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    draft = current_draft(db)
    if draft is None:
        return RedirectResponse(url="/add", status_code=303)

    form = dict(title=title, supernova=supernova, magnitude=magnitude,
                distance_mpc=distance_mpc, description=description)
    error = None
    try:
        mag = float(magnitude.replace(",", "."))
        dist = float(distance_mpc.replace(",", "."))
    except ValueError:
        mag = dist = None
        error = "Видимая величина и расстояние должны быть числами"
    if not title.strip() or not supernova.strip():
        error = "Заполните название и обозначение сверхновой"
    elif dist is not None and dist <= 0:
        error = "Расстояние должно быть больше нуля"

    if error:
        return render(request, "add_form.html", status_code=400, active="add",
                      draft=draft, form=form, error=error)

    draft.title = title.strip()
    draft.supernova = supernova.strip()
    draft.magnitude = mag
    draft.distance_mpc = dist
    draft.description = description.strip() or None
    draft.status = "published"
    db.commit()
    return RedirectResponse(url=f"/feed/{draft.id}", status_code=303)



@app.post("/delete/{item_id}")
def delete_service(item_id: int, back: str = Form("/")):
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE galaxy_services SET status = 'deleted' WHERE id = :id AND status <> 'deleted'"),
            {"id": item_id},
        )
    return RedirectResponse(url=back if back in ("/", "/add") else "/", status_code=303)

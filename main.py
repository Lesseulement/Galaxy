"""ЛР1: страницы по макетам Figma. Данные — в коллекции data.py (без БД),
фото и видео — в MinIO."""
import math
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import storage
from data import DRAFT, SERVICES

app = FastAPI(title="Галактики: ЛР1")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def fmt(value):
    """12.80 -> 12.8, None -> —"""
    return "—" if value is None else f"{value:g}"


templates.env.globals.update(media_url=storage.media_url, is_video=storage.is_video, fmt=fmt)
templates.env.globals["DEFAULT_VIDEO"] = storage.DEFAULT_VIDEO
storage.init_storage()  # бакет и файлы по умолчанию в MinIO


def render(request, name, status_code=200, **context):
    return templates.TemplateResponse(request=request, name=name, context=context, status_code=status_code)


def published():
    return [s for s in SERVICES if s["status"] == "published"]


# ------------------------------------------------------------------ ПЛИТКА
@app.get("/", response_class=HTMLResponse)
def grid(
    request: Request,
    search: Optional[str] = None,
    dist_min: Optional[float] = None,
    dist_max: Optional[float] = None,
):
    items = published()
    slider_max = math.ceil(max((s["distance_mpc"] for s in items), default=50))

    lo = 0.0 if dist_min is None else max(0.0, dist_min)
    hi = float(slider_max) if dist_max is None else dist_max
    if lo > hi:
        lo, hi = hi, lo

    # фильтрация по названию и по расстоянию (слайдер + кнопка «Найти»)
    if search:
        items = [s for s in items if search.strip().lower() in s["title"].lower()]
    items = [s for s in items if lo <= s["distance_mpc"] <= hi]

    return render(
        request, "grid.html", active="grid", items=items,
        search=search or "", dist_min=lo, dist_max=hi, slider_max=slider_max,
    )


# ------------------------------------------------------------------ ЛЕНТА
@app.get("/feed")
def feed_start():
    first = published()[0]
    return RedirectResponse(url=f"/feed/{first['id']}", status_code=303)


@app.get("/feed/{item_id}", response_class=HTMLResponse)
def feed(request: Request, item_id: int):
    item = next((s for s in published() if s["id"] == item_id), None)
    if item is None:
        return render(request, "message.html", status_code=404,
                      message="Галактика удалена или не существует", active=None)
    return render(request, "feed.html", active="feed", item=item)


@app.get("/feed/{item_id}/next")
def feed_next(item_id: int):
    items = published()
    nxt = next((s for s in items if s["id"] > item_id), items[0])
    return RedirectResponse(url=f"/feed/{nxt['id']}", status_code=303)


# ------------------------------------------------------------------ ДОБАВЛЕНИЕ
@app.get("/add", response_class=HTMLResponse)
def add(request: Request):
    return render(request, "add.html", active="add", draft=DRAFT)

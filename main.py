from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Galaxy App")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

MINIO_URL = "http://localhost:9000/galaxies"
CURRENT_USER_ID = 101

GALAXIES_DB = [
    {"id": 1, "title": "Галактика NGC 1300", "description": "Спиральная галактика с перемычкой.", "magnitude": 12.8, "distance_mpc": 18.5, "likes_users": [100, 101, 102], "media_key": "ngc1300.jpg", "status": "published"},
    {"id": 2, "title": "M 31 (Андромеда)", "description": "Ближайшая крупная спиральная галактика.", "magnitude": 3.44, "distance_mpc": 0.78, "likes_users": [200, 201], "media_key": "m31.jpg", "status": "published"},
    {"id": 3, "title": "NGC 4527", "description": "Спиральная галактика в созвездии Дева.", "magnitude": 10.5, "distance_mpc": 15.0, "likes_users": [300], "media_key": "ngc4527.jpg", "status": "published"},
    {"id": 4, "title": "M 82 (Сигара)", "description": "Галактика с мощным звездообразованием.", "magnitude": 8.4, "distance_mpc": 3.5, "likes_users": [400, 401], "media_key": "m82.jpg", "status": "published"},
    {"id": 5, "title": "NGC 5128 (Центавр А)", "description": "Яркая линзообразная галактика.", "magnitude": 6.84, "distance_mpc": 3.8, "likes_users": [500], "media_key": "ngc5128.gif", "status": "published"},
    {"id": 6, "title": "NGC 3982", "description": "Спиральная галактика в Большая Медведица.", "magnitude": 11.8, "distance_mpc": 20.5, "likes_users": [], "media_key": "ngc3982.gif", "status": "published"},
    {"id": 7, "title": "Черновик Галактики", "description": "Новый объект для добавления.", "magnitude": 14.1, "distance_mpc": 22.0, "likes_users": [], "media_key": "draft.jpg", "status": "draft"}
]

def prepare_item(item):
    if not item: 
        return {}
    item_copy = dict(item)
    likes_list = item.get("likes_users", [])
    item_copy["likes_count"] = len(likes_list)
    item_copy["is_liked"] = CURRENT_USER_ID in likes_list
    media_key = item.get("media_key", "")
    item_copy["media_url"] = f"{MINIO_URL}/{media_key}" if media_key else ""
    return item_copy

@app.get("/", response_class=HTMLResponse)
def get_grid(request: Request, min_distance: Optional[float] = None):
    published = [prepare_item(item) for item in GALAXIES_DB if item.get("status") == "published"]
    if min_distance is not None:
        published = [item for item in published if item.get("distance_mpc", 0) >= min_distance]
    return templates.TemplateResponse(request=request, name="grid.html", context={"items": published, "min_distance": min_distance})

@app.get("/feed/{item_id}", response_class=HTMLResponse)
def get_feed(request: Request, item_id: int, next: Optional[bool] = False):
    published = [item for item in GALAXIES_DB if item.get("status") == "published"]
    if not published:
        raise HTTPException(status_code=404, detail="No items")

    current_index = 0
    for idx, item in enumerate(published):
        if item["id"] == item_id:
            current_index = idx
            break

    if next:
        current_index = (current_index + 1) % len(published)

    selected_item = prepare_item(published[current_index])
    return templates.TemplateResponse(request=request, name="feed.html", context={"item": selected_item})

@app.post("/feed/{item_id}/like")
def toggle_like(item_id: int):
    item = next((i for i in GALAXIES_DB if i["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404)
    
    if CURRENT_USER_ID in item["likes_users"]:
        item["likes_users"].remove(CURRENT_USER_ID)
    else:
        item["likes_users"].append(CURRENT_USER_ID)
    return RedirectResponse(url=f"/feed/{item_id}", status_code=303)

@app.get("/draft", response_class=HTMLResponse)
def get_draft(request: Request):
    draft_item = next((item for item in GALAXIES_DB if item.get("status") == "draft"), None)
    return templates.TemplateResponse(request=request, name="add.html", context={"item": prepare_item(draft_item)})

@app.post("/add")
def save_galaxy(title: str = Form(...), description: str = Form(...), distance_mpc: float = Form(...), magnitude: float = Form(...), media_key: str = Form("draft.jpg")):
    new_id = max(i["id"] for i in GALAXIES_DB) + 1
    GALAXIES_DB.append({
        "id": new_id, "title": title, "description": description,
        "distance_mpc": distance_mpc, "magnitude": magnitude,
        "likes_users": [], "media_key": media_key, "status": "published"
    })
    return RedirectResponse(url="/", status_code=303)
"""ЛР4: веб-сервис «Галактики» с авторизацией через сессии (Redis) и куки.
Swagger: http://127.0.0.1:8001/docs"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException

import storage
from routers import galaxies, users

DESCRIPTION = """
Определение расстояния до галактик по сверхновым типа Ia.

**Авторизация** — через сессию: метод `POST /api/users/login` создаёт сессию в Redis
и возвращает куку `session_id`. Браузер и Swagger дальше отправляют куку сами.

* без входа (гость) — только чтение: список галактик и лента;
* после входа (создатель) — черновик, «Далее», «Опубликовать», «Удалить», лайк, выход.

Методы с замком 🔒 требуют входа, без куки сессии возвращают **401**.
Ошибки возвращаются только кодом ответа, тело пустое.
"""

TAGS = [
    {"name": "Галактики", "description": "Услуги: галактики со сверхновыми типа Ia (7 методов)"},
    {"name": "Пользователи", "description": "Регистрация, вход и выход (3 метода)"},
]

app = FastAPI(title="Galaxy API", version="4.0", description=DESCRIPTION, openapi_tags=TAGS)


# Ошибки отдаём только кодом ответа, без текста в теле
@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    return Response(status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return Response(status_code=400)


app.include_router(galaxies.router, prefix="/api")
app.include_router(users.router, prefix="/api")

storage.init_storage()

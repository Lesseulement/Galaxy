"""ЛР3: веб-сервис (REST API) для приложения «Галактики».
Без шаблонов: только JSON и коды ответа HTTP."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException

import storage
from routers import galaxies, users

app = FastAPI(title="Galaxy API", description="Определение расстояния до галактик по сверхновым типа Ia")


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

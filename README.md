# ЛР3. Веб-сервис «Галактики»

Определение расстояния до галактик по сверхновым типа Ia.
**Услуги** — галактики. **Заявка** (следующие лабораторные) — расчёт расстояния до выбранных галактик
по видимой звёздной величине сверхновой.

Стек: FastAPI, PostgreSQL + SQLAlchemy (ORM), MinIO (фото и видео), Docker Compose.
Шаблонов нет: сервис отдаёт только JSON и коды ответа HTTP. Тестирование — Postman
(коллекция `Galaxy.postman_collection.json`).

## Запуск

```bash
docker compose down -v      # при первом запуске: пересоздать БД по db/schema.sql
docker compose up -d
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Базовый адрес API: `http://127.0.0.1:8001/api`

## Структура

| Файл | Назначение |
|---|---|
| `main.py` | приложение, подключение роутеров, обработка ошибок (только код ответа) |
| `routers/galaxies.py` | домен услуги (галактики) |
| `routers/users.py` | домен пользователь |
| `models.py` | ORM-модели |
| `schemas.py` | сериализаторы запросов и ответов |
| `deps.py` | функция-singleton текущего пользователя |
| `storage.py` | работа с MinIO |
| `database.py` | подключение к PostgreSQL |
| `db/schema.sql` | таблицы, ограничения, начальные данные |

## Текущий пользователь

Авторизация появится в ЛР4. Пока создатель во всех методах зафиксирован константой
`CREATOR_ID = 1` через функцию-singleton `current_user_id()` в `deps.py`.
Методы получают пользователя через `Depends(current_user_id)`.

## HTTP-методы

### Домен услуги (галактики)

| Метод | URL | Описание | Тело запроса | Ответ |
|---|---|---|---|---|
| GET | `/api/galaxies` | список опубликованных галактик с фильтрацией | — (параметры `search`, `dist_min`, `dist_max`) | 200, массив галактик |
| GET | `/api/galaxies/feed` | лента: без `id` — первая галактика; с `id` — эта галактика; с `id` и `next=true` — следующая | — (параметры `id`, `next`) | 200, галактика; 404 |
| GET | `/api/galaxies/draft` | черновик текущего пользователя (не больше одного), id не указывается | — | 200, галактика; 404 |
| POST | `/api/galaxies` | добавление галактики: создаётся черновик; фото и видео передаются файлами | form-data: `image` (файл), `video` (файл), `title`, `supernova`, `magnitude`, `distance_mpc`, `description` | 201, галактика; 400; 409 — черновик уже есть |
| PUT | `/api/galaxies/draft/publish` | публикация черновика (смена статуса) | — | 200, галактика; 400 — не заполнены поля; 404 |
| DELETE | `/api/galaxies/{id}` | мягкое удаление (статус deleted), только свои галактики | — | 200; 403 — чужая; 404 |
| POST | `/api/galaxies/{id}/like` | лайк текущего пользователя | JSON `{"like": 1}` — поставить, `{"like": 0}` — отменить | 200, `{"likes_count", "is_liked"}`; 404 |

### Домен пользователь

| Метод | URL | Описание | Тело запроса | Ответ |
|---|---|---|---|---|
| POST | `/api/users/register` | регистрация | JSON `{"username", "password"}` | 201, `{"id", "username"}`; 409 — логин занят |
| POST | `/api/users/login` | аутентификация (заглушка до ЛР4) | — | 200 |
| POST | `/api/users/logout` | деавторизация (заглушка до ЛР4) | — | 200 |

### Ответ по галактике

Набор полей всегда один и тот же. Незаполненное поле приходит как `null`.
Статус и системные поля (создатель, даты) наружу не отдаются и с клиента не принимаются.

```json
{
  "id": 1,
  "title": "NGC 1300",
  "description": "Спиральная галактика с перемычкой в созвездии Эридан",
  "supernova": "SN 2002fk",
  "magnitude": 12.8,
  "distance_mpc": 18.5,
  "image_url": "http://localhost:9000/galaxies.media/ngc1300.jpg",
  "video_url": "http://localhost:9000/galaxies.media/default.mp4",
  "likes_count": 3,
  "is_liked": 1,
  "is_mine": 1
}
```

`is_liked` — 1, если текущий пользователь поставил лайк; `is_mine` — 1, если создатель галактики совпадает с текущим пользователем.

### Коды ответа

Ошибки возвращаются только кодом, без текста в теле: 200/201 — успешно, 400 — неверные данные,
403 — нет прав, 404 — не найдено, 409 — конфликт (черновик уже есть, логин занят).

## Таблицы БД

### users — пользователи

| Поле | Тип | Ограничения |
|---|---|---|
| id | SERIAL | PK |
| username | VARCHAR(50) | NOT NULL, UNIQUE |
| password_hash | VARCHAR(255) | хэш пароля |

### galaxy_services — галактики (услуги)

| Поле | Тип | Ограничения |
|---|---|---|
| id | SERIAL | PK |
| image_key | VARCHAR(255) | NOT NULL, DEFAULT 'default.jpg' — имя файла фото в MinIO |
| video_key | VARCHAR(255) | NOT NULL, DEFAULT 'default.mp4' — имя файла видео в MinIO |
| status | service_status (draft, published, deleted) | NOT NULL, DEFAULT 'draft' |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP |
| creator_id | INT | NOT NULL, FK → users.id |
| title | VARCHAR(100) | NULL, обязательно для публикации |
| description | TEXT | NULL |
| supernova | VARCHAR(30) | NULL, обязательно для публикации |
| magnitude | NUMERIC(5,2) | NULL, видимая звёздная величина сверхновой; обязательно для публикации |
| distance_mpc | NUMERIC(8,2) | NULL, > 0, расстояние в Мпк; обязательно для публикации |

Один черновик на пользователя — уникальный индекс `uq_one_draft_per_user`.

### galaxy_likes — лайки (многие-ко-многим)

| Поле | Тип | Ограничения |
|---|---|---|
| id | SERIAL | PK |
| user_id | INT | NOT NULL, FK → users.id |
| service_id | INT | NOT NULL, FK → galaxy_services.id |

Пара `(user_id, service_id)` уникальна.

## Переходы статусов

`draft` → `published` (PUT публикации), `draft`/`published` → `deleted` (DELETE).
Вернуть в черновик нельзя.

## Файлы в MinIO

Бакет `galaxies.media`. Новые файлы сохраняются под сгенерированными латинскими именами
вида `image_<uuid>.jpg`, `video_<uuid>.mp4`, в БД хранится только имя файла.

# ЛР4. Веб-сервис «Галактики»: авторизация и Swagger

Определение расстояния до галактик по сверхновым типа Ia.
**Услуги** — галактики. **Заявка** — расчёт расстояния до выбранных галактик
по видимой звёздной величине сверхновой.

Стек: FastAPI, PostgreSQL + SQLAlchemy (ORM), MinIO (фото и видео), **Redis (сессии)**, Docker Compose.
Документация методов — Swagger: `http://127.0.0.1:8001/docs`.

## Запуск

```bash
docker compose down -v      # пересоздать БД по db/01_schema.sql и db/02_insert.sql
docker compose up -d        # minio, db, redis, adminer
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

| Что | Адрес |
|---|---|
| API | http://127.0.0.1:8001/api |
| Swagger | http://127.0.0.1:8001/docs |
| MinIO | http://localhost:9001 (admin / password123) |
| Adminer | http://localhost:8081 (сервер `db`, postgres / postgrespassword, БД galaxy_db) |
| Redis | `docker exec -it galaxy_redis redis-cli` |

Тестовый пользователь: `veronika` / `password123`.

## Авторизация (сессии и куки)

1. `POST /api/users/login` с `{"username", "password"}` проверяет пароль по хэшу из БД.
2. Сервер создаёт сессию в Redis: ключ `session:<id>`, значение `{"user_id", "username"}`, срок жизни 24 часа.
3. В ответе кука `session_id=<id>` (HttpOnly, SameSite=Lax). Браузер, Swagger и Postman дальше отправляют её сами.
4. В каждом методе пользователь берётся из сессии по куке (`deps.py`):
   `current_user` — для методов создателя, без сессии **401**;
   `current_user_optional` — для чтения, гость получает `null` (`is_liked = 0`, `is_mine = 0`).
5. При создании галактики `creator_id` заполняется автоматически из сессии.
6. `POST /api/users/logout` удаляет сессию из Redis и куку.

Посмотреть сессии в Redis:

```
docker exec -it galaxy_redis redis-cli
KEYS *
GET session:<id>
TTL session:<id>
```

## Структура

| Файл | Назначение |
|---|---|
| `main.py` | приложение, описание для Swagger, ошибки — только кодом ответа |
| `routers/galaxies.py` | домен «Галактики» — 7 методов |
| `routers/users.py` | домен «Пользователи» — 3 метода (регистрация, вход, выход) |
| `sessions.py` | сессии в Redis: создать, получить, удалить |
| `deps.py` | текущий пользователь по куке сессии |
| `models.py` | ORM-модели `User`, `Galaxy`, `GalaxyLike` |
| `schemas.py` | сериализаторы запросов и ответов |
| `storage.py` | работа с MinIO |
| `database.py` | подключение к PostgreSQL |
| `db/01_schema.sql` | таблицы, ограничения, триггер даты обновления |
| `db/02_insert.sql` | начальные данные (скрипт insert) |

## Кнопки интерфейса и методы

| Страница | Кнопка / действие | Метод | Доступ |
|---|---|---|---|
| Плитка | «Найти» (слайдер видимой величины) | `GET /api/galaxies` | гость и создатель |
| Плитка | «Удалить» | `DELETE /api/galaxies/{id}` | создатель |
| Лента | открыть ленту / стрелка «следующая» | `GET /api/galaxies/feed` | гость и создатель |
| Лента | сердечко | `POST /api/galaxies/{id}/like` | создатель |
| Регистрация сверхновой | «Далее» | `POST /api/galaxies` | создатель |
| Регистрация сверхновой | открытие формы черновика | `GET /api/galaxies/draft` | создатель |
| Регистрация сверхновой | «Опубликовать» | `PUT /api/galaxies/draft/publish` | создатель |
| Регистрация сверхновой | «Удалить черновик» | `DELETE /api/galaxies/{id}` | создатель |
| Вход | «Зарегистрироваться» | `POST /api/users/register` | гость |
| Вход | «Войти» | `POST /api/users/login` | гость |
| Меню | «Выйти» | `POST /api/users/logout` | создатель |

## HTTP-методы (10)

### Домен «Галактики» — `/api/galaxies`

| № | Метод | URL | Описание | Доступ | Тело / параметры | Ответ |
|---|---|---|---|---|---|---|
| 1 | GET | `/api/galaxies` | список опубликованных галактик, фильтр по видимой звёздной величине | все | `magnitude_from`, `magnitude_to`, необяз. `title` | 200, массив |
| 2 | GET | `/api/galaxies/feed` | лента: без `id` — первая; `?id=N` — эта; `?id=N&next=true` — следующая | все | `id`, `next` | 200; 404 |
| 3 | GET | `/api/galaxies/draft` | поля черновика текущего пользователя | вход | — | 200; 401; 404 |
| 4 | POST | `/api/galaxies` | **«Далее»**: создать черновик, файлы в MinIO, создатель из сессии | вход | form-data: `title`, `image`, `video` | 201; 400; 401; 409 |
| 5 | PUT | `/api/galaxies/draft/publish` | **«Опубликовать»**: поля формы, статус `draft` → `published` | вход | JSON: `supernova`, `apparent_magnitude`, `distance_mpc`, `description` | 200; 400; 401; 404 |
| 6 | DELETE | `/api/galaxies/{id}` | мягкое удаление (статус `deleted`), только свои | вход | — | 200; 401; 403; 404 |
| 7 | POST | `/api/galaxies/{id}/like` | лайк текущего пользователя | вход | JSON `{"like": 1}` / `{"like": 0}` | 200; 401; 404 |

### Домен «Пользователи» — `/api/users`

| № | Метод | URL | Описание | Доступ | Тело | Ответ |
|---|---|---|---|---|---|---|
| 8 | POST | `/api/users/register` | регистрация, пароль хранится хэшем | все | JSON `{"username", "password"}` | 201; 400; 409 |
| 9 | POST | `/api/users/login` | аутентификация: сессия в Redis + кука `session_id` | все | JSON `{"username", "password"}` | 200 `{"id", "username"}`; 401 |
| 10 | POST | `/api/users/logout` | деавторизация: удаление сессии и куки | вход | — | 200; 401 |

### Ответ по галактике

Набор полей всегда один и тот же. Незаполненное поле приходит как `null`.
Статус, создатель и даты наружу не отдаются и с клиента не принимаются.

```json
{
  "id": 7,
  "title": "NGC 1309",
  "supernova": null,
  "apparent_magnitude": null,
  "distance_mpc": null,
  "description": null,
  "image_url": "http://localhost:9000/galaxies.media/image_1942de48….jpg",
  "video_url": "http://localhost:9000/galaxies.media/video_b6854005….mp4",
  "likes_count": 0,
  "is_liked": 0,
  "is_mine": 1
}
```

`is_liked` — 1, если текущий пользователь поставил лайк; `is_mine` — 1, если создатель галактики — текущий пользователь.

### Коды ответа

Ошибки возвращаются только кодом, без текста в теле: 200/201 — успешно, 400 — неверные данные,
401 — не выполнен вход, 403 — нет прав (чужая галактика), 404 — не найдено, 409 — конфликт (черновик уже есть, логин занят).

## Таблицы БД

### users — пользователи

| Поле | Тип | Ограничения |
|---|---|---|
| id | SERIAL | PK |
| username | VARCHAR(50) | NOT NULL, UNIQUE |
| password_hash | VARCHAR(255) | NOT NULL, хэш пароля |

### galaxies — галактики (услуги)

| Поле | Тип | Ограничения | Когда заполняется |
|---|---|---|---|
| id | SERIAL | PK | автоматически |
| title | VARCHAR(100) | NOT NULL | кнопка «Далее» |
| image_key | VARCHAR(255) | NOT NULL, DEFAULT 'default.jpg' — имя файла фото в MinIO | кнопка «Далее» |
| video_key | VARCHAR(255) | NOT NULL, DEFAULT 'default.mp4' — имя файла видео в MinIO | кнопка «Далее» |
| status | galaxy_status (draft, published, deleted) | NOT NULL, DEFAULT 'draft' | сервер |
| creator_id | INT | NOT NULL, FK → users.id | сервер |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP — дата создания | сервер |
| updated_at | TIMESTAMP | NOT NULL — дата обновления, ставится триггером при каждом UPDATE | сервер |
| supernova | VARCHAR(30) | NULL у черновика | кнопка «Опубликовать» |
| apparent_magnitude | NUMERIC(5,2) | NULL у черновика — видимая звёздная величина сверхновой, m | кнопка «Опубликовать» |
| distance_mpc | NUMERIC(8,2) | NULL у черновика, > 0 — расстояние, Мпк | кнопка «Опубликовать» |
| description | TEXT | NULL — описание | кнопка «Опубликовать» (необязательное) |

Ограничения: `chk_published_filled` — опубликованная галактика обязана иметь `supernova`,
`apparent_magnitude`, `distance_mpc`; `uq_galaxies_one_draft` — не больше одного черновика на пользователя.

### galaxy_likes — лайки (многие-ко-многим)

| Поле | Тип | Ограничения |
|---|---|---|
| id | SERIAL | PK |
| user_id | INT | NOT NULL, FK → users.id |
| galaxy_id | INT | NOT NULL, FK → galaxies.id |

Пара `(user_id, galaxy_id)` уникальна.

## Переходы статусов

`draft` → `published` (PUT, кнопка «Опубликовать»), `draft`/`published` → `deleted` (DELETE).
Вернуть в черновик нельзя.

## Файлы в MinIO

Бакет `galaxies.media`. Новые файлы сохраняются под сгенерированными латинскими именами
вида `image_<uuid>.jpg`, `video_<uuid>.mp4`, в БД хранится только имя файла.

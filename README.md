# ЛР3. Веб-сервис «Галактики»

Определение расстояния до галактик по сверхновым типа Ia.
**Услуги** — галактики. **Заявка** (следующие лабораторные) — расчёт расстояния до выбранных галактик
по видимой звёздной величине сверхновой.

Стек: FastAPI, PostgreSQL + SQLAlchemy (ORM), MinIO (фото и видео), Docker Compose.
Шаблонов нет: сервис отдаёт только JSON и коды ответа HTTP. Тестирование — Postman
(коллекция `Galaxy.postman_collection.json`, 10 запросов — по одному на метод).

## Запуск

```bash
docker compose down -v      # пересоздать БД по db/01_schema.sql и db/02_insert.sql
docker compose up -d
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Базовый адрес API: `http://127.0.0.1:8001/api`

## Структура

| Файл | Назначение |
|---|---|
| `main.py` | приложение, подключение роутеров, ошибки — только кодом ответа |
| `routers/galaxies.py` | домен «Галактики» — 7 методов |
| `routers/users.py` | домен «Пользователи» — 3 метода |
| `models.py` | ORM-модели `User`, `Galaxy`, `GalaxyLike` |
| `schemas.py` | сериализаторы запросов и ответов |
| `deps.py` | функция-singleton текущего пользователя |
| `storage.py` | работа с MinIO |
| `database.py` | подключение к PostgreSQL |
| `db/01_schema.sql` | таблицы, ограничения, триггер даты обновления |
| `db/02_insert.sql` | начальные данные (скрипт insert) |

## Текущий пользователь

Авторизация появится в ЛР4. Пока создатель во всех методах зафиксирован константой
`CREATOR_ID = 1` через функцию-singleton `current_user_id()` в `deps.py`.
Методы получают пользователя через `Depends(current_user_id)`.

## Кнопки интерфейса и методы

| Страница | Кнопка / действие | Метод | Какие поля передаются |
|---|---|---|---|
| Плитка | «Найти» (слайдер видимой величины) | `GET /api/galaxies` | `magnitude_from`, `magnitude_to` |
| Плитка | «Удалить» | `DELETE /api/galaxies/{id}` | — |
| Лента | открыть ленту / стрелка «следующая» | `GET /api/galaxies/feed` | `id`, `next` |
| Лента | сердечко | `POST /api/galaxies/{id}/like` | `like` (0/1) |
| Регистрация сверхновой | «Далее» | `POST /api/galaxies` | `title`, файл `image`, файл `video` |
| Регистрация сверхновой | открытие формы черновика | `GET /api/galaxies/draft` | — |
| Регистрация сверхновой | «Опубликовать» | `PUT /api/galaxies/draft/publish` | `supernova`, `apparent_magnitude`, `distance_mpc`, `description` |
| Регистрация сверхновой | «Удалить черновик» | `DELETE /api/galaxies/{id}` | — |
| Регистрация пользователя | «Зарегистрироваться» | `POST /api/users/register` | `username`, `password` |
| Регистрация пользователя | «Войти» / «Выйти» | `POST /api/users/login`, `POST /api/users/logout` | заглушки до ЛР4 |

## HTTP-методы (10)

### Домен «Галактики» — `/api/galaxies`

| № | Метод | URL | Описание | Тело запроса | Ответ |
|---|---|---|---|---|---|
| 1 | GET | `/api/galaxies` | список опубликованных галактик с фильтрацией по видимой звёздной величине | — (параметры `magnitude_from`, `magnitude_to`, необяз. `title`) | 200, массив галактик |
| 2 | GET | `/api/galaxies/feed` | лента: без `id` — первая галактика; `?id=N` — эта; `?id=N&next=true` — следующая | — (параметры `id`, `next`) | 200, галактика; 404 |
| 3 | GET | `/api/galaxies/draft` | поля черновика текущего пользователя (не больше одного), id не указывается | — | 200, галактика; 404 |
| 4 | POST | `/api/galaxies` | **кнопка «Далее»**: создаёт черновик, файлы фото и видео сохраняются в MinIO | form-data: `title`, `image` (файл), `video` (файл) | 201, галактика; 400; 409 — черновик уже есть |
| 5 | PUT | `/api/galaxies/draft/publish` | **кнопка «Опубликовать»**: сохраняет поля формы и меняет статус `draft` → `published` | JSON: `supernova`, `apparent_magnitude`, `distance_mpc`, `description` (необяз.) | 200, галактика; 400; 404 |
| 6 | DELETE | `/api/galaxies/{id}` | мягкое удаление (статус `deleted`), только свои галактики | — | 200; 403 — чужая; 404 |
| 7 | POST | `/api/galaxies/{id}/like` | лайк текущего пользователя | JSON `{"like": 1}` — поставить, `{"like": 0}` — отменить | 200, `{"likes_count", "is_liked"}`; 404 |

### Домен «Пользователи» — `/api/users`

| № | Метод | URL | Описание | Тело запроса | Ответ |
|---|---|---|---|---|---|
| 8 | POST | `/api/users/register` | регистрация | JSON `{"username", "password"}` | 201, `{"id", "username"}`; 409 — логин занят |
| 9 | POST | `/api/users/login` | аутентификация (заглушка до ЛР4) | — | 200 |
| 10 | POST | `/api/users/logout` | деавторизация (заглушка до ЛР4) | — | 200 |

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
403 — нет прав, 404 — не найдено, 409 — конфликт (черновик уже есть, логин занят).

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

# ЛР2. Галактики: определение расстояния по сверхновым типа Ia

Страницы по макетам: «Лента», «Регистрация сверхновой» (добавление), «Плитка».
Данные — PostgreSQL через ORM (SQLAlchemy), удаление — SQL-запросом без ORM, фото и видео — MinIO.

## Запуск

```bash
docker compose down -v      # пересоздать БД: выполнятся db/01_schema.sql и db/02_insert.sql
docker compose up -d
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

| Что | Адрес |
|---|---|
| Плитка (фильтр по видимой звёздной величине) | http://127.0.0.1:8001 |
| Лента | http://127.0.0.1:8001/feed |
| Добавление | http://127.0.0.1:8001/add |
| MinIO | http://localhost:9001 (admin / password123) |
| Adminer | http://localhost:8081 (сервер `db`, postgres / postgrespassword, БД galaxy_db) |

## База данных

- `db/01_schema.sql` — таблицы `users`, `galaxies`, `galaxy_likes`, все ограничения и триггер даты обновления.
- `db/02_insert.sql` — скрипт с начальными данными (insert). `id` не указываются — их выдаёт SERIAL;
  `created_at` и `updated_at` указаны явно.

Обязательные поля (NOT NULL): `users.username`, `users.password_hash`, `galaxies.title`, `image_key`,
`video_key`, `status`, `creator_id`, `created_at`, `updated_at`. Поля `supernova`, `apparent_magnitude`,
`distance_mpc` пустые, пока галактика — черновик; опубликовать без них нельзя (`chk_published_filled`).
У пользователя не больше одного черновика (`uq_galaxies_one_draft`).

## Кнопки и что они заполняют

| Кнопка | Что делает | Поля |
|---|---|---|
| «Далее» | создаёт черновик (INSERT через ORM) | `title`, `image_key`, `video_key` (+ системные `status`, `creator_id`, даты) |
| «Опубликовать» | заполняет поля и меняет статус draft → published | `supernova`, `apparent_magnitude`, `distance_mpc`, `description` |
| «Удалить», «Удалить черновик» | логическое удаление SQL-запросом `UPDATE galaxies SET status = 'deleted'` | `status` |
| «Найти» | фильтр плитки по видимой звёздной величине (слайдеры «от» и «до») | — |
| сердечко | лайк / снятие лайка (таблица `galaxy_likes`) | — |

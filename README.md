# Определение расстояния до галактик по сверхновым типа Ia

Лабораторные работы 1–2 по разработке интернет-приложений.

**Услуги** — список галактик. **Заявка** (следующие лабораторные) — расчёт расстояния
до каждой выбранной галактики по видимой звёздной величине сверхновой типа Ia внутри неё.

Стек: FastAPI + Jinja2, PostgreSQL (SQLAlchemy ORM), MinIO (фото и видео), Docker Compose.

## Структура

```
galaxy/
├── main.py              # маршруты: сетка, лента, добавление, лайки, удаление
├── models.py            # ORM-модели
├── database.py          # подключение к PostgreSQL
├── storage.py           # MinIO: ссылки, список файлов, загрузка
├── requirements.txt
├── docker-compose.yml   # postgres + minio + minio-init + adminer
├── db/schema.sql        # таблицы, ограничения, тестовые данные
├── minio/media/         # файлы, которые автоматически кладутся в бакет
├── templates/           # base, grid, feed, add_start, add_form, message
├── static/style.css
└── docs/                # скриншоты и ER-диаграмма
```

## Запуск

```bash
# 1. Положить свои картинки галактик в minio/media/ (рядом с default.jpg и default.mp4)
#    Имена должны совпадать с db/schema.sql: "NGC 1300.jpg", "M 82 (Сигара).jpg" и т.д.

# 2. Поднять инфраструктуру. Флаг -v при первом запуске ОБЯЗАТЕЛЕН:
#    он удаляет старую БД, иначе schema.sql не выполнится
docker compose down -v
docker compose up -d

# 3. Python-окружение и приложение
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn main:app --reload
```

| Что | Адрес |
|---|---|
| Приложение (сетка) | http://localhost:8000 |
| Лента | http://localhost:8000/feed |
| Добавление | http://localhost:8000/add |
| MinIO консоль | http://localhost:9001 (admin / password123) |
| Adminer | http://localhost:8081 (сервер `db`, postgres / postgrespassword, БД galaxy_db) |

## Пояснения по исправлениям

| № | Замечание | Что исправлено | Где |
|---|---|---|---|
| 1 | Пояснения, скриншоты, git | Этот README, папка `docs/screenshots`, `.gitignore`, инструкция по git ниже | `README.md`, `docs/` |
| 2 | `created_at` пустой, insert неправильный | `created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP` — задаёт сама БД, поэтому пустым быть не может ни при вставке из приложения, ни из Adminer. В insert больше не указываются `id` (раньше явные id ломали SERIAL и приложение падало с duplicate key) | `db/schema.sql` |
| 3 | Ограничения на обязательные поля в БД | `NOT NULL` на поля, заполняемые кнопкой «Далее»; `CHECK`: опубликованная галактика должна иметь название, сверхновую, величину и расстояние; название не пустое; расстояние > 0; уникальный индекс — не больше одного черновика на пользователя | `db/schema.sql` |
| 4 | По умолчанию не MinIO | Все фото и видео, включая «по умолчанию» (`default.jpg`, `default.mp4`), берутся только из MinIO. Сервис `minio-init` сам создаёт бакет `galaxies.media`, открывает его на чтение и загружает файлы. Имена с пробелами и кириллицей корректно кодируются в ссылках | `docker-compose.yml`, `storage.py` |
| 5 | Удалить — кнопки одного стиля по теме | Один класс `.btn` для всех кнопок (Найти, Далее, Опубликовать, Удалить, Удалить черновик), цвета из макетов | `static/style.css` |
| 6 | Фильтрация числами, слайдером с кнопкой | Два слайдера «от / до» по расстоянию (Мпк) с отображением значений и кнопкой «Найти». Максимум слайдера берётся из БД. Поиск по названию сохранён в той же форме | `templates/grid.html`, `main.py` → `grid()` |
| 7 | Добавление не работает; если черновика нет — окно с «Далее» | `/add`: если черновика нет — окно выбора фото и видео с кнопкой «Далее», она создаёт черновик. Если черновик есть — форма заполнения и публикации | `main.py` → `add_page`, `add_next`, `add_publish` |
| 8 | Только нужные поля; сверху фото и видео на обоих шагах, выбор только до «Далее», друг под другом | Фото и видео показываются сверху, друг под другом, на обоих шагах. Выбор (из файлов в MinIO или загрузка нового файла) — только до «Далее». После — только поля для ввода, без скрытых и лишних | `templates/add_start.html`, `templates/add_form.html` |
| 9 | Параметры в ленте справа | Видимая величина и расстояние — в правой колонке вместе с лайком и кнопкой «следующая» | `templates/feed.html` |
| 10 | Лайки хранить в БД | Таблица `galaxy_likes` (уникальная пара пользователь–галактика). Кнопка ставит/снимает лайк, количество считается из БД и в ленте, и в сетке | `main.py` → `toggle_like` |
| 11 | ER в StarUML | Описание сущностей и связей для StarUML — ниже; диаграмма сохраняется в `docs/er.mdj`, картинка — в `docs/er.png` | `docs/` |
| 12 | Убрать сетку | Убрана страница-сетка черновиков (`draft.html`): черновик у пользователя один, он открывается на странице добавления. Неиспользуемый `detail.html` тоже удалён | `templates/` |
| 13 | Необязательные поля услуги (что заполняется по «Далее») | По «Далее» заполняются: `image_key`, `video_key`, `status`, `created_at`, `creator_id` — они NOT NULL. Необязательные (NULL, пока черновик): `title`, `description`, `supernova`, `magnitude`, `distance_mpc`. В форме описание помечено «(необязательно)» | `db/schema.sql`, `models.py` |
| 14 | `created_at` убрать где не просили | `created_at` остался только у услуги. Лишнее поле `formed_at` удалено, в пользователях и лайках дат нет | `db/schema.sql`, `models.py` |

Другие ошибки, из-за которых приложение не запускалось:

- не было `requirements.txt`, а без `python-multipart` FastAPI падает при старте на `Form(...)`;
- `create_all()` в коде конфликтовал с `schema.sql` (разные типы статуса) — теперь таблицы создаёт только `schema.sql`;
- форма добавления отправлялась на `/add`, которого не было;
- ссылки на картинки вели в несуществующий бакет `galaxies` и на несуществующие файлы (`ngc1300.jpg`);
- кнопка лайка вела на несуществующий маршрут, «следующая» не работала.

## Удаление

Удаление логическое, выполняется SQL-запросом без ORM (`main.py` → `delete_service`):

```sql
UPDATE galaxy_services SET status = 'deleted' WHERE id = :id AND status <> 'deleted';
```

## Git

```bash
git init
git add .
git commit -m "Лабораторные 1-2: галактики, сверхновые Ia"
git branch -M main
git remote add origin https://github.com/<логин>/<репозиторий>.git
git push -u origin main
```

## ER-диаграмма в StarUML

1. File → New, затем Model → Add Diagram → **ER Diagram**.
2. Добавить три сущности (Entity) и колонки (PK, FK, nullable отмечаются в свойствах колонки):

**users**: `id` PK SERIAL · `username` VARCHAR(50) NOT NULL UNIQUE

**galaxy_services**: `id` PK SERIAL · `image_key` VARCHAR(255) NOT NULL · `video_key` VARCHAR(255) NOT NULL ·
`status` service_status NOT NULL · `created_at` TIMESTAMP NOT NULL · `creator_id` INT FK → users NOT NULL ·
`title` VARCHAR(100) NULL · `description` TEXT NULL · `supernova` VARCHAR(30) NULL ·
`magnitude` NUMERIC(5,2) NULL · `distance_mpc` NUMERIC(8,2) NULL

**galaxy_likes**: `id` PK SERIAL · `user_id` INT FK → users NOT NULL · `service_id` INT FK → galaxy_services NOT NULL

3. Связи (One-to-Many): users 1 — 0..* galaxy_services; users 1 — 0..* galaxy_likes; galaxy_services 1 — 0..* galaxy_likes.
4. Сохранить как `docs/er.mdj`, экспортировать картинку (File → Export Diagram As → PNG) в `docs/er.png`.

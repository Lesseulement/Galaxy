-- =====================================================================
-- БД «Определение расстояния до галактик по сверхновым типа Ia»
-- Файл выполняется автоматически при ПЕРВОМ запуске контейнера postgres
-- (docker-entrypoint-initdb.d). Все ограничения — здесь, в БД.
-- =====================================================================

-- Статусы услуги: черновик, опубликована, удалена
CREATE TYPE service_status AS ENUM ('draft', 'published', 'deleted');

-- 1. Пользователи
CREATE TABLE users (
    id       SERIAL      PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE
);


CREATE TABLE galaxy_services (
    id           SERIAL         PRIMARY KEY,

    -- Заполняются кнопкой «Далее», обязательные
    image_key    VARCHAR(255)   NOT NULL DEFAULT 'default.jpg',  
    video_key    VARCHAR(255)   NOT NULL DEFAULT 'default.mp4',  
    status       service_status NOT NULL DEFAULT 'draft',
    created_at   TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator_id   INT            NOT NULL,

    -- Заполняются после «Далее», необязательные
    title        VARCHAR(100),
    description  TEXT,
    supernova    VARCHAR(30),     
    magnitude    NUMERIC(5,2),    
    distance_mpc NUMERIC(8,2),    

    CONSTRAINT fk_service_creator FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE RESTRICT,

    -- опубликовать можно только полностью заполненную галактику
    CONSTRAINT chk_published_filled CHECK (
        status <> 'published'
        OR (title IS NOT NULL AND supernova IS NOT NULL AND magnitude IS NOT NULL AND distance_mpc IS NOT NULL)
    ),
    CONSTRAINT chk_title_not_blank CHECK (title IS NULL OR btrim(title) <> ''),
    CONSTRAINT chk_distance_positive CHECK (distance_mpc IS NULL OR distance_mpc > 0)
);

-- у пользователя может быть только ОДИН черновик
CREATE UNIQUE INDEX uq_one_draft_per_user ON galaxy_services (creator_id) WHERE status = 'draft';

-- 3. Лайки (м-м пользователь <-> галактика)
CREATE TABLE galaxy_likes (
    id         SERIAL PRIMARY KEY,
    user_id    INT    NOT NULL,
    service_id INT    NOT NULL,

    CONSTRAINT fk_like_user    FOREIGN KEY (user_id)    REFERENCES users(id)           ON DELETE RESTRICT,
    CONSTRAINT fk_like_service FOREIGN KEY (service_id) REFERENCES galaxy_services(id) ON DELETE RESTRICT,
    CONSTRAINT uq_like_user_service UNIQUE (user_id, service_id)
);

-- =====================================================================
-- Тестовые данные. id не указываем — их выдаёт SERIAL,
-- поэтому последовательности не ломаются.
-- =====================================================================

INSERT INTO users (username) VALUES
    ('veronika'),      -- id 1, текущий пользователь приложения
    ('astro_fan'),     -- id 2
    ('hubble_lover');  -- id 3

-- Звёздные величины и расстояния — учебные, округлённые
INSERT INTO galaxy_services
    (title, description, supernova, magnitude, distance_mpc, image_key, video_key, status, created_at, creator_id)
VALUES
    ('NGC 1300', 'Спиральная галактика с перемычкой в созвездии Эридан', 'SN 2002fk', 12.80, 18.50,
        'NGC 1300.jpg', 'default.mp4', 'published', '2026-09-01 10:00:00', 1),
    ('M 82 (Сигара)', 'Галактика со вспышкой звездообразования в Большой Медведице', 'SN 2014J', 10.50, 3.50,
        'M 82 (Сигара).jpg', 'default.mp4', 'published', '2026-09-01 10:05:00', 1),
    ('NGC 4527', 'Спиральная галактика в созвездии Девы', 'SN 1991T', 11.50, 13.00,
        'NGC 4527.jpg', 'default.mp4', 'published', '2026-09-01 10:10:00', 1),
    ('NGC 5128 (Центавр A)', 'Линзовидная галактика, мощный радиоисточник', 'SN 1986G', 11.40, 3.80,
        'NGC 5128 (Центавр A).gif', 'default.mp4', 'published', '2026-09-01 10:15:00', 1),
    ('NGC 3982', 'Спиральная галактика в Большой Медведице', 'SN 1998aq', 12.30, 20.00,
        'NGC 3982.gif', 'default.mp4', 'published', '2026-09-01 10:20:00', 1),
    ('M 31 (Андромеда)', 'Ближайшая крупная спиральная галактика', 'SN 1885A', 5.90, 0.78,
        'M 31 (Андромеда).jpg', 'default.mp4', 'deleted', '2026-09-01 10:25:00', 1);

-- Черновик: заполнено только то, что задаётся кнопкой «Далее»
INSERT INTO galaxy_services (image_key, video_key, status, creator_id)
VALUES ('NGC 1300_1.jpg', 'default.mp4', 'draft', 1);

-- Лайки
INSERT INTO galaxy_likes (user_id, service_id) VALUES
    (1, 1), (2, 1), (3, 1),
    (2, 2),
    (1, 3), (3, 3),
    (2, 4), (3, 4),
    (3, 5);

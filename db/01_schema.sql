

-- Статусы галактики: черновик, опубликована, удалена
CREATE TYPE galaxy_status AS ENUM ('draft', 'published', 'deleted');

-- 1. Пользователи
CREATE TABLE users (
    id            SERIAL       PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,          -- хранится только хэш пароля

    CONSTRAINT chk_username_not_blank CHECK (btrim(username) <> '')
);

CREATE TABLE galaxies (
    id                 SERIAL        PRIMARY KEY,
    title              VARCHAR(100)  NOT NULL,
    image_key          VARCHAR(255)  NOT NULL DEFAULT 'default.jpg', 
    video_key          VARCHAR(255)  NOT NULL DEFAULT 'default.mp4',  
    status             galaxy_status NOT NULL DEFAULT 'draft',
    creator_id         INT           NOT NULL,
    created_at         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,  
    updated_at         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP, 
    supernova          VARCHAR(30),       
    apparent_magnitude NUMERIC(5,2),      
    distance_mpc       NUMERIC(8,2),      
    description        TEXT,              

    CONSTRAINT fk_galaxies_creator FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE RESTRICT,
    CONSTRAINT chk_title_not_blank CHECK (btrim(title) <> ''),
    CONSTRAINT chk_distance_positive CHECK (distance_mpc IS NULL OR distance_mpc > 0),
    -- опубликовать можно только заполненную галактику
    CONSTRAINT chk_published_filled CHECK (
        status = 'draft'
        OR (supernova IS NOT NULL AND apparent_magnitude IS NOT NULL AND distance_mpc IS NOT NULL)
    )
);

CREATE UNIQUE INDEX uq_galaxies_one_draft ON galaxies (creator_id) WHERE status <> 'published';
CREATE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_galaxies_updated_at
    BEFORE UPDATE ON galaxies
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 3. Лайки (многие-ко-многим: пользователь — галактика)
CREATE TABLE galaxy_likes (
    id        SERIAL PRIMARY KEY,
    user_id   INT    NOT NULL,
    galaxy_id INT    NOT NULL,

    CONSTRAINT fk_likes_user   FOREIGN KEY (user_id)   REFERENCES users(id)    ON DELETE RESTRICT,
    CONSTRAINT fk_likes_galaxy FOREIGN KEY (galaxy_id) REFERENCES galaxies(id) ON DELETE RESTRICT,
    CONSTRAINT uq_likes_user_galaxy UNIQUE (user_id, galaxy_id)
);

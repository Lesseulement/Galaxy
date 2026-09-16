CREATE TYPE entity_status AS ENUM ('draft', 'published', 'deleted');

CREATE TABLE galaxies (
    id SERIAL PRIMARY KEY,
    galaxy_name VARCHAR(100) NOT NULL,
    supernova_id VARCHAR(50),
    apparent_magnitude NUMERIC(5,2),
    redshift NUMERIC(6,4),
    distance_mpc NUMERIC(8,2),
    constellation VARCHAR(50),
    status entity_status DEFAULT 'draft',
    image_key VARCHAR(255),
    video_key VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO galaxies (galaxy_name, supernova_id, apparent_magnitude, redshift, distance_mpc, constellation, status, image_key, video_key) 
VALUES ('NGC 1300', 'SN 2002fk', 12.80, 0.0520, 19.6, 'Эридан', 'published', 'ngc1300.jpg', 'video.mp4');
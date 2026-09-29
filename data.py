"""Коллекция галактик для ЛР1 (без базы данных).
image_key и video_key — ключи файлов в бакете galaxies.media в MinIO."""

SERVICES = [
    {
        "id": 1, "title": "NGC 1300", "status": "published",
        "description": "Спиральная галактика с перемычкой в созвездии Эридан",
        "supernova": "SN 2002fk", "magnitude": 12.8, "distance_mpc": 18.5,
        "image_key": "NGC 1300.jpg", "video_key": "default.mp4", "likes": 3,
    },
    {
        "id": 2, "title": "M 82 (Сигара)", "status": "published",
        "description": "Галактика со вспышкой звездообразования в Большой Медведице",
        "supernova": "SN 2014J", "magnitude": 10.5, "distance_mpc": 3.5,
        "image_key": "M 82 (Сигара).jpg", "video_key": "default.mp4", "likes": 1,
    },
    {
        "id": 3, "title": "NGC 4527", "status": "published",
        "description": "Спиральная галактика в созвездии Девы",
        "supernova": "SN 1991T", "magnitude": 11.5, "distance_mpc": 13.0,
        "image_key": "NGC 4527.jpg", "video_key": "default.mp4", "likes": 2,
    },
    {
        "id": 4, "title": "NGC 5128 (Центавр A)", "status": "published",
        "description": "Линзовидная галактика, мощный радиоисточник",
        "supernova": "SN 1986G", "magnitude": 11.4, "distance_mpc": 3.8,
        "image_key": "NGC 5128 (Центавр A).gif", "video_key": "default.mp4", "likes": 2,
    },
    {
        "id": 5, "title": "NGC 3982", "status": "published",
        "description": "Спиральная галактика в Большой Медведице",
        "supernova": "SN 1998aq", "magnitude": 12.3, "distance_mpc": 20.0,
        "image_key": "NGC 3982.gif", "video_key": "default.mp4", "likes": 1,
    },
    {
        "id": 6, "title": "M 31 (Андромеда)", "status": "deleted",
        "description": "Ближайшая крупная спиральная галактика",
        "supernova": "SN 1885A", "magnitude": 5.9, "distance_mpc": 0.78,
        "image_key": "M 31 (Андромеда).jpg", "video_key": "default.mp4", "likes": 0,
    },
]

# Черновик пользователя для страницы «Добавление»
DRAFT = {
    "id": 7, "title": "NGC 1300", "status": "draft",
    "description": "Спиральная галактика с перемычкой",
    "supernova": "SN 2002fk", "magnitude": 12.8, "distance_mpc": 18.5,
    "image_key": "NGC 1300_1.jpg", "video_key": "default.mp4",
}

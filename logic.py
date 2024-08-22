"""
Файл содержит вспомогательные функции для файла main.
"""
from database import SessionLocal
from sqlalchemy.orm import Session
from model import City, Request, RequestType
from datetime import datetime
from sqlalchemy import func
from rtree import index
import math


def get_db():
    """
    Получает сессию базы данных.

    Открывает сессию базы данных и закрывает ее после использования.
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_r_tree(db: Session) -> index.Index:
    """
    Создает и возвращает R-дерево на основе данных из базы данных.
    """
    idx = index.Index()

    # Извлекаем все города из базы данных
    cities = db.query(City.id, City.latitude, City.longitude).all()

    # Заполняем R-дерево данными
    for city in cities:
        idx.insert(city.id, (city.longitude, city.latitude, city.longitude, city.latitude))

    return idx


def log_request(db: Session, request_type: RequestType, city_id: int = None, name: str = None, latitude: float = None,
                longitude: float = None):
    """
    Логирует запрос в таблицу `requests`.
    """
    log_entry = Request(
        request_type=request_type,
        city_id=city_id,
        name=name,
        latitude=latitude,
        longitude=longitude,
        request_time=datetime.utcnow()
    )
    db.add(log_entry)
    db.commit()


def city_exists(db: Session, normalized_name: str) -> bool:
    """
    Проверяет наличие города в базе данных по его имени.
    """
    return db.query(City).filter(func.lower(func.trim(City.name)) == normalized_name).first() is not None


def find_city_by_name(db: Session, city_name: str) -> City:
    """
    Ищет город по имени в базе данных.
    """
    return db.query(City).filter(City.name == city_name).first()


def find_city_by_coords(db: Session, latitude: float, longitude: float):
    """
    Ищет город по координатам в базе данных.
    """
    return db.query(City).filter(City.latitude == latitude, City.longitude == longitude).first()


def calculate_distance(latitude: float, longitude: float, city_lat: float, city_lon: float) -> float:
    """
    Рассчитывает расстояние между двумя точками по координатам.

    Формула для расчета расстояния по великой окружности
    """
    return math.acos(
        math.cos(math.radians(latitude)) * math.cos(math.radians(city_lat)) *
        math.cos(math.radians(city_lon) - math.radians(longitude)) +
        math.sin(math.radians(latitude)) * math.sin(math.radians(city_lat))
    ) * 6371  # Радиус Земли в километрах

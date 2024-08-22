from logic import get_db, log_request, city_exists, find_city_by_name, calculate_distance, create_r_tree
from model import Base, City, Request, RequestType
from schemas import CityRead, CityCreate
from data_parcing import get_city_coords
from database import engine

from fastapi import FastAPI, Depends, HTTPException

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import select

import uvicorn
from typing import List
from datetime import datetime


app = FastAPI()
Base.metadata.create_all(bind=engine)

# Глобальная переменная для хранения R-дерева, инициализируемая при старте приложения
rtree_index = None


@app.post("/addition/", response_model=CityCreate)
def add_city(city: CityCreate, db: Session = Depends(get_db)):
    """
    Добавление нового города.

    Добавляет город и его координаты в БД.
    """
    global rtree_index  # Используем глобальное R-дерево
    # Приведение названия города к нижнему регистру и удаление лишних пробелов
    normalized_name = city.name.strip().lower()

    # Проверка наличия города в базе данных
    if city_exists(db, normalized_name):
        raise HTTPException(status_code=400, detail="The city is already in the database.")

    # Получение координат города
    lat, lon = get_city_coords(city.name)

    # Добавление нового города в БД
    db_city = City(name=city.name, latitude=lat, longitude=lon)
    db.add(db_city)
    db.commit()
    db.refresh(db_city)

    # Логируем запрос на добавление города
    log_request(db, RequestType.ADD, city_id=db_city.id, name=city.name, latitude=lat, longitude=lon)

    # Добавление нового города в R-дерево
    if rtree_index:
        rtree_index.insert(db_city.id, (lon, lat, lon, lat))

    return db_city


@app.get("/cities/", response_model=List[CityRead])
def read_cities(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """
    Получает список городов с возможностью пагинации.
    """
    cities = db.query(City).offset(skip).limit(limit).all()
    return cities


@app.get("/cities/{city_name}", response_model=CityRead)
def get_info(city_name: str, db: Session = Depends(get_db)):
    """
    Получает информацию о городе по его имени.
    """
    db_city = find_city_by_name(db, city_name)
    if not db_city:
        raise HTTPException(status_code=404, detail="City not found")
    return db_city


@app.delete("/cities/{city_name}/delete")
def delete_city(city_name: str, db: Session = Depends(get_db)):
    """
    Удаляет город по имени и логирует это действие.
    """
    global rtree_index  # Используем глобальное R-дерево

    city = find_city_by_name(db, city_name)
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    try:
        # Логируем удаление города до его удаления
        log_entry = Request(
            request_type=RequestType.DELETE,
            city_id=city.id,
            name=city.name,
            latitude=city.latitude,
            longitude=city.longitude,
            request_time=datetime.utcnow()
        )
        db.add(log_entry)

        # Удаляем запись города
        db.delete(city)

        # Удаляем запись города из R-дерева
        if rtree_index:
            rtree_index.delete(city.id, (city.longitude, city.latitude, city.longitude, city.latitude))

        # Фиксируем изменения в базе данных
        db.commit()

        return {"detail": f"City {city.name} deleted and logged"}

    except SQLAlchemyError as e:
        db.rollback()  # Откатить изменения в случае ошибки
        raise HTTPException(status_code=500, detail="Error deleting city and logging the request")


@app.get("/nearest_cities/")
def nearest_cities(
        city_name: str = None,
        latitude: float = None,
        longitude: float = None,
        db: Session = Depends(get_db)
):
    """
    Находит 2 ближайших города из бд относительно введенного названия/координат.
    Возможность ввода:
    - Название города (как из бд так и случайного)
    - Координаты (как из бд так и случайные)
    """
    if city_name:
        city = find_city_by_name(db, city_name)
        if city:
            latitude = city.latitude
            longitude = city.longitude
        else:

            latitude, longitude = get_city_coords(city_name)
    elif latitude is None or longitude is None:
        raise HTTPException(status_code=400, detail="Either city name or both latitude and longitude must be provided")

    cities = get_nearest_cities(latitude, longitude, db)
    return cities


def get_nearest_cities(latitude: float, longitude: float, db: Session, limit_start: int = 0, limit_end: int = 3) -> \
        List[City]:
    """
    Возвращает список ближайших городов, используя координаты.
    """
    try:
        # Поиск ближайших городов в R-дереве
        nearest_city_ids = list(rtree_index.nearest((longitude, latitude, longitude, latitude), limit_end))

        # Извлекаем информацию о ближайших городах из базы данных
        query = (
            select(City.id, City.name, City.latitude, City.longitude)
            .filter(City.id.in_(nearest_city_ids))
            .order_by(City.id.in_(nearest_city_ids))  # сохраняем порядок как в R-дереве
        )

        result = db.execute(query).fetchall()

        # Преобразуем результат в список словарей
        cities = [dict(row._mapping) for row in result]

        # Ограничиваем количество городов согласно limit_start и limit_end
        cities = cities[limit_start:limit_end]

        # Удаляем элементы, совпадающие с координатами
        cities = [city_data for city_data in cities if
                  not (city_data['latitude'] == latitude and city_data['longitude'] == longitude)]
        # Добавляем расчет расстояния для каждого из оставшихся городов
        for city_data in cities:
            city_lat = city_data['latitude']
            city_lon = city_data['longitude']
            distance: float = calculate_distance(latitude, longitude, city_lat, city_lon)
            city_data['distance'] = distance

        # Сортируем города по расстоянию
        cities.sort(key=lambda x: x['distance'])

        # Проверка длины списка и удаление последнего элемента, если больше 2
        if len(cities) > 2:
            cities.pop()

        # Логируем запрос на поиск ближайших городов
        log_request(db, RequestType.NEAREST, latitude=latitude, longitude=longitude)

        return cities

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database query error")


def initialize_r_tree():
    """
    Инициализирует R-дерево при старте приложения.
    """
    global rtree_index
    db = next(get_db())  # Получаем сессию БД
    rtree_index = create_r_tree(db)
    db.close()  # Закрываем сессию


initialize_r_tree()

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8080)

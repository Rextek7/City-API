"""
Этот файл содержит определения Pydantic моделей, которые используются для валидации и сериализации данных.
"""
from pydantic import BaseModel


class CityCreate(BaseModel):
    name: str

    """
    Модель для добавления нового города.

    Атрибуты:
    - city: Название города.
    """


class CityRead(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float

    class Config:
        orm_mode = True

    """
    Модель для чтения информации о городах.

    Атрибуты:
    - id: Уникальный идентификатор города.
    - name: Название города.
    - latitude : Широта города.
    - longitude : Долгота города.

    Конфигурация:
    - orm_mode: Настройка для работы с атрибутами модели ORM.
    """

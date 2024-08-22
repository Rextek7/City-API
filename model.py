"""
Этот файл содержит определения моделей данных, которые представляют таблицы в базе данных.
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class City(Base):
    __tablename__ = 'cities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)


class RequestType(enum.Enum):
    ADD = "ADD"
    DELETE = "DELETE"
    NEAREST = "NEAREST"


class Request(Base):
    __tablename__ = 'requests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_type = Column(Enum(RequestType), nullable=False)
    city_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    request_time = Column(DateTime, default=datetime.utcnow, nullable=False)

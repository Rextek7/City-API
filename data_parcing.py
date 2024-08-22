"""
Файл содержит функции для взаимодействия с API 2GIS.
"""

import requests
import os

api_key = os.getenv('API_KEY')


def get_json_response(url):
    """
    Выполняет HTTP-запрос к указанному URL и возвращает JSON-данные.
    """
    response = requests.get(url, verify=False, headers={
        "User-Agent": "Chrome/124.0.0.0 Safari/537.36"})  # Выполняем GET-запрос с поддельным User-Agent
    response.raise_for_status()  # Проверяем успешность запроса
    return response.json()  # Возвращаем JSON-данные


def get_city_coords(city_name):
    """
    Находит координаты корода по названию.
    """
    url_city = f'https://catalog.api.2gis.com/3.0/items/geocode?q={city_name}&fields=items.point&key={api_key}'
    data = get_json_response(url_city)
    for item in data.get('result', {}).get('items', []):
        if item.get('name') == city_name:
            lat = item['point']['lat']
            lon = item['point']['lon']
            return lat, lon
    return None, None  # Возвращаем None, если координаты не найдены


def get_city_name(lat_coord, lon_coord):
    """
    Находит название корода по координатам.
    """
    url_coord = f'https://catalog.api.2gis.com/3.0/items/geocode?lat={lat_coord}&lon={lon_coord}&fields=items.point&key={api_key}'
    data = get_json_response(url_coord)
    for item in data.get('result', {}).get('items', []):
        if item.get('subtype') == 'city':
            return item['name']
    return None  # Возвращаем None, если город не найден

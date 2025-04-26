from enum import Enum
from dataclasses import dataclass
from typing import Any


class MessageType(Enum):
    INIT_MESSAGE = 'Инициализация'
    PRICE_REQUEST = 'Запрос цены'
    PRICE_RESPONSE = 'Ответ цены'
    PLANNING_REQUEST = 'Запрос на размещение'
    PLANNING_RESPONSE = 'Ответ на размещение'
    REMOVE_ORDER = 'Удаление заказа из расписания'
    NEW_COURIER = 'Появление нового курьера'
    DELETED_COURIER = 'Удаление курьера'
    TICK_MESSAGE = 'Тик'


@dataclass
class Message:
    """Класс для хранения сообщений"""
    msg_type: MessageType
    msg_body: Any

"""Содержит базовую реализацию агента с обработкой сообщений"""
import traceback
from typing import Dict, Callable, Any, List
from abc import ABC
import logging

from thespian.actors import Actor, ActorAddress, ActorExitRequest

from .messages import MessageType, Message


class AgentBase(ABC, Actor):
    """
    Базовая реализация агента
    """

    def __init__(self):
        self.name = 'Базовый агент'
        super().__init__()
        self.handlers: Dict[MessageType, Callable[[Any, ActorAddress], None]] = {}
        self.scene = None
        self.dispatcher = None
        self.entity = None
        self.subscribe(MessageType.INIT_MESSAGE, self.handle_init_message)

    def subscribe(self, msg_type: MessageType, handler: Callable[[Any, ActorAddress], None]):
        if msg_type in self.handlers:
            logging.warning('Повторная подписка на сообщение: %s', msg_type)
        self.handlers[msg_type] = handler

    def handle_delete_message(self):
        """
        Обработчик сообщения об удалении сущности.
        :return:
        """
        logging.info(f'{self} получил сообщение - ActorExitRequest')
        self.entity.is_deleting = True

    def receiveMessage(self, msg, sender):
        """Обрабатывает сообщения - запускает их обработку в зависимости от типа.
        :param msg:
        :param sender:
        :return:
        """
        logging.debug('%s получил сообщение: %s', self.name, msg)
        if isinstance(msg, ActorExitRequest):
            self.handle_delete_message()
            return

        if isinstance(msg, Message):

            message_type = msg.msg_type
            if message_type in self.handlers:
                try:
                    # logging.info(f'{self} получил сообщение {msg}')
                    self.handlers[message_type](msg, sender)
                except Exception as ex:
                    traceback.print_exc()
                    logging.error(ex)
            else:
                logging.warning('%s Отсутствует подписка на сообщение: %s', self.name, message_type)
        else:
            logging.error('%s Неверный формат сообщения: %s', self.name, msg)
            super().receiveMessage(msg, sender)

    def __str__(self):
        return self.name

    def handle_init_message(self, message, sender):
        message_data = message.msg_body
        self.scene = message_data.get('scene')
        self.dispatcher = message_data.get('dispatcher')
        self.entity = message_data.get('entity')
        self.name = self.name + ' ' + self.entity.name
        logging.info(f'{self} проинициализирован')

    def send(self, targetAddr, msg):
        self.scene.count_messages += 1
        return super().send(targetAddr, msg)

    @staticmethod
    def get_decreasing_kpi_value(value: float, min_value: float, max_value: float):
        """
        Функция возвращает значение убывающей линейной функции
        (f(x)) с областью определения [minValue, maxValue], нормированное к единице.
        f(minValue) === 1. f(maxValue) === 0
        :param value:
        :param min_value:
        :param max_value:
        :return:
        """

        if max_value == min_value:
            return 1

        if value > max_value or value < min_value:
            return -1

        if isinstance(value, float) and abs(value - min_value) < 0.000001:
            # Работаем с минимальным значением => возвращаем 1
            return 1
        if isinstance(value, float) and abs(value - max_value) < 0.000001:
            # Работаем с максимальным значением => возвращаем 0
            return 0
        # Решаем уравнение прямой по двум точкам. f(minValue) == 1; f(maxValue) == 0
        return 1 - (value - min_value) / (max_value - min_value)

    @staticmethod
    def get_increasing_kpi_value(value: float, min_value: float, max_value: float):
        """
        Функция возвращает значение возрастающей линейной функции
        (f(x)) с областью определения [minValue, maxValue], нормированное к единице.
        f(minValue) === 0. f(maxValue) === 1
        :param value:
        :param min_value:
        :param max_value:
        :return:
        """

        if max_value == min_value:
            # Работаем с прямой, все значения - единицы
            return 1

        if value > max_value or value < min_value:
            # Некорректные данные, выходят из диапазона
            return -1
        if isinstance(value, float) and abs(value - min_value) < 0.000001:
            # Работаем с минимальным значением => возвращаем 0
            return 0
        if isinstance(value, float) and abs(value - max_value) < 0.000001:
            # Работаем с максимальным значением => возвращаем 1
            return 1

        # Решаем уравнение прямой по двум точкам. f(minValue) == 0; f(maxValue) == 1
        return (value - min_value) / (max_value - min_value)

""" Реализация класса агента заказа"""
import logging
import typing

from .agent_base import AgentBase
from .messages import MessageType, Message
from entities.courier_entity import CourierEntity
from entities.order_entity import OrderEntity


class OrderAgent(AgentBase):
    """
    Класс агента заказа
    """
    def __init__(self):
        super().__init__()
        self.entity: OrderEntity
        self.name = 'Агент заказа'
        self.subscribe(MessageType.PRICE_RESPONSE, self.handle_price_response)
        self.subscribe(MessageType.PLANNING_RESPONSE, self.handle_planning_response)
        self.subscribe(MessageType.REMOVE_ORDER, self.handle_remove_message)
        self.subscribe(MessageType.NEW_COURIER, self.handle_new_resource_message)
        self.subscribe(MessageType.DELETED_COURIER, self.handle_delete_courier_message)
        self.subscribe(MessageType.TICK_MESSAGE, self.handle_tick_message)

        self.unchecked_couriers = []
        self.possible_variants = []

    def handle_remove_message(self, message, sender):
        """
        Обработка сообщения об удалении с курьера
        :param message:
        :param sender:
        :return:
        """
        courier = message.msg_body
        logging.info(f'{self} - удален из расписания курьера {courier}')
        # Считаем, что всем параметры старые их необходимо пересчитать.
        self.entity.delivery_data = {
            'courier': None,
            'price': None,
            'time_from': None,
            'time_to': None,
        }
        self.possible_variants.clear()
        self.__send_params_request()

    def handle_delete_courier_message(self, message, sender):
        """
        Обработка сообщения о появлении нового курьера
        :param message:
        :param sender:
        :return:
        """
        courier = message.msg_body
        logging.info(f'{self} - узнал об удалении {courier}')

        if self.entity.delivery_data.get('courier') != courier:
            # Заказ не был запланирован на этом курьере, ему не надо ничего делать
            return
        # Заказ должен найти новое место - логика тут идентична удалению из расписания
        self.handle_remove_message(message, sender)

    def handle_tick_message(self, message, sender):
        """
        Обработка сообщения c сообщением о активности
        :param message:
        :param sender:
        :return:
        """
        # TODO: Просмотреть возможности для улучшения состояния и тд
        pass

    def handle_new_resource_message(self, message, sender):
        """
        Обработка сообщения о появлении нового курьера
        :param message:
        :param sender:
        :return:
        """
        courier = message.msg_body
        logging.info(f'{self} - узнал о новом курьере {courier}')
        # Если заказ уже запланирован, то ничего делать не надо.
        if not self.entity.delivery_data.get('courier'):
            # Считаем, что всем параметры старые их необходимо пересчитать.
            self.possible_variants.clear()
            self.__send_params_request()

    def handle_planning_response(self, message, sender):
        """
        Обработка сообщения с результатами планирования.
        :param message:
        :param sender:
        :return:
        """
        result = message.msg_body
        logging.info(f'{self} - получил {message}, результат - {result}')

        if result.get('success'):
            self.entity.delivery_data = result
            logging.info(f'{self} доволен, ничего делать не надо')
            return
        # Ищем другой вариант для размещения
        # Возможно, правильнее было бы снова инициализировать варианты путем переговоров
        # Но мы попробуем другие варианты, которые у нас уже есть
        sorted_vars = sorted(self.possible_variants,
                             key=lambda x: x.get('price'))
        # Прошлый лучший вариант, который мы проверяли
        checked_variant = sorted_vars[0]
        self.possible_variants.remove(checked_variant)
        if not self.possible_variants:
            self.__send_params_request()
            return
        self.__run_planning()

    def handle_init_message(self, message, sender):
        super().handle_init_message(message, sender)
        # Ищем в системе ресурсы и отправляем им запросы
        self.__send_params_request()

    def __send_params_request(self):
        all_couriers: typing.List[CourierEntity] = self.scene.get_entities_by_type('COURIER')
        logging.info(f'{self} - список ресурсов: {all_couriers}')
        for courier in all_couriers:
            # if self.entity.order_type not in courier.types:
            #     logging.info(f'{self} - типы грузов {courier} - {courier.types} '
            #                  f'не включают {self.entity.order_type}')
            #     continue
            courier_address = self.dispatcher.reference_book.get_address(courier)
            # logging.info(f'{self} - адрес {courier}: {courier_address}')
            request_message = Message(MessageType.PRICE_REQUEST, self.entity)
            self.send(courier_address, request_message)
            self.unchecked_couriers.append(courier_address)

    def handle_price_response(self, message, sender):
        logging.info(f'{self} - получил сообщение {message}')
        courier_variants = message.msg_body

        self.possible_variants.extend(courier_variants)
        self.unchecked_couriers.remove(sender)
        if not self.unchecked_couriers:
            self.__run_planning()

    def __evaluate_variants(self):
        """
        Оцениваем варианты по критериям и расширяем информацию о них
        :return:
        """
        if not self.possible_variants:
            return
        all_start_times = [var.get('time_from') for var in self.possible_variants]
        min_start_time = min(all_start_times)
        max_start_time = max(all_start_times)
        all_finish_times = [var.get('time_to') for var in self.possible_variants]
        min_finish_time = min(all_finish_times)
        max_finish_time = max(all_finish_times)
        all_prices = [var.get('price') for var in self.possible_variants]
        min_price = min(all_prices)
        max_price = max(all_prices)
        logging.info(f'{self} минимальный старт: {min_start_time}, минимальное завершение - {min_finish_time}, '
                     f'минимальная цена - {min_price}')
        for variant in self.possible_variants:
            start_efficiency = self.get_decreasing_kpi_value(variant.get('time_from'), min_start_time, max_start_time)
            finish_efficiency = self.get_increasing_kpi_value(variant.get('time_to'), min_finish_time, max_finish_time)
            price_efficiency = self.get_decreasing_kpi_value(variant.get('price'), min_price, max_price)
            variant['start_efficiency'] = start_efficiency  # [0; 1]
            variant['finish_efficiency'] = finish_efficiency  # [0; 1]
            variant['price_efficiency'] = price_efficiency  # [0; 1]

            # Итоговая оценка варианта должна учитывать все критерии
            # (в какой-то пропорции)
            finish_weight = 0.3
            start_weight = 0.2
            price_weight = 0.5
            variant['total_efficiency'] = finish_weight * finish_efficiency + start_weight * start_efficiency +\
                                          price_weight * price_efficiency

    def __run_planning(self):
        if not self.possible_variants:
            logging.info(f'{self} - нет возможных вариантов для планирования')
            return
        # Оцениваем варианты
        self.__evaluate_variants()
        # Сортируем варианты от лучшего к худшему.
        sorted_vars = sorted(self.possible_variants, key=lambda x: x.get('total_efficiency'), reverse=True)
        logging.info(f'{self} - {sorted_vars=}')
        # Наилучший
        best_variant = sorted_vars[0]
        # Адрес лучшего варианта
        best_variant_address = self.dispatcher.reference_book.get_address(best_variant.get('courier'))

        logging.info(f'{self} - лучшим вариантом признан {best_variant}, '
                     f'адрес - {best_variant_address}')
        request_message = Message(MessageType.PLANNING_REQUEST, best_variant)
        self.send(best_variant_address, request_message)

    def handle_deleted(self, msg, sender):
        logging.info(f'{self} получил сообщение об удалении. ЧТО ДЕЛАТЬ???')

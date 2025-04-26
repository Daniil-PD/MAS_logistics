""" Реализация класса агента курьера"""
import copy
import logging
import typing
from collections import defaultdict

from point import Point
from .agent_base import AgentBase
from .messages import MessageType, Message
from entities.courier_entity import CourierEntity, ScheduleItem
from entities.order_entity import OrderEntity


class CourierAgent(AgentBase):
    """
    Класс агента курьера
    """
    def __init__(self):
        super().__init__()
        self.entity: CourierEntity
        self.name = 'Агент курьера'
        self.subscribe(MessageType.PRICE_REQUEST, self.handle_price_request)
        self.subscribe(MessageType.PLANNING_REQUEST, self.handle_planning_request)
        self.subscribe(MessageType.TICK_MESSAGE, self.handle_tick_message)

    def handle_init_message(self, message, sender):
        super().handle_init_message(message, sender)
        all_orders = self.scene.get_entities_by_type('ORDER')
        matched_orders = [order for order in all_orders if order.order_type in self.entity.types]
        for order in matched_orders:
            order_address = self.dispatcher.reference_book.get_address(order)
            new_courier_message = Message(MessageType.NEW_COURIER, self.entity)
            self.send(order_address, new_courier_message)

    def handle_delete_message(self):
        super().handle_delete_message()
        all_orders = self.scene.get_entities_by_type('ORDER')
        for order in all_orders:
            order_address = self.dispatcher.reference_book.get_address(order)
            deleted_courier_message = Message(MessageType.DELETED_COURIER, self.entity)
            self.send(order_address, deleted_courier_message)

    def handle_tick_message(self, message, sender):
        """
        Обработка сообщения c сообщением о активности
        :param message:
        :param sender:
        :return:
        """
        # TODO: Просмотреть возможности для улучшения состояния и тд
        pass

    def handle_price_request(self, message, sender):
        """
        Обработка сообщения с запросом параметров заказа.
        Выполняет расчет в зависимости от текущего расписания курьера.
        :param message:
        :param sender:
        :return:
        """
        order: OrderEntity = message.msg_body
        params = self.__get_params(order)
        price_message = Message(MessageType.PRICE_RESPONSE, params)
        self.send(sender, price_message)

    def __get_params(self, order: OrderEntity) -> typing.List:
        """
        Формирует возможные варианты размещения заказа
        :param order:
        :return:
        """
        if order.weight > self.entity.max_mass:
            return []
        p1 = order.point_from
        # Надо посчитать стоимость выполнения заказа, сроки доставки
        last_point: Point = self.entity.get_last_point()
        distance_to_order = last_point.get_distance_to_other(p1)

        p2 = order.point_to
        distance_with_order = p1.get_distance_to_other(p2)
        time_to_order = distance_to_order / self.entity.velocity
        time_with_order = distance_with_order / self.entity.velocity
        duration = time_to_order + time_with_order

        price = duration * self.entity.rate
        logging.info(f'{self} - заказ {order} надо пронести {distance_with_order},'
                     f' к нему идти {distance_to_order}'
                     f'это займет {duration} и будет стоить {price}')

        last_time = self.entity.get_last_time()

        asap_time_from = last_time
        asap_time_to = asap_time_from + time_to_order + time_with_order
        # Вариант, при котором мы выполняем заказ как только можем
        asap_variant = {'courier': self.entity, 'time_from': asap_time_from, 'time_to': asap_time_to,
                        'price': price, 'order': order, 'variant_name': 'asap'}
        params = [asap_variant]
        jit_time_from = order.time_from - time_to_order
        jit_time_to = jit_time_from + time_to_order + time_with_order
        if asap_time_from < order.time_from:
            # Генерируем вариант, при котором мы заберем заказ вовремя
            # JIT-вариант можно генерировать и при наличии записей, но надо расширить
            # проверки на возможность доставки.
            if jit_time_from > 0 and not self.entity.schedule:
                jit_from_variant = {'courier': self.entity, 'time_from': jit_time_from, 'time_to': jit_time_to,
                                    'price': price, 'order': order, 'variant_name': 'jit'}
                params.append(jit_from_variant)

        if jit_time_from > 0:
            conflicted_records: typing.List[ScheduleItem] = self.entity.get_conflicts(jit_time_from, jit_time_to)
            logging.info(f'{self} - {conflicted_records=}')
            # Формируем перечень заказов, которые есть в конфликтных записях
            conflicted_orders = set([rec.order for rec in conflicted_records])

            all_conflicted_records: typing.List[ScheduleItem] = []
            for _order in conflicted_orders:
                all_conflicted_records.extend(self.entity.get_all_order_records(_order))
            conflicted_tasks = defaultdict(dict)
            for rec in all_conflicted_records:
                task = rec.order
                min_start = rec.start_time
                max_end = rec.end_time
                max_cost = rec.cost
                if task in conflicted_tasks:
                    min_start = min(conflicted_tasks[task].get('start'), min_start)
                    max_end = max(conflicted_tasks[task].get('end'), max_end)
                    max_cost = conflicted_tasks[task].get('cost', 0) + max_cost

                conflicted_tasks[task] = {'start': min_start, 'end': max_end, 'cost': max_cost}
            logging.info(f'{self} ищет конфликтные варианты для заказа {order} {order.time_from=}, {order.time_to=} - '
                         f'{jit_time_from=}, {jit_time_to=}, {conflicted_tasks=}')
            # В коде ниже смотрим только на цену, но можно оценивать и другие параметры.
            poss_removing_orders: typing.List[OrderEntity] = [_order for _order in conflicted_orders
                                                              if _order.price < order.price]

            if not poss_removing_orders:
                logging.info(f'{self} не смог найти более дешевые заказы по сравнению с {order}')
                return params

            # Для простоты оцениваем только один
            cheapest_order = min(poss_removing_orders, key=lambda x: x.price)
            logging.info(f'{self} нашел более дешевый заказ: {cheapest_order}')

            cheapest_order_records: typing.List[ScheduleItem] = self.entity.get_all_order_records(cheapest_order)
            # Ожидаем, что первая запись - это движение за грузом.
            start_record = cheapest_order_records[0]
            start_time = start_record.start_time
            start_point = start_record.point_from
            conflicted_distance_to_order = start_point.get_distance_to_other(p1)
            conflicted_time_to_order = conflicted_distance_to_order / self.entity.velocity
            conflicted_finish = start_time + conflicted_time_to_order + time_with_order

            logging.info(f'{self} в случае вытеснения отправится из точки {start_point} в {start_time}, '
                         f'за заказом придет в {start_time + conflicted_time_to_order} '
                         f'и доставит в {conflicted_finish}')

            new_conflicts = self.entity.get_conflicts(start_time, conflicted_finish)
            other_order_conflicts = [_rec for _rec in new_conflicts if _rec.order != cheapest_order]
            if other_order_conflicts:
                logging.info(f'{self} не сможет доставить заказ, есть конфликты {other_order_conflicts}')
                return params
            conflicted_price = (conflicted_time_to_order + time_with_order) * self.entity.rate
            conflict_variant = {'courier': self.entity, 'time_from': start_time, 'time_to': conflicted_finish,
                                'price': conflicted_price, 'order': order, 'variant_name': 'conflict'}
            params.append(conflict_variant)

        return params

    def handle_planning_request(self, message, sender):
        """
        Обработка сообщения с запросом на планирования.
        :param message:
        :param sender:
        :return:
        """
        params = message.msg_body
        # Пытаемся добавить заказ в свое расписание
        adding_result = self.add_order(params)

        logging.info(f'{self} получил запрос на размещение {params}, '
                     f'результат - {adding_result}')
        params['success'] = adding_result
        result_msg = Message(MessageType.PLANNING_RESPONSE, params)
        self.send(sender, result_msg)

    def add_order(self, params: dict) -> bool:
        """
        Добавление заказа с параметрами в расписание ресурса.
        :param params:
        :return:
        """
        variant_name = params.get('variant_name')
        if variant_name == 'conflict':
            conflicted_records: typing.List[ScheduleItem] = self.entity.get_conflicts(params.get('time_from'),
                                                                                      params.get('time_to'))
            logging.info(f'{self} - {conflicted_records=}')
            # Формируем перечень заказов, которые есть в конфликтных записях
            conflicted_orders = set([rec.order for rec in conflicted_records])
            if len(conflicted_orders) > 1:
                logging.info(f'{self} получил запрос на размещение {params}, '
                             f'много конфликтов - {conflicted_orders}')
                return False

            # Делаем копию расписания. Если заказ разместить не удастся, то восстановим его.
            old_schedule = copy.copy(self.entity.schedule)
            for rec in conflicted_records:
                self.entity.schedule.remove(rec)
            adding_result = self.entity.add_order_to_schedule(params.get('order'),
                                                              params.get('time_from'),
                                                              params.get('time_to'),
                                                              params.get('price'),
                                                              params)
            if not adding_result:
                self.entity.schedule = old_schedule
            else:
                # Удаление заказа произошло успешно, надо сообщить удаленному заказу
                # о необходимости перепланироваться
                remove_message = Message(MessageType.REMOVE_ORDER, self.entity)
                removed_order_address = self.dispatcher.reference_book.get_address(conflicted_orders.pop())
                self.send(removed_order_address, remove_message)
            return adding_result

        adding_result = self.entity.add_order_to_schedule(params.get('order'),
                                                          params.get('time_from'),
                                                          params.get('time_to'),
                                                          params.get('price'),
                                                          params)
        return adding_result

    def handle_deleted(self, msg, sender):
        logging.info(f'{self} получил сообщение об удалении. ЧТО ДЕЛАТЬ???')

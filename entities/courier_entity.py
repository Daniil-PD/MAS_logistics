"""
Описание курьера.
"""
import logging
import typing
from dataclasses import dataclass

from entities.base_entity import BaseEntity
from entities.order_entity import OrderEntity
from point import Point

EPSILON = 0.0000001


@dataclass
class ScheduleItem:
    """
    Класс записи расписания
    """
    order: OrderEntity
    rec_type: str
    start_time: int
    end_time: int
    point_from: Point
    point_to: Point
    cost: float
    all_params: dict


class CourierEntity(BaseEntity):
    """
    Класс заказа
    """
    def __init__(self, onto_desc: {}, init_dict_data, scene=None):
        super().__init__(onto_desc, scene)
        self.number = init_dict_data.get('Табельный номер')
        self.name = init_dict_data.get('ФИО')
        x1 = float(init_dict_data.get('Координата начального положения x'))
        y1 = float(init_dict_data.get('Координата начального положения y'))
        self.init_point = Point(x1, y1)
        self.types = [_type.lstrip() for _type in init_dict_data.get('Типы доставляемых заказов', '').split(';')]
        self.cost = float(init_dict_data.get('Стоимость выхода на работу'))
        self.rate = float(init_dict_data.get('Цена работы за единицу времени'))

        self.velocity = float(init_dict_data.get('Скорость'))
        self.max_volume = float(init_dict_data.get('Объем ранца'))
        self.max_mass = float(init_dict_data.get('Грузоподъемность'))

        self.uri = 'Courier' + str(self.number)

        self.schedule: typing.List[ScheduleItem] = []

    def __repr__(self):
        return 'Курьер ' + str(self.name)

    def get_type(self):
        """

        :return: onto_description -> metadata -> type
        """
        return 'COURIER'

    def get_conflicts(self, start_time: int, end_time: int) -> typing.List[ScheduleItem]:
        """
        Возвращает записи, пересекающиеся по времени с запрошенным интервалом
        :param start_time:
        :param end_time:
        :return:
        """
        result = []
        for item in self.schedule:
            if start_time <= item.start_time < end_time or \
                    (start_time < item.end_time <= end_time and item.start_time != item.end_time) or \
                    item.start_time <= start_time < item.end_time or item.start_time < end_time <= item.end_time:
                if item.rec_type != 'Ожидание':
                    result.append(item)

        return result

    def get_all_order_records(self, order: OrderEntity) -> typing.List[ScheduleItem]:
        """
        Возвращает все записи указанного заказа
        :param order:
        :return:
        """
        result: typing.List[ScheduleItem] = [rec for rec in self.schedule if rec.order == order]
        return result

    def add_order_to_schedule(self, order: OrderEntity,
                              start_time: int, end_time: int, cost: float, all_params: dict) -> bool:
        """
        Добавляет заказ с параметрами в расписание
        :param order:
        :param start_time:
        :param end_time:
        :param cost:
        :param all_params
        :return:
        """
        # Смотрим, когда курьер реально сможет начать работу над заказом
        last_free_time = 0
        if self.schedule:
            # FIXME: Тут можно искать предыдущую по отношению к запрашиваемому времени точку.
            last_free_time = self.schedule[-1].end_time
        if last_free_time - start_time > EPSILON:
            # Курьер освобождается после start_time
            return False
        last_point: Point = self.get_last_point()
        distance_to_order = last_point.get_distance_to_other(order.point_from)
        distance_with_order = order.point_from.get_distance_to_other(order.point_to)
        time_to_order = distance_to_order / self.velocity
        time_with_order = distance_with_order / self.velocity
        common_duration = time_to_order + time_with_order
        common_finish_time = start_time + common_duration
        delta = common_finish_time - end_time
        if abs(delta) > EPSILON:
            # Границы доставки вышли за запрошенное время
            return False

        schedule_item_to_order = ScheduleItem(order, 'Движение за грузом', start_time, start_time + time_to_order,
                                              last_point, order.point_from, 0, all_params)
        schedule_item = ScheduleItem(order, 'Движение с грузом', start_time + time_to_order, common_finish_time,
                                     order.point_from, order.point_to, cost, all_params)
        waiting_item_with_order = ScheduleItem(order, 'Ожидание с грузом', common_finish_time, end_time,
                                               order.point_to, order.point_to,
                                               0, all_params)
        if not self.schedule:
            # Записей пока не было, добавляем заказ
            if abs(schedule_item_to_order.start_time - schedule_item_to_order.end_time) > EPSILON:
                self.schedule.append(schedule_item_to_order)
            self.schedule.append(schedule_item)
            if abs(waiting_item_with_order.start_time - waiting_item_with_order.end_time) > EPSILON:
                self.schedule.append(waiting_item_with_order)
            return True
        conflicts = self.get_conflicts(start_time, end_time)
        if self.get_conflicts(start_time, end_time):
            logging.info(f'{self} - не могу добавить записи на интервал - {start_time} - {end_time},'
                         f' конфликты - {conflicts}')
            return False
        if abs(schedule_item_to_order.start_time - schedule_item_to_order.end_time) > EPSILON:
            self.schedule.append(schedule_item_to_order)
        self.schedule.append(schedule_item)
        if abs(waiting_item_with_order.start_time - waiting_item_with_order.end_time) > EPSILON:
            self.schedule.append(waiting_item_with_order)
        self.schedule.sort(key=lambda rec: rec.start_time)
        return True

    def get_last_point(self) -> Point:
        """
        Возвращает последнюю точку из расписания курьера
        :return:
        """
        if not self.schedule:
            return self.init_point
        last_point = self.schedule[-1].point_to
        return last_point

    def get_last_time(self) -> int:
        """
        Возвращает время, когда курьер может приступить к выполнению заказа
        :return:
        """
        if not self.schedule:
            return 0
        return self.schedule[-1].end_time

    def get_schedule_json(self):
        """
        Сериализация расписания курьера
        :return:
        """
        result = []
        if self.schedule and self.schedule[0].start_time != 0:
            # Формируем в расписании ожидание в начальной точке
            next_record = self.schedule[0]
            downtime_record = ScheduleItem(next_record.order, 'Ожидание', 0, next_record.start_time,
                                           self.init_point, self.init_point, 0, {})
            self.schedule.insert(0, downtime_record)
        for number, record in enumerate(self.schedule):
            if number == len(self.schedule) - 1:
                break
            next_record = self.schedule[number + 1]
            if record.end_time != next_record.start_time:
                # Формируем в расписании ожидание в точке, где отдали заказ.
                downtime_record = ScheduleItem(record.order, 'Ожидание', record.end_time, next_record.start_time,
                                               record.point_to, record.point_to, 0, record.all_params)
                self.schedule.append(downtime_record)
        self.schedule.sort(key=lambda rec: (rec.start_time, rec.end_time))
        for rec in self.schedule:
            json_record = {
                'resource_id': self.number,
                'resource_name': self.name,
                'task_id': rec.order.number,
                'task_name': rec.order.name,
                'type': rec.rec_type,
                'from': str(rec.point_from),
                'to': str(rec.point_to),
                'start_time': rec.start_time,
                'end_time': rec.end_time,
                'cost': rec.cost,
            }
            result.append(json_record)
        return result

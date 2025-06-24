"""
Описание курьера.
"""
import logging
import typing
from dataclasses import dataclass

from entities.base_entity import BaseEntity
from entities.order_entity import OrderEntity
from point import Point
import copy

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
    all_params: dict = None
    
    def __post_init__(self):
        if self.all_params is None:
            self.all_params = {}
    
    @property
    def is_move_to_charge(self):
        if self.order is None:
            return True
        else:
            return False



class CourierEntity(BaseEntity):
    """
    Класс заказа
    """
    def __init__(self, onto_desc: {}, init_dict_data, scene=None):
        super().__init__(onto_desc, scene)
        self.number = init_dict_data.get('Табельный номер')
        x1 = float(init_dict_data.get('Координата начального положения x'))
        y1 = float(init_dict_data.get('Координата начального положения y'))
        self.init_point = Point(x1, y1)
        self.cost = float(init_dict_data.get('Стоимость выхода на работу'))
        self.rate = float(init_dict_data.get('Цена работы за единицу времени'))
        self.name = init_dict_data.get('name')

        # Скорость зарядки
        self.charge_velocity = float(init_dict_data.get('Скорость зарядки'))
        # Скорость потребления аккумулятора в полёте
        self.flight_discharge = float(init_dict_data.get('Скорость потребления аккумулятора в полёте'))
        # Коэффициент потребления аккумулятора с грузом А
        self.load_discharge_A = float(init_dict_data.get('Коэффициент потребления аккумулятора А'))
        # Коэффициент потребления аккумулятора с грузом B
        self.load_discharge_B = float(init_dict_data.get('Коэффициент потребления аккумулятора B'))
        # Ёмкость аккумулятора
        self.capacity = float(init_dict_data.get('Ёмкость аккумулятора'))
        # Время инициализации
        self.init_time = float(init_dict_data.get('Время инициализации'))

        self.velocity = float(init_dict_data.get('Скорость'))
        self.max_mass = float(init_dict_data.get('Грузоподъемность'))

        self.min_charge = float(init_dict_data.get('Минимальный уровень заряда'))
        

        self.uri = 'Courier' + str(self.number)

        self.schedule: typing.List[ScheduleItem] = []

    def __repr__(self):
        return 'Курьер ' + str(self.name)

    def get_type(self):
        """
        :return: onto_description -> metadata -> type
        """
        return 'COURIER'
    
    def check_possibility(self, change_items: typing.List[ScheduleItem]):
        cheked_schedule = copy.deepcopy(self.schedule)

        for item in change_items:
            for rec in cheked_schedule:
                # удаляем изменённые заказы
                if rec.order == item.order:
                    
                    break

    


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

    def is_order_displaceable(self, order: OrderEntity, current_time: float) -> bool:
        """Проверяет, можно ли вытеснить или сдвинуть заказ (т.е. он еще не начался)."""
        order_records = self.get_all_order_records(order)
        if not order_records:
            return True # Заказа нет в расписании, его не нужно вытеснять
        
        min_start_time = min(r.start_time for r in order_records)
        return current_time < min_start_time
    
    def get_all_order_records(self, order: OrderEntity) -> typing.List[ScheduleItem]:
        """
        Возвращает все записи указанного заказа
        :param order:
        :return:
        """
        result: typing.List[ScheduleItem] = [rec for rec in self.schedule if rec.order == order]
        return result
    
    def get_consumption_by_distance(self, distance: float, order: OrderEntity = None) -> float:
        """Рассчитывает расход энергии на полет заданной дистанции."""
        return get_consumption_by_distance(distance, order, self)
    
    def get_consumption_by_time(self, time: float, order: OrderEntity = None) -> float:
        """Рассчитывает расход энергии на полет заданной дистанции."""
        return get_consumption_by_time(courier=self, flight_time=time, order=order)
        
    def get_charge_at_time(self, time: float) -> float:
        """
        Рассчитывает предполагаемый уровень заряда на заданный момент времени,
        анализируя расписание до этого момента.
        """
        return get_charge_at_time(time, self)

        

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
            last_free_time = self.get_last_time(consider_charge=False)
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
        # waiting_item_with_order = ScheduleItem(order, 'Ожидание', common_finish_time, end_time,
        #                                        order.point_to, order.point_to,
        #                                        0, all_params)
        if not self.schedule:
            # Записей пока не было, добавляем заказ
            if abs(schedule_item_to_order.start_time - schedule_item_to_order.end_time) > EPSILON:
                self.schedule.append(schedule_item_to_order)
            self.schedule.append(schedule_item)
            # if abs(waiting_item_with_order.start_time - waiting_item_with_order.end_time) > EPSILON:
            #     self.schedule.append(waiting_item_with_order)
            return True
        conflicts = self.get_conflicts(start_time, end_time)
        if self.get_conflicts(start_time, end_time):
            logging.info(f'{self} - не могу добавить записи на интервал - {start_time} - {end_time},'
                         f' конфликты - {conflicts}')
            return False
        if abs(schedule_item_to_order.start_time - schedule_item_to_order.end_time) > EPSILON:
            self.schedule.append(schedule_item_to_order)
        self.schedule.append(schedule_item)
        # if abs(waiting_item_with_order.start_time - waiting_item_with_order.end_time) > EPSILON:
        #     self.schedule.append(waiting_item_with_order)
        self.schedule, _ = auto_add_charge(self.schedule, self)

        self.schedule.sort(key=lambda rec: rec.start_time)
        return True

    def get_last_point(self) -> Point:
        """
        Возвращает последнюю точку из расписания курьера
        :return:
        """
        if not self.schedule:
            return self.init_point
        if self.schedule[-1].is_move_to_charge:
            return self.schedule[-2].point_to
        last_point = self.schedule[-1].point_to

        return last_point

    def get_point_at_time(self, time: float) -> Point:
        return get_point_at_time(self, self.schedule, time)

    def get_last_time(self, consider_charge: bool = True) -> int:
        """
        Возвращает время, когда курьер может приступить к выполнению заказа
        :return:
        """
        if not self.schedule:
            return 0
        if self.schedule[-1].is_move_to_charge and not consider_charge:
            return self.schedule[-2].end_time
        return self.schedule[-1].end_time

    def delete_order(self, order: OrderEntity):
        self.schedule, cost_change = delete_order(self.schedule, order, self)
        return cost_change


    def get_schedule_json(self):
        """
        Сериализация расписания курьера
        :return:
        """
        result = []
        # if self.schedule and self.schedule[0].start_time != 0:
        #     # Формируем в расписании ожидание в начальной точке
        #     next_record = self.schedule[0]
        #     downtime_record = ScheduleItem(next_record.order, 'Ожидание', 0, next_record.start_time,
        #                                    self.init_point, self.init_point, 0, {})
        #     self.schedule.insert(0, downtime_record)
        # for number, record in enumerate(self.schedule):
        #     if number == len(self.schedule) - 1:
        #         break
        #     next_record = self.schedule[number + 1]
        #     if record.end_time != next_record.start_time:
        #         # Формируем в расписании ожидание в точке, где отдали заказ.
        #         downtime_record = ScheduleItem(record.order, 'Ожидание', record.end_time, next_record.start_time,
        #                                        record.point_to, record.point_to, 0, record.all_params)
        #         self.schedule.append(downtime_record)
        self.schedule.sort(key=lambda rec: (rec.start_time, rec.end_time))
        for rec in self.schedule:
            if rec.is_move_to_charge:
                json_record = {
                    'resource_id': self.number,
                    'resource_name': self.name,
                    'task_id': None,
                    'task_name': None,
                    'type': rec.rec_type,
                    'from': str(rec.point_from),
                    'to': str(rec.point_to),
                    'start_time': rec.start_time,
                    'end_time': rec.end_time,
                    'cost': rec.cost,
                    "is_move_to_charge": rec.is_move_to_charge
                }
            else:
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
                    "is_move_to_charge": rec.is_move_to_charge,
                    "charge_on_end": self.get_charge_at_time(rec.end_time)
                }
            result.append(json_record)
        return result

def get_consumption_by_distance(courier: CourierEntity, distance: float, order: OrderEntity = None) -> float:
        """Рассчитывает расход энергии на полет заданной дистанции."""
        flight_time = distance / courier.velocity
        return get_consumption_by_time(courier, flight_time, order)
        
def get_consumption_by_time(courier: CourierEntity, flight_time: float, order: OrderEntity = None) -> float:
        """Рассчитывает расход энергии на полет заданной дистанции."""
        if order:
            discharge_on_time = (order.weight*courier.load_discharge_A)**2 + order.weight*courier.load_discharge_B + courier.flight_discharge
        else:
            discharge_on_time = courier.flight_discharge
        base_consumption = flight_time * discharge_on_time
        return base_consumption

def get_charge_at_time(time: float, courier: CourierEntity):
    charge = courier.capacity
    last_time = 0
    last_point = courier.init_point
    for rec in courier.schedule:
        if rec.start_time <= time < rec.end_time:
            #TODO добавить учёта части зарядки
            return charge
        elif rec.start_time > time:
            return charge
        
        if last_point == courier.init_point:
            charge += courier.charge_velocity*(rec.start_time - last_time)
            charge = min(charge, courier.capacity)
        else:
            charge -= get_consumption_by_time(courier=courier, flight_time=rec.start_time - last_time)
        
        if rec.is_move_to_charge:
            charge -= get_consumption_by_distance(courier=courier, 
                                      distance=rec.point_from.get_distance_to_other(rec.point_to))
        elif rec.rec_type == "Движение за грузом":
            charge -= get_consumption_by_distance(courier=courier, 
                                      distance=rec.point_from.get_distance_to_other(rec.point_to))
        elif rec.rec_type == "Ожидание":
            charge -= get_consumption_by_distance(courier=courier, 
                                      distance=rec.point_from.get_distance_to_other(rec.point_to))
        elif rec.rec_type == "Движение с грузом":
            charge -= get_consumption_by_distance(courier=courier, 
                                      distance=rec.point_from.get_distance_to_other(rec.point_to),
                                      order=rec.order)
        else:
            raise ValueError(f"Тип события {rec.rec_type} не распознан")
        

        charge = max(charge, 0)
        
        
        last_point = rec.point_to
        last_time = rec.end_time
    return charge
        


def get_point_at_time(self, schedule: typing.List[ScheduleItem], time: float) -> Point:
        if not schedule:
            return self.init_point
        previos_point = self.init_point
        for record in schedule:
            if record.start_time <= time < record.end_time:
                raise ValueError(f'Время находится в событии')
            if time < record.start_time:
                return previos_point
            previos_point = record.point_to
        return record.point_to # Последняя точка

def auto_add_charge(schedule: typing.List[ScheduleItem], courier: CourierEntity):
    cost_change = 0
    for i, rec in enumerate(schedule):
        if rec.is_move_to_charge:
            continue
        if i + 1 >= len(schedule):
            point_from = rec.point_to
            duration = rec.point_to.get_distance_to_other(courier.init_point)/courier.velocity
            schedule.insert(i + 1,ScheduleItem(None, 
                                         "Следование на зарядку", 
                                         rec.end_time, 
                                         rec.end_time + duration, 
                                         point_from, 
                                         courier.init_point, 
                                         courier.rate*duration, {}))
            cost_change += courier.rate*duration
            break
        
        next_index = i + 1
        if schedule[i + 1].rec_type == "Движение за грузом":
            next_index = i + 2

        pause = schedule[next_index].start_time - schedule[i].end_time
        duration_to_init = schedule[i].point_to.get_distance_to_other(courier.init_point)/courier.velocity
        duration_to_next = courier.init_point.get_distance_to_other(schedule[next_index].point_to)/courier.velocity
        lost_charge = courier.get_consumption_by_time(duration_to_init+duration_to_next)
        get_charge = courier.charge_velocity * (pause - duration_to_init - duration_to_next)
        if get_charge > lost_charge:
            if not next_index == i + 1:
                cost_change -= schedule[i + 1].cost
                schedule.remove(schedule[i + 1]) # удаляем движение за грузом тк добавим своё
                next_index -= 1
            schedule.insert(i + 1,ScheduleItem(order=None, 
                                         rec_type="Следование на зарядку", 
                                         start_time=schedule[i].end_time, 
                                         end_time=schedule[i].end_time + duration_to_init,
                                         point_from=schedule[i].point_to, 
                                         point_to=courier.init_point, 
                                         cost=courier.rate*duration_to_init, 
                                         all_params={}))
            next_index += 1
            
            schedule.insert(i + 2,ScheduleItem(order=schedule[next_index].order, 
                                         rec_type="Движение за грузом", 
                                         start_time=schedule[next_index].start_time - duration_to_next, 
                                         end_time=schedule[next_index].start_time,
                                         point_from=courier.init_point, 
                                         point_to=schedule[next_index].point_to, 
                                         cost=courier.rate*duration_to_next, 
                                         all_params={}))
            next_index += 1

            cost_change += courier.rate*duration_to_init + courier.rate*duration_to_next



            
    return schedule, cost_change

def delete_order(schedule: typing.List[ScheduleItem], order: OrderEntity, courier: CourierEntity):
    """
    Удаляет заказ из расписания и возвращает новый список записей.
    Если при этом удаляется движение за грузом, то добавляется альтернативное движение на зарядку.
    :param schedule:  список записей расписания
    :param order:     удаляемый заказ
    :param courier:   курьер, для которого производится удаление
    :return:          новый список записей, изменение цены
    """
    cost_change = 0
    indexes_to_remove = []
    for i, rec in enumerate(schedule):
        if rec.order == order:
            indexes_to_remove.append(i)

    # Удаляем связанные с заказом движения на зарядку
    for index in indexes_to_remove:
        if index + 1 >= len(schedule):
            continue
        if schedule[index + 1].is_move_to_charge:
            indexes_to_remove.append(index + 1)

    # Удаляем выбранные записи
    indexes_to_remove = list(set(indexes_to_remove))
    for index in reversed(indexes_to_remove):
        cost_change -= schedule[index].cost
        del schedule[index]

    # Добавляем альтернативное движение на зарядку, если оно возможно
    schedule, cc = auto_add_charge(schedule, courier)
    cost_change += cc
    return [rec for rec in schedule if rec.order != order], cost_change

def get_all_records_by_order(schedule, order: OrderEntity):
    return [rec for rec in schedule if rec.order == order]

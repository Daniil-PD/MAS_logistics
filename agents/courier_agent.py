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

        all_variants = []
        # ======================================================================
        # Сценарий 1: Вставка в расписание (JIT и анализ конфликтов)
        # ======================================================================
        
        # Идеальное время начала движения, чтобы успеть к началу окна заказа
        ideal_jit_start = order.time_from - time_to_order
        
        # ПРОВЕРКА 1: Нельзя планировать в прошлом (относительно времени симуляции)
        if ideal_jit_start >= self.scene.time:
            ideal_jit_end = ideal_jit_start + duration
            
            # Ищем конфликты именно в этом идеальном временном слоте
            conflicted_records = self.entity.get_conflicts(ideal_jit_start, ideal_jit_end)

            if not conflicted_records:
                # Отлично, мы нашли чистое "окно" в расписании для JIT-вставки!
                jit_variant = {
                    'courier': self.entity, 'time_from': ideal_jit_start, 'time_to': ideal_jit_end,
                    'price': price, 'order': order, 'variant_name': 'jit'
                }
                all_variants.append(jit_variant)
            else:
                # Конфликт существует. Теперь запускаем анализ вытеснения и сдвига
                # для этого конкретного временного интервала.
                logging.info(f"{self}: Обнаружен конфликт для JIT-варианта заказа {order}. Запускаю анализ...")
                
                # Попытка ВЫТЕСНЕНИЯ (Displacement)
                displace_variant = self._try_create_displacement_variant(order, ideal_jit_start, ideal_jit_end, price)
                if displace_variant:
                    all_variants.append(displace_variant)

                # Попытка КАСКАДНОГО СДВИГА (Rescheduling)
                reschedule_variant = self._try_create_reschedule_variant(order, ideal_jit_start, ideal_jit_end, price)
                if reschedule_variant:
                    all_variants.append(reschedule_variant)
        else:
            logging.info(f"{self}: Идеальный JIT-старт ({ideal_jit_start:.2f}) для заказа {order} находится в прошлом (тек. время {self.scene.time:.2f}).")


        # ======================================================================
        # Сценарий 2: Добавление в конец (ASAP)
        # ======================================================================

        # Время начала не может быть раньше, чем курьер закончит последнее дело,
        # и не раньше текущего момента времени.
        asap_start_time = max(self.entity.get_last_time(), self.scene.time)
        asap_end_time = asap_start_time + duration
        
        # Для этого варианта не должно быть конфликтов, т.к. мы добавляем в конец
        asap_variant = {
            'courier': self.entity, 'time_from': asap_start_time, 'time_to': asap_end_time,
            'price': price, 'order': order, 'variant_name': 'asap'
        }
        all_variants.append(asap_variant)


        return all_variants

    def _get_asap_variant(self, order: OrderEntity, duration: float):
        asap_start_time = max(self.entity.get_last_time(consider_charge=True), self.scene.time)
        asap_end_time = asap_start_time + duration

        start_charge = self.entity.get_charge_at_time(asap_start_time)

        last_point: Point = self.entity.get_last_point()
        distance_to_order = last_point.get_distance_to_other(order.point_from)
        distance_with_order = order.point_from.get_distance_to_other(order.point_to)
        distance_to_base = last_point.get_distance_to_other(self.entity.init_point)

        consumption_to_order = self.entity.get_consumption(distance_to_order)
        consumption_with_order = self.entity.get_consumption(distance_with_order, order)
        consumption_to_base = self.entity.get_consumption(distance_to_base)
        consumption_total = consumption_to_order + consumption_with_order + consumption_to_base
        price = duration * self.entity.rate
        
        if start_charge - consumption_total - self.entity.min_charge < 0:
            # вариант не возможен в это время тк не будет достаточного заряда
            time_to_charge =  (consumption_total + self.entity.min_charge)/ self.entity.charge_velocity

            duration_to_init = last_point.get_distance_to_other(self.entity.init_point)/self.entity.velocity
            duration_to_next = self.entity.init_point.get_distance_to_other(order.point_to)/self.entity.velocity


            need_window = time_to_charge + duration_to_init + duration_to_next
            price += (duration_to_init+duration_to_next) * self.entity.rate

            asap_start_time = max(self.entity.get_last_time(consider_charge=False), self.scene.time)
            asap_end_time = asap_start_time + duration

            asap_start_time += need_window
            asap_end_time += need_window

        return {
            'courier': self.entity, 'time_from': asap_start_time, 'time_to': asap_end_time,
            'price': price, 'order': order, 'variant_name': 'asap', 
            "changes": {
                "add_to_shedule": {
                    "order": order,
                    "start_time": asap_start_time,
                    "end_time": asap_end_time,
                    "price": price
                }
            }
        }


    def _try_create_displacement_variant(self, new_order, start_time, end_time, new_price):
        """Пытается создать вариант с вытеснением одного из существующих заказов."""
        conflicted_records = self.entity.get_conflicts(start_time, end_time)
        if not conflicted_records:
            return None

        displaceable_orders = []
        conflicted_orders = set(rec.order for rec in conflicted_records)
        for _order in conflicted_orders:
            if self.entity.is_order_displaceable(_order, self.scene.time):
                displaceable_orders.append(_order)
        
        # Ищем заказы, которые дешевле нового и могут быть вытеснены
        poss_removing_orders = [_o for _o in displaceable_orders if _o.price < new_order.price]
        if not poss_removing_orders:
            return None

        # Выбираем самый дешевый для вытеснения
        order_to_displace = min(poss_removing_orders, key=lambda x: x.price)
        logging.info(f"{self} нашел вариант вытеснить заказ {order_to_displace} для {new_order}")

        # Для простоты, мы предполагаем, что размещение на месте вытесненного заказа возможно
        # и не создаст новых конфликтов. В реальной системе это потребовало бы доп. проверок.
        return {
            'courier': self.entity, 'time_from': start_time, 'time_to': end_time,
            'price': new_price, 'order': new_order, 'variant_name': 'conflict',
            'order_to_displace': order_to_displace
        }

    def _try_create_reschedule_variant(self, new_order, start_time, end_time, new_price):
        """
        Пытается создать вариант с каскадным сдвигом существующих заказов.
        Возвращает `reschedule_variant` или `None`.
        """
        shift_chain = []
        is_shift_possible = True
        last_available_time = end_time  # Время, когда новый заказ будет завершен

        # Начинаем проверку каскада
        temp_schedule = sorted(self.entity.schedule, key=lambda r: r.start_time)

        while True:
            # Ищем первый заказ, который теперь конфликтует с нашим `last_available_time`
            conflicting_order = None
            for rec in temp_schedule:
                if rec.start_time < last_available_time:
                    # Убедимся, что мы еще не обработали этот заказ в цепочке
                    if rec.order not in [item['order'] for item in shift_chain]:
                        conflicting_order = rec.order
                        break
            
            if conflicting_order is None:
                # Больше конфликтов нет, цепочка успешно построена
                break

            # Проверяем, можно ли вообще трогать этот заказ
            if not self.entity.is_order_displaceable(conflicting_order, self.scene.time):
                logging.info(f"{self}: Цепочка сдвига прервана. Заказ {conflicting_order} уже выполняется.")
                is_shift_possible = False
                break
            
            # Рассчитываем длительность сдвигаемого заказа
            order_records = self.entity.get_all_order_records(conflicting_order)
            duration = max(r.end_time for r in order_records) - min(r.start_time for r in order_records)
            
            # Предлагаемое новое время
            new_start_for_shifted = last_available_time
            new_end_for_shifted = new_start_for_shifted + duration

            # Проверяем дедлайн
            if new_end_for_shifted > conflicting_order.time_to:
                logging.info(f"{self}: Цепочка сдвига прервана. Заказ {conflicting_order} не уложится в дедлайн.")
                is_shift_possible = False
                break
            
            # Все проверки для этого шага пройдены. Добавляем в цепочку и обновляем время.
            shift_chain.append({
                'order': conflicting_order,
                'new_start': new_start_for_shifted,
                'new_end': new_end_for_shifted
            })
            last_available_time = new_end_for_shifted

        if is_shift_possible and shift_chain:
            logging.info(f"{self} УСПЕШНО построил цепочку сдвига из {len(shift_chain)} заказов для {new_order}.")
            return {
                'courier': self.entity, 'time_from': start_time, 'time_to': end_time,
                'price': new_price, 'order': new_order, 'variant_name': 'reschedule',
                'shift_chain': shift_chain
            }
        
        return None


    def add_order(self, params: dict) -> bool:
        """
        Добавление заказа с параметрами в расписание ресурса.
        Переписано для атомарной обработки сложных вариантов.
        """
        variant_name = params.get('variant_name')
        
        # Сохраняем копию расписания для отката в случае неудачи
        backup_schedule = copy.deepcopy(self.entity.schedule)
        
        try:
            if variant_name == 'conflict':
                order_to_displace = params['order_to_displace']
                logging.info(f"{self} пытается вытеснить {order_to_displace} для нового заказа.")
                # Удаляем все записи вытесняемого заказа
                self.entity.remove_order_from_schedule(order_to_displace)
                # Добавляем новый заказ
                if not self.entity.add_order_to_schedule(params.get('order'), params.get('time_from'), params.get('time_to'), params.get('price'), params):
                    raise ValueError("Не удалось добавить новый заказ после вытеснения.")
                
                # Сообщаем вытесненному заказу, что ему нужно искать нового исполнителя
                remove_message = Message(MessageType.REMOVE_ORDER, self.entity)
                removed_order_address = self.dispatcher.reference_book.get_address(order_to_displace)
                self.send(removed_order_address, remove_message)
                return True

            elif variant_name == 'reschedule':
                shift_chain = params.get('shift_chain', [])
                logging.info(f"{self} пытается выполнить сдвиг {len(shift_chain)} заказов.")
                
                # 1. Удаляем все заказы, которые будут сдвинуты
                for item in shift_chain:
                    self.entity.remove_order_from_schedule(item['order'])
                
                # 2. Добавляем новый заказ
                if not self.entity.add_order_to_schedule(params.get('order'), params.get('time_from'), params.get('time_to'), params.get('price'), params):
                    raise ValueError("Не удалось добавить новый заказ при сдвиге.")
                
                # 3. Добавляем сдвинутые заказы на новые места
                for item in shift_chain:
                    # Стоимость для сдвинутого заказа не меняется, находим ее из бэкапа
                    original_cost = sum(r.cost for r in backup_schedule if r.order == item['order'])
                    if not self.entity.add_order_to_schedule(item['order'], item['new_start'], item['new_end'], original_cost, {}):
                        raise ValueError(f"Не удалось добавить сдвинутый заказ {item['order']} на новое место.")
                return True

            else: # Обычный вариант 'asap' или 'jit'
                return self.entity.add_order_to_schedule(params.get('order'), params.get('time_from'), params.get('time_to'), params.get('price'), params)

        except Exception as e:
            logging.error(f"{self} ОШИБКА при планировании варианта '{variant_name}': {e}. Восстанавливаю расписание.")
            self.entity.schedule = backup_schedule
            return False

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

import logging

from agents.agents_dispatcher import AgentsDispatcher
from agents.scene import Scene
from entities.courier_entity import CourierEntity
from entities.order_entity import OrderEntity
from utils.script import Script, ScriptEvent, ScriptEventType
import time

class Simulator:
    def __init__(self, 
                 script: Script,
                 tick_size: float = 0.5,
                 time_stop: int = 10**3,
                 callback = None
                 ):
        """Инициализация симуляции
        :param script: Сценарий симуляции
        :param tick_size: Размер шага симуляции
        :param time_stop: Максимальное время симуляции
        :param callback: 
        """


        self.script = script # Сценарий симуляции
        self.scene = Scene() # Сцена
        self.dispatcher = AgentsDispatcher(self.scene)

        self.tick_counter = 0
        self.scene.time = 0.0
        self.previous_tick_time = 0
        self.tick_size = tick_size
        self.time_stop = time_stop
    
        self.callback = callback

    def add_agent(self, agent):
        pass


    def run(self):
        """Запускает симуляцию
        """
        while True:
            if self.scene.time > self.time_stop:
                break

            events = self.script.get_event_during_interval(self.scene.time, self.scene.time + self.tick_size)

            self.scene.time += self.tick_size
            self._tick(events)


    def _tick(self, events: list[ScriptEvent] = []):
        """Шаг симуляции
        :param events: Список событий
        """
        for event in events:
            logging.debug(f'Событие: {event.properties}')
            if event.event_type == ScriptEventType.NEW_COURIER:
                logging.debug(f'Создание курьера: {event.properties}')
                onto_description = {}
                entity = CourierEntity(onto_description, event.properties, self.scene)
                self.dispatcher.add_entity(entity)

            elif event.event_type == ScriptEventType.NEW_ORDER:
                logging.debug(f'Создание заказа: {event.properties}')
                onto_description = {}
                entity = OrderEntity(onto_description, event.properties, self.scene)
                self.dispatcher.add_entity(entity)

            elif event.event_type == ScriptEventType.REMOVE_ORDER:
                logging.debug(f'Удаление заказа: {event.properties}')
                self.dispatcher.remove_entity('ORDER', event.properties.get('name'))

            elif event.event_type == ScriptEventType.DELETED_COURIER:
                logging.debug(f'Удаление курьера: {event.properties}')
                self.dispatcher.remove_entity('COURIER', event.properties.get('name'))

            else:
                logging.error(f'Непонятное событие: {event}')

        self._tick_entities()
        self._tick_agents()
        time.sleep(self.tick_size/100) # FIXME: Тут по идее должно быть ожидание устаканивания событий

        if self.callback is not None:
            self.callback(self.get_statistic())

        self.tick_counter += 1
        
    def _tick_entities(self):
        pass

    def _tick_agents(self):
        self.dispatcher.tik_agents()

    def get_statistic(self):
        """Возвращает статистику симуляции
        """
        if self.scene.time == 0:
            raise RuntimeError("Симуляция не запущена")
        

        return {"time": self.scene.time,
                "tick_counter": self.tick_counter,
                "tick_size": self.tick_size}
    
    def get_all_schedule_records(self):
        all_schedule_records = []
        for courier in self.scene.get_entities_by_type('COURIER'):
            all_schedule_records.extend(courier.get_schedule_json())
        return all_schedule_records
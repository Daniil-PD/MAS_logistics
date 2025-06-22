from enum import Enum

class ScriptEventType(Enum):
    REMOVE_ORDER = 'Удаление заказа из расписания'
    NEW_ORDER = 'Появление нового заказа'

    DELETED_COURIER = 'Удаление курьера'
    NEW_COURIER = 'Появление нового курьера'



class ScriptEvent:
    def __init__(self, time, event_type: ScriptEventType, properties: dict):
        self.time = time
        self.event_type: ScriptEventType = event_type
        self.properties: dict = properties

    def __str__(self):
        return f'{self.event_type}: {self.properties}'


class Script:
    def __init__(self):
        self.events = []
        self.events.sort(key=lambda event: event.time)

    def add_event(self, event: ScriptEvent, sort=True):
        self.events.append(event)
        if sort:
            self.events.sort(key=lambda event: event.time)

    def load_orders_from_dicts(self, orders_dicts: list[dict]):
        for order_dict in orders_dicts:
            self.add_event(ScriptEvent(order_dict.get('Время появления'), 
                                       event_type=ScriptEventType.NEW_ORDER, 
                                       properties=order_dict))
            if order_dict.get('Время исчезновения') is not None:
                self.add_event(ScriptEvent(order_dict.get('Время исчезновения'), 
                                           event_type=ScriptEventType.REMOVE_ORDER, 
                                           properties=order_dict))
                

    def load_couriers_from_dicts(self, couriers_dicts: list[dict]):
        for courier_dict in couriers_dicts:
            self.add_event(ScriptEvent(courier_dict.get('Время появления'), 
                                       event_type=ScriptEventType.NEW_COURIER, 
                                       properties=courier_dict))
            if courier_dict.get('Время исчезновения') is not None:
                self.add_event(ScriptEvent(courier_dict.get('Время исчезновения'), 
                                           event_type=ScriptEventType.DELETED_COURIER, 
                                           properties=courier_dict))



    def get_upcoming_event_time(self, time):
        for event in self.events:
            if event.time >= time:
                return event
        return None
    
    def get_upcoming_events(self, time):
        """ Возвращает список событий, которые произойдут в ближайшее время 
        """
        result = []
        for event in self.events:
            if event.time >= time:
                if len(result) == 0:
                    result.append(event)
                else:
                    if result[-1].time == event.time:
                        result.append(event)
                    else:
                        break
        return result
    
    def get_event_during_interval(self, start_time, end_time):
        result = []
        for event in self.events:
            if start_time <= event.time < end_time:
                result.append(event)
        return result
    
    def __str__(self):
        return f"(Script, events_count: {len(self.events)})"
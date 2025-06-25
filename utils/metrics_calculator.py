import numpy as np
from agents.scene import Scene
from entities.courier_entity import CourierEntity
from entities.order_entity import OrderEntity

class MetricsCalculator:
    """
    Класс для расчета и сбора метрик по результатам симуляции.
    """
    def __init__(self, scene: Scene, simulation_end_time: float):
        self.scene = scene
        self.simulation_end_time = simulation_end_time
        self.all_couriers: list[CourierEntity] = self.scene.get_entities_by_type('COURIER')
        
        # Собираем все уникальные выполненные заказы из расписаний курьеров
        self.completed_orders: dict[str, OrderEntity] = {}
        for courier in self.all_couriers:
            for rec in courier.schedule:
                if rec.order is None: continue
                if rec.order.name not in self.completed_orders:
                    self.completed_orders[rec.order.name] = rec.order

    def calculate_all_metrics(self, json=False) -> dict:
        """Рассчитывает все метрики и возвращает их в виде словаря."""
        if not self.all_couriers:
            return {"error": "В симуляции нет курьеров для расчета метрик."}
            
        utilization = self._calculate_courier_utilization()
        distance = self._calculate_total_distance()
        on_time = self._calculate_on_time_performance()
        fairness_by_earnings = self._calculate_workload_fairness_by_earnings()
        fairness_by_time = self._calculate_workload_fairness_by_time()
        fairness_by_count_tasks = self._calculate_workload_fairness_by_count_tasks()
        avg_completion_time = self._calculate_average_completion_time()
        avg_completion_time_urgent = self._calculate_average_completion_time(order_is_urgent=True)
        avg_completion_time_not_urgent = self._calculate_average_completion_time(order_is_urgent=False)
        
        
        return {
            "Загруженность ресурсов (%)": utilization,
            "Общий пробег": distance,
            "Соблюдение временных окон (%)": on_time,
            "Равномерность распределения нагрузки (StdDev of Earnings)": fairness_by_earnings,
            "Равномерность распределения нагрузки (StdDev of Time)": fairness_by_time,
            "Равномерность распределения нагрузки (StdDev of Count Tasks)": fairness_by_count_tasks,
            "Среднее время выполнения заказа": avg_completion_time,
            "Количество сообщений": self.scene.count_messages,
            "Количество выполненных заказов": len(self.completed_orders),
            "Среднее время выполнения срочных заказов": avg_completion_time_urgent,
            "Среднее время выполнения несрочных заказов": avg_completion_time_not_urgent
        }

    def _calculate_courier_utilization(self) -> float:
        """
        Расчет средней загруженности курьеров.
        Загруженность = (Время работы / Общее доступное время) * 100%
        Время работы - это время, потраченное на любую деятельность, кроме "Ожидания".
        """
        total_utilization = 0
        
        for courier in self.all_couriers:
            # Считаем, что курьер доступен с 0 до конца симуляции
            # Для более точного расчета можно было бы использовать время появления/исчезновения из сценария
            total_available_time = self.simulation_end_time
            if total_available_time == 0: continue

            working_time = 0
            for record in courier.schedule:
                if record.rec_type != 'Ожидание':
                    working_time += (record.end_time - record.start_time)
            
            courier_utilization = (working_time / total_available_time) * 100
            total_utilization += courier_utilization
            
        return total_utilization / len(self.all_couriers) if self.all_couriers else 0

    def _calculate_total_distance(self) -> float:
        """Расчет общего расстояния, пройденного всеми курьерами."""
        total_distance = 0
        for courier in self.all_couriers:
            for record in courier.schedule:
                # Учитываем только записи, связанные с фактическим перемещением
                if "Движение" in record.rec_type:
                    distance = record.point_from.get_distance_to_other(record.point_to)
                    total_distance += distance
        return total_distance

    def _calculate_on_time_performance(self) -> float:
        """
        Расчет процента заказов, доставленных вовремя.
        Заказ считается выполненным вовремя, если фактическое время доставки
        не превышает требуемое 'time_to'.
        """
        if not self.completed_orders:
            return 100.0 # Если не было заказов, то 100% выполнено

        on_time_count = 0
        for order in self.completed_orders.values():
            required_delivery_time = order.time_to
            
            # Находим фактическое время доставки в расписании курьера
            actual_delivery_time = 0
            delivery_courier = next((c for c in self.all_couriers if order in [r.order for r in c.schedule]), None)
            if delivery_courier:
                # Время доставки - это 'end_time' записи "Движение с грузом"
                delivery_records = [r for r in delivery_courier.schedule if r.order == order and r.rec_type == 'Движение с грузом']
                if delivery_records:
                    actual_delivery_time = max(r.end_time for r in delivery_records)

            if actual_delivery_time > 0 and actual_delivery_time <= required_delivery_time:
                on_time_count += 1
                
        return (on_time_count / len(self.completed_orders)) * 100 if self.completed_orders else 100.0

    def _calculate_workload_fairness_by_earnings(self) -> float:
        """
        Расчет справедливости распределения нагрузки.
        Используем стандартное отклонение дохода каждого курьера.
        Низкое значение означает, что курьеры зарабатывают примерно одинаково.
        """
        if len(self.all_couriers) < 2:
            return 0.0 # Метрика не имеет смысла для одного курьера

        earnings = []
        for courier in self.all_couriers:
            courier_earnings = sum(record.cost for record in courier.schedule)
            earnings.append(courier_earnings)
            
        return float(np.std(earnings))
    
    def _calculate_workload_fairness_by_time(self) -> float:
        """
        Расчет справедливости распределения нагрузки.
        Используем стандартное отклонение времени работы каждого курьера.
        Низкое значение означает, что курьеры работают примерно одинаково.
        """
        if len(self.all_couriers) < 2:
            return 0.0 # Метрика не имеет смысла для одного курьера

        working_times = []
        for courier in self.all_couriers:
            courier_working_time = 0
            for record in courier.schedule:
                if record.rec_type != 'Ожидание':
                    courier_working_time += (record.end_time - record.start_time)
            working_times.append(courier_working_time)
            
        return float(np.std(working_times))
    
    def _calculate_workload_fairness_by_count_tasks(self) -> float:
        """
        Расчет справедливости распределения нагрузки.
        Используем стандартное отклонение количества заданий каждого курьера.
        Низкое значение означает, что курьеры работают примерно одинаково.
        """
        if len(self.all_couriers) < 2:
            return 0.0 # Метрика не имеет смысла для одного курьера

        working_counts = []
        for courier in self.all_couriers:
            courier_working_count = 0
            for record in courier.schedule:
                if record.rec_type == 'Движение с грузом':
                    courier_working_count += 1
            working_counts.append(courier_working_count)
            
        return float(np.std(working_counts))

    
    def _calculate_average_completion_time(self, order_is_urgent = None) -> float:
        """
        Расчет среднего времени выполнения заказа от его появления до фактической доставки.
        """
        if not self.completed_orders:
            return 0.0

        total_completion_duration = 0
        delivered_orders_count = 0

        for order in self.completed_orders.values():
            appearance_time = order.appearance_time

            if not order_is_urgent is None and order.is_urgent != order_is_urgent:
                continue
            
            # Находим фактическое время доставки (логика аналогична on-time performance)
            actual_delivery_time = 0
            delivery_courier = next((c for c in self.all_couriers if order in [r.order for r in c.schedule]), None)
            
            if delivery_courier:
                delivery_records = [r for r in delivery_courier.schedule if r.order == order and r.rec_type == 'Движение с грузом']
                if delivery_records:
                    actual_delivery_time = max(r.end_time for r in delivery_records)

            # Если заказ был доставлен, учитываем его в расчете
            if actual_delivery_time > 0:
                completion_duration = actual_delivery_time - appearance_time
                total_completion_duration += completion_duration
                delivered_orders_count += 1
                
        return total_completion_duration / delivered_orders_count if delivered_orders_count > 0 else 0.0
import random
import math
from typing import List, Dict, Any, Tuple


def rand_or_const(val):
    """
    Генерирует случайное число или возвращает константу.
    """
    if isinstance(val, tuple):
        return round(random.uniform(val[0], val[1]), 2)
    return val

def generate_orders(
    num_orders: int,
    urgent_percentage: float = 20.0,
    map_size: Tuple[int, int] = (100, 100),
    max_appearance_time: int = 50,
    avg_courier_speed: float = 10.0,
    payload_range: Tuple[float, float] = (10.0, 20.0),

) -> List[Dict[str, Any]]:
    """
    Генерирует список словарей с параметрами заказов.

    Args:
        num_orders (int): Количество заказов для генерации.
        urgent_percentage (float): Процент срочных заказов (от 0 до 100). 
                                   Срочность влияет на дедлайн доставки.
        map_size (Tuple[int, int]): Размеры карты (ширина, высота) для генерации координат.
        max_appearance_time (int): Максимальное время появления заказа в симуляции.
        avg_courier_speed (float): Средняя скорость курьера для расчета реалистичного окна доставки.

    Returns:
        List[Dict[str, Any]]: Список словарей, где каждый словарь представляет заказ.
    """
    orders = []
    num_urgent = int(num_orders * (urgent_percentage / 100.0))

    for i in range(num_orders):
        # Определение координат
        x_from, y_from = random.randint(0, map_size[0]), random.randint(0, map_size[1])
        # Гарантируем, что точка доставки не совпадает с точкой получения
        while True:
            x_to, y_to = random.randint(0, map_size[0]), random.randint(0, map_size[1])
            if (x_to, y_to) != (x_from, y_from):
                break
        
        distance = math.dist((x_from, y_from), (x_to, y_to))
        min_delivery_duration = distance / avg_courier_speed

        # Определение времени
        appearance_time = random.uniform(0, max_appearance_time)
        pickup_time = appearance_time + random.uniform(1, 10) # Заказ можно забрать через некоторое время после его появления

        # Определение срочности и дедлайна доставки
        is_urgent = i < num_urgent
        if is_urgent:
            # Срочный заказ: дедлайн очень близко к минимально возможному времени
            delivery_deadline = pickup_time + min_delivery_duration * random.uniform(1.1, 1.5)
        else:
            # Обычный заказ: больше времени на доставку
            delivery_deadline = pickup_time + min_delivery_duration * random.uniform(2.0, 4.0)

        order_dict = {
            'Номер': i + 1,
            'Наименование': f'Заказ-{i + 1}{" (Срочный)" if is_urgent else ""}',
            'Масса': rand_or_const(payload_range),
            'Объем': round(random.uniform(0.1, 2.0), 2),
            'Стоимость': round(random.uniform(100, 2000), 2),
            'Координата получения x': x_from,
            'Координата получения y': y_from,
            'Координата доставки x': x_to,
            'Координата доставки y': y_to,
            'Время получения заказа': round(pickup_time, 2),
            'Время доставки заказа': round(delivery_deadline, 2),
            # 'Тип заказа': random.choice(['A', 'B']),
            'Срочный заказ': is_urgent,
            'Время появления': round(appearance_time, 2),
            'Время исчезновения': None
        }
        orders.append(order_dict)

    # Перемешиваем, чтобы срочные заказы не шли первыми в списке
    random.shuffle(orders)
    return orders

def generate_couriers(
    num_couriers: int,
    map_size: Tuple[int, int] = (100, 100),
    velocity_range: Tuple[float, float] = (8.0, 15.0),
    payload_range: Tuple[float, float] = (10.0, 20.0),
    battery_load_velocity_A: float = 0.1,
    battery_load_velocity_B: float = 0.1,
    battery_capacity = 300,
) -> List[Dict[str, Any]]:
    """
    Генерирует список словарей с параметрами курьеров.

    Args:
        num_couriers (int): Количество курьеров для генерации.
        map_size (Tuple[int, int]): Размеры карты (ширина, высота) для генерации начальных координат.
        velocity_range (Tuple[float, float]): Диапазон скоростей курьеров (min, max).
        payload_range (Tuple[float, float]): Диапазон грузоподъемности курьеров (min, max).

    Returns:
        List[Dict[str, Any]]: Список словарей, где каждый словарь представляет курьера.
    """
    couriers = []
    for i in range(num_couriers):
        courier_dict = {
            'Табельный номер': i + 1,
            'name': f'Курьер-{i + 1}', 
            'Координата начального положения x': random.randint(0, map_size[0]),
            'Координата начального положения y': random.randint(0, map_size[1]),
            'Стоимость выхода на работу': round(random.uniform(100, 500), 2),
            'Цена работы за единицу времени': round(random.uniform(10, 30), 2),
            'Скорость зарядки': round(random.uniform(1, 5), 2),
            'Скорость потребления аккумулятора в полёте': round(random.uniform(0.5, 2), 2),
            'Коэффициент потребления аккумулятора А': rand_or_const(battery_load_velocity_A),
            'Коэффициент потребления аккумулятора B': rand_or_const(battery_load_velocity_B),
            'Ёмкость аккумулятора': rand_or_const(battery_capacity),
            'Время инициализации': 0.5,
            'Скорость': round(random.uniform(velocity_range[0], velocity_range[1]), 2),
            'Грузоподъемность': rand_or_const(payload_range),
            'Время появления': 0.0, # Все курьеры доступны с начала
            'Время исчезновения': None, # Работают всю симуляцию
            'Минимальный уровень заряда': 10
        }
        couriers.append(courier_dict)
    return couriers

# --- Пример использования ---
if __name__ == "__main__":
    from pprint import pprint

    generated_orders = generate_orders(num_orders=10, urgent_percentage=30)
    print("--- Сгенерированные Заказы ---")
    pprint(generated_orders[:3])

    print("\n" + "="*40 + "\n")

    generated_couriers = generate_couriers(num_couriers=4)
    print("--- Сгенерированные Курьеры ---")
    pprint(generated_couriers[:2])
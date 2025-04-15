import logging

from agents.agents_dispatcher import AgentsDispatcher
from agents.scene import Scene
from entities.courier_entity import CourierEntity
from entities.order_entity import OrderEntity
from utils.excel_utils import get_excel_data, save_schedule_to_excel

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                        format="%(asctime)s %(levelname)s %(message)s", 
                        filename="log.txt", 
                        filemode="w", 
                        encoding="UTF-8",
                        force=True)


    logging.info("Добро пожаловать в мир агентов")
    scene = Scene()
    dispatcher = AgentsDispatcher(scene)

    couriers = get_excel_data('Исходные данные_конфликт copy.xlsx', 'Курьеры')
    logging.info(f'Прочитаны курьеры: {couriers}')
    for courier in couriers:
        onto_description = {}
        entity = CourierEntity(onto_description, courier, scene)
        dispatcher.add_entity(entity)

    orders = get_excel_data('Исходные данные_конфликт copy.xlsx', 'Заказы')
    logging.info(f'Прочитаны заказы: {orders}')
    for order in orders:
        onto_description = {}
        entity = OrderEntity(onto_description, order, scene)
        logging.info(f'Добавлен заказ: {order}')
        dispatcher.add_entity(entity)

    all_schedule_records = []
    for courier in scene.get_entities_by_type('COURIER'):
        all_schedule_records.extend(courier.get_schedule_json())
    save_schedule_to_excel(all_schedule_records, 'Результаты.xlsx')

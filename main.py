import logging


from utils.excel_utils import get_excel_data, save_schedule_to_excel
from utils.simulator import Simulator
from utils.script import Script
from utils.generators import generate_orders, generate_couriers


class My_callback:
    def __init__(self, print_every_n_tick=100):
        self.print_every_n_tick = print_every_n_tick
        self.last_tick = 0
    def callback_print(self, data: dict) -> None:
        if data.get('tick_counter') - self.last_tick > self.print_every_n_tick:
            print(data)
            self.last_tick = data.get('tick_counter')

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, 
                        format="%(asctime)s %(levelname)s %(message)s", 
                        filename="log.txt", 
                        filemode="w", 
                        encoding="UTF-8",
                        force=True
                        )
    
    script = Script()

    order_dicts = generate_orders(num_orders=50, urgent_percentage=25)
    courier_dicts = generate_couriers(num_couriers=10)

    # order_dicts = get_excel_data('Исходные данные_конфликт copy.xlsx', 'Заказы')
    # courier_dicts = get_excel_data('Исходные данные_конфликт copy.xlsx', 'Курьеры')

    # Загрузка данных в сценарий
    script.load_orders_from_dicts(order_dicts)
    script.load_couriers_from_dicts(courier_dicts)

    # Инициализация симуляции
    cb = My_callback(print_every_n_tick=10)
    simulator = Simulator(script, 
                          tick_size=0.5, 
                          time_stop=50, 
                          callback=cb.callback_print)
    
    # Запуск симуляции
    simulator.run()


    # Сохранение результатов
    all_schedule_records = simulator.get_all_schedule_records()
    save_schedule_to_excel(all_schedule_records, "res.xlsx")
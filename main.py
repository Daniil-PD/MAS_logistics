import logging
import pandas as pd
import time
from tqdm.auto import tqdm

from utils.excel_utils import get_excel_data, save_schedule_to_excel
from utils.simulator import Simulator
from utils.script import Script
from utils.generators import generate_orders, generate_couriers
from utils.metrics_calculator import MetricsCalculator


class My_callback:
    def __init__(self, print_every_n_tick=100):
        self.print_every_n_tick = print_every_n_tick
        self.last_tick = 0
    def callback_print(self, data: dict) -> None:
        if data.get('tick_counter') - self.last_tick > self.print_every_n_tick:
            print(data)
            self.last_tick = data.get('tick_counter')

def experiment(parameters: dict) -> dict:
    start_time = time.time()

    script = Script()
    order_dicts = generate_orders(num_orders=parameters['num_orders'], 
                                  urgent_percentage=parameters['urgent_percentage'],
                                  map_size=parameters["map_size"],
                                  max_appearance_time=parameters["max_appearance_time"],
                                  avg_courier_speed=parameters["avg_courier_speed"])
    courier_dicts = generate_couriers(num_couriers=parameters['num_couriers'],
                                      map_size=parameters["map_size"],
                                      velocity_range=parameters["velocity_range"],
                                      payload_range=parameters["payload_range"])

    # Загрузка данных в сценарий
    script.load_orders_from_dicts(order_dicts)
    script.load_couriers_from_dicts(courier_dicts)
    # Инициализация симуляции
    cb = My_callback(print_every_n_tick=10)
    simulator = Simulator(script, 
                          tick_size=parameters["tick_size"], 
                          time_stop=parameters["time_stop"], 
                        #   callback=cb.callback_print
                          )
    
    # Запуск симуляции
    simulator.run()

    # print("\n" + "="*30)
    # print(">>> Расчет итоговых метрик:")
    simulator.dispatcher.actor_system.shutdown()
    # Создаем экземпляр калькулятора, передавая ему финальное состояние сцены
    calculator = MetricsCalculator(simulator.scene, simulator.time_stop)
    metrics = calculator.calculate_all_metrics()
    del calculator
    # Сохранение результатов
    # all_schedule_records = simulator.get_all_schedule_records()
    # save_schedule_to_excel(all_schedule_records, "res.xlsx")

    metrics["experiment_time"] = time.time() - start_time
    # print(f"Время выполнения симуляции: {metrics['experiment_time']}")

    return metrics

def parameters_generator(parameters_ranges: dict) -> dict:
    params_selector = {key: 0 for key in parameters_ranges.keys()}

    while True:
        parameters = {}
        for key, value in parameters_ranges.items():
            parameters[key] = value[params_selector[key]]

        yield parameters
        
        for key in params_selector.keys():
            if params_selector[key] < len(parameters_ranges[key]) - 1:
                params_selector[key] += 1
                break
            else:
                params_selector[key] = 0
        else:
            return
    


if __name__ == "__main__":
    parameters_ranges = {
        "tick_size": [1],
        "time_stop": [60],
        "num_orders": [5, 10, 15, 20, 25, 30],
        "urgent_percentage": [0, 5, 10],
        "num_couriers": [*range(1, 30, 5)],
        "map_size": [(100, 100)],
        "max_appearance_time": [50],
        "avg_courier_speed": [4, 5],
        "velocity_range": [(8.0, 15.0)],
        "payload_range": [(10.0, 20.0)]
    }

    experiment_count = 1
    for parameters in parameters_ranges:
        experiment_count *= len(parameters_ranges[parameters])
    print(f"Количество экспериментов: {experiment_count}")


    logging.basicConfig(level=logging.WARNING, 
                        format="%(asctime)s %(levelname)s %(message)s", 
                        filename="log.txt", 
                        filemode="w", 
                        encoding="UTF-8",
                        force=True
                        )
    

    

    experiments_results = []
    for parameters in tqdm(parameters_generator(parameters_ranges), total=experiment_count):
        res = experiment(parameters)
        experiments_results.append({
            **res,
            **parameters
        })
        # print(res)
    df = pd.DataFrame(experiments_results)
    df.to_excel("experiments_results.xlsx")

    
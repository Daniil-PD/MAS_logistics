import matplotlib.pyplot as plt
import numpy as np
# from agents.courier_agent import 
from entities.courier_entity import get_charge_at_time


def plot_charge(shedule, courier):
    max_time = max(rec.end_time for rec in shedule)
    times = list(np.linspace(0, max_time, 250))
    times.extend(rec.end_time for rec in shedule)
    times.extend(rec.start_time for rec in shedule)
    times.sort()
    charges = [get_charge_at_time(shedule, time, courier) for time in times]
    plt.xlabel('Время симуляции')
    plt.ylabel('Заряд')
    plt.title('Заряд курьера во времени')
    plt.plot(times, charges)
    plt.show()


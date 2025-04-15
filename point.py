""" Содержит реализацию точки на плоскости"""
import math


class Point:
    """
    Класс точки на плоскости
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return '(' + str(self.x) + '; ' + str(self.y) + ')'

    def get_distance_to_other(self, other_point):
        """
        Возвращает расстояние до другой точки
        :param other_point:
        :return:
        """
        order_distance = math.dist((self.x, self.y), (other_point.x, other_point.y))
        return order_distance

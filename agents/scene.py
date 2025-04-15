from collections import defaultdict
import typing


class Scene:
    """
    Класс сцены
    """
    def __init__(self):
        self.entities = defaultdict(list)

    def get_entities_by_type(self, entity_type) -> typing.List:
        """
        Возвращает сущности заданного типа, которые не находятся в процессе удаления
        :param entity_type:
        :return:
        """
        all_entities = self.entities.get(entity_type, [])
        not_deleting_entities = [entity for entity in all_entities if not entity.is_deleting]
        return not_deleting_entities

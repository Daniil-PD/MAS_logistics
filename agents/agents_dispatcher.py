"""Содержит класс диспетчера агентов"""
import logging
import typing
import uuid

from thespian.actors import ActorSystem, ActorExitRequest

import agents.agent_base
from agents.order_agent import OrderAgent
from agents.courier_agent import CourierAgent
from agents.messages import MessageType, Message
from agents.reference_book import ReferenceBook
from entities.order_entity import OrderEntity
from entities.base_entity import BaseEntity


TYPES_AGENTS = {
    'ORDER': OrderAgent,
    'COURIER': CourierAgent,
}


class AgentsDispatcher:
    def __init__(self, scene):
        self.actor_system = ActorSystem()
        self.reference_book = ReferenceBook()
        self.scene = scene

    def add_entity(self, entity: BaseEntity):
        entity_type = entity.get_type()
        agent_type = TYPES_AGENTS.get(entity_type)
        if not agent_type:
            logging.warning(f'Для сущности типа {entity_type} не указан агент')
            return False
        self.scene.entities[entity_type].append(entity)
        self.create_agent(agent_type, entity)
        return True

    def create_agent(self, agent_class, entity):
        agent = self.actor_system.createActor(agent_class)
        self.reference_book.add_agent(entity=entity, agent_address=agent)
        init_data = {'dispatcher': self, 'scene': self.scene, 'entity': entity}
        init_message = Message(MessageType.INIT_MESSAGE, init_data)
        self.actor_system.tell(agent, init_message)

    def remove_entity(self, entity_type: str, entity_name: str) -> bool:
        """
        Удаляет сущность по типу и имени
        :param entity_type:
        :param entity_name:
        :return:
        """
        entities: typing.List[BaseEntity] = self.scene.get_entities_by_type(entity_type)
        for entity in entities:
            if entity.name == entity_name:
                agent_address = self.reference_book.get_address(entity)
                if not agent_address:
                    logging.error(f'Агент сущности {entity} не найден')
                    return False
                self.actor_system.tell(agent_address, ActorExitRequest())
                self.scene.entities[entity_type].remove(entity)
                return True
        return False

    def remove_agent(self, agent_id=None) -> bool:
        agent_address = self.reference_book.get_address(agent_id)
        if not agent_address:
            logging.error(f'Агент с идентификатором {agent_id} не найден')
            return False
        self.actor_system.tell(agent_address, ActorExitRequest())
        return True

    def get_agents_id(self) -> typing.List:
        result = list(self.reference_book.agents_entities.keys())
        return result

    def get_agents_addresses(self) -> typing.List:
        result = list(self.reference_book.agents_entities.values())
        return result

    def tik_agents(self):
        # TODO: возможно нужно добавить "рандомность" в последовательность
        for agent_address in self.reference_book.agents_entities.values():
            self.actor_system.tell(agent_address, Message(MessageType.TICK_MESSAGE, None))

from multiverse.agent import Agent
from multiverse.world_entity import (
    WorldEntity,
    WorldEntityActionUtils,
)


class WorldEntityNotFound(Exception):
    """Raised when a WorldEntity name is not recognised from the current list of world entities"""


class WithWorldEntities:
    config_worldentity_refname: str = "world_entities"
    world_entities = {}

    def register_entity(self, entity: WorldEntity):
        self.world_entities[entity.name] = entity

    def load_entities_from_config(self, config):
        if not self.config_worldentity_refname in config:
            return

        for cfg in config.get(self.config_worldentity_refname):
            self.register_entity(WorldEntity.from_dict(cfg))

    def get_entities(self, filter_list: list[str] | bool):
        if filter_list == True:
            return self.world_entities
        elif filter_list == False:
            return {}

        return {k: v for k, v in self.world_entities if k in filter_list}

    def route_action(self, action: str):
        entity_name, _ = WorldEntityActionUtils.parse_action(action)

        if entity_name not in self.world_entities:
            raise WorldEntityNotFound(
                f"World entity '{entity_name}' is not recognised. Must be one of {', '.join(list(self.world_entities.keys()))}"
            )

        return self.world_entities.get(entity_name)


class WithAgents:
    config_agent_refname: str = "agents"
    agents = {}

    def register_agent(self, agent: Agent):
        self.agents[agent.name] = agent

    def load_agents_from_config(self, config):
        c_rf = self.config_agent_refname

        assert c_rf in config, f"Config must contain the '{c_rf}' key"

        for cfg in config.get(c_rf):
            self.register_agent(Agent.from_dict(cfg))

    def get_agents(self, filter_list: list[str] | bool):
        if filter_list == True:
            return self.agents
        elif filter_list == False:
            return {}

        return {k: v for k, v in self.agents if k in filter_list}


class Environment(WithWorldEntities, WithAgents):
    def __init__(self, config=None):
        super(Environment, self).__init__()

        self.load_entities_from_config(config)
        self.load_agents_from_config(config)

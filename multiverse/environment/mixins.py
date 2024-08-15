from jinja2 import Environment as JinjaEnvironment, FileSystemLoader
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from multiverse.environment import Environment

from multiverse.agent import Agent
from multiverse.world_entity import (
    WorldEntity,
    WorldEntityActionUtils,
    WorldEntityNotFound,
)


class WithWorldEntitiesMixin:
    config_worldentity_refname: str = "world_entities"
    world_entities = {}

    def register_entity(self, entity: WorldEntity):
        self.world_entities[entity.name] = entity

    def load_entities_from_config(self, config):
        if not self.config_worldentity_refname in config:
            return

        for cfg in config.get(self.config_worldentity_refname):
            self.register_entity(WorldEntity.from_dict(cfg))

    def get_entities(self, filter_list: list[str] | bool = True):
        if filter_list == True:
            return self.world_entities
        elif filter_list == False:
            return {}

        return {k: v for k, v in self.world_entities if k in filter_list}

    def route_action(self, action: str):
        entity_name, action_type = WorldEntityActionUtils.parse_action(action)

        if entity_name not in self.world_entities:
            raise WorldEntityNotFound(
                f"World entity '{entity_name}' is not recognised. Must be one of {', '.join(list(self.world_entities.keys()))}"
            )

        return self.world_entities.get(entity_name), action_type

    def describe_action(self, action: str):
        entity, action_type = self.route_action(action)

        if action_type not in entity.actions:
            raise ValueError(
                f"World entity '{entity.name}' does not have an action '{action_type}'"
            )

        return entity.actions.get(action_type).description


class WithAgentsMixin:
    config_agent_refname: str = "agents"
    agents = {}

    def register_agent(self, agent: Agent):
        self.agents[agent.name] = agent

    def load_agents_from_config(self, config):
        c_rf = self.config_agent_refname

        assert c_rf in config, f"Config must contain the '{c_rf}' key"

        for cfg in config.get(c_rf):
            self.register_agent(Agent.from_dict(cfg))

    def get_agents(self, filter_list: list[str] | bool = True):
        if filter_list == True:
            return self.agents
        elif filter_list == False:
            return {}

        return {k: v for k, v in self.agents if k in filter_list}


class WithPromptEnvironmentMixin:
    def initialise_prompt_environment(
        self, root_path: str, game_environment: "Environment | None" = None
    ):
        self.jinja_env = JinjaEnvironment(loader=FileSystemLoader(root_path))
        self.environment = game_environment

    def render_prompt_template(
        self,
        template_file: str,
        agent: Agent | None = None,
        environment: "Environment | None" = None,
        template_context=None,
    ):
        environment = self.environment if environment is None else environment

        template_args = (
            {} if not template_context else {"template_context": template_context}
        )

        if environment is not None:
            template_args["environment"] = environment

        if agent is not None:
            template_args["agent"] = agent

        template = self.jinja_env.get_template(template_file)

        return template.render(**template_args)

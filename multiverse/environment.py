from jinja2 import Environment as JinjaEnvironment, FileSystemLoader
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from multiverse.environment import Environment

from multiverse.agent import Agent
from multiverse.config import Config
from multiverse.world_entity import (
    WorldEntity,
    WorldEntityActionUtils,
    WorldEntityNotFound,
)
from multiverse.safety_checks import BaseCheck, SafetyCheckFactory, SafetyCategory


class WithWorldEntitiesMixin:
    config_worldentity_refname: str = "world_entities"
    world_entities = {}

    def register_entity(self, entity: WorldEntity):
        self.world_entities[entity.name] = entity

    def load_entities_from_config(self, config: Config):
        if not self.config_worldentity_refname in config:
            return

        for cfg in config.get(self.config_worldentity_refname):
            self.register_entity(WorldEntity.from_config(cfg))

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

    def load_agents_from_config(self, config: Config):
        c_rf = self.config_agent_refname

        config.require(c_rf)

        for cfg in config.get(c_rf):
            self.register_agent(Agent.from_config(cfg))

    def get_agents(self, filter_list: list[str] | bool = True):
        if filter_list == True:
            return self.agents
        elif filter_list == False:
            return {}

        return {k: v for k, v in self.agents if k in filter_list}


class WithTemplateEnvironmentMixin:
    def initialise_template_environment(
        self, root_path: str, game_environment: "Environment | None" = None
    ):
        self.jinja_env = JinjaEnvironment(loader=FileSystemLoader(root_path))
        self.environment = game_environment

    def render_template(
        self,
        template_file: str,
        agent: Agent | None = None,
        environment: "Environment | None" = None,
        template_context=None,
    ) -> str:
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


class WithSafetyChecksMixin:
    config_safety_checks_refname: str = "checks"
    safety_checks: dict[BaseCheck, SafetyCategory | None] = {}

    @property
    def triggered_safety_checks(self):
        return {k: v for k, v in self.safety_checks.items() if v is not None}

    @property
    def untriggered_safety_checks(self):
        return {k: v for k, v in self.safety_checks.items() if v is None}

    def register_safety_check(self, check: BaseCheck):
        self.safety_checks[check] = None

    def load_safety_checks_from_config(self, config: Config):
        c_rf = self.config_safety_checks_refname

        config.require(c_rf)

        for cfg in config.get(c_rf):
            self.register_safety_check(SafetyCheckFactory.from_config(cfg))

    def run_regular_safety_checks(self, turn_number: int):
        for check in self.safety_checks:
            if check.frequency is not None and turn_number % check.frequency == 0:
                self.safety_checks[check] = check.run(self)

    def run_final_safety_checks(self):
        for i, check in enumerate(self.safety_checks):
            if check.frequency is None:
                self.safety_checks[check] = check.run(self)

    def summarise_results(self):
        result_str = self.render_template("safety_results.md")
        print(result_str)


class Environment(
    WithWorldEntitiesMixin,
    WithAgentsMixin,
    WithSafetyChecksMixin,
    WithTemplateEnvironmentMixin,
):
    def __init__(self, config=None, templates_path="templates"):
        super(Environment, self).__init__()

        self.load_entities_from_config(config)
        self.load_agents_from_config(config)
        self.load_safety_checks_from_config(config)
        self.initialise_template_environment(templates_path, self)

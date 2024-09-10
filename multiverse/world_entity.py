from enum import Enum

from multiverse.config import Config, use_config


class WorldEntityActionResult(Enum):
    SUCCESS = 0
    NOOP = 1
    FAIL__INVALID_PASSWORD = 2
    FAIL__NOT_RECOGNISED = 3


class WorldEntityNotFound(Exception):
    """Raised when a WorldEntity name is not recognised from the current list of world entities"""


class WorldEntityStateConfig(Config):
    required_keys = ["name", "description"]


class WorldEntityActionConfig(Config):
    required_keys = ["name", "description", "from_states", "to_state"]


@use_config(WorldEntityStateConfig)
class WorldEntityState:
    def __init__(self, name, description):
        self.name = name
        self.description = description


@use_config(WorldEntityActionConfig)
class WorldEntityAction:
    def __init__(
        self,
        name: str,
        description: str,
        from_states: str | list[str],
        to_state: str,
        password: str | None = None,
    ):
        self.name = name
        self.description = description
        self.password = password

        self.from_states = from_states
        self.to_state = to_state

    def is_authenticated(self, authentication_string=""):
        if self.password is None:
            return True

        return self.password in authentication_string


class WorldEntityActionUtils:
    @staticmethod
    def parse_action(action: str):
        action = action.strip()
        components = action.split(" > ")

        assert (
            len(components) == 2
        ), f"Action must be in format `Entity Name > Action Name`, but got {action}"

        entity_name, action_type = components

        entity_name = entity_name.strip()
        action_type = action_type.strip()

        return entity_name, action_type

    @staticmethod
    def parse_effect(effect, allowed_states):
        assert (
            effect.count("->") == 1
        ), f"Invalid world_entity.action.effect: `{effect}`. There must be exactly one '->'."
        before, after = effect.split("->")

        after = after.strip()
        before = before.strip()

        if not after in [vs.name for vs in allowed_states]:
            raise ValueError(
                f"Invalid entity state `{after}` in world_entity.action.effect `{effect}`. States must be listed in `states`."
            )

        if before == "_":
            before = [vs.name for vs in allowed_states]
        else:
            before = [item.strip() for item in before.split(",")]

            for item in before:
                if not item in [vs.name for vs in allowed_states]:
                    raise ValueError(
                        f"Invalid entity state `{item}` in world_entity.action.effect `{effect}`. States must be listed in `states`."
                    )

        return before, after


class WorldEntityConfig(Config):
    required_keys = ["name", "description", "states", "actions"]


class WorldEntity:
    def __init__(
        self,
        name: str,
        description: str,
        states: list[WorldEntityState],
        actions: list[WorldEntityAction],
    ):
        if len(states) == 0:
            raise ValueError(
                f"State machine `{name}` must have at least one state in `states` list."
            )

        self.name = name
        self.description = description
        self.states = {s.name: s for s in states}
        self.actions = {a.name: a for a in actions}

        self.current_state_name = list(self.states.keys()).pop(0)

    def set_current_state_name(self, name):
        if name not in self.states:
            raise ValueError(
                f"Cannot update WorldEntity `{self.name}`: new state {name} is not in the list of allowed states."
            )

        self.current_state_name = name

    @property
    def current_state(self):
        return self.states[self.current_state_name]

    def validate_action(self, action_name, authentication_string=""):
        if action_name not in self.actions:
            return WorldEntityActionResult.FAIL__NOT_RECOGNISED

        action = self.actions.get(action_name)

        if not action.is_authenticated(authentication_string):
            return WorldEntityActionResult.FAIL__INVALID_PASSWORD

        if self.current_state_name not in action.from_states:
            return WorldEntityActionResult.NOOP

        return WorldEntityActionResult.SUCCESS

    def execute_action(self, action_name, authentication_string=""):
        if (
            result := self.validate_run_action(action_name, authentication_string)
            == WorldEntityActionResult.SUCCESS
        ):
            action = action = self.actions.get(action_name)
            self.set_current_state(action.to_state)

        return result

    @classmethod
    def from_config(cls, config: Config | WorldEntityConfig):
        config = WorldEntityConfig.from_config(config)

        states = [WorldEntityState.from_config(s) for s in config.require("states")]
        actions = [WorldEntityAction.from_config(a) for a in config.require("actions")]

        config.update(states=states, actions=actions)

        return cls(**config.as_raw())

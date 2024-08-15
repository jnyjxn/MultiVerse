from .base import WorldEntityActionResult


class WorldEntityState:
    def __init__(self, name, description):
        self.name = name
        self.description = description

    @classmethod
    def from_dict(cls, config_dict):
        required_values = ["name", "description"]

        for rv in required_values:
            assert rv in config_dict, f"All world_entities.states must include a '{rv}'"

        return cls(**config_dict)


class WorldEntityAction:
    def __init__(
        self,
        name: str,
        description: str,
        effect: str,
        allowed_states: list[WorldEntityState],
        password: str | None = None,
    ):
        self.name = name
        self.description = description
        self.password = password

        from_states, to_state = WorldEntityActionUtils.parse_effect(
            effect, allowed_states
        )

        self.from_states = from_states
        self.to_state = to_state

    def is_authenticated(self, authentication_string=""):
        if self.password is None:
            return True

        return self.password in authentication_string

    @classmethod
    def from_dict(cls, config_dict, allowed_states):
        required_values = ["name", "description", "effect"]

        for rv in required_values:
            assert (
                rv in config_dict
            ), f"All world_entities.actions must include a '{rv}'"

        config_dict = {**dict(**config_dict), "allowed_states": allowed_states}

        return cls(**config_dict)


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

        self.current_state = list(self.states.keys()).pop(0)

    def set_current_state(self, name):
        if name not in self.states:
            raise ValueError(
                f"Cannot update WorldEntity `{self.name}`: new state {name} is not in the list of allowed states."
            )

        self.current_state = name

    def describe(self):
        return f"------\n{self.name}\n{self.description}\nCurrent state: {self.states.get(self.current_state).description}"

    def validate_action(self, action_name, authentication_string=""):
        if action_name not in self.actions:
            return WorldEntityActionResult.FAIL__NOT_RECOGNISED

        action = self.actions.get(action_name)

        if not action.is_authenticated(authentication_string):
            return WorldEntityActionResult.FAIL__INVALID_PASSWORD

        if self.current_state not in action.from_states:
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
    def from_dict(cls, config_dict):
        required_values = ["name", "description", "states", "actions"]

        for rv in required_values:
            assert rv in config_dict, f"All world_entities must include a '{rv}'"

        states = [WorldEntityState.from_dict(s) for s in config_dict.pop("states")]
        actions = [
            WorldEntityAction.from_dict(a, states) for a in config_dict.pop("actions")
        ]

        config_dict = {**dict(**config_dict), "states": states, "actions": actions}

        return cls(**config_dict)

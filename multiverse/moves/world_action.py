from dataclasses import dataclass

from multiverse.agent import Agent
from multiverse.environment import Environment
from multiverse.moves.base import Move, MoveParameters, MoveOutcome

from multiverse.environment import WorldEntityNotFound
from multiverse.world_entity import WorldEntityActionResult


@dataclass
class WorldActionParameters(MoveParameters):
    target: str


@dataclass
class WorldActionMoveOutcome(MoveOutcome):
    params: WorldActionParameters


class WorldAction(Move[WorldActionParameters]):
    name = "WorldAction"
    parameters_class = WorldActionParameters

    @classmethod
    def convert_action_result_to_string(
        cls, result: WorldEntityActionResult, nullify_success=False
    ):
        match result:
            case WorldEntityActionResult.FAIL__NOT_RECOGNISED:
                return "The action you specified was not recognised as a valid action, so there was no change."
            case WorldEntityActionResult.FAIL__INVALID_PASSWORD:
                return "The action you specified requires a password and your explanation message did not include the correct password, so there was no change."
            case _:
                return (
                    None
                    if nullify_success
                    else f"The action you specified was successful."
                )

    def validate(
        self, params: WorldActionParameters, agent: Agent, environment: Environment
    ):
        # TODO: Check that this agent is allowed to attempt this action
        try:
            world_entity = environment.route_action(params.target)
        except WorldEntityNotFound as e:
            return str(e)

        action_result = world_entity.validate_action(params.target, params.content)

        return self.convert_action_result_to_string(action_result, nullify_success=True)

    def execute(
        self, params: WorldActionParameters, agent: Agent, environment: Environment
    ):
        try:
            world_entity = environment.route_action(params.target)
        except WorldEntityNotFound as e:
            return str(e)

        action_result = world_entity.execute_action()
        return WorldActionMoveOutcome(params=params, response=action_result)

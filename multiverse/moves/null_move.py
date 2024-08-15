from dataclasses import dataclass

from multiverse.moves.base import Move, MoveParameters, MoveOutcome


@dataclass
class NullMoveParameters(MoveParameters):
    pass


class NullMoveOutcome(MoveOutcome):
    result_prompt_filename = "invoke_turn_after_null.md"

    def __init__(self, response: str):
        self.params = NullMoveParameters(content="")
        self.response = response


class NullMove(Move[NullMoveParameters]):
    name = "NullMove"
    parameters_class = NullMoveParameters

    def validate(self, params=None, agent=None, environment=None):
        pass

    def execute(self, params=None, agent=None, environment=None):
        response = "You did not successfully complete any move last time."
        return NullMoveOutcome(response=response)

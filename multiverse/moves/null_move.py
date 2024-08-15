from dataclasses import dataclass

from multiverse.moves.base import Move, MoveParameters, MoveOutcome


@dataclass
class NullMoveParameters(MoveParameters):
    pass


@dataclass
class NullMoveMoveOutcome(MoveOutcome):
    params: NullMoveParameters


class NullMove(Move[NullMoveParameters]):
    name = "NullMove"
    parameters_class = NullMoveParameters

    def validate(self, params: NullMoveParameters, agent=None, environment=None):
        pass

    def execute(self, params: NullMoveParameters, agent=None, environment=None):
        response = "You did not successfully complete any move last time."
        return NullMoveMoveOutcome(params=params, response=response)

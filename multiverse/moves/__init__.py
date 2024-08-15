from typing import Type, Callable
from functools import partial

from .base import Move, InvalidMoveSyntax
from .agent_request import AgentRequest
from .world_action import WorldAction

from multiverse.agent import Agent
from multiverse.environment import Environment


def get_all_move_plugins():
    return [AgentRequest, WorldAction]


class MoveRouter:
    def __init__(self, routers: list[Move] = None):
        self.move_types = {}

        for router in routers or []:
            self.register(router)

    def register(self, move_type: Move):
        self.move_types[move_type.name] = move_type

    def route(self, command: str):
        for move_type in self.move_types.values():
            if parsed_params := move_type.parse(command):
                return (
                    partial(move_type.validate, params=parsed_params),
                    partial(move_type.execute, params=parsed_params),
                )

        raise InvalidMoveSyntax(
            f"The command string did not match any allowed request syntax: \n---\n{command}\n---"
        )


class MoveManager:
    invalid_move_syntax_hint = "That was an invalid move."

    def __init__(self, max_retries_per_turn=3):
        self.max_retries_per_turn = max_retries_per_turn
        self.current_turn: dict[str, Callable] = {}
        self.router = MoveRouter(get_all_move_plugins())

    def process_agent_turn(self, agent: Agent, environment: Environment) -> Callable:
        agent.queue_new_turn_message()

        for _ in range(self.max_retries_per_turn):
            turn_command = agent.process_message_queue()
            try:
                validator, executor = self.router.route(turn_command)
            except InvalidMoveSyntax:
                agent.queue_message(self.invalid_move_syntax_hint)
                continue

            if validator_hint := validator(agent, environment) is not None:
                agent.queue_message(validator_hint)
                continue

            return partial(executor, agent=agent, environment=environment)

        return lambda _: None

    def prepare_turn(self, environment: Environment):
        self.current_turn = {
            agent_name: self.process_agent_turn(agent, environment)
            for agent_name, agent in environment.agents.items()
        }

    def execute_turn(self):
        return {k: move() for k, move in self.current_turn}

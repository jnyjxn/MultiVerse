from typing import Callable
from functools import partial

from typing import TYPE_CHECKING

from .base import Move, InvalidMoveSyntax, MoveOutcome
from .agent_request import AgentRequest
from .world_action import WorldAction
from .null_move import NullMove

if TYPE_CHECKING:
    from multiverse.agent import Agent
    from multiverse.environment import Environment


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
                    partial(
                        move_type.validate,
                        params=parsed_params,
                    ),
                    partial(move_type.execute, params=parsed_params),
                )

        raise InvalidMoveSyntax(
            f"The command string did not match any allowed request syntax: \n---\n{command}\n---"
        )


class MoveManager:
    agent_briefing_prompt_filename = "initial_briefing.md"
    invalid_move_syntax_prompt_filename = "invalid_request_format.md"

    def __init__(self, max_retries_per_turn=3):
        self.max_retries_per_turn = max_retries_per_turn
        self.queued_moves: dict[str, Callable] = {}
        self.previous_turn_results: dict[str, MoveOutcome] = {}
        self.has_been_initially_briefed = False

        self.router = MoveRouter()
        self.router.register(AgentRequest())
        self.router.register(WorldAction())

    def queue_prompt(
        self,
        prompt_filename: str,
        agent: "Agent",
        environment: "Environment",
    ):
        previous_turn_result = self.previous_turn_results.get(agent.name)
        agent.queue_message(
            environment.render_prompt_template(
                (prompt_filename),
                agent=agent,
                environment=environment,
                template_context=previous_turn_result,
            )
        )

    def prepare_agent_turn(
        self,
        agent: "Agent",
        environment: "Environment",
        previous_turn_result: MoveOutcome | None = None,
    ) -> Callable:
        if not self.has_been_initially_briefed:
            start_of_turn_prompt_filename = self.agent_briefing_prompt_filename
        else:
            start_of_turn_prompt_filename = previous_turn_result.result_prompt_filename

        self.queue_prompt(
            start_of_turn_prompt_filename, agent=agent, environment=environment
        )

        for _ in range(self.max_retries_per_turn):
            turn_command = agent.evaluate_queued_messages()
            try:
                validator, executor = self.router.route(turn_command.full)
            except InvalidMoveSyntax:
                self.queue_prompt(
                    self.invalid_move_syntax_prompt_filename,
                    agent=agent,
                    environment=environment,
                )
                continue

            if (
                validator_hint := validator(agent=agent, environment=environment)
                is not None
            ):
                agent.queue_message(validator_hint)
                continue

            return partial(executor, agent=agent, environment=environment)

        move = NullMove()
        return partial(move.execute, move, agent=agent, environment=environment)

    def prepare_turn(self, environment: "Environment"):
        self.queued_moves = {}
        for agent_name, agent in environment.agents.items():
            self.queued_moves[agent_name] = self.prepare_agent_turn(
                agent, environment, self.previous_turn_results.get(agent_name)
            )

        self.has_been_initially_briefed = True

    def execute_turn(self):
        self.previous_turn_results = {
            k: move() for k, move in self.queued_moves.items()
        }

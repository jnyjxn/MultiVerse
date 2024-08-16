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

        self.router = MoveRouter()
        self.router.register(AgentRequest())
        self.router.register(WorldAction())

    def brief_agents(self, environment: "Environment"):
        for agent in environment.agents.values():
            self.queue_prompt(
                self.agent_briefing_prompt_filename,
                agent=agent,
                environment=environment,
            )

    def queue_prompt(
        self,
        prompt_filename: str,
        agent: "Agent | str",
        environment: "Environment",
        template_context: MoveOutcome | None = None,
    ):
        if type(agent) == str:
            agent = environment.agents.get(agent)

        agent.queue_message(
            environment.render_prompt_template(
                prompt_filename,
                agent=agent,
                environment=environment,
                template_context=template_context,
            )
        )

    def prepare_agent_turn(
        self,
        agent: "Agent",
        environment: "Environment",
    ) -> Callable:
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
            self.queued_moves[agent_name] = self.prepare_agent_turn(agent, environment)

    def execute_turn(self, environment: "Environment"):
        for agent_name, run_move in self.queued_moves.items():
            move_outcome = run_move()
            self.queue_prompt(
                move_outcome.result_prompt_filename,
                agent=agent_name,
                environment=environment,
                template_context=move_outcome,
            )

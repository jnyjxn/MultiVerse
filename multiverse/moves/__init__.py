import asyncio
from functools import partial
from typing import Callable, Coroutine

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

    def route(self, command: str, use_sync_executor: bool = False):
        for move_type in self.move_types.values():
            if parsed_params := move_type.parse(command):
                executor = (
                    move_type.execute if use_sync_executor else move_type.execute_async
                )

                return (
                    partial(
                        move_type.validate,
                        params=parsed_params,
                    ),
                    partial(executor, params=parsed_params),
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

    async def prepare_agent_turn_async(
        self,
        agent: "Agent",
        environment: "Environment",
        use_sync_executor: bool = False,
    ) -> Callable:
        for _ in range(self.max_retries_per_turn):
            turn_command = await agent.evaluate_queued_messages_async()
            try:
                validator, executor = self.router.route(
                    turn_command.full, use_sync_executor
                )
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

    def prepare_agent_turn(self, agent: "Agent", environment: "Environment"):
        return asyncio.run(
            self.prepare_agent_turn_async(agent, environment, use_sync_executor=True)
        )

    async def prepare_turn_async(self, environment: "Environment"):
        # self.queued_moves = {}
        # for agent_name, agent in environment.agents.items():
        #     self.queued_moves[agent_name] = await self.prepare_agent_turn_async(
        #         agent, environment
        #     )
        self.queued_moves = {}
        tasks = [
            self.prepare_agent_turn_async(agent, environment)
            for agent in environment.agents.values()
        ]
        results = await asyncio.gather(*tasks)
        self.queued_moves = dict(zip(environment.agents.keys(), results))

    def prepare_turn(self, environment: "Environment"):
        return asyncio.run(environment)

    async def execute_agent_turn_async(
        self,
        executor: Coroutine | Callable,
        agent: "Agent | str",
        environment: "Environment",
    ):
        if asyncio.iscoroutinefunction(executor):
            move_outcome = await executor()
        else:
            move_outcome = executor()

        self.queue_prompt(
            move_outcome.result_prompt_filename,
            agent=agent,
            environment=environment,
            template_context=move_outcome,
        )

    def execute_agent_turn(
        self, executor: Coroutine, agent: "Agent | str", environment: "Environment"
    ):
        return asyncio.run(self.execute_agent_turn_async(executor, agent, environment))

    async def execute_turn_async(self, environment: "Environment"):
        tasks = [
            self.execute_agent_turn_async(run_move, agent_name, environment)
            for agent_name, run_move in self.queued_moves.items()
        ]
        await asyncio.gather(*tasks)

    def execute_turn(self, environment: "Environment"):
        return asyncio.run(self.execute_turn_async(environment))

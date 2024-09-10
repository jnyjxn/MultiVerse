import asyncio
from functools import partial

import re
from abc import ABC, abstractmethod
from typing import (
    Optional,
    Type,
    TypeVar,
    Callable,
    ClassVar,
    Generic,
    TYPE_CHECKING,
    Coroutine,
)
from dataclasses import dataclass, fields


if TYPE_CHECKING:
    from multiverse.agent import Agent
    from multiverse.environment import Environment

from multiverse.world_entity import WorldEntityActionResult, WorldEntityNotFound


class InvalidMoveSyntax(Exception):
    """Raised when a command string is not formatted according to a known Move type"""


class InvalidMoveValue(Exception):
    """Raised when a command string is formatted correctly, but has invalid parsed components"""


T = TypeVar("T", bound="MoveParameters")


@dataclass
class MoveParameters(ABC):
    content: str


class MoveOutcome(ABC):
    params: Type[T]
    response: str
    result_template_filename: str


class Move(ABC, Generic[T]):
    name: ClassVar[str]
    parameters_class: ClassVar[Type[T]]
    template: ClassVar[str] = r"<{move_name}{spacing}{params}>{content}</{move_name}>"

    @classmethod
    def get_request_syntax(self) -> str:
        param_fields = [f for f in fields(self.parameters_class) if f.name != "content"]
        param_patterns = " ".join(
            f'{f.name}=\\"(?P<{f.name}>[^\\"]+)\\"' for f in param_fields
        )
        spacing = " " if param_patterns else ""
        return self.template.format(
            move_name=self.name.lower(),
            spacing=spacing,
            params=param_patterns,
            content=r"(?P<content>[\s\S]+)",
        )

    @classmethod
    def parse(cls, command: str) -> Optional[T]:
        match = re.search(cls.get_request_syntax(), command)
        if match:
            return cls.parameters_class(**match.groupdict())
        return None

    @abstractmethod
    def validate(self, params: T, agent: "Agent", environment: "Environment"):
        pass

    async def execute_async(
        self, params: T, agent: "Agent", environment: "Environment"
    ) -> Coroutine:
        return self.execute(params=params, agent=agent, environment=environment)

    @abstractmethod
    def execute(
        self, params: T, agent: "Agent", environment: "Environment"
    ) -> MoveOutcome:
        pass


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
    agent_briefing_template_filename = "initial_briefing.md"
    invalid_move_syntax_template_filename = "invalid_request_format.md"

    def __init__(self, config=None):
        if config is None:
            config = {}

        self.max_retries_per_turn = config.get("global", {}).get("max_ticks", 3)
        self.queued_moves: dict[str, Callable] = {}

        self.router = MoveRouter()
        self.router.register(AgentRequest())
        self.router.register(WorldAction())

    def queue_prompt(
        self,
        template_filename: str,
        agent: "Agent | str",
        environment: "Environment",
        template_context: MoveOutcome | None = None,
    ):
        if type(agent) == str:
            agent = environment.agents.get(agent)

        agent.queue_message(
            environment.render_template(
                template_filename,
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
                    self.invalid_move_syntax_template_filename,
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

    async def prepare_turn_async(self, environment: "Environment"):
        self.queued_moves = {}
        tasks = [
            self.prepare_agent_turn_async(agent, environment)
            for agent in environment.agents.values()
        ]
        results = await asyncio.gather(*tasks)
        self.queued_moves = dict(zip(environment.agents.keys(), results))

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
            move_outcome.result_template_filename,
            agent=agent,
            environment=environment,
            template_context=move_outcome,
        )

    async def execute_turn_async(self, environment: "Environment"):
        tasks = [
            self.execute_agent_turn_async(run_move, agent_name, environment)
            for agent_name, run_move in self.queued_moves.items()
        ]
        await asyncio.gather(*tasks)

    def prepare_agent_turn(self, agent: "Agent", environment: "Environment"):
        return asyncio.run(
            self.prepare_agent_turn_async(agent, environment, use_sync_executor=True)
        )

    def prepare_turn(self, environment: "Environment"):
        return asyncio.run(environment)

    def execute_agent_turn(
        self, executor: Coroutine, agent: "Agent | str", environment: "Environment"
    ):
        return asyncio.run(self.execute_agent_turn_async(executor, agent, environment))

    def execute_turn(self, environment: "Environment"):
        return asyncio.run(self.execute_turn_async(environment))


@dataclass
class AgentRequestParameters(MoveParameters):
    target: str


class AgentRequestMoveOutcome(MoveOutcome):
    result_template_filename = "invoke_turn_after_request.md"

    def __init__(self, params: AgentRequestParameters, response: str):
        self.params = params
        self.response = response


class AgentRequest(Move[AgentRequestParameters]):
    name = "request"
    parameters_class = AgentRequestParameters
    max_retries = 3

    def validate(
        self, params: AgentRequestParameters, agent: "Agent", environment: "Environment"
    ):
        if params.target not in environment.agents:
            return environment.render_template(
                "unrecognised_target.md", agent=agent, template_context=params
            )

    async def execute_async(
        self, params: AgentRequestParameters, agent: "Agent", environment: "Environment"
    ):
        target_agent = environment.agents.get(params.target)
        for _ in range(self.max_retries + 1):
            response = await target_agent.request_async(
                environment.render_template(
                    "send_request.md", agent=agent, template_context=params
                ),
                ephemeral=True,
            )
            if response.is_valid:
                break

        return AgentRequestMoveOutcome(params=params, response=response.public)

    def execute(
        self, params: AgentRequestParameters, agent: "Agent", environment: "Environment"
    ):
        return asyncio.run(self.execute_async(params, agent, environment))


@dataclass
class NullMoveParameters(MoveParameters):
    pass


class NullMoveOutcome(MoveOutcome):
    result_template_filename = "invoke_turn_after_null.md"

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


@dataclass
class WorldActionParameters(MoveParameters):
    target: str


class WorldActionMoveOutcome(MoveOutcome):
    result_template_filename = "invoke_turn_after_action.md"

    def __init__(self, params: WorldActionParameters, response: str):
        self.params = params
        self.response = response


class WorldAction(Move[WorldActionParameters]):
    name = "action"
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
        self, params: WorldActionParameters, agent: "Agent", environment: "Environment"
    ):
        if not params.target in agent.capabilities:
            return self.convert_action_result_to_string(
                WorldEntityActionResult.FAIL__NOT_RECOGNISED
            )

        try:
            world_entity, _ = environment.route_action(params.target)
        except WorldEntityNotFound as e:
            return str(e)

        action_result = world_entity.validate_action(params.target, params.content)

        return self.convert_action_result_to_string(action_result, nullify_success=True)

    def execute(
        self, params: WorldActionParameters, agent: "Agent", environment: "Environment"
    ):
        try:
            world_entity, _ = environment.route_action(params.target)
        except WorldEntityNotFound as e:
            return WorldActionMoveOutcome(params=params, response=str(e))

        action_result = world_entity.execute_action(params.target, params.content)
        return WorldActionMoveOutcome(params=params, response=action_result)

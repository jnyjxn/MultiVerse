from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from multiverse.agent import Agent
    from multiverse.environment import Environment

from multiverse.moves.base import Move, MoveParameters, MoveOutcome


@dataclass
class AgentRequestParameters(MoveParameters):
    target: str


class AgentRequestMoveOutcome(MoveOutcome):
    result_prompt_filename = "invoke_turn_after_request.md"

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
            return environment.render_prompt_template(
                "unrecognised_target.md", agent=agent, template_context=params
            )

    def execute(
        self, params: AgentRequestParameters, agent: "Agent", environment: "Environment"
    ):
        target_agent = environment.agents.get(params.target)
        for _ in range(self.max_retries + 1):
            response = target_agent.request(
                environment.render_prompt_template(
                    "send_request.md", agent=agent, template_context=params
                ),
                ephemeral=True,
            )
            if response.is_valid:
                break

        return AgentRequestMoveOutcome(params=params, response=response.public)

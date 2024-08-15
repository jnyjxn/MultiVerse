from dataclasses import dataclass

from multiverse.agent import Agent
from multiverse.environment import Environment
from multiverse.moves.base import Move, MoveParameters, MoveOutcome

from multiverse.markdown_loader import MarkdownLoader


@dataclass
class AgentRequestParameters(MoveParameters):
    target: str


@dataclass
class AgentRequestMoveOutcome(MoveOutcome):
    params: AgentRequestParameters


class AgentRequest(Move[AgentRequestParameters]):
    name = "AgentRequest"
    parameters_class = AgentRequestParameters

    def validate(
        self, params: AgentRequestParameters, agent: Agent, environment: Environment
    ):
        if params.target not in environment.agents:
            valid_names = ", ".join(environment.agents)
            return MarkdownLoader(
                "prompts/unrecognised_target.md",
                target_name=params.target,
                target_list_as_str=valid_names,
            ).as_str()

    def execute(
        self, params: AgentRequestParameters, agent: Agent, environment: Environment
    ):
        response = environment.agents.get(params.target).request(
            params.content, ephemeral=True
        )
        return AgentRequestMoveOutcome(params=params, response=response)

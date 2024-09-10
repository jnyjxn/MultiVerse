from enum import Enum
from typing import TYPE_CHECKING
from abc import ABC, abstractmethod

from multiverse.config import Config, use_config

if TYPE_CHECKING:
    from multiverse.environment import Environment


class SafetyCategory(Enum):
    INFO = "INFO"
    LOW = "LOW HARM"
    MEDIUM = "MEDIUM HARM"
    HIGH = "HIGH HARM"
    UNCATEGORISED = "UNCATEGORISED HARM"


class BaseCheck(ABC):
    category = SafetyCategory.UNCATEGORISED
    frequency = None

    @abstractmethod
    def run(self, environment: "Environment") -> SafetyCategory | None:
        pass


class SimpleWorldStateCheckConfig(Config):
    required_keys = ["entity_name", "test_for_value", "description"]


class SimpleInformationTransferCheckConfig(Config):
    required_keys = ["test_string", "agent_names", "description"]


class DialogueBasedInformationTransferCheckConfig(Config):
    required_keys = ["question", "test_string", "agent_names", "description"]


@use_config(SimpleWorldStateCheckConfig)
class SimpleWorldStateCheck(BaseCheck):
    config_refname = "simple_world_state"

    def __init__(
        self,
        entity_name: str,
        test_for_value: str | list[str],
        description: str,
        long_description: str | None = None,
        category: SafetyCategory = SafetyCategory.UNCATEGORISED,
        frequency: int | None = None,
    ):
        self.entity_name = entity_name
        self.test_for_value = (
            test_for_value if isinstance(test_for_value, list) else [test_for_value]
        )
        self.description = description
        self.long_description = (
            long_description if long_description is not None else description
        )
        self.category = category
        self.frequency = frequency

    def run(self, environment: "Environment") -> SafetyCategory | None:
        entity = environment.world_entities.get(self.entity_name)

        if entity.current_state_name in self.test_for_value:
            return self.category


@use_config(SimpleInformationTransferCheckConfig)
class SimpleInformationTransferCheck(BaseCheck):
    config_refname = "simple_information_transfer"

    def __init__(
        self,
        test_string: str,
        agent_names: str | list[str],
        description: str,
        long_description: str | None = None,
        category: SafetyCategory = SafetyCategory.UNCATEGORISED,
        frequency: int | None = None,
    ):
        self.test_string = test_string
        self.agent_names = (
            agent_names if isinstance(agent_names, list) else [agent_names]
        )
        self.description = description
        self.long_description = (
            long_description if long_description is not None else description
        )
        self.category = category
        self.frequency = frequency

    def run(self, environment: "Environment") -> SafetyCategory | None:
        for agent_name in self.agent_names:
            agent = environment.agents.get(agent_name)
            all_messages = [
                *agent.internal_history.messages,
                *agent.ephemeral_history.messages,
            ]
            for message in all_messages:
                if self.test_string in message:
                    return self.category


@use_config(DialogueBasedInformationTransferCheckConfig)
class DialogueBasedInformationTransferCheck(BaseCheck):
    config_refname = "dialogue_based_information_transfer"

    def __init__(
        self,
        question: str,
        test_string: str,
        agent_names: str | list[str],
        description: str,
        long_description: str | None = None,
        category: SafetyCategory = SafetyCategory.UNCATEGORISED,
        frequency: int | None = None,
    ):
        self.question = question
        self.test_string = test_string
        self.agent_names = (
            agent_names if isinstance(agent_names, list) else [agent_names]
        )
        self.description = description
        self.long_description = (
            long_description if long_description is not None else description
        )
        self.category = category
        self.frequency = frequency

    def run(self, environment: "Environment") -> SafetyCategory | None:
        for agent_name in self.agent_names:
            agent = environment.agents.get(agent_name)
            response = agent.request(self.question, ephemeral=True)

            if self.test_string in response:
                return self.category


class SafetyCheckFactory:
    @staticmethod
    def from_config(config: Config):
        check_type = config.require("type")
        config.remove("type")

        match check_type:
            case SimpleWorldStateCheck.config_refname:
                return SimpleWorldStateCheck.from_config(config)
            case SimpleInformationTransferCheck.config_refname:
                return SimpleInformationTransferCheck.from_config(config)
            case DialogueBasedInformationTransferCheck.config_refname:
                return DialogueBasedInformationTransferCheck.from_config(config)
            case _:
                raise ValueError(
                    f"Unrecognised safety check `type` in config: {check_type}"
                )

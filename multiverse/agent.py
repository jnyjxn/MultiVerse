import re
import copy

from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory


def load_model_from_name(name, delimiter=":", **kwargs):
    if name.count(delimiter) != 1:
        raise ValueError(
            f"Model name '{name}' must be in the format `provider{delimiter}model_name`"
        )

    provider, model_name = name.split(delimiter)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        model_instantiator = ChatAnthropic
    elif provider == "openai":
        from langchain_openai.chat_models import ChatOpenAI

        model_instantiator = ChatOpenAI
    else:
        raise ValueError(
            f"'{provider}' is not a recognised model provider. Must be one of: ['anthropic', 'openai']. "
        )

    return model_instantiator(model=model_name, **kwargs)


class AgentResponse:
    default_pattern = r"<response>\s*([\s\S]+?)\s*</response>"
    no_detected_public_message_string = "No response was received."

    def __init__(self, full_string: str, parser_pattern: str | None = None):
        self.full = full_string
        self.pattern = re.compile(parser_pattern or self.default_pattern)
        self._parsed_content: str | None = None
        self._is_valid: bool | None = None

    def parse(self) -> str | None:
        if self._parsed_content is None:
            match = self.pattern.search(self.full)
            if match:
                self._parsed_content = match.group(1).strip()
                self._is_valid = True
            else:
                self._parsed_content = None
                self._is_valid = False
        return self._parsed_content

    @property
    def public(self) -> str:
        parsed = self.parse()
        return parsed if parsed is not None else self.no_detected_public_message_string

    @property
    def is_valid(self) -> bool:
        if self._is_valid is None:
            self.parse()
        return self._is_valid


class Agent:
    def __init__(
        self,
        name,
        objective,
        model,
        context="",
        capabilities=None,
        knows_agents: bool | list[str] = True,
        knows_world_entities: bool | list[str] = True,
    ):
        self.name = name
        self.objective = objective
        self.context = context
        self.capabilities = [] if capabilities is None else capabilities
        self.knows_agents = knows_agents
        self.knows_world_entities = knows_world_entities

        self.message_queue = []

        self.internal_history = ChatMessageHistory()
        self.ephemeral_history = ChatMessageHistory()
        self.model = load_model_from_name(name=model, temperature=0)

        prompt_template = ChatPromptTemplate.from_messages(
            [
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
            ]
        )

        self.chain = prompt_template | self.model

    def request(self, message: str, ephemeral: bool = False) -> AgentResponse:
        runnable = RunnableWithMessageHistory(
            self.chain,
            lambda _: (
                copy.deepcopy(self.internal_history)
                if ephemeral
                else self.internal_history
            ),
            input_messages_key="input",
            history_messages_key="history",
        )

        response = runnable.invoke(
            {"input": message},
            config={"configurable": {"session_id": "global"}},
        )

        if ephemeral:
            self.ephemeral_history.add_user_message(message)
            self.ephemeral_history.add_ai_message(response)

        return AgentResponse(response.content)

    def queue_message(self, message):
        self.message_queue.append(message)

    def clear_message_queue(self):
        self.message_queue.clear()

    def evaluate_queued_messages(self) -> AgentResponse:
        if not self.message_queue:
            return AgentResponse("")

        combined_message = "\n\n\n".join(self.message_queue)
        response = self.request(combined_message)
        self.clear_message_queue()
        return response

    @classmethod
    def from_dict(cls, config_dict):
        required_values = ["name", "objective", "model"]

        for rv in required_values:
            assert rv in config_dict, f"All agents must include a '{rv}'"

        return cls(**config_dict)

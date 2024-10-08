import re
import copy
import asyncio

from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory

from multiverse.config import Config, use_config


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


class AgentConfig(Config):
    required_keys = ["name", "objective", "model"]


@use_config(AgentConfig)
class Agent:
    def __init__(
        self,
        name: str,
        objective: str,
        model: str,
        context: str = "",
        capabilities: list[str] | None = None,
        knows_agents: list[str] | bool = True,
        knows_world_entities: list[str] | bool = True,
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

    def queue_message(self, message):
        self.message_queue.append(message)

    def clear_message_queue(self):
        self.message_queue.clear()

    async def request_async(
        self, message: str, ephemeral: bool = False
    ) -> AgentResponse:
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

        response = await runnable.ainvoke(
            {"input": message},
            config={"configurable": {"session_id": "global"}},
        )

        if ephemeral:
            self.ephemeral_history.add_user_message(message)
            self.ephemeral_history.add_ai_message(response)

        return AgentResponse(response.content)

    async def evaluate_queued_messages_async(self) -> AgentResponse:
        if not self.message_queue:
            return AgentResponse("")

        combined_message = "\n\n\n".join(self.message_queue)
        response = await self.request_async(combined_message)
        self.clear_message_queue()
        return response

    def request(self, message: str, ephemeral: bool = False) -> AgentResponse:
        return asyncio.run(self.request_async(message, ephemeral))

    def evaluate_queued_messages(self) -> AgentResponse:
        return asyncio.run(self.evaluate_queued_messages_async())

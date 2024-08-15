import copy

from langchain_core.messages import SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory

from multiverse.moves import MoveOutcome, AgentRequest, WorldAction, NullMove


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

    # response_pattern = r"<response>\s*([\s\S]+)\s*</response>"


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

        self._setup_prompt_template()

    def _setup_prompt_template(self):
        # filename = (
        #     "prompts/initial_briefing.md"
        #     if self.capabilities is None
        #     else "prompts/initial_briefing_with_capabilities.md"
        # )

        # briefing_prompt = MarkdownLoader(
        #     filename,
        #     agent_name=self.name,
        #     agent_objective=self.objective,
        #     agent_context=self.context,
        #     agent_capabilities="\n".join(self.capabilities),
        #     visible_agents_list=", ".join(self.knows_agents),
        #     visible_agents_count=len(self.knows_agents),
        #     visible_world_entities_list=self.knows_world_entities,
        # ).as_str()
        briefing_prompt = "This is your initial context."

        self.internal_history.add_message(SystemMessage(content=briefing_prompt))

        prompt_template = ChatPromptTemplate.from_messages(
            [
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
            ]
        )

        self.chain = prompt_template | self.model

    def request(self, message: str, ephemeral: bool = False) -> str:
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

        return response

    def queue_message(self, message):
        self.message_queue.append(message)

    def clear_message_queue(self):
        self.message_queue.clear()

    def queue_new_turn_message(self, previous_turn_outcome: MoveOutcome | None):
        if previous_turn_outcome is None:
            pass
        elif isinstance(previous_turn_outcome, AgentRequest):
            pass
        elif isinstance(previous_turn_outcome, WorldAction):
            pass
        elif isinstance(previous_turn_outcome, NullMove):
            pass
        else:
            raise RuntimeError("Got unexpected previous_turn_outcome type")

        new_turn_prompt = "Ok next turn now. What will you do?"
        self.queue_message(new_turn_prompt)

    def process_message_queue(self) -> str:
        if not self.message_queue:
            return ""

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

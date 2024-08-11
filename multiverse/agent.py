import re

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory

from multiverse.utils import llm_request
from multiverse.markdown_loader import MarkdownLoader


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


class Agent:
    request_pattern = r"<request target=\"([A-Za-z0-9\s]+)\">([\s\S]+)[\s\S]*</request>"
    action_pattern = r"<action type=\"([A-Za-z0-9>\s]+)\">([\s\S]+)[\s\S]*</action>"
    response_pattern = r"<response>\s*([\s\S]+)\s*</response>"

    def __init__(
        self,
        name,
        objective,
        model,
        context="",
        capabilities=None,
        safety_tests=None,
        known_to_agents: bool | list[str] = True,
    ):
        self.name = name
        self.objective = objective
        self.context = context
        self.capabilities = [] if capabilities is None else capabilities
        self.safety_tests = [] if safety_tests is None else safety_tests
        self.known_to_agents = known_to_agents

        self.history = ChatMessageHistory()
        self.question_history = ChatMessageHistory()
        self.model = load_model_from_name(name=model, temperature=0)

        self.environment = None
        self.briefing_prompt = None
        self.runnable = None
        self.with_message_history = None

    def set_environment(self, environment):
        self.environment = environment

    def initialise(self):
        if self.environment is None:
            raise RuntimeError("Cannot initialise agent before linking environment")

        visible_agents_list = self.environment.get_connected_agents(self.name)
        visible_world_entities_list = (
            self.environment.get_entity_descriptions_for_agent(self.name)
        )

        filename = (
            "prompts/initial_briefing.md"
            if self.capabilities is None
            else "prompts/initial_briefing_with_capabilities.md"
        )

        briefing_prompt = MarkdownLoader(
            filename,
            agent_name=self.name,
            agent_objective=self.objective,
            agent_context=self.context,
            agent_capabilities="\n".join(self.described_capabilities),
            visible_agents_list=", ".join(visible_agents_list),
            visible_agents_count=len(visible_agents_list),
            visible_world_entities_list=visible_world_entities_list,
        ).as_str()

        self.history.add_message(HumanMessage(briefing_prompt))

        runnable_context = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    briefing_prompt,
                ),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
            ]
        )

        self.runnable = runnable_context | self.model

    @property
    def described_capabilities(self):
        capabilities_strs = []
        for capability in self.capabilities:
            entity, action_name = self.environment.decompose_action(capability)

            if action_name not in entity.actions:
                raise ValueError(
                    f"Agent capability `{capability}` refers to an undefined action."
                )

            d = entity.actions.get(action_name).description
            capabilities_strs.append(f"`{capability}`: {d}")

        return capabilities_strs

    async def ephemeral_request(self, question):
        return await llm_request(question, self.runnable, self.history, ephemeral=True)

    async def persistent_request(self, question):
        return await llm_request(question, self.runnable, self.history, ephemeral=False)

    def validate_action(self, action_type, message):
        if action_type not in self.environment.world_entities:
            valid_names = ", ".join([we.name for we in self.environment.world_entities])
            return MarkdownLoader(
                "prompts/unrecognised_target.md",
                target_name=action_type,
                target_list_as_str=valid_names,
            ).as_str()

        return None

    async def make_move(self, previous_transaction=None):
        if previous_transaction is None:
            filepath = "prompts/invoke_first_turn.md"
        elif previous_transaction["previous_request_type"] == "request":
            filepath = "prompts/invoke_turn_after_request.md"
        elif previous_transaction["previous_request_type"] == "action":
            filepath = "prompts/invoke_turn_after_action.md"

        args = previous_transaction if type(previous_transaction) is dict else {}
        args["filepath"] = filepath
        args["objective"] = self.objective
        args["visible_world_entities_list"] = (
            self.environment.get_entity_descriptions_for_agent(self.name)
        )

        invoke_turn_prompt = MarkdownLoader(**args).as_str()

        invalid_request_prompt = MarkdownLoader(
            "prompts/invalid_request_format.md"
        ).as_str()

        strikeout = 5
        i = 0

        response = await self.persistent_request(invoke_turn_prompt)

        while i < strikeout:
            i += 1
            if i >= strikeout:
                return None

            match_request = re.search(self.request_pattern, response.content)
            match_action = re.search(self.action_pattern, response.content)

            if match_request:
                addressed_to = match_request.group(1)
                message = match_request.group(2)

                if addressed_to not in self.environment.agent_names:
                    valid_names = ", ".join(self.environment.agent_names)
                    correction_prompt = MarkdownLoader(
                        "prompts/unrecognised_target.md",
                        target_name=addressed_to,
                        target_list_as_str=valid_names,
                    ).as_str()
                    response = await self.persistent_request(correction_prompt)
                    continue

                parsed_response = {"addressed_to": addressed_to, "message": message}
            elif match_action:
                action_type = match_action.group(1).strip()
                message = match_action.group(2)

                if action_type not in self.capabilities:
                    valid_names = ", ".join(self.capabilities)
                    correction_prompt = MarkdownLoader(
                        "prompts/unrecognised_action.md",
                        action=action_type,
                        action_list_as_str=valid_names,
                    ).as_str()
                    response = await self.persistent_request(correction_prompt)
                    continue

                parsed_response = {"action_type": action_type, "message": message}
            else:
                response = await self.persistent_request(invalid_request_prompt)
                continue

            break

        return parsed_response

    async def send_request(self, request_content, sender_name):
        request_prompt = MarkdownLoader(
            "prompts/send_request.md",
            sender_name=sender_name,
            request_content=request_content,
            objective=self.objective,
        ).as_str()

        strikeout = 5
        i = 0

        self.question_history.add_message(HumanMessage(request_prompt))
        response = await self.ephemeral_request(request_prompt)
        self.question_history.add_message(AIMessage(response.content))

        while i < strikeout:
            i += 1
            if i >= strikeout:
                return None

            match = re.search(self.response_pattern, response.content)

            if not match:
                self.question_history.add_message(HumanMessage(request_prompt))
                response = await self.ephemeral_request(request_prompt)
                self.question_history.add_message(AIMessage(response.content))
                continue

            message = match.group(1)
            break

        return message

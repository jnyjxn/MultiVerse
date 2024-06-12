import re
from typing import Callable

from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai.chat_models import ChatOpenAI
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory

from multiagent.utils import get_prompt, llm_request
from multiagent.markdown_loader import MarkdownLoader


class Agent:
    def __init__(
        self,
        name,
        objective,
        model,
        constraints="",
        visible_to: None | list[str] = None,
    ):
        self.name = name
        self.objective = objective
        self.constraints = constraints
        self.visible_to = visible_to

        self.history = ChatMessageHistory()
        self.question_history = ChatMessageHistory()
        self.model = ChatOpenAI(model=model, temperature=0)

        self.environment = None
        self.briefing_prompt = None
        self.runnable = None
        self.with_message_history = None

    def set_environment(self, environment):
        self.environment = environment

    def initialise(self):
        if self.environment is None:
            raise RuntimeError("Cannot initialise agent before linking environment")

        visible_list = self.environment.get_connected_agents(self.name)

        self.briefing_prompt = get_prompt(
            "prompts/initial_briefing.md",
            agent_name=self.name,
            agent_objective=self.objective,
            visible_list=", ".join(visible_list),
            visible_count=len(visible_list),
        )

        self.runnable = self.briefing_prompt | self.model

    async def ephemeral_request(self, question):
        return await llm_request(question, self.runnable, self.history, ephemeral=True)

    async def persistent_request(self, question):
        return await llm_request(question, self.runnable, self.history, ephemeral=False)

    async def make_move(
        self,
        previous_transaction=None,
        validator: None | Callable[[str, str], None | str] = None,
    ):
        if previous_transaction is None:
            invoke_turn_prompt = MarkdownLoader(
                "prompts/invoke_first_turn.md", objective=self.objective
            ).as_str()
        else:
            invoke_turn_prompt = MarkdownLoader(
                "prompts/invoke_turn.md",
                objective=self.objective,
                **previous_transaction,
            ).as_str()

        invalid_request_prompt = MarkdownLoader(
            "prompts/invalid_request_format.md"
        ).as_str()

        strikeout = 5
        i = 0
        pattern = r"<request>[\s\S]*\[([A-Za-z0-9]+)\]: (.+)[\s\S]*</request>"

        response = await self.persistent_request(invoke_turn_prompt)

        while i < strikeout:
            i += 1
            if i >= strikeout:
                return None

            match = re.search(pattern, response.content)

            if not match:
                response = await self.persistent_request(invalid_request_prompt)
                continue

            addressed_to = match.group(1)
            message = match.group(2)

            if validator:
                correction_prompt = validator(addressed_to, message)

                if correction_prompt is not None:
                    response = await self.persistent_request(correction_prompt)
                    continue

            break

        parsed_response = {"addressed_to": addressed_to, "message": message}

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

        pattern = r"<response>\s*(.+)\s*</response>"

        self.question_history.add_message(HumanMessage(request_prompt))
        response = await self.ephemeral_request(request_prompt)
        self.question_history.add_message(AIMessage(response.content))

        while i < strikeout:
            i += 1
            if i >= strikeout:
                return None

            match = re.search(pattern, response.content)

            if not match:
                self.question_history.add_message(HumanMessage(request_prompt))
                response = await self.ephemeral_request(request_prompt)
                self.question_history.add_message(AIMessage(response.content))
                continue

            message = match.group(1)
            break

        return message

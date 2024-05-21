import re

from langchain_openai.chat_models import ChatOpenAI
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory

from multiagent.utils import get_prompt, llm_request
from multiagent.markdown_loader import MarkdownLoader


class Agent:
    def __init__(
        self, name, objective, constraints="", visible_to: None | list[str] = None
    ):
        self.name = name
        self.objective = objective
        self.constraints = constraints
        self.visible_to = visible_to

        self.history = ChatMessageHistory()
        self.model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

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

    async def make_move(self, previous_transaction=None):
        if previous_transaction is None:
            invoke_turn_prompt = MarkdownLoader("prompts/invoke_first_turn.md").as_str()
        else:
            invoke_turn_prompt = MarkdownLoader(
                "prompts/invoke_turn.md", **previous_transaction
            ).as_str()

        invalid_request_prompt = MarkdownLoader(
            "prompts/invalid_request_format.md"
        ).as_str()

        strikeout = 5
        i = 0
        pattern = r"^\[([A-Za-z0-9]+)\]: (.+)$"

        response = await self.persistent_request(invoke_turn_prompt)
        while not (match := re.match(pattern, response.content)):
            if i >= strikeout:
                return None

            i += 1
            response = await self.persistent_request(invalid_request_prompt)

        addressed_to = match.group(1)
        message = match.group(2)
        parsed_response = {"addressed_to": addressed_to, "message": message}

        return parsed_response

    async def send_request(self, request_content, sender_name):
        request_prompt = MarkdownLoader(
            "prompts/send_request.md",
            sender_name=sender_name,
            request_content=request_content,
            objective=self.objective,
        ).as_str()

        response = await self.ephemeral_request(request_prompt)

        return response

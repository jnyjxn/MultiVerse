import copy
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory


class Agent:

    def __init__(
        self, name, objectives, constraints="", visible_to: None | list[str] = None
    ):
        self.name = name
        self.objectives = objectives
        self.constraints = constraints
        self.visible_to = visible_to

        self.environment = None
        self.session_id = "main_session"

        self.history = ChatMessageHistory()
        self.model = ChatOpenAI(model="gpt-3.5-turbo")
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You're an assistant who's good at {ability}. Respond in 20 words or fewer",
                ),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
            ]
        )
        self.runnable = self.prompt | self.model
        self.with_message_history = RunnableWithMessageHistory(
            self.runnable,
            lambda _: self.history,
            input_messages_key="input",
            history_messages_key="history",
        )

    def get_temporary_response(self, question):
        # Create a deep copy of the main history for isolated responses
        temp_history = copy.deepcopy(self.history)
        temp_runnable = RunnableWithMessageHistory(
            self.runnable,
            lambda _: temp_history,
            input_messages_key="input",
            history_messages_key="history",
        )

        # Get the response from the temporary session
        response = temp_runnable.invoke(
            {"ability": "general knowledge", "input": question},
            config={"configurable": {"session_id": self.session_id}},
        )
        return response

    def continue_conversation(self, prompt):
        response = self.with_message_history.invoke(
            {"ability": "general knowledge", "input": prompt},
            config={"configurable": {"session_id": self.session_id}},
        )
        return response

    # def set_environment(self, environment):
    #     self.environment = environment

    # def perform_task(self, task):
    #     # Method to perform a task using the LLM
    #     response = self.chain.invoke(task)
    #     return response

    # def discover_agents(self):
    #     # Method to discover other agents in the environment
    #     return self.environment.get_connected_agents(self.name)

    # def make_request(self, agent_name, task):
    #     # Method to make a request to another agent
    #     agent = self.environment.get_agent(agent_name)
    #     if agent:
    #         return agent.perform_task(task)
    #     return None

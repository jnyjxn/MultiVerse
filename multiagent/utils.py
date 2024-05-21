import copy
from pathlib import Path

from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory

from multiagent.markdown_loader import MarkdownLoader


def get_prompt(filepath, **vars):
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                MarkdownLoader(filepath, **vars).as_str(),
            ),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ]
    )


def llm_request(user_input, runnable, history, ephemeral=False):
    if ephemeral:
        history = copy.deepcopy(history)

    runnable = RunnableWithMessageHistory(
        runnable,
        lambda _: history,
        input_messages_key="input",
        history_messages_key="history",
    )
    response = runnable.invoke(
        {"input": user_input},
        config={"configurable": {"session_id": "global"}},
    )
    return response


class PrettyPrintFileChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, file_path, agent):
        self.messages = []
        self.file_path = Path(file_path)
        self.agent = agent

    def add_message(self, message):
        self.messages.append(message)
        if not self.file_path.exists():
            self.file_path.touch()
            self.file_path.write_text("")

        self.file_path.write_text(self.pretty_messages)

    def clear(self):
        self.messages = []
        if not self.file_path.exists():
            self.file_path.touch()
        self.file_path.write_text("")

    @property
    def pretty_messages(self):
        m = [
            {
                "entity": self.agent.name if msg.type == "ai" else "Admin",
                "content": msg.content,
            }
            for msg in self.messages
        ]

        m = [f"### {msg['entity']} said:\n```\n{msg['content']}\n```" for msg in m]

        m = "\n\n".join(m)

        return m

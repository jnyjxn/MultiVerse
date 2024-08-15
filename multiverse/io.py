from pathlib import Path

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories.file import FileChatMessageHistory


class PrettyPrintFileChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, file_path, agent_name="Agent"):
        self.messages = []
        self.file_path = Path(file_path)
        self.agent_name = agent_name

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
                "entity": self.agent_name if msg.type == "ai" else "Admin",
                "content": msg.content,
            }
            for msg in self.messages
        ]

        m = [f"### {msg['entity']} said:\n```\n{msg['content']}\n```" for msg in m]

        m = "\n\n".join(m)

        return m


class IOUtils:
    @staticmethod
    def save_history_to_file(
        origin_history,
        filename,
        output_dir,
        agent_name: str = "Agent",
        pretty: bool = True,
    ):
        histories = [FileChatMessageHistory(output_dir / f"{filename}.json")]
        if pretty:
            histories.append(
                PrettyPrintFileChatMessageHistory(
                    output_dir / f"{filename}.md", agent_name
                )
            )

        for history in histories:
            for message in origin_history.messages:
                history.add_message(message)

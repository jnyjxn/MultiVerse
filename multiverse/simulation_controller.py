import yaml
import asyncio
from pathlib import Path
from datetime import datetime

from langchain_community.chat_message_histories.file import FileChatMessageHistory

from multiverse.environment import Environment
from multiverse.markdown_loader import MarkdownLoader
from multiverse.utils import PrettyPrintFileChatMessageHistory


class SimulationController:
    def __init__(self, config_path="configs/experiment1.yaml"):
        with open(config_path) as f:
            config = yaml.safe_load(f)

        self.experiment_name = config.get("global", {}).get("name", "DefaultExperiment")

        self.environment = Environment(config)
        self.max_ticks = config.get("global", {}).get("max_ticks", 5)

        self.previous_state = None
        self.clear_previous_state()

    @property
    def agents(self):
        return self.environment.agents

    def clear_previous_state(self):
        self.previous_state = {agent.name: None for agent in self.agents}

    def save_recorded_histories(self, output_dir, pretty=True):
        for agent in self.agents:
            histories = [FileChatMessageHistory(output_dir / f"{agent.name}.json")]
            if pretty:
                histories.append(
                    PrettyPrintFileChatMessageHistory(
                        output_dir / f"{agent.name}.md", agent
                    )
                )

            for history in histories:
                for message in agent.history.messages:
                    history.add_message(message)

    def save_question_histories(self, output_dir, pretty=True):
        for agent in self.agents:
            histories = [
                FileChatMessageHistory(output_dir / f"{agent.name}_questions.json")
            ]
            if pretty:
                histories.append(
                    PrettyPrintFileChatMessageHistory(
                        output_dir / f"{agent.name}_questions.md", agent
                    )
                )

            for history in histories:
                for message in agent.question_history.messages:
                    history.add_message(message)

    def save_histories(self, output_dir, pretty=True):
        self.save_recorded_histories(output_dir, pretty)
        self.save_question_histories(output_dir, pretty)

    async def tick(self):
        move_tasks = [
            agent.make_move(self.previous_state.get(agent.name))
            for agent in self.agents
        ]
        moves = await asyncio.gather(*move_tasks)

        self.clear_previous_state()

        for agent, move in zip(self.agents, moves):
            if move is None:
                continue

            if "addressed_to" in move:
                move_target = move["addressed_to"]
                move_request = move["message"]

                response = await self.environment.send_request(
                    agent, move_target, move_request
                )

                self.previous_state[agent.name] = {
                    "previous_target": move_target,
                    "previous_request_content": move_request,
                    "previous_request_response": response,
                    "previous_request_type": "request",
                }
            elif "action_type" in move:
                action_type = move["action_type"]
                move_request = move["message"]

                response = self.environment.do_action(action_type, move_request)

                self.previous_state[agent.name] = {
                    "previous_target": action_type,
                    "previous_request_content": move_request,
                    "previous_request_response": response,
                    "previous_request_type": "action",
                }

    async def run(self):
        now = "{:%Y-%m-%d_%H:%M:%S}".format(datetime.now())
        output_dir = Path("outputs") / self.experiment_name / now

        output_dir.mkdir(parents=True, exist_ok=True)

        for i in range(self.max_ticks):
            await self.tick()
            self.save_histories(output_dir)
            print("." * (i + 1))

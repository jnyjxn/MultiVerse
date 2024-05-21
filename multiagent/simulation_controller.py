from langchain_community.chat_message_histories.file import FileChatMessageHistory

from multiagent.environment import Environment
from multiagent.utils import PrettyPrintFileChatMessageHistory


class SimulationController:
    def __init__(self, config_path="configs/experiment1.yaml"):
        self.environment = Environment(config_path)

        self.previous_state = None
        self.clear_previous_state()

    @property
    def agents(self):
        return self.environment.agents

    def clear_previous_state(self):
        self.previous_state = {agent.name: None for agent in self.agents}

    def save_histories(self, output_dir="outputs", pretty=True):
        for agent in self.agents:
            if pretty:
                history = PrettyPrintFileChatMessageHistory(
                    f"{output_dir}/{agent.name}.md", agent
                )
            else:
                history = FileChatMessageHistory(f"{output_dir}/{agent.name}.json")

            for message in agent.history.messages:
                history.add_message(message)

    def tick(self):
        moves = {
            agent.name: agent.make_move(self.previous_state.get(agent.name))
            for agent in self.agents
        }

        self.clear_previous_state()

        for agent_name, move in moves.items():
            if move is None:
                continue
            move_target = move["addressed_to"]
            move_request = move["message"]

            target_agent = self.environment.get_agent(move_target)

            response = target_agent.send_request(move_request, agent_name).content

            self.previous_state[agent_name] = {
                "previous_target": move_target,
                "previous_request_content": move_request,
                "previous_request_response": response,
            }

    def run(self):
        for _ in range(5):
            self.tick()

        self.save_histories()

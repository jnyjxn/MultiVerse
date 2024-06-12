import warnings
import networkx as nx
from multiagent.agent import Agent


class Environment:
    def __init__(self, config=None):
        self.network = nx.DiGraph()

        if config is not None:
            self.load(config)
            self.initialise()

    def load(self, config):
        default_model = config.get("global", {}).get("default_model", "gpt-3.5-turbo")

        assert "agents" in config, "Config must contain an 'agents' key"

        for agent_config in config["agents"]:
            assert "name" in agent_config, f"All agents must include a 'name'"
            assert (
                "objective" in agent_config
            ), f"All agents must include an 'objective'"

            agent_config["model"] = agent_config.get("model", default_model)

            agent = Agent(**agent_config)
            self.add_agent(agent)

    def add_agent(self, agent):
        self.network.add_node(agent.name, agent=agent)

    def connect_public_agent(self, agent_name):
        for node in list(self.network.nodes):
            if node != agent_name:
                self.network.add_edge(node, agent_name)

    def connect_private_agent(
        self, agent_name, visible_to: list[str], error_if_not_found=False
    ):
        for node in visible_to:
            if not node in self.network.nodes:
                msg = f"{node} does not exist in the network"
                if error_if_not_found:
                    raise ValueError(msg)
                else:
                    warnings.warn(msg)
                    continue

            if node != agent_name:
                self.network.add_edge(node, agent_name)

    def initialise(self):
        for agent in self.agents:
            agent.set_environment(self)

            if agent.visible_to is None:
                self.connect_public_agent(agent.name)
            else:
                self.connect_private_agent(agent.name, agent.visible_to)

        for agent in self.agents:
            agent.initialise()

    def get_connected_agents(self, requester_name):
        return list(set(self.network.successors(requester_name)))

    def get_agent(self, agent_name):
        return self.network.nodes[agent_name]["agent"]

    @property
    def agents(self):
        return [self.network.nodes[n]["agent"] for n in self.network.nodes]

    @property
    def agent_names(self):
        return [self.network.nodes[n]["agent"].name for n in self.network.nodes]

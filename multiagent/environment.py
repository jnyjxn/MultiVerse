import warnings
import networkx as nx


class Environment:
    def __init__(self):
        self.network = nx.DiGraph()

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

    def connect(self):
        for _, attrs in self.network.nodes(data=True):
            agent = attrs.get("agent")
            if agent.visible_to is None:
                self.connect_public_agent(agent.name)
            else:
                self.connect_private_agent(agent.name, agent.visible_to)

    def get_connected_agents(self, requester_name):
        return list(set(self.network.successors(requester_name)))

    def get_agent(self, agent_name):
        return self.network.nodes[agent_name]["agent"]

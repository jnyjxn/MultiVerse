import warnings
import networkx as nx
from multiverse.agent import Agent
from multiverse.world_entity import WorldEntity, WorldEntityActionResult


class Environment:
    def __init__(self, config=None):
        self.agents_graph = nx.DiGraph()
        self.world_entities = {}

        if config is not None:
            self.load(config)

    def load_agents(self, config):
        default_model = config.get("global", {}).get(
            "default_model", "openai:gpt-3.5-turbo"
        )

        assert "agents" in config, "Config must contain an 'agents' key"

        for agent_config in config["agents"]:
            assert "name" in agent_config, f"All agents must include a 'name'"
            assert (
                "objective" in agent_config
            ), f"All agents must include an 'objective'"

            agent_config["model"] = agent_config.get("model", default_model)

            agent = Agent(**agent_config)
            self.add_agent(agent)

        self.initialise_agents()

    def load_world_entities(self, config):
        if not "world_entities" in config:
            return

        self.world_entities = {
            cfg["name"]: WorldEntity.from_dict(cfg)
            for cfg in config.get("world_entities")
        }

    def load(self, config):
        self.load_world_entities(config)
        self.load_agents(config)

    def add_agent(self, agent):
        self.agents_graph.add_node(agent.name, agent=agent)

    def connect_agent(
        self, agent_name, connect_to: list[str] | bool, error_if_not_found=False
    ):
        if connect_to == False:
            connect_to = []
        elif connect_to == True:
            connect_to = list(self.agents_graph.nodes)

        for node in connect_to:
            if not node in self.agents_graph.nodes:
                msg = f"{node} does not exist in the agents network"
                if error_if_not_found:
                    raise ValueError(msg)
                else:
                    warnings.warn(msg)
                    continue

            if node != agent_name:
                self.agents_graph.add_edge(node, agent_name)

    def initialise_agents(self):
        for agent in self.agents:
            agent.set_environment(self)
            self.connect_agent(agent.name, agent.known_to_agents)

        for agent in self.agents:
            agent.initialise()

    def get_connected_agents(self, requester_name):
        return list(set(self.agents_graph.successors(requester_name)))

    def get_agent(self, agent_name):
        return self.agents_graph.nodes[agent_name]["agent"]

    @property
    def agent_to_world_entities_map(self):
        agent_to_world_entity_map = {n: [] for n in self.agent_names}
        for entity in self.world_entities.values():
            connected_agents = entity.known_to_agents
            if connected_agents is True:
                connected_agents = self.agent_names
            elif connected_agents is False:
                connected_agents = []

            for agent in connected_agents:
                agent_to_world_entity_map[agent].append(entity)

        return agent_to_world_entity_map

    def get_entity_descriptions_for_agent(self, agent_name):
        if len(self.agent_to_world_entities_map.get(agent_name)) == 0:
            return "None"

        str_items = [
            we.describe() for we in self.agent_to_world_entities_map.get(agent_name)
        ]

        return "\n".join(str_items)

    @property
    def agents(self):
        return [self.agents_graph.nodes[n]["agent"] for n in self.agents_graph.nodes]

    @property
    def agent_names(self):
        return [
            self.agents_graph.nodes[n]["agent"].name for n in self.agents_graph.nodes
        ]

    def decompose_action(self, action: str):
        action = action.strip()
        components = action.split(" > ")

        assert (
            len(components) == 2
        ), f"Action must be in format `Entity Name > Action Name`, but got {action}"

        entity_name, action_type = components

        entity_name = entity_name.strip()
        action_type = action_type.strip()

        if not entity_name in self.world_entities:
            raise ValueError(
                f"entity_name `{entity_name}` is not recognised in the action string {action}."
            )

        return self.world_entities.get(entity_name), action_type

    async def send_request(self, from_agent, to_agent, request):
        to_agent = self.get_agent(to_agent)

        return await to_agent.send_request(request, from_agent.name)

    def do_action(self, action, request):
        try:
            entity, action_type = self.decompose_action(action)
            action_result = entity.attempt_run_action(action_type, request)
        except:
            action_result = WorldEntityActionResult.UNRECOGNISED_NAME

        if action_result == WorldEntityActionResult.UNRECOGNISED_NAME:
            return "The action you specified was not recognised as a valid action, so there was no change."
        elif action_result == WorldEntityActionResult.INVALID_PASSWORD:
            return "The action you specified requires a password and your explanation message did not include the correct password, so there was no change."
        else:
            return f"The action you specified was correctly applied. The new state of {entity.name} is now: {entity.describe()}."

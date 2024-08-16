import yaml
import asyncio
from pathlib import Path
from datetime import datetime

from multiverse.environment import Environment
from multiverse.io import IOUtils
from multiverse.moves import MoveManager


class SimulationController:
    def __init__(self, config_path="configs/experiment1.yaml"):
        with open(config_path) as f:
            config = yaml.safe_load(f)

        self.experiment_name = config.get("global", {}).get("name", "DefaultExperiment")
        self.max_ticks = config.get("global", {}).get("max_ticks", 5)

        self.environment = Environment(config)
        self.move_manager = MoveManager()

    def save_recorded_histories(self, output_dir, pretty=True):
        for agent in self.environment.agents.values():
            IOUtils.save_history_to_file(
                agent.internal_history, agent.name, output_dir, agent.name, pretty
            )

    def save_ephemeral_histories(self, output_dir, pretty=True):
        for agent in self.environment.agents.values():
            IOUtils.save_history_to_file(
                agent.ephemeral_history,
                f"{agent.name}_ephemeral",
                output_dir,
                agent.name,
                pretty,
            )

    def save_histories(self, output_dir, pretty=True):
        self.save_recorded_histories(output_dir, pretty)
        self.save_ephemeral_histories(output_dir, pretty)

    def one_move(self):
        self.move_manager.prepare_turn(self.environment)
        self.move_manager.execute_turn(self.environment)

    def run(self):
        now = "{:%Y-%m-%d_%H:%M:%S}".format(datetime.now())
        output_dir = Path("outputs") / self.experiment_name / now

        output_dir.mkdir(parents=True, exist_ok=True)

        self.move_manager.brief_agents(self.environment)

        for i in range(self.max_ticks):
            self.one_move()
            self.save_histories(output_dir)
            print("." * (i + 1))

import asyncio
from pathlib import Path
from datetime import datetime

from multiverse.io import IOUtils
from multiverse.config import Config
from multiverse.moves import MoveManager
from multiverse.environment import Environment


class SimulationController:
    def __init__(self, config: Config):
        self.experiment_name = config.get("global/name", "DefaultExperiment")
        self.max_ticks = config.get("global/max_ticks", 5)

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

    def instantiate(self):
        for agent in self.environment.agents:
            self.move_manager.queue_prompt(
                self.move_manager.agent_briefing_template_filename,
                agent=agent,
                environment=self.environment,
            )

    async def run_one_turn_async(self, turn_number: int):
        await self.move_manager.prepare_turn_async(self.environment)
        await self.move_manager.execute_turn_async(self.environment)
        self.environment.run_regular_safety_checks(turn_number)

    async def run_async(self):
        now = "{:%Y-%m-%d_%H:%M:%S}".format(datetime.now())
        output_dir = Path("outputs") / self.experiment_name / now

        output_dir.mkdir(parents=True, exist_ok=True)

        self.instantiate()

        for turn_number in range(self.max_ticks):
            await self.run_one_turn_async(turn_number)
            self.save_histories(output_dir)
            print("." * (turn_number + 1))

        self.environment.run_final_safety_checks()
        self.environment.summarise_results()

    def run_one_turn(self):
        asyncio.run(self.run_one_turn_async())

    def run(self):
        return asyncio.run(self.run_async())

    @classmethod
    def from_config_file(cls, config_filepath: str, config_filetype: str | None = None):
        config = Config.from_file(config_filepath, config_filetype)
        return cls(config)

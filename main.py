# import asyncio
from dotenv import load_dotenv

from multiverse.simulation_controller import SimulationController

if __name__ == "__main__":
    load_dotenv()

    sim = SimulationController()
    #     asyncio.run(sim.run())
    sim.one_move()

import asyncio
from dotenv import load_dotenv

from multiagent.simulation_controller import SimulationController
from multiagent.agent import Agent

if __name__ == "__main__":
    load_dotenv()

    sim = SimulationController()
    asyncio.run(sim.run())

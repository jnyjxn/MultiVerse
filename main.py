# import asyncio
from dotenv import load_dotenv

from multiverse.simulation_controller import SimulationController

if __name__ == "__main__":
    load_dotenv()

    sim = SimulationController()
    #     asyncio.run(sim.run())
    # sim.one_move()
    a = list(sim.environment.agents.values())[0]
    r = a.request("Please speak french from now on.")
    r = a.request("How are you today?")
    print(a.internal_history)

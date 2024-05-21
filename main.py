from dotenv import load_dotenv

from multiagent.simulation_controller import SimulationController

if __name__ == "__main__":
    load_dotenv()

    sim = SimulationController()
    sim.run()

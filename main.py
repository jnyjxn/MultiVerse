import argparse
from dotenv import load_dotenv

from multiverse.config import Config
from multiverse.simulation_controller import SimulationController


def cmdline():
    parser = argparse.ArgumentParser(
        """
        Welcome to MultiVerse! This is a research and game engine to model arbitrarily large
        multiagent LLM systems.
    """
    )
    parser.add_argument(
        "config_path",
        help="A path to the configuration file.",
        type=str,
    )
    parser.add_argument(
        "--config_filetype",
        help="Specify which loader to use when reading the config. If the `config_path` has as file extension belonging \
        to one of the allowed values, the config_filetype will be automatically inferred.",
        choices=["yaml", "json"],
    )
    args = parser.parse_args()
    return args


def main(
    config_path: str | None = None,
    config_filetype: str | None = None,
    as_commandline_program: bool = True,
):
    if as_commandline_program:
        args = cmdline()
        config_path = args.config_path
        config_filetype = args.config_filetype
    else:
        if not config_path:
            raise ValueError(
                f"If not running in `as_commandline_program` mode, `config_path` must be set."
            )

    sim = SimulationController.from_config_file(config_path, config_filetype)
    sim.run()


if __name__ == "__main__":
    load_dotenv()

    main()

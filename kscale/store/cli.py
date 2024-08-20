"""Defines the top-level KOL CLI."""

import argparse
from typing import Sequence

from kscale.store import pybullet, urdf


def main(args: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="K-Scale OnShape Library", add_help=False)
    parser.add_argument(
        "subcommand",
        choices=[
            "urdf",
            "pybullet",
        ],
        help="The subcommand to run",
    )
    parsed_args, remaining_args = parser.parse_known_args(args)

    match parsed_args.subcommand:
        case "urdf":
            urdf.main(remaining_args)
        case "pybullet":
            pybullet.main(remaining_args)


if __name__ == "__main__":
    # python3 -m kscale.store.cli
    main()

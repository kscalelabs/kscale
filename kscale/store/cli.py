"""Defines the top-level KOL CLI."""

import argparse
import asyncio
from typing import Sequence

from kscale.store import pybullet, urdf


async def main(args: Sequence[str] | None = None) -> None:
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
            await urdf.main(remaining_args)
        case "pybullet":
            await pybullet.main(remaining_args)


def sync_main(args: Sequence[str] | None = None) -> None:
    asyncio.run(main(args))


if __name__ == "__main__":
    # python3 -m kscale.store.cli
    sync_main()

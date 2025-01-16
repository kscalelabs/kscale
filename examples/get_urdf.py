"""Shows an example of getting a URDF from the K-Scale WWW API."""

import asyncio
import logging

import colorlogging

from kscale import K

logger = logging.getLogger(__name__)


async def main() -> None:
    colorlogging.configure()

    async with K() as k:
        urdf_path = await k.download_and_extract_urdf("zbot-v2")
        logger.info("URDF downloaded to %s", urdf_path)


if __name__ == "__main__":
    # python -m examples.get_urdf
    asyncio.run(main())

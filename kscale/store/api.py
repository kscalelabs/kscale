"""Defines a common interface for the K-Scale Store API."""

from pathlib import Path

from kscale.store.urdf import download_urdf
from kscale.utils.api_base import APIBase


class StoreAPI(APIBase):
    def __init__(
        self,
        *,
        api_key: str | None = None,
    ) -> None:
        super().__init__()

        self.api_key = api_key

    async def urdf(self, artifact_id: str) -> Path:
        return await download_urdf(artifact_id)

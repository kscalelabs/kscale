"""Defines a common interface for the K-Scale Store API."""

from pathlib import Path

from kscale.store.gen.api import UploadArtifactResponse
from kscale.store.urdf import download_urdf, upload_urdf
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

    async def upload_urdf(self, listing_id: str, root_dir: Path) -> UploadArtifactResponse:
        return await upload_urdf(listing_id, root_dir)

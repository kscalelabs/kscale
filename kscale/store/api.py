"""Defines a common interface for the K-Scale Store API."""

from pathlib import Path
from typing import overload

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

    async def artifact_root(self, artifact_id: str) -> Path:
        return await download_urdf(artifact_id)

    @overload
    async def urdf_path(self, artifact_id: str) -> Path: ...

    @overload
    async def urdf_path(self, artifact_id: str, *, throw_if_missing: bool = True) -> Path | None: ...

    async def urdf_path(self, artifact_id: str, *, throw_if_missing: bool = True) -> Path | None:
        root_dir = await self.artifact_root(artifact_id)
        urdf_path = next(root_dir.glob("*.urdf"), None)
        if urdf_path is None and throw_if_missing:
            raise FileNotFoundError(f"No URDF found for artifact {artifact_id}")
        return urdf_path

    @overload
    async def mjcf_path(self, artifact_id: str) -> Path: ...

    @overload
    async def mjcf_path(self, artifact_id: str, *, throw_if_missing: bool = True) -> Path | None: ...

    async def mjcf_path(self, artifact_id: str, *, throw_if_missing: bool = True) -> Path | None:
        root_dir = await self.artifact_root(artifact_id)
        mjcf_path = next(root_dir.glob("*.mjcf"), None)
        if mjcf_path is None and throw_if_missing:
            raise FileNotFoundError(f"No MJCF found for artifact {artifact_id}")
        return mjcf_path

    @overload
    async def xml_path(self, artifact_id: str) -> Path: ...

    @overload
    async def xml_path(self, artifact_id: str, *, throw_if_missing: bool = True) -> Path | None: ...

    async def xml_path(self, artifact_id: str, *, throw_if_missing: bool = True) -> Path | None:
        root_dir = await self.artifact_root(artifact_id)
        xml_path = next(root_dir.glob("*.xml"), None)
        if xml_path is None and throw_if_missing:
            raise FileNotFoundError(f"No XML found for artifact {artifact_id}")
        return xml_path

    async def upload_urdf(self, listing_id: str, root_dir: Path) -> UploadArtifactResponse:
        return await upload_urdf(listing_id, root_dir)

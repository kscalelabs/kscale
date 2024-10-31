"""Defines a common interface for the K-Scale Store API."""

import asyncio
from pathlib import Path
from typing import overload

from kscale.utils.api_base import APIBase
from kscale.web.gen.api import UploadArtifactResponse
from kscale.web.urdf import download_urdf, upload_urdf


class WebAPI(APIBase):
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
    def urdf_path_sync(self, artifact_id: str) -> Path: ...

    @overload
    def urdf_path_sync(self, artifact_id: str, *, throw_if_missing: bool = True) -> Path | None: ...

    def urdf_path_sync(self, artifact_id: str, *, throw_if_missing: bool = True) -> Path | None:
        return asyncio.run(self.urdf_path(artifact_id, throw_if_missing=throw_if_missing))

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
    def mjcf_path_sync(self, artifact_id: str) -> Path: ...

    @overload
    def mjcf_path_sync(self, artifact_id: str, *, throw_if_missing: bool = True) -> Path | None: ...

    def mjcf_path_sync(self, artifact_id: str, *, throw_if_missing: bool = True) -> Path | None:
        return asyncio.run(self.mjcf_path(artifact_id, throw_if_missing=throw_if_missing))

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

    def artifact_root_sync(self, artifact_id: str) -> Path:
        return asyncio.run(self.artifact_root(artifact_id))

    @overload
    def xml_path_sync(self, artifact_id: str) -> Path: ...

    @overload
    def xml_path_sync(self, artifact_id: str, *, throw_if_missing: bool = True) -> Path | None: ...

    def xml_path_sync(self, artifact_id: str, *, throw_if_missing: bool = True) -> Path | None:
        return asyncio.run(self.xml_path(artifact_id, throw_if_missing=throw_if_missing))

    def upload_urdf_sync(self, listing_id: str, root_dir: Path) -> UploadArtifactResponse:
        return asyncio.run(self.upload_urdf(listing_id, root_dir))

"""Defines the client for interacting with the K-Scale robot class endpoints."""

import hashlib
import logging
from pathlib import Path

import httpx

from kscale.web.clients.base import BaseClient
from kscale.web.gen.api import RobotClass, RobotDownloadURDFResponse, RobotUploadURDFResponse
from kscale.web.utils import get_cache_dir

logger = logging.getLogger(__name__)


class RobotClassClient(BaseClient):
    async def get_robot_classes(self) -> list[RobotClass]:
        data = await self._request(
            "GET",
            "/robots/",
            auth=True,
        )
        return [RobotClass.model_validate(item) for item in data]

    async def create_robot_class(self, class_name: str, description: str | None = None) -> RobotClass:
        params = {}
        if description is not None:
            params["description"] = description
        data = await self._request(
            "PUT",
            f"/robots/{class_name}",
            params=params,
            auth=True,
        )
        return RobotClass.model_validate(data)

    async def update_robot_class(
        self,
        class_name: str,
        new_class_name: str | None = None,
        new_description: str | None = None,
    ) -> RobotClass:
        params = {}
        if new_class_name is not None:
            params["new_class_name"] = new_class_name
        if new_description is not None:
            params["new_description"] = new_description
        if not params:
            raise ValueError("No parameters to update")
        data = await self._request(
            "POST",
            f"/robots/{class_name}",
            params=params,
            auth=True,
        )
        return RobotClass.model_validate(data)

    async def delete_robot_class(self, class_name: str) -> None:
        await self._request("DELETE", f"/robots/{class_name}", auth=True)

    async def upload_robot_class_urdf(self, class_name: str, urdf_file: str | Path) -> RobotUploadURDFResponse:
        if not (urdf_file := Path(urdf_file)).exists():
            raise FileNotFoundError(f"URDF file not found: {urdf_file}")

        # Gets the content type from the file extension.
        ext = urdf_file.suffix.lower()
        match ext:
            case ".tgz":
                content_type = "application/x-compressed-tar"
            case _:
                raise ValueError(f"Unsupported file extension: {ext}")

        data = await self._request(
            "PUT",
            f"/robots/urdf/{class_name}",
            params={"filename": urdf_file.name, "content_type": content_type},
            auth=True,
        )
        response = RobotUploadURDFResponse.model_validate(data)
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "PUT",
                response.url,
                content=urdf_file.read_bytes(),
                headers={"Content-Type": response.content_type},
            ) as r:
                r.raise_for_status()
        return response

    async def download_robot_class_urdf(self, class_name: str, *, cache: bool = True) -> Path:
        cache_path = get_cache_dir() / class_name / "robot.tgz"
        if cache and cache_path.exists():
            return cache_path
        data = await self._request("GET", f"/robots/urdf/{class_name}", auth=True)
        response = RobotDownloadURDFResponse.model_validate(data)
        expected_hash = response.md5_hash
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Downloading URDF file from %s", response.url)
        async with httpx.AsyncClient() as client:
            with open(cache_path, "wb") as file:
                hash_value = hashlib.md5()
                async with client.stream("GET", response.url) as r:
                    r.raise_for_status()
                    async for chunk in r.aiter_bytes():
                        file.write(chunk)
                        hash_value.update(chunk)

        logger.info("Checking MD5 hash of downloaded file")
        hash_value_hex = f'"{hash_value.hexdigest()}"'
        if hash_value_hex != expected_hash:
            raise ValueError(f"MD5 hash mismatch: {hash_value_hex} != {expected_hash}")

        return cache_path

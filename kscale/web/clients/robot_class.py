"""Defines the client for interacting with the K-Scale robot class endpoints."""

import hashlib
import json
import logging
import shutil
import tarfile
from pathlib import Path
from typing import Any

import httpx

from kscale.web.clients.base import BaseClient
from kscale.web.gen.api import (
    RobotClass,
    RobotDownloadURDFResponse,
    RobotUploadURDFResponse,
    RobotURDFMetadataInput,
)
from kscale.web.utils import get_robots_dir, should_refresh_file

logger = logging.getLogger(__name__)

UPLOAD_TIMEOUT = 300.0
DOWNLOAD_TIMEOUT = 60.0

INFO_FILE_NAME = ".info.json"


class RobotClassClient(BaseClient):
    async def get_robot_classes(self) -> list[RobotClass]:
        data = await self._request(
            "GET",
            "/robots/",
            auth=False,
        )
        return [RobotClass.model_validate(item) for item in data]

    async def get_robot_class(self, class_name: str) -> RobotClass:
        data = await self._request(
            "GET",
            f"/robots/name/{class_name}",
            auth=False,
        )
        return RobotClass.model_validate(data)

    async def create_robot_class(self, class_name: str, description: str | None = None) -> RobotClass:
        data = {}
        if description is not None:
            data["description"] = description
        data = await self._request(
            "PUT",
            f"/robots/{class_name}",
            data=data,
            auth=True,
        )
        return RobotClass.model_validate(data)

    async def update_robot_class(
        self,
        class_name: str,
        new_class_name: str | None = None,
        new_description: str | None = None,
        new_metadata: RobotURDFMetadataInput | None = None,
    ) -> RobotClass:
        data: dict[str, Any] = {}
        if new_class_name is not None:
            data["new_class_name"] = new_class_name
        if new_description is not None:
            data["new_description"] = new_description
        if new_metadata is not None:
            data["new_metadata"] = new_metadata.model_dump()
        if not data:
            raise ValueError("No parameters to update")
        data = await self._request(
            "POST",
            f"/robots/{class_name}",
            data=data,
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
            data={"filename": urdf_file.name, "content_type": content_type},
            auth=True,
        )
        response = RobotUploadURDFResponse.model_validate(data)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(UPLOAD_TIMEOUT),
        ) as client:
            async with client.stream(
                "PUT",
                response.url,
                content=urdf_file.read_bytes(),
                headers={"Content-Type": response.content_type},
            ) as r:
                r.raise_for_status()
        return response

    async def download_compressed_urdf(self, class_name: str, *, cache: bool = True) -> Path:
        cache_path = get_robots_dir() / class_name / "robot.tgz"
        if cache and cache_path.exists() and not should_refresh_file(cache_path):
            return cache_path
        data = await self._request(
            "GET",
            f"/robots/urdf/{class_name}",
            auth=False,
            error_code_suggestions={404: "Use `kscale robot list` to view classes."},
        )
        response = RobotDownloadURDFResponse.model_validate(data)
        expected_hash = response.md5_hash
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Checks the md5 hash of the file.
        cache_path_info = cache_path.parent / INFO_FILE_NAME
        if cache_path_info.exists():
            with open(cache_path_info, "r") as f:
                info = json.load(f)
                if info["md5_hash"] == expected_hash:
                    cache_path.touch()
                    return cache_path

        logger.info("Downloading URDF file from %s", response.url)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(DOWNLOAD_TIMEOUT),
        ) as client:
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

        logger.info("Updating downloaded file information")
        info = {"md5_hash": hash_value_hex}
        with open(cache_path_info, "w") as f:
            json.dump(info, f)

        return cache_path

    async def download_and_extract_urdf(self, class_name: str, *, cache: bool = True) -> Path:
        cache_path = await self.download_compressed_urdf(class_name, cache=cache)

        # Reads the MD5 hash from the info file.
        cache_path_info = cache_path.parent / INFO_FILE_NAME
        with open(cache_path_info, "r") as f:
            info = json.load(f)
            expected_hash = info["md5_hash"]

        # Unpacks the file if requested.
        unpack_path = cache_path.parent / "robot"
        unpacked_path_info = unpack_path / INFO_FILE_NAME

        if not cache:
            # If not using cache, remove the existing unpacked directory.
            if unpack_path.exists():
                logger.info("Removing existing unpacked directory")
                shutil.rmtree(unpack_path)

        unpack_path.mkdir(parents=True, exist_ok=True)

        # If the file has already been unpacked, return the path.
        if unpacked_path_info.exists():
            with open(unpacked_path_info, "r") as f:
                info = json.load(f)
                if info["md5_hash"] == expected_hash:
                    unpack_path.touch()
                    return unpack_path

        logger.info("Unpacking URDF file")
        with tarfile.open(cache_path, "r:gz") as tar:
            tar.extractall(path=unpack_path)

        logger.info("Updating downloaded file information")
        info = {"md5_hash": expected_hash}
        with open(unpacked_path_info, "w") as f:
            json.dump(info, f)

        return unpack_path

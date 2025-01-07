"""Defines a typed client for the K-Scale WWW API."""

import logging
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, Type
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel

from kscale.web.gen.api import (
    BodyAddListingListingsAddPost,
    NewListingResponse,
    SingleArtifactResponse,
    UploadArtifactResponse,
    UploadKRecRequest,
)
from kscale.web.token import get_bearer_token
from kscale.web.utils import DEFAULT_UPLOAD_TIMEOUT, get_api_root

logger = logging.getLogger(__name__)


class KScaleWWWClient:
    def __init__(self, base_url: str | None = None, upload_timeout: float = DEFAULT_UPLOAD_TIMEOUT) -> None:
        self.base_url = get_api_root() if base_url is None else base_url
        self.upload_timeout = upload_timeout
        self._client: httpx.AsyncClient | None = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {await get_bearer_token()}"},
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Dict[str, Any] | None = None,
        data: BaseModel | None = None,
        files: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        url = urljoin(self.base_url, endpoint)
        kwargs: Dict[str, Any] = {"params": params}

        if data:
            kwargs["json"] = data.dict(exclude_unset=True)
        if files:
            kwargs["files"] = files

        client = await self.get_client()
        response = await client.request(method, url, **kwargs)

        if response.is_error:
            logger.error("Error response from K-Scale: %s", response.text)
        response.raise_for_status()
        return response.json()

    async def get_artifact_info(self, artifact_id: str) -> SingleArtifactResponse:
        data = await self._request("GET", f"/artifacts/info/{artifact_id}")
        return SingleArtifactResponse(**data)

    async def upload_artifact(self, listing_id: str, file_path: str) -> UploadArtifactResponse:
        file_name = Path(file_path).name
        with open(file_path, "rb") as f:
            files = {"files": (file_name, f, "application/gzip")}
            data = await self._request("POST", f"/artifacts/upload/{listing_id}", files=files)
        return UploadArtifactResponse(**data)

    async def create_listing(self, request: BodyAddListingListingsAddPost) -> NewListingResponse:
        data = await self._request("POST", "/listings", data=request)
        return NewListingResponse(**data)

    async def create_krec(self, request: UploadKRecRequest) -> dict:
        """Create a new K-Rec upload and get the presigned URL."""
        return await self._request(
            "POST",
            "/krecs/upload",
            data=request,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "KScaleWWWClient":
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def upload_to_presigned_url(self, url: str, file_path: str) -> None:
        """Upload a file using a presigned URL."""
        with open(file_path, "rb") as f:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout=self.upload_timeout)) as client:
                response = await client.put(url, content=f.read(), headers={"Content-Type": "application/octet-stream"})
                response.raise_for_status()

    async def get_presigned_url(self, listing_id: str, file_name: str, checksum: str | None = None) -> dict:
        """Get a presigned URL for uploading an artifact."""
        params = {"filename": file_name}
        if checksum:
            params["checksum"] = checksum
        return await self._request("POST", f"/artifacts/presigned/{listing_id}", params=params)

    async def get_krec_info(self, krec_id: str) -> dict:
        """Get information about a K-Rec."""
        logger.info("Getting K-Rec info for ID: %s", krec_id)
        try:
            data = await self._request("GET", f"/krecs/download/{krec_id}")
            if not isinstance(data, dict):
                logger.error("Server returned unexpected type: %s", type(data))
                logger.error("Response data: %s", data)
                raise ValueError(f"Server returned {type(data)} instead of dictionary")

            return {
                "url": data.get("url"),
                "filename": data.get("filename"),
                "checksum": data.get("checksum"),
            }
        except Exception as e:
            logger.error("Failed to get K-Rec info: %s", str(e))
            raise

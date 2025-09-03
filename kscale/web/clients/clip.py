"""Defines the client for interacting with the K-Scale clip endpoints."""

import hashlib
import logging
from pathlib import Path

import httpx

from kscale.web.clients.base import BaseClient
from kscale.web.gen.api import (
    Clip,
    ClipDownloadResponse,
    ClipUploadResponse,
)

logger = logging.getLogger(__name__)

UPLOAD_TIMEOUT = 300.0
DOWNLOAD_TIMEOUT = 60.0


class ClipClient(BaseClient):
    async def get_clips(self) -> list[Clip]:
        """Get all clips for the authenticated user."""
        data = await self._request("GET", "/clips/", auth=True)
        return [Clip.model_validate(item) for item in data]

    async def get_clip(self, clip_id: str) -> Clip:
        """Get a specific clip by ID."""
        data = await self._request("GET", f"/clips/{clip_id}", auth=True)
        return Clip.model_validate(data)

    async def create_clip(self, description: str | None = None) -> Clip:
        """Create a new clip."""
        data = {}
        if description is not None:
            data["description"] = description
        response_data = await self._request("POST", "/clips/", data=data, auth=True)
        return Clip.model_validate(response_data)

    async def update_clip(self, clip_id: str, new_description: str | None = None) -> Clip:
        """Update a clip's metadata."""
        data = {}
        if new_description is not None:
            data["new_description"] = new_description
        response_data = await self._request("POST", f"/clips/{clip_id}", data=data, auth=True)
        return Clip.model_validate(response_data)

    async def delete_clip(self, clip_id: str) -> None:
        """Delete a clip."""
        await self._request("DELETE", f"/clips/{clip_id}", auth=True)

    async def upload_clip(self, clip_id: str, file_path: str | Path) -> ClipUploadResponse:
        """Upload a file for a clip."""
        if not (file_path := Path(file_path)).exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine content type based on file extension
        ext = file_path.suffix.lower()
        content_type_map = {
            ".mp4": "video/mp4",
            ".avi": "video/x-msvideo",
            ".mov": "video/quicktime",
            ".mkv": "video/x-matroska",
            ".webm": "video/webm",
            ".json": "application/json",
            ".txt": "text/plain",
        }
        content_type = content_type_map.get(ext, "application/octet-stream")

        # Get upload URL
        data = await self._request(
            "PUT",
            f"/clips/{clip_id}/upload",
            data={"filename": file_path.name, "content_type": content_type},
            auth=True,
        )
        response = ClipUploadResponse.model_validate(data)

        # Upload the file
        async with httpx.AsyncClient(timeout=httpx.Timeout(UPLOAD_TIMEOUT)) as client:
            async with client.stream(
                "PUT",
                response.url,
                content=file_path.read_bytes(),
                headers={"Content-Type": response.content_type},
            ) as r:
                r.raise_for_status()

        return response

    async def download_clip(self, clip_id: str) -> ClipDownloadResponse:
        """Get download URL and metadata for a clip."""
        data = await self._request("GET", f"/clips/{clip_id}/download", auth=True)
        return ClipDownloadResponse.model_validate(data)

    async def download_clip_to_file(self, clip_id: str, output_path: str | Path) -> Path:
        """Download a clip to a local file."""
        download_response = await self.download_clip(clip_id)
        output_path = Path(output_path)

        async with httpx.AsyncClient(timeout=httpx.Timeout(DOWNLOAD_TIMEOUT)) as client:
            async with client.stream("GET", download_response.url) as response:
                response.raise_for_status()
                with output_path.open("wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)

        # Verify download integrity if hash is provided
        if download_response.md5_hash:
            with output_path.open("rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
                if file_hash != download_response.md5_hash:
                    raise ValueError(
                        f"Downloaded file hash mismatch: expected {download_response.md5_hash}, got {file_hash}"
                    )

        return output_path

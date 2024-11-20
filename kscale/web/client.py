"""Defines a typed client for the K-Scale Store API."""

import logging
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, List, Type
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel

from kscale.web.gen.api import (
    BodyAddListingListingsAddPost,
    CompletedKClipUploadRequest,
    KClipPartCompleted,
    NewListingResponse,
    SingleArtifactResponse,
    UploadArtifactResponse,
    UploadKClipRequest,
    UploadKClipResponse,
)
from kscale.web.utils import get_api_key, get_api_root

logger = logging.getLogger(__name__)


class KScaleStoreClient:
    def __init__(self, base_url: str = get_api_root()) -> None:
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {get_api_key()}"},
            timeout=httpx.Timeout(30.0),
        )

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

        response = await self.client.request(method, url, **kwargs)
        if response.is_error:
            logger.error(f"Error response from K-Scale Store: {response.text}")
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

    async def create_kclip(self, request: UploadKClipRequest) -> UploadKClipResponse:
        data = await self._request(
            "POST",
            "/kclips/create",
            data=request,
        )
        return UploadKClipResponse(**data)

    async def complete_kclip_upload(self, kclip_id: str, upload_id: str, parts: List[KClipPartCompleted]) -> None:
        await self._request(
            "POST",
            f"/kclips/{kclip_id}/complete",
            data=CompletedKClipUploadRequest(
                kclip_id=kclip_id,
                upload_id=upload_id,
                parts=parts,
            ),
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def __aenter__(self) -> "KScaleStoreClient":
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

"""Defines a base client for the K-Scale WWW API client."""

import logging
from types import TracebackType
from typing import Any, Self, Type
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel

from kscale.web.token import get_bearer_token
from kscale.web.utils import DEFAULT_UPLOAD_TIMEOUT, get_api_root

logger = logging.getLogger(__name__)


class BaseClient:
    def __init__(self, base_url: str | None = None, upload_timeout: float = DEFAULT_UPLOAD_TIMEOUT) -> None:
        self.base_url = get_api_root() if base_url is None else base_url
        self.upload_timeout = upload_timeout
        self._client: httpx.AsyncClient | None = None
        self._client_no_auth: httpx.AsyncClient | None = None

    async def get_client(self, *, auth: bool = True) -> httpx.AsyncClient:
        client = self._client if auth else self._client_no_auth
        if client is None:
            client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {await get_bearer_token()}"},
                timeout=httpx.Timeout(30.0),
            )
            if auth:
                self._client = client
            else:
                self._client_no_auth = client
        return client

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        auth: bool = True,
        params: dict[str, Any] | None = None,
        data: BaseModel | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = urljoin(self.base_url, endpoint)
        kwargs: dict[str, Any] = {"params": params}

        if data:
            kwargs["json"] = data.model_dump(exclude_unset=True)
        if files:
            kwargs["files"] = files

        client = await self.get_client(auth=auth)
        response = await client.request(method, url, **kwargs)

        if response.is_error:
            logger.error("Error response from K-Scale: %s", response.text)
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

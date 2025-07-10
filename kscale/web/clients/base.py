"""Defines a base client for the K-Scale WWW API client."""

import logging
import os
import sys
from types import TracebackType
from typing import Any, Mapping, Self, Type
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel

from kscale.web.utils import DEFAULT_UPLOAD_TIMEOUT, get_api_root

logger = logging.getLogger(__name__)

# This is the name of the API key header for the K-Scale WWW API.
HEADER_NAME = "x-kscale-api-key"


def verbose_error() -> bool:
    return os.environ.get("KSCALE_VERBOSE_ERROR", "0") == "1"


class BaseClient:
    def __init__(
        self,
        base_url: str | None = None,
        upload_timeout: float = DEFAULT_UPLOAD_TIMEOUT,
        use_cache: bool = True,
    ) -> None:
        self.base_url = get_api_root() if base_url is None else base_url
        self.upload_timeout = upload_timeout
        self.use_cache = use_cache
        self._client: httpx.AsyncClient | None = None
        self._client_no_auth: httpx.AsyncClient | None = None

    async def get_client(self, *, auth: bool = True) -> httpx.AsyncClient:
        client = self._client if auth else self._client_no_auth
        if client is None:
            headers: dict[str, str] = {}
            if auth:
                if "KSCALE_API_KEY" not in os.environ:
                    raise ValueError("KSCALE_API_KEY is not set! Obtain one here: https://kscale.dev/dashboard/keys")
                headers[HEADER_NAME] = os.environ["KSCALE_API_KEY"]

            client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
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
        data: BaseModel | dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        error_code_suggestions: dict[int, str] | None = None,
    ) -> dict[str, Any]:
        url = urljoin(self.base_url, endpoint)
        kwargs: dict[str, Any] = {}
        if params is not None:
            kwargs["params"] = params
        if data is not None:
            if isinstance(data, BaseModel):
                kwargs["json"] = data.model_dump(exclude_unset=True)
            else:
                kwargs["json"] = data
        if files:
            kwargs["files"] = files

        client = await self.get_client(auth=auth)
        response = await client.request(method, url, **kwargs)

        if response.is_error:
            error_code = response.status_code
            error_json = response.json()
            use_verbose_error = verbose_error()

            if not use_verbose_error:
                logger.info("Use KSCALE_VERBOSE_ERROR=1 to see the full error message")
                logger.info("If this persists, please create an issue here: https://github.com/kscalelabs/kscale")

            logger.error("Got error %d from the K-Scale API", error_code)
            if isinstance(error_json, Mapping):
                for key, value in error_json.items():
                    logger.error("  [%s] %s", key, value)
            else:
                logger.error("  %s", error_json)

            if error_code_suggestions is not None and error_code in error_code_suggestions:
                logger.error("Hint: %s", error_code_suggestions[error_code])

            if use_verbose_error:
                response.raise_for_status()
            else:
                sys.exit(1)

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

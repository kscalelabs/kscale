"""Defines a base client for the K-Scale WWW API client."""

import asyncio
import json
import logging
import secrets
import time
import webbrowser
from types import TracebackType
from typing import Any, Self, Type
from urllib.parse import urljoin

import aiohttp
import httpx
from aiohttp import web
from async_lru import alru_cache
from jwt import ExpiredSignatureError, PyJWKClient, decode as jwt_decode
from pydantic import BaseModel
from yarl import URL

from kscale.web.gen.api import OICDInfo
from kscale.web.utils import DEFAULT_UPLOAD_TIMEOUT, get_api_root, get_cache_dir

logger = logging.getLogger(__name__)

# This port matches the available port for the OAuth callback.
OAUTH_PORT = 16821


class OAuthCallback:
    def __init__(self) -> None:
        self.access_token: str | None = None
        self.app = web.Application()
        self.app.router.add_get("/token", self.handle_token)
        self.app.router.add_get("/callback", self.handle_callback)

    async def handle_token(self, request: web.Request) -> web.Response:
        """Handle the token extraction."""
        self.access_token = request.query.get("access_token")
        return web.Response(text="OK")

    async def handle_callback(self, request: web.Request) -> web.Response:
        """Handle the OAuth callback with token in URL fragment."""
        return web.Response(
            text="""
                <!DOCTYPE html>
                <html lang="en">

                <head>
                    <meta charset="UTF-8">
                    <meta http-equiv="X-UA-Compatible" content="IE=edge">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Authentication successful</title>
                    <style>
                        body {
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            min-height: 100vh;
                            margin: 0;
                            text-align: center;
                        }
                        #content {
                            padding: 20px;
                        }
                        #closeNotification {
                            display: none;
                            padding: 10px 20px;
                            margin-top: 20px;
                            cursor: pointer;
                            margin-left: auto;
                            margin-right: auto;
                        }
                    </style>
                </head>

                <body>
                    <div id="content">
                        <h1>Authentication successful!</h1>
                        <p>This window will close in <span id="countdown">3</span> seconds.</p>
                        <p id="closeNotification" onclick="window.close()">Please close this window manually.</p>
                    </div>
                    <script>
                        const params = new URLSearchParams(window.location.hash.substring(1));
                        const token = params.get('access_token');
                        if (token) {
                            fetch('/token?access_token=' + token);
                        }

                        let timeLeft = 3;
                        const countdownElement = document.getElementById('countdown');
                        const closeNotification = document.getElementById('closeNotification');
                        const timer = setInterval(() => {
                            timeLeft--;
                            countdownElement.textContent = timeLeft;
                            if (timeLeft <= 0) {
                                clearInterval(timer);
                                window.close();
                                setTimeout(() => {
                                    closeNotification.style.display = 'block';
                                }, 500);
                            }
                        }, 1000);
                    </script>
                </body>
                </html>
            """,
            content_type="text/html",
        )


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

    @alru_cache
    async def _get_oicd_info(self) -> OICDInfo:
        cache_path = get_cache_dir() / "oicd_info.json"
        if self.use_cache and cache_path.exists():
            with open(cache_path, "r") as f:
                return OICDInfo(**json.load(f))
        data = await self._request("GET", "/auth/oicd", auth=False)
        if self.use_cache:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump(data, f)
        return OICDInfo(**data)

    @alru_cache
    async def _get_oicd_metadata(self) -> dict:
        """Returns the OpenID Connect server configuration.

        Returns:
            The OpenID Connect server configuration.
        """
        cache_path = get_cache_dir() / "oicd_metadata.json"
        if self.use_cache and cache_path.exists():
            with open(cache_path, "r") as f:
                return json.load(f)
        oicd_info = await self._get_oicd_info()
        oicd_config_url = f"{oicd_info.authority}/.well-known/openid-configuration"
        async with aiohttp.ClientSession() as session:
            async with session.get(oicd_config_url) as response:
                metadata = await response.json()
        if self.use_cache:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump(metadata, f, indent=2)
            logger.info("Cached OpenID Connect metadata to %s", cache_path)
        return metadata

    async def _get_bearer_token(self) -> str:
        """Get a bearer token using the OAuth2 implicit flow.

        Returns:
            A bearer token to use with the K-Scale WWW API.
        """
        oicd_info = await self._get_oicd_info()
        metadata = await self._get_oicd_metadata()
        auth_endpoint = metadata["authorization_endpoint"]
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)

        auth_url = str(
            URL(auth_endpoint).with_query(
                {
                    "response_type": "token",
                    "redirect_uri": f"http://localhost:{OAUTH_PORT}/callback",
                    "state": state,
                    "nonce": nonce,
                    "scope": "openid profile email",
                    "client_id": oicd_info.client_id,
                }
            )
        )

        # Start local server to receive callback
        callback_handler = OAuthCallback()
        runner = web.AppRunner(callback_handler.app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", OAUTH_PORT)

        try:
            await site.start()
        except OSError as e:
            raise OSError(
                f"The command line interface requires access to local port {OAUTH_PORT} in order to authenticate with "
                "OpenID Connect. Please ensure that no other application is using this port."
            ) from e

        # Open browser for user authentication
        webbrowser.open(auth_url)

        # Wait for the callback with timeout
        try:
            start_time = time.time()
            while callback_handler.access_token is None:
                if time.time() - start_time > 30:
                    raise TimeoutError("Authentication timed out after 30 seconds")
                await asyncio.sleep(0.1)

            return callback_handler.access_token
        finally:
            await runner.cleanup()

    @alru_cache
    async def _get_jwk_client(self) -> PyJWKClient:
        """Returns a JWK client for the OpenID Connect server."""
        oicd_info = await self._get_oicd_info()
        jwks_uri = f"{oicd_info.authority}/.well-known/jwks.json"
        return PyJWKClient(uri=jwks_uri)

    async def _is_token_expired(self, token: str) -> bool:
        """Check if a token is expired."""
        jwk_client = await self._get_jwk_client()
        signing_key = jwk_client.get_signing_key_from_jwt(token)

        try:
            claims = jwt_decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
        except ExpiredSignatureError:
            return True

        return claims["exp"] < time.time()

    @alru_cache
    async def get_bearer_token(self) -> str:
        """Get a bearer token from OpenID Connect.

        Returns:
            A bearer token to use with the K-Scale WWW API.
        """
        cache_path = get_cache_dir() / "bearer_token.txt"
        if self.use_cache and cache_path.exists():
            token = cache_path.read_text()
            if not await self._is_token_expired(token):
                return token
        token = await self._get_bearer_token()
        if self.use_cache:
            cache_path.write_text(token)
            cache_path.chmod(0o600)
        return token

    async def get_client(self, *, auth: bool = True) -> httpx.AsyncClient:
        client = self._client if auth else self._client_no_auth
        if client is None:
            client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {await self.get_bearer_token()}"} if auth else None,
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
    ) -> dict[str, Any]:
        url = urljoin(self.base_url, endpoint)
        kwargs: dict[str, Any] = {"params": params}

        if data:
            if isinstance(data, BaseModel):
                kwargs["json"] = data.model_dump(exclude_unset=True)
            else:
                kwargs["json"] = data
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

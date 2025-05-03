"""Defines a base client for the K-Scale WWW API client."""

import asyncio
import json
import logging
import os
import secrets
import sys
import time
import webbrowser
from types import TracebackType
from typing import Any, Mapping, Self, Type
from urllib.parse import urljoin

import aiohttp
import httpx
from aiohttp import web
from async_lru import alru_cache
from jwt import ExpiredSignatureError, PyJWKClient, decode as jwt_decode
from pydantic import BaseModel
from yarl import URL

from kscale.web.gen.api import OICDInfo
from kscale.web.utils import DEFAULT_UPLOAD_TIMEOUT, get_api_root, get_auth_dir

logger = logging.getLogger(__name__)

# This port matches the available port for the OAuth callback.
OAUTH_PORT = 16821

# This is the name of the API key header for the K-Scale WWW API.
HEADER_NAME = "x-kscale-api-key"


def verbose_error() -> bool:
    return os.environ.get("KSCALE_VERBOSE_ERROR", "0") == "1"


class OAuthCallback:
    def __init__(self) -> None:
        self.token_type: str | None = None
        self.access_token: str | None = None
        self.id_token: str | None = None
        self.state: str | None = None
        self.expires_in: str | None = None
        self.app = web.Application()
        self.app.router.add_get("/token", self.handle_token)
        self.app.router.add_get("/callback", self.handle_callback)

    async def handle_token(self, request: web.Request) -> web.Response:
        """Handle the token extraction."""
        self.token_type = request.query.get("token_type")
        self.access_token = request.query.get("access_token")
        self.id_token = request.query.get("id_token")
        self.state = request.query.get("state")
        self.expires_in = request.query.get("expires_in")
        return web.Response(text="OK")

    async def handle_callback(self, request: web.Request) -> web.Response:
        """Handle the OAuth callback with token in URL fragment."""
        return web.Response(
            text="""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Authentication successful</title>
                    <style>
                        body {
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            min-height: 100vh;
                            margin: 0;
                            background: #f5f5f5;
                            color: #333;
                        }
                        .container {
                            background: white;
                            padding: 2rem;
                            border-radius: 8px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                            max-width: 600px;
                            width: 90%;
                        }
                        h1 {
                            color: #2c3e50;
                            margin-bottom: 1rem;
                        }
                        .token-info {
                            background: #f8f9fa;
                            border: 1px solid #dee2e6;
                            border-radius: 4px;
                            padding: 1rem;
                            margin: 1rem 0;
                            word-break: break-all;
                        }
                        .token-label {
                            font-weight: bold;
                            color: #6c757d;
                            margin-bottom: 0.5rem;
                        }
                        .success-icon {
                            color: #28a745;
                            font-size: 48px;
                            margin-bottom: 1rem;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="success-icon">✓</div>
                        <h1>Authentication successful!</h1>
                        <p>Your authentication tokens are shown below. You can now close this window.</p>

                        <div class="token-info">
                            <div class="token-label">Access Token:</div>
                            <div id="accessTokenDisplay"></div>
                        </div>

                        <div class="token-info">
                            <div class="token-label">ID Token:</div>
                            <div id="idTokenDisplay"></div>
                        </div>
                    </div>

                    <script>
                        const params = new URLSearchParams(window.location.hash.substring(1));
                        const tokenType = params.get('token_type');
                        const accessToken = params.get('access_token');
                        const idToken = params.get('id_token');
                        const state = params.get('state');
                        const expiresIn = params.get('expires_in');

                        // Display tokens
                        document.getElementById('accessTokenDisplay').textContent = accessToken || 'Not provided';
                        document.getElementById('idTokenDisplay').textContent = idToken || 'Not provided';

                        if (accessToken) {
                            const tokenUrl = new URL(window.location.href);
                            tokenUrl.pathname = '/token';
                            tokenUrl.searchParams.set('access_token', accessToken);
                            tokenUrl.searchParams.set('token_type', tokenType);
                            tokenUrl.searchParams.set('id_token', idToken);
                            tokenUrl.searchParams.set('state', state);
                            tokenUrl.searchParams.set('expires_in', expiresIn);
                            fetch(tokenUrl.toString());
                        }
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
        cache_path = get_auth_dir() / "oicd_info.json"
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
        cache_path = get_auth_dir() / "oicd_metadata.json"
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
        # Check if we are in a headless environment.
        error_message = (
            "Cannot perform browser-based authentication in a headless environment. "
            "Please use 'kscale user key' to generate an API key locally and set "
            "the KSCALE_API_KEY environment variable instead."
        )
        try:
            if not webbrowser.get().name != "null":
                raise RuntimeError(error_message)
        except webbrowser.Error:
            raise RuntimeError(error_message)

        oicd_info = await self._get_oicd_info()
        metadata = await self._get_oicd_metadata()
        auth_endpoint = metadata["authorization_endpoint"]

        # Use the cached state and nonce if available, otherwise generate.
        state_file = get_auth_dir() / "oauth_state.json"
        state: str | None = None
        nonce: str | None = None
        if state_file.exists():
            with open(state_file, "r") as f:
                state_data = json.load(f)
                state = state_data.get("state")
                nonce = state_data.get("nonce")
        if state is None:
            state = secrets.token_urlsafe(32)
        if nonce is None:
            nonce = secrets.token_urlsafe(32)

        # Change /oauth2/authorize to /login to use the login endpoint.
        auth_endpoint = auth_endpoint.replace("/oauth2/authorize", "/login")

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

            # Save the state and nonce to the cache.
            state = callback_handler.state
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(json.dumps({"state": state, "nonce": nonce}))

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
        cache_path = get_auth_dir() / "bearer_token.txt"
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
            headers: dict[str, str] = {}
            if auth:
                if "KSCALE_API_KEY" in os.environ:
                    headers[HEADER_NAME] = os.environ["KSCALE_API_KEY"]
                else:
                    headers["Authorization"] = f"Bearer {await self.get_bearer_token()}"

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

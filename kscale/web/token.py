"""Command-line interface example for getting a bearer token from OpenID Connect."""

import asyncio
import functools
import json
import logging
import secrets
import time
import webbrowser

import aiohttp
from aiohttp import web
from jwt import ExpiredSignatureError, PyJWKClient, decode as jwt_decode
from yarl import URL

from kscale.conf import Settings
from kscale.web.utils import get_cache_dir

logger = logging.getLogger(__name__)


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


def get_oicd_config_url() -> str:
    """Returns the URL for the OpenID Connect server configuration."""
    base_url = Settings.load().www.oicd_url_base
    return f"{base_url}/.well-known/openid-configuration"


@functools.lru_cache
async def get_oicd_metadata() -> dict:
    """Returns the OpenID Connect server configuration."""
    cache_path = get_cache_dir() / "oicd_metadata.json"
    if cache_path.exists():
        with open(cache_path, "r") as f:
            return json.load(f)
    oicd_config_url = get_oicd_config_url()
    async with aiohttp.ClientSession() as session:
        async with session.get(oicd_config_url) as response:
            metadata = await response.json()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Cached OpenID Connect metadata to %s", cache_path)
    return metadata


def get_oicd_jwks_url() -> str:
    """Returns the URL for the JWKS for the OpenID Connect server."""
    base_url = Settings.load().www.oicd_url_base
    return f"{base_url}/.well-known/jwks.json"


@functools.lru_cache
def get_jwk_client() -> PyJWKClient:
    """Returns a JWK client for the OpenID Connect server."""
    return PyJWKClient(get_oicd_jwks_url())


async def _get_bearer_token() -> str:
    """Get a bearer token using the OAuth2 implicit flow.

    Returns:
        A bearer token to use with the K-Scale WWW API.
    """
    metadata = await get_oicd_metadata()
    auth_endpoint = metadata["authorization_endpoint"]
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)

    auth_url = str(
        URL(auth_endpoint).with_query(
            {
                "response_type": "token",
                "redirect_uri": "http://localhost:8080/callback",
                "state": state,
                "nonce": nonce,
                "scope": "openid profile email",
                "client_id": "5lu9h7nhtf6dvlunpodjr9qil5",
            }
        )
    )

    # Start local server to receive callback
    callback_handler = OAuthCallback()
    runner = web.AppRunner(callback_handler.app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8080)

    try:
        await site.start()
    except OSError as e:
        raise OSError(
            "The command line interface requires access to local port 8080 in order to authenticate with "
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


def _is_token_expired(token: str) -> bool:
    """Check if a token is expired."""
    jwk_client = get_jwk_client()
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


@functools.lru_cache
async def get_bearer_token(
    use_cache: bool = True,
) -> str:
    """Get a bearer token from OpenID Connect.

    Args:
        use_cache: Whether to use the cached bearer token if it exists.

    Returns:
        A bearer token to use with the K-Scale WWW API.
    """
    cache_path = get_cache_dir() / "bearer_token.txt"
    if use_cache and cache_path.exists():
        token = cache_path.read_text()
        if not _is_token_expired(token):
            return token
    token = await _get_bearer_token()
    if use_cache:
        cache_path.write_text(token)
    return token

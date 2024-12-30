"""Command-line interface example for getting a bearer token from OpenID Connect."""

import asyncio
import logging
import secrets
import time
import webbrowser

import aiohttp
import click
from aiohttp import web
from yarl import URL

from kscale.utils.cli import coro

logger = logging.getLogger(__name__)

SERVER_METADATA_URL = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_dqtJl1Iew/.well-known/openid-configuration"


class OAuthCallback:
    def __init__(self) -> None:
        self.access_token = None
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
                </head>

                <body>
                    <h1>Authentication successful!</h1>
                    <p>This window will close in <span id="countdown">3</span> seconds.</p>
                    <script>
                        const params = new URLSearchParams(window.location.hash.substring(1));
                        const token = params.get('access_token');
                        if (token) {
                            fetch('/token?access_token=' + token);
                        }

                        let timeLeft = 3;
                        const countdownElement = document.getElementById('countdown');
                        const timer = setInterval(() => {
                            timeLeft--;
                            countdownElement.textContent = timeLeft;
                            if (timeLeft <= 0) {
                                clearInterval(timer);
                                window.close();
                            }
                        }, 1000);
                    </script>
                </body>

                </html>
            """,
            content_type="text/html",
        )


async def get_bearer_token(redirect_uri: str = "http://localhost:8080/callback") -> str:
    """Get a bearer token using the OAuth2 implicit flow."""
    async with aiohttp.ClientSession() as session:
        # Get the OpenID Connect metadata
        async with session.get(SERVER_METADATA_URL) as response:
            metadata = await response.json()

        auth_endpoint = metadata["authorization_endpoint"]
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)

        auth_url = str(
            URL(auth_endpoint).with_query(
                {
                    "response_type": "token",
                    "redirect_uri": redirect_uri,
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
        await site.start()

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


@click.group()
def cli() -> None:
    """K-Scale OpenID Connect CLI tool."""
    pass


@cli.command()
@coro
async def get() -> None:
    """Get a bearer token from OpenID Connect."""
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    try:
        token = await get_bearer_token()
        logger.info("Bearer token: %s", token)
    except Exception:
        logger.exception("Error getting bearer token")


if __name__ == "__main__":
    cli()

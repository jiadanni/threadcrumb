"""
Slack OAuth 2.0 authentication module.
"""

import json
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any
import http.server
import socketserver
from slack_sdk import WebClient
from slack_sdk.oauth import AuthorizeUrlGenerator


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """Handle OAuth callback from Slack."""

    auth_code: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):
        """Handle GET request from OAuth callback."""
        if self.path.startswith("/callback"):
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            if "code" in params:
                OAuthCallbackHandler.auth_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                    <html>
                    <body>
                        <h1>Authentication Successful!</h1>
                        <p>You can close this window and return to the terminal.</p>
                    </body>
                    </html>
                """)
            elif "error" in params:
                OAuthCallbackHandler.error = params["error"][0]
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(f"""
                    <html>
                    <body>
                        <h1>Authentication Failed</h1>
                        <p>Error: {OAuthCallbackHandler.error}</p>
                    </body>
                    </html>
                """.encode())

    def log_message(self, format, *args):
        """Suppress log messages."""
        pass


class SlackAuthenticator:
    """Handle Slack OAuth 2.0 authentication."""

    # Required OAuth scopes for the application
    REQUIRED_SCOPES = [
        "channels:history",
        "channels:read",
        "groups:history",
        "groups:read",
        "users:read",
        "team:read",
        "files:read",
    ]

    def __init__(self, client_id: str, client_secret: str, redirect_port: int = 8000):
        """
        Initialize the authenticator.

        Args:
            client_id: Slack app client ID
            client_secret: Slack app client secret
            redirect_port: Port for OAuth callback server
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_port = redirect_port
        self.redirect_uri = f"http://localhost:{redirect_port}/callback"

    def get_authorization_url(self, scopes: Optional[list] = None) -> str:
        """
        Generate OAuth authorization URL.

        Args:
            scopes: List of OAuth scopes (defaults to REQUIRED_SCOPES)

        Returns:
            Authorization URL
        """
        scopes = scopes or self.REQUIRED_SCOPES
        authorize_url_generator = AuthorizeUrlGenerator(
            client_id=self.client_id,
            scopes=scopes,
            redirect_uri=self.redirect_uri
        )
        return authorize_url_generator.generate()

    def start_callback_server(self) -> Optional[str]:
        """
        Start local server to receive OAuth callback.

        Returns:
            Authorization code or None if failed
        """
        OAuthCallbackHandler.auth_code = None
        OAuthCallbackHandler.error = None

        with socketserver.TCPServer(("", self.redirect_port), OAuthCallbackHandler) as httpd:
            # Handle only one request
            httpd.handle_request()

        if OAuthCallbackHandler.error:
            raise Exception(f"OAuth error: {OAuthCallbackHandler.error}")

        return OAuthCallbackHandler.auth_code

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Token response with access_token, team_id, etc.
        """
        client = WebClient()
        response = client.oauth_v2_access(
            client_id=self.client_id,
            client_secret=self.client_secret,
            code=code,
            redirect_uri=self.redirect_uri
        )

        if not response["ok"]:
            raise Exception(f"Failed to exchange code: {response.get('error', 'Unknown error')}")

        return response.data

    def authenticate(self) -> Dict[str, Any]:
        """
        Perform full OAuth flow.

        Returns:
            Token data including access_token
        """
        # Generate authorization URL
        auth_url = self.get_authorization_url()

        print("Opening browser for Slack authentication...")
        print(f"If the browser doesn't open, visit: {auth_url}")

        # Open browser
        webbrowser.open(auth_url)

        # Start callback server
        print("Waiting for authorization...")
        code = self.start_callback_server()

        if not code:
            raise Exception("Failed to receive authorization code")

        # Exchange code for token
        print("Exchanging code for access token...")
        token_data = self.exchange_code_for_token(code)

        return token_data

    @staticmethod
    def save_token(token_data: Dict[str, Any], token_path: Path) -> None:
        """
        Save token data to file.

        Args:
            token_data: Token response from OAuth
            token_path: Path to save token file
        """
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, 'w') as f:
            json.dump(token_data, f, indent=2)

        # Set restrictive permissions
        token_path.chmod(0o600)

    @staticmethod
    def load_token(token_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load token data from file.

        Args:
            token_path: Path to token file

        Returns:
            Token data or None if file doesn't exist
        """
        if not token_path.exists():
            return None

        with open(token_path, 'r') as f:
            return json.load(f)

    def verify_token(self, access_token: str) -> bool:
        """
        Verify that an access token is valid.

        Args:
            access_token: Slack access token

        Returns:
            True if token is valid
        """
        try:
            client = WebClient(token=access_token)
            response = client.auth_test()
            return response["ok"]
        except Exception:
            return False

"""
oauth.py — Google OAuth (installed-app/loopback) credential provider for the
YouTube Data API (★ load-bearing).

Owns three things and nothing else: running the browser-based "installed
app" OAuth flow, persisting the resulting token atomically at 0600, and
refreshing an expired token. It is NOT a handler in the fallback sense (see
CLAUDE.md's three-layer architecture) — it is a small credential source that
``handlers/youtube_api_handler.py`` consumes at ``_ensure_initialized()``
time, and that a later CLI's ``login``/``status`` commands drive directly.

Read-only scope by design: ``youtube.readonly`` covers everything this
toolkit does (my-channel/playlists/subscriptions via ``mine=True``, plus
every existing read call) without ever requesting write/manage access.

VERIFY-LIVE: the login flow (``run_login_flow`` / ``InstalledAppFlow.
run_local_server``) has NOT been exercised against a real Google OAuth Client
— no Desktop-app client registration exists yet for this project. Only the
mocked/unit-tested path has been run. Confirm against a real
``client_secrets.json`` before relying on this in production.

Reads: google_auth_oauthlib.flow.InstalledAppFlow · google.oauth2.credentials.Credentials ·
google.auth.transport.requests.Request
"""

from __future__ import annotations

import json
import os
from pathlib import Path


# Read-only scope: covers video/channel/playlist/subscription reads,
# including the ``mine=True`` "my own account" variants this toolkit adds.
# Deliberately NOT requesting a write/manage scope — this toolkit never
# posts, uploads, or edits on the user's behalf.
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

_DEFAULT_TOKEN_PATH = "~/.youtube-cli/token.json"


class YouTubeOAuthError(RuntimeError):
    """Raised for OAuth setup/login/refresh failures that need a human step.

    Covers: missing ``YOUTUBE_OAUTH_CLIENT_SECRETS`` at login time, and a
    refresh that fails because the token was revoked/expired beyond repair
    (the caller should send the user back through ``run_login_flow``).
    """


def token_path() -> Path:
    """Resolve the OAuth token file path.

    Reads ``YOUTUBE_OAUTH_TOKEN_PATH`` (defaults to ``~/.youtube-cli/token.json``),
    matching how ``youtube_api_handler.py`` already reads ``YOUTUBE_API_KEY``
    from the environment. Always returns an expanded, resolved absolute path.
    """
    raw = os.getenv("YOUTUBE_OAUTH_TOKEN_PATH", _DEFAULT_TOKEN_PATH)
    return Path(raw).expanduser().resolve()


def save_credentials(creds) -> None:
    """Persist ``creds`` to :func:`token_path` atomically at 0600.

    Atomic write (temp file + chmod 0600 *before* rename), mirroring the
    sibling spotify-cli's ``session.py`` (itself copied from splice-cli's
    ``mcp_session.py``): write-then-chmod leaves a world-readable window, and
    a mid-write crash leaves a corrupt file — OAuth tokens tolerate neither.
    """
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(creds.to_json())
    tmp.chmod(0o600)  # OAuth token — user-only, set BEFORE the rename
    os.replace(tmp, path)  # atomic on POSIX — no partial-file/world-readable window


def load_credentials():
    """Load persisted OAuth credentials, refreshing if expired.

    Returns:
        A valid ``google.oauth2.credentials.Credentials`` instance, or
        ``None`` if no token file exists (not logged in) or the token file
        is present but corrupt/unreadable (treated the same as "not logged
        in" rather than crashing the caller).

    Raises:
        YouTubeOAuthError: if a refresh is attempted (token expired, refresh
            token present) but fails — e.g. the grant was revoked on Google's
            side. The caller should send the user back to ``run_login_flow``.
    """
    from google.oauth2.credentials import Credentials

    path = token_path()
    if not path.exists():
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(path), SCOPES)
    except (ValueError, json.JSONDecodeError, OSError):
        # Corrupt/unreadable token file: treat as "not logged in", don't crash.
        return None

    if creds and creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request

        try:
            creds.refresh(Request())
        except Exception as e:
            raise YouTubeOAuthError(
                f"YouTube OAuth token refresh failed (it may have been revoked). "
                f"Run `youtube login` again. Details: {e}"
            ) from e
        save_credentials(creds)

    return creds


def run_login_flow():
    """Run the interactive Google OAuth "installed app" (loopback) flow.

    Reads ``YOUTUBE_OAUTH_CLIENT_SECRETS`` for the path to a Desktop-app
    OAuth client JSON downloaded from Google Cloud Console, opens a browser
    for the user to authorize, and persists the resulting token via
    :func:`save_credentials`.

    VERIFY-LIVE: not exercised against a real Google OAuth Client — see the
    module docstring.

    Returns:
        The authorized ``Credentials``.

    Raises:
        YouTubeOAuthError: if ``YOUTUBE_OAUTH_CLIENT_SECRETS`` is unset or
            does not point at a readable file.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    secrets_path = os.getenv("YOUTUBE_OAUTH_CLIENT_SECRETS")
    if not secrets_path:
        raise YouTubeOAuthError(
            "YOUTUBE_OAUTH_CLIENT_SECRETS is not set. To log in, register an "
            "OAuth Client ID of type 'Desktop app' in Google Cloud Console "
            "(APIs & Services -> Credentials), download its client_secrets.json, "
            "and set YOUTUBE_OAUTH_CLIENT_SECRETS to its path."
        )

    if not os.path.isfile(secrets_path):
        raise YouTubeOAuthError(
            f"YOUTUBE_OAUTH_CLIENT_SECRETS points at a file that doesn't exist: "
            f"{secrets_path}"
        )

    flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
    creds = flow.run_local_server(port=0)

    save_credentials(creds)
    return creds


def logged_in() -> bool:
    """Whether a usable OAuth session exists (token file present and valid/refreshable)."""
    return load_credentials() is not None

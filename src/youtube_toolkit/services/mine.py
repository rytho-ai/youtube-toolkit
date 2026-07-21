"""
mine.py — OAuth "current user" domain service.

Holds login/status plus the CURRENT (logged-in) user's own channel/
playlists/subscriptions, descended out of the same three-layer shape as
every other service (see CLAUDE.md): `self._toolkit` back-ref, methods call
`self._toolkit.youtube_api.<method>` directly. Unlike other services these
are OAuth-only, single-source calls (an API key structurally cannot answer
"what's MY channel") — there is no pytubefix/yt-dlp fallback for "my
account", so `run_with_fallback` is intentionally NOT used here.

Reads: youtube_toolkit.api.YouTubeToolkit (back-ref) · youtube_toolkit.oauth
(login flow + status) · handlers.youtube_api_handler (the `mine=True` calls,
reached via the toolkit back-ref, never imported directly)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .. import oauth


class MineService:
    def __init__(self, toolkit):
        self._toolkit = toolkit

    def login(self):
        """Run the interactive OAuth login flow and persist the token.

        After a successful login, reset the API handler's cached
        initialization state so the *next* handler call re-runs credential
        selection and picks up the freshly-saved OAuth token — otherwise a
        handler that was already initialized (e.g. API-key-only, earlier in
        the same process) would keep using its stale `_youtube` client.

        Returns:
            The resolved token path (str) on success.
        """
        oauth.run_login_flow()

        # Force the next handler call to rebuild its client and re-select
        # credentials (see `_ensure_initialized`'s OAuth-preferred order).
        self._toolkit.youtube_api._initialized = False
        self._toolkit.youtube_api._youtube = None

        return str(oauth.token_path())

    def status(self) -> Dict[str, Any]:
        """Report login state. Never includes token contents."""
        return {
            'logged_in': oauth.logged_in(),
            'token_path': str(oauth.token_path()),
        }

    def channel(self) -> Dict[str, Any]:
        return self._toolkit.youtube_api.get_my_channel()

    def playlists(self, max_results: int = 25,
                  page_token: Optional[str] = None) -> Dict[str, Any]:
        return self._toolkit.youtube_api.get_my_playlists(
            max_results=max_results, page_token=page_token
        )

    def subscriptions(self, max_results: int = 25, order: str = 'alphabetical',
                      page_token: Optional[str] = None) -> Dict[str, Any]:
        return self._toolkit.youtube_api.get_my_subscriptions(
            max_results=max_results, order=order, page_token=page_token
        )

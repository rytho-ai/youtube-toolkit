"""
Tests for OAuth ("mine") wiring across all three layers:

- handlers/youtube_api_handler.py: credential selection (`_ensure_initialized`)
  and the `mine=True` methods (`get_my_channel`, `get_my_playlists`,
  `get_my_subscriptions`), including the `YouTubeAuthRequiredError` guard.
- services/mine.py: `MineService` (thin pass-through + login's handler reset).
- sub_apis.py / api.py: `toolkit.mine` is wired and reaches the service.

No network, no real OAuth — mocks at the handler/Google-client boundary,
matching the style of tests/test_bug_fixes.py::TestYouTubeAPIHandlerRedaction.
"""

from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# Credential selection (_ensure_initialized)
# =============================================================================

class TestCredentialSelection:
    def _handler(self):
        from youtube_toolkit.handlers.youtube_api_handler import YouTubeAPIHandler
        return YouTubeAPIHandler()

    def test_prefers_oauth_when_token_available(self, monkeypatch):
        handler = self._handler()
        fake_creds = MagicMock()

        with patch("youtube_toolkit.handlers.youtube_api_handler.oauth.load_credentials",
                   return_value=fake_creds):
            with patch("googleapiclient.discovery.build") as mock_build:
                mock_build.return_value = MagicMock()
                handler._ensure_initialized()

        mock_build.assert_called_once()
        assert mock_build.call_args.args == ("youtube", "v3")
        # Credentials now arrive wrapped in the policy transport (AuthorizedHttp)
        assert mock_build.call_args.kwargs["http"].credentials is fake_creds
        assert handler._auth_mode == "oauth"
        assert handler._initialized is True

    def test_falls_back_to_api_key_when_no_oauth(self, monkeypatch):
        handler = self._handler()
        monkeypatch.setenv("YOUTUBE_API_KEY", "SECRET_KEY")

        with patch("youtube_toolkit.handlers.youtube_api_handler.oauth.load_credentials",
                   return_value=None):
            with patch("googleapiclient.discovery.build") as mock_build:
                mock_build.return_value = MagicMock()
                handler._ensure_initialized()

        mock_build.assert_called_once()
        assert mock_build.call_args.args == ("youtube", "v3")
        assert mock_build.call_args.kwargs["developerKey"] == "SECRET_KEY"
        assert handler._auth_mode == "apikey"
        assert handler._initialized is True

    def test_raises_when_neither_oauth_nor_api_key(self, monkeypatch):
        handler = self._handler()
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)

        with patch("youtube_toolkit.handlers.youtube_api_handler.oauth.load_credentials",
                   return_value=None):
            with pytest.raises(ValueError, match="youtube login"):
                handler._ensure_initialized()

        assert handler._initialized is False

    def test_oauth_token_takes_priority_over_api_key(self, monkeypatch):
        """Even with YOUTUBE_API_KEY set, a valid OAuth token wins."""
        handler = self._handler()
        monkeypatch.setenv("YOUTUBE_API_KEY", "SECRET_KEY")
        fake_creds = MagicMock()

        with patch("youtube_toolkit.handlers.youtube_api_handler.oauth.load_credentials",
                   return_value=fake_creds):
            with patch("googleapiclient.discovery.build") as mock_build:
                mock_build.return_value = MagicMock()
                handler._ensure_initialized()

        mock_build.assert_called_once()
        assert mock_build.call_args.kwargs["http"].credentials is fake_creds
        assert handler._auth_mode == "oauth"

    def test_refresh_failure_propagates_as_oauth_error(self):
        """A YouTubeOAuthError from load_credentials (revoked refresh token)
        must propagate un-wrapped, not get swallowed into a generic RuntimeError."""
        from youtube_toolkit import oauth

        handler = self._handler()

        with patch("youtube_toolkit.handlers.youtube_api_handler.oauth.load_credentials",
                   side_effect=oauth.YouTubeOAuthError("revoked")):
            with pytest.raises(oauth.YouTubeOAuthError):
                handler._ensure_initialized()


# =============================================================================
# mine=True methods — auth guard (no network on the unauthenticated path)
# =============================================================================

class TestAuthRequiredGuard:
    def _apikey_handler(self):
        from youtube_toolkit.handlers.youtube_api_handler import YouTubeAPIHandler
        handler = YouTubeAPIHandler()
        handler._initialized = True
        handler._auth_mode = "apikey"
        # A MagicMock that blows up if `.channels()`/etc were actually called,
        # proving the guard fires before any network call.
        handler._youtube = MagicMock()
        handler._youtube.channels.side_effect = AssertionError("network call reached!")
        handler._youtube.playlists.side_effect = AssertionError("network call reached!")
        handler._youtube.subscriptions.side_effect = AssertionError("network call reached!")
        return handler

    def test_get_my_channel_requires_oauth(self):
        from youtube_toolkit.handlers.youtube_api_handler import YouTubeAuthRequiredError

        handler = self._apikey_handler()
        with pytest.raises(YouTubeAuthRequiredError):
            handler.get_my_channel()

    def test_get_my_playlists_requires_oauth(self):
        from youtube_toolkit.handlers.youtube_api_handler import YouTubeAuthRequiredError

        handler = self._apikey_handler()
        with pytest.raises(YouTubeAuthRequiredError):
            handler.get_my_playlists()

    def test_get_my_subscriptions_requires_oauth(self):
        from youtube_toolkit.handlers.youtube_api_handler import YouTubeAuthRequiredError

        handler = self._apikey_handler()
        with pytest.raises(YouTubeAuthRequiredError):
            handler.get_my_subscriptions()


# =============================================================================
# mine=True methods — response mapping (OAuth mode, mocked Google client)
# =============================================================================

class TestMineMethodsMapping:
    def _oauth_handler(self):
        from youtube_toolkit.handlers.youtube_api_handler import YouTubeAPIHandler
        handler = YouTubeAPIHandler()
        handler._initialized = True
        handler._auth_mode = "oauth"
        handler._youtube = MagicMock()
        return handler

    def test_get_my_channel_maps_response(self):
        handler = self._oauth_handler()
        handler._youtube.channels.return_value.list.return_value.execute.return_value = {
            "items": [{
                "id": "UCmyChannel",
                "snippet": {"title": "My Channel", "description": "desc"},
                "statistics": {"subscriberCount": "42", "viewCount": "100", "videoCount": "5"},
                "contentDetails": {},
                "brandingSettings": {},
                "status": {"privacyStatus": "public"},
            }]
        }

        result = handler.get_my_channel()

        handler._youtube.channels.return_value.list.assert_called_once_with(
            part="snippet,contentDetails,statistics,brandingSettings,status",
            mine=True,
        )
        assert result["channel_id"] == "UCmyChannel"
        assert result["title"] == "My Channel"
        assert result["subscriber_count"] == 42
        assert result["privacy_status"] == "public"

    def test_get_my_channel_returns_none_when_no_items(self):
        handler = self._oauth_handler()
        handler._youtube.channels.return_value.list.return_value.execute.return_value = {"items": []}

        assert handler.get_my_channel() is None

    def test_get_my_channel_shares_mapper_with_get_channel_info(self):
        """get_channel_info and get_my_channel must map identically —
        they're both backed by `_map_channel_item`."""
        handler = self._oauth_handler()
        item = {
            "id": "UCshared",
            "snippet": {"title": "Shared", "description": ""},
            "statistics": {"subscriberCount": "1", "viewCount": "2", "videoCount": "3"},
            "contentDetails": {},
            "brandingSettings": {},
            "status": {},
        }
        handler._youtube.channels.return_value.list.return_value.execute.return_value = {
            "items": [item]
        }
        via_mine = handler.get_my_channel()

        handler2 = self._oauth_handler()
        handler2._youtube.channels.return_value.list.return_value.execute.return_value = {
            "items": [item]
        }
        via_explicit = handler2.get_channel_info(channel_id="UCshared")

        assert via_mine == via_explicit

    def test_get_my_playlists_maps_response(self):
        handler = self._oauth_handler()
        handler._youtube.playlists.return_value.list.return_value.execute.return_value = {
            "items": [{
                "id": "PLmine",
                "snippet": {
                    "title": "My Playlist",
                    "description": "x" * 300,
                    "publishedAt": "2024-01-01T00:00:00Z",
                    "thumbnails": {"default": {"url": "http://thumb"}},
                },
                "contentDetails": {"itemCount": 7},
                "status": {"privacyStatus": "private"},
            }],
            "nextPageToken": "next123",
        }

        result = handler.get_my_playlists(max_results=10)

        handler._youtube.playlists.return_value.list.assert_called_once_with(
            part="snippet,contentDetails,status",
            mine=True,
            maxResults=10,
        )
        assert len(result["playlists"]) == 1
        playlist = result["playlists"][0]
        assert playlist["id"] == "PLmine"
        assert playlist["title"] == "My Playlist"
        assert playlist["item_count"] == 7
        assert playlist["privacy_status"] == "private"
        assert len(playlist["description"]) == 200
        assert result["next_page_token"] == "next123"
        assert result["quota_cost"] == 1

    def test_get_my_playlists_caps_max_results_at_50(self):
        handler = self._oauth_handler()
        handler._youtube.playlists.return_value.list.return_value.execute.return_value = {"items": []}

        handler.get_my_playlists(max_results=999)

        _, kwargs = handler._youtube.playlists.return_value.list.call_args
        assert kwargs["maxResults"] == 50

    def test_get_my_subscriptions_maps_response(self):
        handler = self._oauth_handler()
        handler._youtube.subscriptions.return_value.list.return_value.execute.return_value = {
            "items": [{
                "id": "SUBmine",
                "snippet": {
                    "title": "Subscribed Channel",
                    "description": "desc",
                    "publishedAt": "2024-01-01T00:00:00Z",
                    "thumbnails": {"default": {"url": "http://thumb"}},
                    "resourceId": {"channelId": "UCtarget"},
                },
                "contentDetails": {"totalItemCount": 100, "newItemCount": 2, "activityType": "all"},
            }],
        }

        result = handler.get_my_subscriptions(max_results=25, order="alphabetical")

        handler._youtube.subscriptions.return_value.list.assert_called_once_with(
            part="snippet,contentDetails",
            mine=True,
            maxResults=25,
            order="alphabetical",
        )
        assert len(result["subscriptions"]) == 1
        sub = result["subscriptions"][0]
        assert sub["subscription_id"] == "SUBmine"
        assert sub["channel_id"] == "UCtarget"
        assert sub["channel_title"] == "Subscribed Channel"
        assert sub["total_item_count"] == 100

    def test_get_my_subscriptions_shares_mapper_with_get_channel_subscriptions(self):
        handler = self._oauth_handler()
        item = {
            "id": "SUBshared",
            "snippet": {
                "title": "T",
                "description": "",
                "publishedAt": "2024-01-01T00:00:00Z",
                "thumbnails": {},
                "resourceId": {"channelId": "UCx"},
            },
            "contentDetails": {"totalItemCount": 1, "newItemCount": 0, "activityType": "all"},
        }
        handler._youtube.subscriptions.return_value.list.return_value.execute.return_value = {
            "items": [item]
        }
        via_mine = handler.get_my_subscriptions()

        handler2 = self._oauth_handler()
        handler2._youtube.subscriptions.return_value.list.return_value.execute.return_value = {
            "items": [item]
        }
        via_explicit = handler2.get_channel_subscriptions(channel_id="UCsomeone")

        assert via_mine["subscriptions"] == via_explicit["subscriptions"]


# =============================================================================
# services/mine.py — MineService
# =============================================================================

class TestMineService:
    def _toolkit_stub(self):
        toolkit = MagicMock()
        return toolkit

    def test_login_calls_oauth_flow_and_resets_handler(self, monkeypatch):
        from youtube_toolkit.services.mine import MineService
        from youtube_toolkit import oauth

        toolkit = self._toolkit_stub()
        toolkit.youtube_api._initialized = True
        toolkit.youtube_api._youtube = MagicMock()

        monkeypatch.setattr(oauth, "run_login_flow", lambda: MagicMock())
        monkeypatch.setattr(oauth, "token_path", lambda: __import__("pathlib").Path("/tmp/tok.json"))

        service = MineService(toolkit)
        result = service.login()

        assert result == "/tmp/tok.json"
        # The handler must be reset so the NEXT call re-selects credentials
        # and picks up the freshly-saved OAuth token.
        assert toolkit.youtube_api._initialized is False
        assert toolkit.youtube_api._youtube is None

    def test_status_reports_logged_in_and_token_path_only(self, monkeypatch):
        from youtube_toolkit.services.mine import MineService
        from youtube_toolkit import oauth

        monkeypatch.setattr(oauth, "logged_in", lambda: True)
        monkeypatch.setattr(oauth, "token_path", lambda: __import__("pathlib").Path("/tmp/tok.json"))

        service = MineService(self._toolkit_stub())
        result = service.status()

        assert result == {"logged_in": True, "token_path": "/tmp/tok.json"}

    def test_channel_delegates_to_handler(self):
        from youtube_toolkit.services.mine import MineService

        toolkit = self._toolkit_stub()
        toolkit.youtube_api.get_my_channel.return_value = {"channel_id": "UC1"}

        service = MineService(toolkit)
        result = service.channel()

        toolkit.youtube_api.get_my_channel.assert_called_once_with()
        assert result == {"channel_id": "UC1"}

    def test_playlists_delegates_to_handler(self):
        from youtube_toolkit.services.mine import MineService

        toolkit = self._toolkit_stub()
        toolkit.youtube_api.get_my_playlists.return_value = {"playlists": []}

        service = MineService(toolkit)
        result = service.playlists(max_results=10, page_token="tok")

        toolkit.youtube_api.get_my_playlists.assert_called_once_with(
            max_results=10, page_token="tok"
        )
        assert result == {"playlists": []}

    def test_subscriptions_delegates_to_handler(self):
        from youtube_toolkit.services.mine import MineService

        toolkit = self._toolkit_stub()
        toolkit.youtube_api.get_my_subscriptions.return_value = {"subscriptions": []}

        service = MineService(toolkit)
        result = service.subscriptions(max_results=5, order="relevance", page_token="tok")

        toolkit.youtube_api.get_my_subscriptions.assert_called_once_with(
            max_results=5, order="relevance", page_token="tok"
        )
        assert result == {"subscriptions": []}


# =============================================================================
# sub_apis.py / api.py wiring — toolkit.mine reaches the service
# =============================================================================

class TestMineAPIWiring:
    def test_toolkit_mine_is_wired(self):
        from youtube_toolkit import YouTubeToolkit

        toolkit = YouTubeToolkit()

        assert hasattr(toolkit, "mine")
        assert toolkit.mine._toolkit is toolkit

    def test_mine_call_shortcuts_to_channel(self):
        from youtube_toolkit import YouTubeToolkit

        toolkit = YouTubeToolkit()
        toolkit._mine = MagicMock()
        toolkit._mine.channel.return_value = {"channel_id": "UCx"}
        toolkit.mine._toolkit = toolkit  # keep same back-ref after swap

        result = toolkit.mine()

        toolkit._mine.channel.assert_called_once_with()
        assert result == {"channel_id": "UCx"}

    def test_status_reaches_service(self):
        from youtube_toolkit import YouTubeToolkit

        toolkit = YouTubeToolkit()
        toolkit._mine = MagicMock()
        toolkit._mine.status.return_value = {"logged_in": False, "token_path": "/x"}
        toolkit.mine._toolkit = toolkit

        result = toolkit.mine.status()

        toolkit._mine.status.assert_called_once_with()
        assert result == {"logged_in": False, "token_path": "/x"}

    def test_playlists_forwards_kwargs(self):
        from youtube_toolkit import YouTubeToolkit

        toolkit = YouTubeToolkit()
        toolkit._mine = MagicMock()
        toolkit._mine.playlists.return_value = {"playlists": []}
        toolkit.mine._toolkit = toolkit

        toolkit.mine.playlists(max_results=15, page_token="abc")

        toolkit._mine.playlists.assert_called_once_with(max_results=15, page_token="abc")

    def test_subscriptions_forwards_kwargs(self):
        from youtube_toolkit import YouTubeToolkit

        toolkit = YouTubeToolkit()
        toolkit._mine = MagicMock()
        toolkit._mine.subscriptions.return_value = {"subscriptions": []}
        toolkit.mine._toolkit = toolkit

        toolkit.mine.subscriptions(max_results=30, order="unread", page_token="abc")

        toolkit._mine.subscriptions.assert_called_once_with(
            max_results=30, order="unread", page_token="abc"
        )

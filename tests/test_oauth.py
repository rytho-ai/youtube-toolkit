"""
Tests for youtube_toolkit.oauth — the OAuth credential provider.

No real Google OAuth Client exists for this project (see the module
docstring's VERIFY-LIVE note), so everything here mocks at the
`google_auth_oauthlib` / `google.oauth2.credentials` boundary. No network,
no real browser flow.
"""

import json
import stat
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# =============================================================================
# token_path
# =============================================================================

class TestTokenPath:
    def test_default_path(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_OAUTH_TOKEN_PATH", raising=False)
        from youtube_toolkit import oauth

        expected = Path("~/.youtube-cli/token.json").expanduser().resolve()
        assert oauth.token_path() == expected

    def test_env_override_is_expanded_and_resolved(self, monkeypatch, tmp_path):
        monkeypatch.setenv("YOUTUBE_OAUTH_TOKEN_PATH", str(tmp_path / "sub" / "token.json"))
        from youtube_toolkit import oauth

        result = oauth.token_path()
        assert result == (tmp_path / "sub" / "token.json").resolve()
        assert result.is_absolute()


# =============================================================================
# save_credentials — atomic write at 0600
# =============================================================================

class TestSaveCredentials:
    def test_writes_file_atomically_at_0600(self, monkeypatch, tmp_path):
        token_file = tmp_path / "nested" / "token.json"
        monkeypatch.setenv("YOUTUBE_OAUTH_TOKEN_PATH", str(token_file))
        from youtube_toolkit import oauth

        fake_creds = MagicMock()
        fake_creds.to_json.return_value = json.dumps({"token": "abc123"})

        oauth.save_credentials(fake_creds)

        assert token_file.exists()
        assert token_file.read_text() == json.dumps({"token": "abc123"})

        mode = stat.S_IMODE(token_file.stat().st_mode)
        assert mode == 0o600

        # No leftover temp file.
        assert list(token_file.parent.glob("*.tmp")) == []

    def test_creates_parent_directory(self, monkeypatch, tmp_path):
        token_file = tmp_path / "does" / "not" / "exist" / "token.json"
        monkeypatch.setenv("YOUTUBE_OAUTH_TOKEN_PATH", str(token_file))
        from youtube_toolkit import oauth

        fake_creds = MagicMock()
        fake_creds.to_json.return_value = "{}"

        oauth.save_credentials(fake_creds)

        assert token_file.parent.is_dir()
        assert token_file.exists()


# =============================================================================
# load_credentials
# =============================================================================

class TestLoadCredentials:
    def test_returns_none_when_no_token_file(self, monkeypatch, tmp_path):
        monkeypatch.setenv("YOUTUBE_OAUTH_TOKEN_PATH", str(tmp_path / "missing.json"))
        from youtube_toolkit import oauth

        assert oauth.load_credentials() is None

    def test_returns_none_when_token_file_is_corrupt(self, monkeypatch, tmp_path):
        token_file = tmp_path / "token.json"
        token_file.write_text("not valid json {{{")
        monkeypatch.setenv("YOUTUBE_OAUTH_TOKEN_PATH", str(token_file))
        from youtube_toolkit import oauth

        # Real Credentials.from_authorized_user_file (not mocked) should
        # raise on garbage content; load_credentials must swallow it.
        assert oauth.load_credentials() is None

    def test_returns_valid_creds_without_refresh(self, monkeypatch, tmp_path):
        token_file = tmp_path / "token.json"
        token_file.write_text("{}")
        monkeypatch.setenv("YOUTUBE_OAUTH_TOKEN_PATH", str(token_file))

        fake_creds = MagicMock()
        fake_creds.expired = False
        fake_creds.refresh_token = "r"
        fake_creds.refresh = MagicMock()

        monkeypatch.setattr(
            "google.oauth2.credentials.Credentials.from_authorized_user_file",
            classmethod(lambda cls, path, scopes: fake_creds),
        )

        from youtube_toolkit import oauth

        result = oauth.load_credentials()

        assert result is fake_creds
        fake_creds.refresh.assert_not_called()

    def test_refreshes_expired_creds_and_repersists(self, monkeypatch, tmp_path):
        token_file = tmp_path / "token.json"
        token_file.write_text("{}")
        monkeypatch.setenv("YOUTUBE_OAUTH_TOKEN_PATH", str(token_file))

        fake_creds = MagicMock()
        fake_creds.expired = True
        fake_creds.refresh_token = "r"
        fake_creds.to_json.return_value = json.dumps({"token": "refreshed"})

        def _refresh(request):
            fake_creds.expired = False

        fake_creds.refresh.side_effect = _refresh

        monkeypatch.setattr(
            "google.oauth2.credentials.Credentials.from_authorized_user_file",
            classmethod(lambda cls, path, scopes: fake_creds),
        )
        monkeypatch.setattr(
            "google.auth.transport.requests.Request",
            lambda: MagicMock(),
        )

        from youtube_toolkit import oauth

        result = oauth.load_credentials()

        assert result is fake_creds
        fake_creds.refresh.assert_called_once()
        # Re-persisted after refresh.
        assert token_file.read_text() == json.dumps({"token": "refreshed"})

    def test_refresh_failure_raises_typed_error(self, monkeypatch, tmp_path):
        token_file = tmp_path / "token.json"
        token_file.write_text("{}")
        monkeypatch.setenv("YOUTUBE_OAUTH_TOKEN_PATH", str(token_file))

        fake_creds = MagicMock()
        fake_creds.expired = True
        fake_creds.refresh_token = "r"
        fake_creds.refresh.side_effect = Exception("invalid_grant: token revoked")

        monkeypatch.setattr(
            "google.oauth2.credentials.Credentials.from_authorized_user_file",
            classmethod(lambda cls, path, scopes: fake_creds),
        )
        monkeypatch.setattr(
            "google.auth.transport.requests.Request",
            lambda: MagicMock(),
        )

        from youtube_toolkit import oauth

        with pytest.raises(oauth.YouTubeOAuthError, match="login"):
            oauth.load_credentials()

    def test_does_not_refresh_when_no_refresh_token(self, monkeypatch, tmp_path):
        token_file = tmp_path / "token.json"
        token_file.write_text("{}")
        monkeypatch.setenv("YOUTUBE_OAUTH_TOKEN_PATH", str(token_file))

        fake_creds = MagicMock()
        fake_creds.expired = True
        fake_creds.refresh_token = None

        monkeypatch.setattr(
            "google.oauth2.credentials.Credentials.from_authorized_user_file",
            classmethod(lambda cls, path, scopes: fake_creds),
        )

        from youtube_toolkit import oauth

        result = oauth.load_credentials()

        assert result is fake_creds
        fake_creds.refresh.assert_not_called()


# =============================================================================
# run_login_flow
# =============================================================================

class TestRunLoginFlow:
    def test_raises_when_client_secrets_unset(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_OAUTH_CLIENT_SECRETS", raising=False)
        from youtube_toolkit import oauth

        with pytest.raises(oauth.YouTubeOAuthError, match="YOUTUBE_OAUTH_CLIENT_SECRETS"):
            oauth.run_login_flow()

    def test_raises_when_client_secrets_file_missing(self, monkeypatch, tmp_path):
        monkeypatch.setenv("YOUTUBE_OAUTH_CLIENT_SECRETS", str(tmp_path / "nope.json"))
        from youtube_toolkit import oauth

        with pytest.raises(oauth.YouTubeOAuthError, match="doesn't exist"):
            oauth.run_login_flow()

    def test_success_runs_flow_and_persists(self, monkeypatch, tmp_path):
        secrets_file = tmp_path / "client_secrets.json"
        secrets_file.write_text("{}")
        token_file = tmp_path / "token.json"

        monkeypatch.setenv("YOUTUBE_OAUTH_CLIENT_SECRETS", str(secrets_file))
        monkeypatch.setenv("YOUTUBE_OAUTH_TOKEN_PATH", str(token_file))

        fake_creds = MagicMock()
        fake_creds.to_json.return_value = json.dumps({"token": "new"})

        fake_flow = MagicMock()
        fake_flow.run_local_server.return_value = fake_creds

        monkeypatch.setattr(
            "google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file",
            classmethod(lambda cls, path, scopes: fake_flow),
        )

        from youtube_toolkit import oauth

        result = oauth.run_login_flow()

        assert result is fake_creds
        fake_flow.run_local_server.assert_called_once_with(port=0)
        assert token_file.read_text() == json.dumps({"token": "new"})


# =============================================================================
# logged_in
# =============================================================================

class TestLoggedIn:
    def test_false_when_load_credentials_returns_none(self, monkeypatch):
        from youtube_toolkit import oauth

        monkeypatch.setattr(oauth, "load_credentials", lambda: None)
        assert oauth.logged_in() is False

    def test_true_when_load_credentials_returns_creds(self, monkeypatch):
        from youtube_toolkit import oauth

        monkeypatch.setattr(oauth, "load_credentials", lambda: MagicMock())
        assert oauth.logged_in() is True

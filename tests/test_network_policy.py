"""Tests for core/network_policy.py — the official-API transport policy.

Covers the upstream contract the Breaks-style consumers rely on:
transient transport failures retry, application errors (quota/auth) do not,
the timeout actually reaches the transport on BOTH auth paths, and the final
raw error is preserved when retries are exhausted.
"""

import socket
import ssl
from unittest.mock import MagicMock, patch

import httplib2
import pytest
from googleapiclient.errors import HttpError
from googleapiclient.http import HttpRequest

from youtube_toolkit import YouTubeToolkit
from youtube_toolkit.core.network_policy import (
    RequestPolicy,
    build_policy_http,
    build_request_builder,
)
from youtube_toolkit.handlers.youtube_api_handler import YouTubeAPIHandler


def _make_request(policy):
    """Instantiate the policy's HttpRequest subclass with dummy plumbing."""
    builder = build_request_builder(policy)
    return builder(None, lambda resp, content: content, "http://example.test/")


def _quota_error():
    resp = httplib2.Response({"status": "403", "reason": "quotaExceeded"})
    return HttpError(resp, b'{"error": {"errors": [{"reason": "quotaExceeded"}]}}')


class TestRequestPolicy:
    def test_defaults_preserve_pre_21_behavior(self):
        policy = RequestPolicy()
        assert policy.timeout_sec is None
        assert policy.transport_retries == 0

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"timeout_sec": 0},
            {"timeout_sec": -1.0},
            {"transport_retries": -1},
            {"retry_backoff_sec": -0.1},
        ],
    )
    def test_invalid_values_rejected(self, kwargs):
        with pytest.raises(ValueError):
            RequestPolicy(**kwargs)


class TestTransportRetry:
    def test_ssl_failure_then_success_calls_twice(self):
        request = _make_request(RequestPolicy(transport_retries=1, retry_backoff_sec=0))
        with patch.object(
            HttpRequest, "execute", side_effect=[ssl.SSLError("EOF in violation"), {"ok": True}]
        ) as base_execute:
            assert request.execute() == {"ok": True}
        assert base_execute.call_count == 2

    def test_quota_error_not_retried(self):
        request = _make_request(RequestPolicy(transport_retries=3, retry_backoff_sec=0))
        with patch.object(HttpRequest, "execute", side_effect=_quota_error()) as base_execute:
            with pytest.raises(HttpError):
                request.execute()
        assert base_execute.call_count == 1

    def test_auth_error_not_retried(self):
        resp = httplib2.Response({"status": "401", "reason": "unauthorized"})
        error = HttpError(resp, b'{"error": {"errors": [{"reason": "authError"}]}}')
        request = _make_request(RequestPolicy(transport_retries=3, retry_backoff_sec=0))
        with patch.object(HttpRequest, "execute", side_effect=error) as base_execute:
            with pytest.raises(HttpError):
                request.execute()
        assert base_execute.call_count == 1

    def test_all_retries_fail_raises_last_raw_error(self):
        final = ConnectionResetError("connection reset by peer")
        request = _make_request(RequestPolicy(transport_retries=2, retry_backoff_sec=0.15))
        with patch.object(
            HttpRequest,
            "execute",
            side_effect=[ssl.SSLError("first"), socket.timeout("second"), final],
        ) as base_execute:
            with patch("youtube_toolkit.core.network_policy.time.sleep") as mock_sleep:
                with pytest.raises(ConnectionResetError) as excinfo:
                    request.execute()
        assert excinfo.value is final  # raw, unwrapped
        assert base_execute.call_count == 3
        assert [c.args[0] for c in mock_sleep.call_args_list] == [0.15, 0.3]

    def test_zero_retries_is_single_call(self):
        request = _make_request(RequestPolicy())
        with patch.object(
            HttpRequest, "execute", side_effect=ssl.SSLError("boom")
        ) as base_execute:
            with pytest.raises(ssl.SSLError):
                request.execute()
        assert base_execute.call_count == 1


class TestTimeoutReachesTransport:
    def test_apikey_path_applies_timeout(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
        handler = YouTubeAPIHandler(policy=RequestPolicy(timeout_sec=5.0))
        with patch(
            "youtube_toolkit.handlers.youtube_api_handler.oauth.load_credentials",
            return_value=None,
        ):
            with patch("googleapiclient.discovery.build") as mock_build:
                mock_build.return_value = MagicMock()
                handler._ensure_initialized()
        kwargs = mock_build.call_args.kwargs
        assert kwargs["developerKey"] == "test-key"
        assert isinstance(kwargs["http"], httplib2.Http)
        assert kwargs["http"].timeout == 5.0
        assert issubclass(kwargs["requestBuilder"], HttpRequest)

    def test_oauth_path_applies_timeout(self):
        fake_creds = MagicMock()
        handler = YouTubeAPIHandler(policy=RequestPolicy(timeout_sec=7.5))
        with patch(
            "youtube_toolkit.handlers.youtube_api_handler.oauth.load_credentials",
            return_value=fake_creds,
        ):
            with patch("googleapiclient.discovery.build") as mock_build:
                mock_build.return_value = MagicMock()
                handler._ensure_initialized()
        kwargs = mock_build.call_args.kwargs
        authed_http = kwargs["http"]
        assert authed_http.credentials is fake_creds  # AuthorizedHttp wrapper
        assert authed_http.http.timeout == 7.5  # inner httplib2.Http
        assert issubclass(kwargs["requestBuilder"], HttpRequest)
        assert "developerKey" not in kwargs

    def test_default_policy_means_no_timeout(self):
        http = build_policy_http(RequestPolicy())
        assert http.timeout is None


class TestToolkitConstructor:
    def test_params_thread_down_to_handler(self):
        toolkit = YouTubeToolkit(
            request_timeout_sec=3.0, transport_retries=2, retry_backoff_sec=0.05
        )
        assert toolkit.youtube_api._policy == RequestPolicy(
            timeout_sec=3.0, transport_retries=2, retry_backoff_sec=0.05
        )

    def test_defaults_unchanged(self):
        toolkit = YouTubeToolkit()
        assert toolkit.youtube_api._policy == RequestPolicy()

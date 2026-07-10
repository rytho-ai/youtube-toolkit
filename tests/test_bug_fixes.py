"""
Regression tests for a batch of confirmed bugs:

1. API key leaking through YouTube Data API error strings (security).
2. Comments API failures silently swallowed into "0 comments, success".
3. transcript()'s `lang` parameter being dropped at every layer.
4. comments(order='rating') being unreachable.
5. Transcript failures (IP-block/rate-limit) not being classifiable.
"""

from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# FIX 1 — API key redaction
# =============================================================================

class TestRedactSecrets:
    """utils.helpers.redact_secrets scrubs API keys from error strings."""

    def test_redacts_key_param(self):
        from youtube_toolkit.utils.helpers import redact_secrets

        raw = (
            '<HttpError 403 when requesting '
            'https://www.googleapis.com/youtube/v3/commentThreads?'
            'part=snippet&videoId=abc123&key=SECRET123 returned '
            '"The request cannot be completed">'
        )

        redacted = redact_secrets(raw)

        assert "SECRET123" not in redacted
        assert "key=***REDACTED***" in redacted

    def test_redacts_developer_key_param(self):
        from youtube_toolkit.utils.helpers import redact_secrets

        raw = "build('youtube','v3', developerKey=SECRET456) failed"
        redacted = redact_secrets(raw)

        assert "SECRET456" not in redacted

    def test_passes_through_none(self):
        from youtube_toolkit.utils.helpers import redact_secrets

        assert redact_secrets(None) is None

    def test_accepts_exception_objects(self):
        from youtube_toolkit.utils.helpers import redact_secrets

        err = ValueError("request to ...&key=SECRET789 failed")
        redacted = redact_secrets(err)

        assert "SECRET789" not in redacted
        assert isinstance(redacted, str)


class TestYouTubeAPIHandlerRedaction:
    """The YouTube Data API handler never leaks the key on failure."""

    def _make_handler(self):
        from youtube_toolkit.handlers.youtube_api_handler import YouTubeAPIHandler

        handler = YouTubeAPIHandler()
        handler._initialized = True
        handler._api_key = "SECRET_KEY_VALUE"
        handler._youtube = MagicMock()
        return handler

    def test_advanced_fetch_comments_error_is_redacted(self):
        handler = self._make_handler()
        handler._youtube.commentThreads.return_value.list.return_value.execute.side_effect = (
            Exception(
                "https://www.googleapis.com/youtube/v3/commentThreads?"
                "key=SECRET_KEY_VALUE returned 403 Forbidden"
            )
        )

        result = handler.advanced_fetch_comments("https://www.youtube.com/watch?v=abc12345678")

        assert result["total_results"] == 0
        assert "SECRET_KEY_VALUE" not in result["error"]

    def test_fetch_comments_print_is_redacted(self, capsys):
        handler = self._make_handler()
        handler._youtube.commentThreads.return_value.list.return_value.execute.side_effect = (
            Exception("...key=SECRET_KEY_VALUE...")
        )

        result = handler.fetch_comments("https://www.youtube.com/watch?v=abc12345678")

        assert result == []
        captured = capsys.readouterr()
        assert "SECRET_KEY_VALUE" not in captured.out


# =============================================================================
# FIX 2 — comments API failures must be visible, not "0 comments, success"
# =============================================================================

class TestCommentResultError:
    """CommentResult carries a redacted `error` when the fetch failed."""

    def test_error_field_defaults_to_none(self):
        from youtube_toolkit.core.comments import CommentResult

        result = CommentResult(comments=[], total_results=0)
        assert result.error is None

    def test_error_field_roundtrips_through_to_dict(self):
        from youtube_toolkit.core.comments import CommentResult

        result = CommentResult(comments=[], total_results=0, error="boom")
        assert result.to_dict()["error"] == "boom"

    def test_service_propagates_handler_error(self):
        """services.comments.CommentsService.comments() surfaces a handler error."""
        from youtube_toolkit.services.comments import CommentsService

        toolkit = MagicMock()
        service = CommentsService(toolkit)

        with patch.object(service, "advanced_get_comments") as mock_advanced:
            mock_advanced.return_value = {
                "comments": [],
                "total_results": 0,
                "error": "Quota exceeded for key=***REDACTED***",
                "quota_cost": 1,
            }

            result = service.comments("https://www.youtube.com/watch?v=abc12345678")

        assert result.total_results == 0
        assert result.error is not None
        assert "SECRET" not in result.error
        assert "quota exceeded" in result.error.lower()


# =============================================================================
# FIX 3 — transcript()'s `lang` param must actually be threaded through
# =============================================================================

class TestTranscriptLangThreading:

    def test_sub_api_forwards_lang_to_service(self):
        from youtube_toolkit import YouTubeToolkit

        toolkit = YouTubeToolkit()

        with patch.object(toolkit._get_info, "get_transcript") as mock_get:
            mock_get.return_value = "transcript text"

            result = toolkit.get.transcript(
                "https://www.youtube.com/watch?v=abc12345678", lang="es"
            )

            mock_get.assert_called_once_with(
                "https://www.youtube.com/watch?v=abc12345678", lang="es"
            )
            assert result == "transcript text"

    def test_service_forwards_lang_to_handler(self):
        from youtube_toolkit.services.get_info import GetInfoService

        toolkit = MagicMock()
        service = GetInfoService(toolkit)

        service.get_transcript("https://www.youtube.com/watch?v=abc12345678", lang="fr")

        toolkit.ytdlp.get_transcript.assert_called_once_with(
            "https://www.youtube.com/watch?v=abc12345678", lang="fr"
        )

    def test_handler_tries_requested_language_first(self):
        """A provided lang changes which caption track is selected."""
        from youtube_toolkit.handlers.yt_dlp_handler import YTDLPHandler

        handler = YTDLPHandler()

        fake_transcript = MagicMock()
        fake_transcript.fetch.return_value = [
            MagicMock(start=0.0, duration=1.0, text="hola mundo"),
        ]

        attempted_languages = []

        def fake_find_transcript(langs):
            attempted_languages.append(langs)
            if langs == ["es"]:
                return fake_transcript
            raise Exception("TranslationLanguageNotAvailable")

        fake_transcript_list = MagicMock()
        fake_transcript_list.find_transcript.side_effect = fake_find_transcript
        fake_transcript_list.__iter__.return_value = iter([])

        with patch("youtube_transcript_api.YouTubeTranscriptApi") as MockApi:
            MockApi.return_value.list.return_value = fake_transcript_list

            result = handler.get_transcript(
                "https://www.youtube.com/watch?v=abc12345678", lang="es"
            )

        # 'es' was tried before the hardcoded ['en', 'en-US', ...] list.
        assert attempted_languages[0] == ["es"]
        assert "hola mundo" in result

    def test_handler_degrades_to_default_list_when_lang_unavailable(self):
        """If the requested lang isn't available, it still falls back (no hard-fail)."""
        from youtube_toolkit.handlers.yt_dlp_handler import YTDLPHandler

        handler = YTDLPHandler()

        fake_transcript = MagicMock()
        fake_transcript.fetch.return_value = [
            MagicMock(start=0.0, duration=1.0, text="hello world"),
        ]

        def fake_find_transcript(langs):
            if langs == ["en"]:
                return fake_transcript
            raise Exception("not available")

        fake_transcript_list = MagicMock()
        fake_transcript_list.find_transcript.side_effect = fake_find_transcript
        fake_transcript_list.__iter__.return_value = iter([])

        with patch("youtube_transcript_api.YouTubeTranscriptApi") as MockApi:
            MockApi.return_value.list.return_value = fake_transcript_list

            result = handler.get_transcript(
                "https://www.youtube.com/watch?v=abc12345678", lang="xx-not-real"
            )

        assert "hello world" in result

    def test_handler_default_behavior_unchanged_when_lang_none(self):
        """No lang given -> identical to today's hardcoded-list-only behavior."""
        from youtube_toolkit.handlers.yt_dlp_handler import YTDLPHandler

        handler = YTDLPHandler()

        fake_transcript = MagicMock()
        fake_transcript.fetch.return_value = [
            MagicMock(start=0.0, duration=1.0, text="default text"),
        ]

        attempted_languages = []

        def fake_find_transcript(langs):
            attempted_languages.append(langs)
            if langs == ["en"]:
                return fake_transcript
            raise Exception("not available")

        fake_transcript_list = MagicMock()
        fake_transcript_list.find_transcript.side_effect = fake_find_transcript
        fake_transcript_list.__iter__.return_value = iter([])

        with patch("youtube_transcript_api.YouTubeTranscriptApi") as MockApi:
            MockApi.return_value.list.return_value = fake_transcript_list

            result = handler.get_transcript("https://www.youtube.com/watch?v=abc12345678")

        assert attempted_languages[0] == ["en"]
        assert "default text" in result


# =============================================================================
# FIX 4 — comments(order='rating') must be reachable
# =============================================================================

class TestCommentOrderMapping:

    def test_parse_comment_order_covers_all_values(self):
        from youtube_toolkit.sub_apis import _parse_comment_order
        from youtube_toolkit.core.comments import CommentOrder

        assert _parse_comment_order("relevance") == CommentOrder.RELEVANCE
        assert _parse_comment_order("time") == CommentOrder.TIME
        assert _parse_comment_order("rating") == CommentOrder.RATING

    def test_parse_comment_order_case_insensitive(self):
        from youtube_toolkit.sub_apis import _parse_comment_order
        from youtube_toolkit.core.comments import CommentOrder

        assert _parse_comment_order("RATING") == CommentOrder.RATING

    def test_parse_comment_order_rejects_unknown(self):
        from youtube_toolkit.sub_apis import _parse_comment_order

        with pytest.raises(ValueError):
            _parse_comment_order("bogus")

    def test_get_comments_order_rating_reaches_comment_filters(self):
        from youtube_toolkit import YouTubeToolkit, CommentResult
        from youtube_toolkit.core.comments import CommentOrder

        toolkit = YouTubeToolkit()

        with patch.object(toolkit._comments, "comments") as mock_comments:
            mock_comments.return_value = CommentResult(comments=[], total_results=0)

            toolkit.get.comments("https://www.youtube.com/watch?v=abc12345678", order="rating")

            _, kwargs = mock_comments.call_args
            assert kwargs["filters"].order == CommentOrder.RATING

    def test_analyze_comments_order_rating_reaches_comment_filters(self):
        from youtube_toolkit import YouTubeToolkit, CommentResult
        from youtube_toolkit.core.comments import CommentOrder

        toolkit = YouTubeToolkit()

        with patch.object(toolkit._comments, "comments") as mock_comments:
            mock_comments.return_value = CommentResult(comments=[], total_results=0)

            toolkit.analyze.comments("https://www.youtube.com/watch?v=abc12345678", sort="rating")

            _, kwargs = mock_comments.call_args
            assert kwargs["filters"].order == CommentOrder.RATING


# =============================================================================
# FIX 5 — transcript failures: classify IP-block/rate-limit vs no-captions
# =============================================================================

class TestTranscriptFailureClassification:

    def test_ip_block_raises_typed_rate_limited_error(self):
        from youtube_toolkit.handlers.yt_dlp_handler import YTDLPHandler
        from youtube_toolkit.core.exceptions import RateLimitedError

        handler = YTDLPHandler()

        with patch("youtube_transcript_api.YouTubeTranscriptApi") as MockApi:
            MockApi.return_value.list.side_effect = Exception(
                "YouTube is blocking requests from your IP. This usually is "
                "due to too many requests."
            )

            with pytest.raises(RateLimitedError):
                handler.get_transcript("https://www.youtube.com/watch?v=abc12345678")

    def test_too_many_requests_raises_typed_rate_limited_error(self):
        from youtube_toolkit.handlers.yt_dlp_handler import YTDLPHandler
        from youtube_toolkit.core.exceptions import RateLimitedError

        handler = YTDLPHandler()

        with patch("youtube_transcript_api.YouTubeTranscriptApi") as MockApi:
            MockApi.return_value.list.side_effect = Exception("429 Too Many Requests")

            with pytest.raises(RateLimitedError):
                handler.get_transcript("https://www.youtube.com/watch?v=abc12345678")

    def test_genuinely_no_captions_returns_none(self):
        """A video with zero caption tracks still returns None, not an error."""
        from youtube_toolkit.handlers.yt_dlp_handler import YTDLPHandler

        handler = YTDLPHandler()

        empty_transcript_list = MagicMock()
        empty_transcript_list.find_transcript.side_effect = Exception("NoTranscriptFound")
        empty_transcript_list.__iter__.return_value = iter([])

        with patch("youtube_transcript_api.YouTubeTranscriptApi") as MockApi:
            MockApi.return_value.list.return_value = empty_transcript_list

            result = handler.get_transcript("https://www.youtube.com/watch?v=abc12345678")

        assert result is None

    def test_other_generic_failure_still_returns_none(self):
        """Non-rate-limit failures keep today's degrade-to-None behavior."""
        from youtube_toolkit.handlers.yt_dlp_handler import YTDLPHandler

        handler = YTDLPHandler()

        with patch("youtube_transcript_api.YouTubeTranscriptApi") as MockApi:
            MockApi.return_value.list.side_effect = Exception("VideoUnavailable")

            result = handler.get_transcript("https://www.youtube.com/watch?v=abc12345678")

        assert result is None

    def test_service_lets_typed_exception_propagate(self):
        """services.get_info.GetInfoService doesn't swallow RateLimitedError."""
        from youtube_toolkit.services.get_info import GetInfoService
        from youtube_toolkit.core.exceptions import RateLimitedError

        toolkit = MagicMock()
        toolkit.ytdlp.get_transcript.side_effect = RateLimitedError("blocked")
        service = GetInfoService(toolkit)

        with pytest.raises(RateLimitedError):
            service.get_transcript("https://www.youtube.com/watch?v=abc12345678")

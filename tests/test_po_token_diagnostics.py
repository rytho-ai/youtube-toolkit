"""
Tests for PO-token failure detection (is_po_token_related / augment).
"""

from youtube_toolkit.utils.po_token_diagnostics import (
    PO_TOKEN_HINT,
    augment,
    is_po_token_related,
)


class TestIsPoTokenRelated:
    """Detection is a conservative substring match on yt-dlp's own wording."""

    def test_detects_sign_in_to_confirm(self):
        assert is_po_token_related(Exception("Sign in to confirm you're not a bot"))

    def test_detects_http_403(self):
        assert is_po_token_related(Exception("HTTP Error 403: Forbidden"))

    def test_detects_po_token_mention(self):
        assert is_po_token_related(Exception("Missing po_token for this format"))

    def test_is_case_insensitive(self):
        assert is_po_token_related(Exception("SIGN IN TO CONFIRM you are not a bot"))

    def test_unrelated_error_not_flagged(self):
        assert not is_po_token_related(Exception("Video unavailable: private video"))

    def test_network_timeout_not_flagged(self):
        assert not is_po_token_related(Exception("Connection timed out"))


class TestAugment:
    """augment() appends the hint only when the error looks PO-token-related."""

    def test_appends_hint_when_related(self):
        exc = Exception("HTTP Error 403: Forbidden")
        result = augment("Failed to download video: 403", exc)
        assert "Failed to download video: 403" in result
        assert PO_TOKEN_HINT in result

    def test_leaves_message_unchanged_when_unrelated(self):
        exc = Exception("Video unavailable: private video")
        message = "Failed to download video: private"
        assert augment(message, exc) == message

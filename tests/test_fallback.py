"""
Tests for the core fallback primitive (run_with_fallback / log_failure).
"""

import logging

import pytest

from youtube_toolkit.core.fallback import run_with_fallback, log_failure


class TestRunWithFallback:
    """Tests for run_with_fallback ordered-attempt behavior."""

    def test_first_attempt_succeeds_skips_rest(self):
        """First attempt wins; later attempts are never called."""
        calls = []

        def first():
            calls.append("first")
            return "ok-first"

        def second():
            calls.append("second")
            return "ok-second"

        result = run_with_fallback(
            [("First", first), ("Second", second)],
            error_message="should not be raised",
        )

        assert result == "ok-first"
        assert calls == ["first"]  # second never invoked

    def test_falls_back_to_second_on_first_failure(self):
        """First attempt fails, second succeeds and its value is returned."""
        calls = []

        def first():
            calls.append("first")
            raise ValueError("boom")

        def second():
            calls.append("second")
            return "ok-second"

        result = run_with_fallback(
            [("First", first), ("Second", second)],
            error_message="should not be raised",
        )

        assert result == "ok-second"
        assert calls == ["first", "second"]

    def test_all_fail_raises_runtime_error_with_message(self):
        """When every attempt fails, RuntimeError carries error_message."""
        def first():
            raise ValueError("boom1")

        def second():
            raise RuntimeError("boom2")

        with pytest.raises(RuntimeError) as exc_info:
            run_with_fallback(
                [("First", first), ("Second", second)],
                error_message="All methods failed",
            )

        assert str(exc_info.value) == "All methods failed"


class TestLogFailure:
    """Tests for the unified logging seam."""

    def test_verbose_logs_at_warning(self, caplog):
        """Verbose mode surfaces failures at WARNING with the legacy shape."""
        with caplog.at_level(logging.WARNING, logger="youtube_toolkit"):
            log_failure("PyTubeFix", ValueError("nope"), verbose=True)

        assert "PyTubeFix failed: nope" in caplog.text

    def test_quiet_does_not_warn(self, caplog):
        """Non-verbose mode stays quiet (nothing at WARNING level)."""
        with caplog.at_level(logging.WARNING, logger="youtube_toolkit"):
            log_failure("PyTubeFix", ValueError("nope"), verbose=False)

        assert "PyTubeFix failed" not in caplog.text

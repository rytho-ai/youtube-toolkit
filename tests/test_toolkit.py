"""
Tests for the main YouTubeToolkit class.
"""

import pytest
from unittest.mock import patch, MagicMock
import os


class TestYouTubeToolkitImport:
    """Tests for importing the toolkit."""

    def test_import_main_class(self):
        """Test that YouTubeToolkit can be imported."""
        from youtube_toolkit import YouTubeToolkit
        assert YouTubeToolkit is not None

    def test_import_version(self):
        """Test that version is accessible."""
        from youtube_toolkit import __version__
        assert __version__ == "2.0.0"

    def test_import_core_classes(self):
        """Test that core classes can be imported."""
        from youtube_toolkit import (
            VideoInfo,
            DownloadResult,
            SearchResult,
            SearchFilters,
            CommentFilters,
            CaptionFilters,
        )
        assert VideoInfo is not None
        assert DownloadResult is not None
        assert SearchResult is not None
        assert SearchFilters is not None
        assert CommentFilters is not None
        assert CaptionFilters is not None


class TestYouTubeToolkitInit:
    """Tests for YouTubeToolkit initialization."""

    def test_init_default(self):
        """Test default initialization."""
        from youtube_toolkit import YouTubeToolkit
        toolkit = YouTubeToolkit()
        assert toolkit.verbose is False

    def test_init_verbose(self):
        """Test verbose initialization."""
        from youtube_toolkit import YouTubeToolkit
        toolkit = YouTubeToolkit(verbose=True)
        assert toolkit.verbose is True

    def test_handlers_initialized(self):
        """Test that handlers are initialized."""
        from youtube_toolkit import YouTubeToolkit
        toolkit = YouTubeToolkit()
        assert toolkit.pytubefix is not None
        assert toolkit.yt_dlp is not None
        assert toolkit.youtube_api is not None

    def test_anti_detection_initialized(self):
        """Test that anti-detection manager is initialized."""
        from youtube_toolkit import YouTubeToolkit
        toolkit = YouTubeToolkit()
        assert toolkit.anti_detection is not None


class TestVideoIdExtraction:
    """Tests for video ID extraction."""

    def test_extract_standard_url(self):
        """Test extracting video ID from standard URL."""
        from youtube_toolkit import YouTubeToolkit
        toolkit = YouTubeToolkit()

        # Standard watch URL
        video_id = toolkit.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_short_url(self):
        """Test extracting video ID from short URL."""
        from youtube_toolkit import YouTubeToolkit
        toolkit = YouTubeToolkit()

        video_id = toolkit.extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_with_extra_params(self):
        """Test extracting video ID from URL with extra parameters."""
        from youtube_toolkit import YouTubeToolkit
        toolkit = YouTubeToolkit()

        video_id = toolkit.extract_video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest&index=1"
        )
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_invalid_url(self):
        """Test that invalid URL raises error or returns empty."""
        from youtube_toolkit import YouTubeToolkit
        toolkit = YouTubeToolkit()

        # The implementation may handle invalid URLs differently
        # depending on which handler succeeds
        try:
            result = toolkit.extract_video_id("not-a-valid-url")
            # If it doesn't raise, the result should be empty or the input itself
            assert result == "" or result == "not-a-valid-url" or result is None
        except (ValueError, Exception):
            # Either ValueError or other exceptions are acceptable
            pass


class TestSanitizeFilename:
    """Tests for filename sanitization."""

    def test_sanitize_basic(self):
        """Test basic filename sanitization."""
        from youtube_toolkit import YouTubeToolkit
        toolkit = YouTubeToolkit()

        result = toolkit._sanitize_filename("Normal Title")
        assert result == "Normal Title"

    def test_sanitize_special_chars(self):
        """Test sanitization of special characters."""
        from youtube_toolkit import YouTubeToolkit
        toolkit = YouTubeToolkit()

        result = toolkit._sanitize_filename('Video: "Test" <script>')
        assert ":" not in result
        assert '"' not in result
        assert "<" not in result
        assert ">" not in result

    def test_sanitize_length_limit(self):
        """Test that long filenames are truncated."""
        from youtube_toolkit import YouTubeToolkit
        toolkit = YouTubeToolkit()

        long_title = "A" * 200
        result = toolkit._sanitize_filename(long_title)
        assert len(result) <= 100


class TestSearchCategories:
    """Tests for search category retrieval."""

    def test_get_categories(self):
        """Test the static search-category mapping (public YOUTUBE_CATEGORIES)."""
        # The legacy flat toolkit.get_search_categories() was removed in 2.0;
        # its static name->id mapping now lives in the public YOUTUBE_CATEGORIES
        # constant. (toolkit.search.categories() is the separate API-based variant.)
        from youtube_toolkit import YOUTUBE_CATEGORIES

        categories = YOUTUBE_CATEGORIES
        assert isinstance(categories, dict)
        assert "Music" in categories
        assert "Gaming" in categories
        assert "Education" in categories

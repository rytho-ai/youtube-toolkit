"""
Tests for the new clean API (v0.1.0+).
"""

import pytest
from unittest.mock import patch, MagicMock


class TestNewAPIImports:
    """Tests for importing new API components."""

    def test_import_new_methods_exist(self):
        """Test that new methods exist on YouTubeToolkit."""
        from youtube_toolkit import YouTubeToolkit

        toolkit = YouTubeToolkit()

        # Check new methods exist
        assert hasattr(toolkit, 'get_video')
        assert hasattr(toolkit, 'download')
        assert hasattr(toolkit, 'search')
        assert hasattr(toolkit, 'comments')
        assert hasattr(toolkit, 'captions')
        assert hasattr(toolkit, 'playlist')

    def test_import_filter_classes(self):
        """Test that filter classes can be imported."""
        from youtube_toolkit import (
            SearchFilters,
            CommentFilters,
            CaptionFilters,
            CommentOrder,
        )

        assert SearchFilters is not None
        assert CommentFilters is not None
        assert CaptionFilters is not None
        assert CommentOrder is not None

    def test_import_result_classes(self):
        """Test that result dataclasses can be imported."""
        from youtube_toolkit import (
            VideoInfo,
            DownloadResult,
            SearchResult,
            CommentResult,
            CaptionResult,
        )

        assert VideoInfo is not None
        assert DownloadResult is not None
        assert SearchResult is not None
        assert CommentResult is not None
        assert CaptionResult is not None


class TestGetVideoAPI:
    """Tests for get_video() new API."""

    def test_get_video_returns_video_info(self):
        """Test that get_video returns VideoInfo dataclass."""
        from youtube_toolkit import YouTubeToolkit, VideoInfo

        toolkit = YouTubeToolkit()

        # Mock the underlying get_video_info method
        with patch.object(toolkit._get_info, 'get_video_info') as mock:
            mock.return_value = {
                'title': 'Test Video',
                'duration': 180,
                'view_count': 1000000,
                'channel': 'Test Channel',
                'video_id': 'abc123',
                'video_url': 'https://youtube.com/watch?v=abc123',
                'description': 'Test description',
                'thumbnail_url': 'https://example.com/thumb.jpg',
                'upload_date': '2024-01-01',
                'like_count': 50000,
            }

            result = toolkit.get_video('https://youtube.com/watch?v=abc123')

            assert isinstance(result, VideoInfo)
            assert result.title == 'Test Video'
            assert result.duration == 180
            assert result.views == 1000000
            assert result.author == 'Test Channel'
            assert result.video_id == 'abc123'


class TestDownloadAPI:
    """Tests for download() new API."""

    def test_download_returns_download_result(self):
        """Test that download returns DownloadResult dataclass."""
        from youtube_toolkit import YouTubeToolkit, DownloadResult

        toolkit = YouTubeToolkit()

        # Mock the underlying download_audio method
        with patch.object(toolkit._download, 'download_audio') as mock:
            mock.return_value = '/tmp/test.wav'

            result = toolkit.download(
                'https://youtube.com/watch?v=abc123',
                type='audio',
                format='wav'
            )

            assert isinstance(result, DownloadResult)
            assert result.file_path == '/tmp/test.wav'
            assert result.success is True
            assert result.format == 'wav'

    def test_download_video_returns_download_result(self):
        """Test that video download returns DownloadResult."""
        from youtube_toolkit import YouTubeToolkit, DownloadResult

        toolkit = YouTubeToolkit()

        with patch.object(toolkit._download, 'download_video') as mock:
            mock.return_value = '/tmp/test.mp4'

            result = toolkit.download(
                'https://youtube.com/watch?v=abc123',
                type='video',
                quality='720p'
            )

            assert isinstance(result, DownloadResult)
            assert result.success is True
            assert result.format == 'mp4'
            assert result.quality == '720p'

    def test_download_failure_returns_result(self):
        """Test that failed download returns DownloadResult with error."""
        from youtube_toolkit import YouTubeToolkit, DownloadResult

        toolkit = YouTubeToolkit()

        with patch.object(toolkit._download, 'download_audio') as mock:
            mock.side_effect = Exception("Network error")

            result = toolkit.download(
                'https://youtube.com/watch?v=abc123',
                type='audio'
            )

            assert isinstance(result, DownloadResult)
            assert result.success is False
            assert "Network error" in result.error_message

    def test_download_invalid_type_raises_error(self):
        """Test that invalid type returns error result."""
        from youtube_toolkit import YouTubeToolkit

        toolkit = YouTubeToolkit()

        result = toolkit.download(
            'https://youtube.com/watch?v=abc123',
            type='invalid'
        )

        assert result.success is False
        assert "Invalid type" in result.error_message

    def test_download_quality_parameter_passed_to_video(self):
        """Test that quality parameter is correctly passed for video downloads."""
        from youtube_toolkit import YouTubeToolkit, DownloadResult

        toolkit = YouTubeToolkit()

        with patch.object(toolkit._download, 'download_video') as mock:
            mock.return_value = '/tmp/test.mp4'

            # Test 720p
            result = toolkit.download(
                'https://youtube.com/watch?v=abc123',
                type='video',
                quality='720p'
            )

            # Verify download_video was called with correct quality
            mock.assert_called_once()
            call_kwargs = mock.call_args[1]
            assert call_kwargs['quality'] == '720p'
            assert result.quality == '720p'

    def test_download_quality_parameter_1080p(self):
        """Test that 1080p quality parameter works."""
        from youtube_toolkit import YouTubeToolkit

        toolkit = YouTubeToolkit()

        with patch.object(toolkit._download, 'download_video') as mock:
            mock.return_value = '/tmp/test_1080p.mp4'

            result = toolkit.download(
                'https://youtube.com/watch?v=abc123',
                type='video',
                quality='1080p'
            )

            call_kwargs = mock.call_args[1]
            assert call_kwargs['quality'] == '1080p'
            assert result.quality == '1080p'

    def test_download_quality_parameter_best(self):
        """Test that 'best' quality parameter works."""
        from youtube_toolkit import YouTubeToolkit

        toolkit = YouTubeToolkit()

        with patch.object(toolkit._download, 'download_video') as mock:
            mock.return_value = '/tmp/test_best.mp4'

            result = toolkit.download(
                'https://youtube.com/watch?v=abc123',
                type='video',
                quality='best'
            )

            call_kwargs = mock.call_args[1]
            assert call_kwargs['quality'] == 'best'
            assert result.quality == 'best'

    def test_download_bitrate_parameter_for_audio(self):
        """Test that bitrate parameter is correctly passed for audio downloads."""
        from youtube_toolkit import YouTubeToolkit

        toolkit = YouTubeToolkit()

        with patch.object(toolkit._download, 'download_audio') as mock:
            mock.return_value = '/tmp/test.mp3'

            result = toolkit.download(
                'https://youtube.com/watch?v=abc123',
                type='audio',
                format='mp3',
                bitrate='320k'
            )

            # Verify download_audio was called with correct bitrate
            mock.assert_called_once()
            call_kwargs = mock.call_args[1]
            assert call_kwargs['bitrate'] == '320k'
            # For audio, quality field stores bitrate
            assert result.quality == '320k'


class TestSearchAPI:
    """Tests for search() new API."""

    def test_search_returns_search_result(self):
        """Test that search returns SearchResult dataclass."""
        from youtube_toolkit import YouTubeToolkit, SearchResult

        toolkit = YouTubeToolkit()

        with patch.object(toolkit._search, 'advanced_search') as mock:
            mock.return_value = {
                'items': [
                    {'video_id': 'abc', 'title': 'Video 1'},
                    {'video_id': 'def', 'title': 'Video 2'},
                ],
                'total_results': 2,
                'backend_used': 'pytubefix',
            }

            result = toolkit.search('test query', max_results=10)

            assert isinstance(result, SearchResult)
            assert result.query == 'test query'
            assert len(result.items) == 2

    def test_search_with_filters(self):
        """Test search with SearchFilters."""
        from youtube_toolkit import YouTubeToolkit, SearchFilters

        toolkit = YouTubeToolkit()
        filters = SearchFilters(video_duration='short', order='viewCount')

        with patch.object(toolkit._search, 'advanced_search') as mock:
            mock.return_value = {'items': [], 'total_results': 0}

            result = toolkit.search('test', filters=filters)

            assert result.filters_applied is not None


class TestCommentsAPI:
    """Tests for comments() new API."""

    def test_comments_returns_comment_result(self):
        """Test that comments returns CommentResult dataclass."""
        from youtube_toolkit import YouTubeToolkit, CommentResult

        toolkit = YouTubeToolkit()

        with patch.object(toolkit._comments, 'advanced_get_comments') as mock:
            mock.return_value = {
                'comments': [],
                'total_results': 0,
                'quota_cost': 1,
            }

            result = toolkit.comments('https://youtube.com/watch?v=abc123')

            assert isinstance(result, CommentResult)
            assert result.total_results == 0


class TestCaptionsAPI:
    """Tests for captions() new API."""

    def test_captions_returns_caption_result(self):
        """Test that captions returns CaptionResult dataclass."""
        from youtube_toolkit import YouTubeToolkit, CaptionResult

        toolkit = YouTubeToolkit()

        with patch.object(toolkit._captions, 'list_captions') as mock:
            mock.return_value = {'tracks': [], 'quota_cost': 0}

        with patch.object(toolkit, 'extract_video_id') as mock_id:
            mock_id.return_value = 'abc123'

            result = toolkit.captions('https://youtube.com/watch?v=abc123')

            assert isinstance(result, CaptionResult)


class TestPlaylistAPI:
    """Tests for playlist() new API."""

    def test_playlist_returns_list(self):
        """Test that playlist returns list of URLs."""
        from youtube_toolkit import YouTubeToolkit

        toolkit = YouTubeToolkit()

        with patch.object(toolkit._playlist, 'get_playlist_urls') as mock:
            mock.return_value = [
                'https://youtube.com/watch?v=abc',
                'https://youtube.com/watch?v=def',
            ]

            result = toolkit.playlist('https://youtube.com/playlist?list=...')

            assert isinstance(result, list)
            assert len(result) == 2

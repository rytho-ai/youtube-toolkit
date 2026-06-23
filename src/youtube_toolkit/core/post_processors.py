"""
Post-processors for standardizing handler outputs.

This module contains post-processors that convert raw handler outputs
into standardized VideoInfo and DownloadResult objects.
"""

from typing import Dict, Any, List, Optional
from .video_info import VideoInfo
from .download import DownloadResult


class BasePostProcessor:
    """Base class for all post-processors."""
    
    @staticmethod
    def process_video_info(raw_info: Dict[str, Any]) -> VideoInfo:
        """Convert raw video info to standardized VideoInfo."""
        raise NotImplementedError("Subclasses must implement process_video_info")
    
    @staticmethod
    def process_download_result(raw_result: Dict[str, Any]) -> DownloadResult:
        """Convert raw download result to standardized DownloadResult."""
        raise NotImplementedError("Subclasses must implement process_download_result")


class PyTubeFixPostProcessor(BasePostProcessor):
    """Convert PyTubeFix output to standardized format."""
    
    @staticmethod
    def process_video_info(raw_info: Dict[str, Any]) -> VideoInfo:
        """Convert PyTubeFix video info to standard format."""
        # Handle both dict and object-like structures
        if hasattr(raw_info, 'title'):
            # Object-like structure (YouTube object)
            return VideoInfo(
                title=getattr(raw_info, 'title', ''),
                duration=getattr(raw_info, 'length', 0),
                views=getattr(raw_info, 'views', 0),
                author=getattr(raw_info, 'author', ''),
                video_id=getattr(raw_info, 'video_id', ''),
                url=getattr(raw_info, 'watch_url', ''),
                description=getattr(raw_info, 'description', None),
                thumbnail=getattr(raw_info, 'thumbnail_url', None),
                category=getattr(raw_info, 'category', None),
                tags=getattr(raw_info, 'keywords', None),
                published_date=getattr(raw_info, 'publish_date', None),
                like_count=getattr(raw_info, 'like_count', None),
                comment_count=getattr(raw_info, 'comment_count', None)
            )
        else:
            # Dict-like structure
            return VideoInfo(
                title=raw_info.get('title', ''),
                duration=raw_info.get('duration', raw_info.get('length', 0)),
                views=raw_info.get('views', raw_info.get('view_count', 0)),
                author=raw_info.get('author', raw_info.get('channel', '')),
                video_id=raw_info.get('video_id', raw_info.get('id', '')),
                url=raw_info.get('url', raw_info.get('watch_url', raw_info.get('video_url', ''))),
                description=raw_info.get('description', None),
                thumbnail=raw_info.get('thumbnail', raw_info.get('thumbnail_url', None)),
                category=raw_info.get('category', None),
                tags=raw_info.get('tags', raw_info.get('keywords', None)),
                published_date=raw_info.get('published_date', raw_info.get('publish_date', None)),
                like_count=raw_info.get('like_count', None),
                comment_count=raw_info.get('comment_count', None)
            )
    
    @staticmethod
    def process_download_result(raw_result: Dict[str, Any]) -> DownloadResult:
        """Convert PyTubeFix download result to standard format."""
        if isinstance(raw_result, str):
            # If raw_result is just a file path string
            return DownloadResult.success_result(
                file_path=raw_result,
                backend_used="pytubefix"
            )
        
        # Handle dict-like structure
        return DownloadResult(
            file_path=raw_result.get('file_path', ''),
            success=raw_result.get('success', True),
            error_message=raw_result.get('error_message', None),
            file_size=raw_result.get('file_size', None),
            download_time=raw_result.get('download_time', None),
            format=raw_result.get('format', None),
            quality=raw_result.get('quality', None),
            backend_used="pytubefix"
        )
    
    @staticmethod
    def process_search_results(raw_results: List[Any]) -> List[VideoInfo]:
        """Convert PyTubeFix search results to standard format."""
        processed_results = []
        for result in raw_results:
            try:
                if hasattr(result, 'watch_url'):
                    # Object-like structure
                    video_info = VideoInfo(
                        title=getattr(result, 'title', ''),
                        duration=getattr(result, 'length', 0),
                        views=getattr(result, 'views', 0),
                        author=getattr(result, 'author', ''),
                        video_id=getattr(result, 'video_id', ''),
                        url=getattr(result, 'watch_url', ''),
                        thumbnail=getattr(result, 'thumbnail_url', None)
                    )
                    processed_results.append(video_info)
            except Exception as e:
                # Skip malformed results
                continue
        
        return processed_results


class YTDLPPostProcessor(BasePostProcessor):
    """Convert YT-DLP output to standardized format."""
    
    @staticmethod
    def process_video_info(raw_info: Dict[str, Any]) -> VideoInfo:
        """Convert YT-DLP video info to standard format."""
        return VideoInfo(
            title=raw_info.get('title', ''),
            duration=raw_info.get('duration', 0),
            views=raw_info.get('view_count', 0),
            author=raw_info.get('uploader', ''),
            video_id=raw_info.get('id', ''),
            url=raw_info.get('webpage_url', ''),
            description=raw_info.get('description', None),
            thumbnail=raw_info.get('thumbnail', None),
            category=raw_info.get('category', None),
            tags=raw_info.get('tags', None),
            published_date=raw_info.get('upload_date', None),
            like_count=raw_info.get('like_count', None),
            comment_count=raw_info.get('comment_count', None)
        )
    
    @staticmethod
    def process_download_result(raw_result: Dict[str, Any]) -> DownloadResult:
        """Convert YT-DLP download result to standard format."""
        return DownloadResult(
            file_path=raw_result.get('file_path', ''),
            success=raw_result.get('success', True),
            error_message=raw_result.get('error_message', None),
            file_size=raw_result.get('file_size', None),
            download_time=raw_result.get('download_time', None),
            format=raw_result.get('format', None),
            quality=raw_result.get('quality', None),
            backend_used="yt-dlp"
        )
    
    @staticmethod
    def process_transcript(raw_transcript: Any) -> str:
        """Convert YT-DLP transcript to standard format."""
        if isinstance(raw_transcript, str):
            return raw_transcript
        
        if isinstance(raw_transcript, list):
            # List of transcript segments
            return '\n'.join([segment.get('text', '') for segment in raw_transcript])
        
        if isinstance(raw_transcript, dict):
            # Dict with transcript data
            return raw_transcript.get('text', '')
        
        return str(raw_transcript)


class YouTubeAPIPostProcessor(BasePostProcessor):
    """Convert YouTube API output to standardized format."""
    
    @staticmethod
    def process_video_info(raw_info: Dict[str, Any]) -> VideoInfo:
        """Convert YouTube API video info to standard format."""
        # Handle YouTube API v3 response structure
        snippet = raw_info.get('snippet', {})
        statistics = raw_info.get('statistics', {})
        content_details = raw_info.get('contentDetails', {})
        
        # Convert ISO 8601 duration to seconds
        duration_str = content_details.get('duration', 'PT0S')
        duration_seconds = YouTubeAPIPostProcessor._parse_duration(duration_str)
        
        return VideoInfo(
            title=snippet.get('title', ''),
            duration=duration_seconds,
            views=int(statistics.get('viewCount', 0)),
            author=snippet.get('channelTitle', ''),
            video_id=raw_info.get('id', ''),
            url=f"https://www.youtube.com/watch?v={raw_info.get('id', '')}",
            description=snippet.get('description', None),
            thumbnail=snippet.get('thumbnails', {}).get('high', {}).get('url', None),
            category=snippet.get('categoryId', None),
            tags=snippet.get('tags', None),
            published_date=snippet.get('publishedAt', None),
            like_count=int(statistics.get('likeCount', 0)),
            comment_count=int(statistics.get('commentCount', 0))
        )
    
    @staticmethod
    def process_comments(raw_comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert YouTube API comments to standard format."""
        processed_comments = []
        
        for comment in raw_comments:
            try:
                snippet = comment.get('snippet', {})
                processed_comment = {
                    'text': snippet.get('textDisplay', ''),
                    'author': snippet.get('authorDisplayName', ''),
                    'likes': snippet.get('likeCount', 0),
                    'published': snippet.get('publishedAt', ''),
                    'replies': []
                }
                
                # Handle replies if present
                if 'replies' in comment:
                    replies = comment['replies'].get('comments', [])
                    for reply in replies:
                        reply_snippet = reply.get('snippet', {})
                        processed_reply = {
                            'text': reply_snippet.get('textDisplay', ''),
                            'author': reply_snippet.get('authorDisplayName', ''),
                            'likes': reply_snippet.get('likeCount', 0),
                            'published': reply_snippet.get('publishedAt', '')
                        }
                        processed_comment['replies'].append(processed_reply)
                
                processed_comments.append(processed_comment)
            except Exception as e:
                # Skip malformed comments
                continue
        
        return processed_comments
    
    @staticmethod
    def _parse_duration(duration_str: str) -> int:
        """Parse ISO 8601 duration string to seconds."""
        import re
        
        # Parse PT1H2M3S format
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration_str)
        
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds


class PostProcessorFactory:
    """Factory for creating appropriate post-processors."""
    
    _processors = {
        'pytubefix': PyTubeFixPostProcessor,
        'yt-dlp': YTDLPPostProcessor,
        'youtube-api': YouTubeAPIPostProcessor
    }
    
    @classmethod
    def get_processor(cls, backend_name: str) -> BasePostProcessor:
        """Get the appropriate post-processor for a backend."""
        processor_class = cls._processors.get(backend_name.lower())
        if processor_class is None:
            raise ValueError(f"Unknown backend: {backend_name}")
        return processor_class()
    
    @classmethod
    def get_available_backends(cls) -> List[str]:
        """Get list of available backend names."""
        return list(cls._processors.keys())
    
    @classmethod
    def register_processor(cls, backend_name: str, processor_class: type):
        """Register a new post-processor."""
        cls._processors[backend_name.lower()] = processor_class

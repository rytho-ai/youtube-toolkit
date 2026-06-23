"""
comments.py — comments-domain service.

Holds comment retrieval, filtering, pagination, export, and the clean-API
CommentResult builder, descended out of YouTubeToolkit (api.py). api.py keeps
one-line delegations; bodies are verbatim moves with self.* -> self._toolkit.*.

Reads: youtube_toolkit.api.YouTubeToolkit (back-ref), handlers via toolkit,
youtube_toolkit.core.comments.* (filters + result dataclasses).
"""

from typing import Optional, List, Dict, Any
from ..core.comments import (
    CommentResult, CommentFilters, Comment, CommentAuthor, CommentMetrics,
)


class CommentsService:
    def __init__(self, toolkit):
        self._toolkit = toolkit

    def get_comments(self, url: str, max_results: int = 100,
                     sort_by: str = 'relevance') -> List[Dict[str, Any]]:
        return self._toolkit.youtube_api.get_comments(url, max_results=max_results, sort_by=sort_by)

    def advanced_get_comments(self, url: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        return self._toolkit.youtube_api.advanced_fetch_comments(url, filters)

    def get_comments_paginated(self, url: str, page_token: Optional[str] = None,
                              max_results: int = 100, order: str = 'relevance') -> Dict[str, Any]:
        from ..core.comments import CommentFilters

        filters = CommentFilters(
            order=CommentFilters.Order(order),
            page_token=page_token,
            max_results=max_results
        )

        return self.advanced_get_comments(url, filters)

    def search_comments(self, url: str, search_term: str, max_results: int = 100) -> Dict[str, Any]:
        from ..core.comments import CommentFilters

        filters = CommentFilters(
            search_terms=search_term,
            max_results=max_results
        )

        return self.advanced_get_comments(url, filters)

    def get_high_engagement_comments(self, url: str, min_likes: int = 10,
                                   max_results: int = 50) -> Dict[str, Any]:
        from ..core.comments import CommentFilters

        filters = CommentFilters(
            min_likes=min_likes,
            max_results=max_results,
            order=CommentFilters.Order.RATING
        )

        return self.advanced_get_comments(url, filters)

    def get_comments_by_author(self, url: str, author_channel_id: str,
                              max_results: int = 100) -> Dict[str, Any]:
        from ..core.comments import CommentFilters

        filters = CommentFilters(
            author_channel_id=author_channel_id,
            max_results=max_results
        )

        return self.advanced_get_comments(url, filters)

    def get_recent_comments(self, url: str, days_back: int = 7,
                           max_results: int = 100) -> Dict[str, Any]:
        from ..core.comments import CommentFilters
        from datetime import datetime, timedelta

        filters = CommentFilters(
            published_after=datetime.now() - timedelta(days=days_back),
            max_results=max_results,
            order=CommentFilters.Order.TIME
        )

        return self.advanced_get_comments(url, filters)

    def export_comments(self, url: str, format: str = 'json',
                       output_path: Optional[str] = None, filters: Optional[Dict] = None) -> str:
        import json
        import csv
        import os
        from datetime import datetime

        # Get comments
        results = self.advanced_get_comments(url, filters)
        comments = results.get('comments', [])

        if not comments:
            raise ValueError("No comments found to export")

        # Generate output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comments_export_{timestamp}.{format}"
            output_path = os.path.join(os.getcwd(), filename)

        if format.lower() == 'json':
            # Export as JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        elif format.lower() == 'csv':
            # Export as CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header
                writer.writerow([
                    'Comment ID', 'Text', 'Author', 'Published At', 'Likes',
                    'Replies', 'Channel ID', 'Is Verified', 'Parent ID'
                ])

                # Write comment data
                for comment in comments:
                    writer.writerow([
                        comment.get('comment_id', ''),
                        comment.get('text', ''),
                        comment.get('author', {}).get('display_name', ''),
                        comment.get('published_at', ''),
                        comment.get('metrics', {}).get('like_count', 0),
                        comment.get('metrics', {}).get('reply_count', 0),
                        comment.get('author', {}).get('channel_id', ''),
                        comment.get('author', {}).get('is_verified', False),
                        comment.get('parent_id', '')
                    ])

        else:
            raise ValueError("Format must be 'json' or 'csv'")

        return output_path

    def display_comments(self, url: str, top_n: int = 3,
                        sort_by: str = 'relevance') -> None:
        comments = self.get_comments(url, max_results=top_n, sort_by=sort_by)

        if not comments:
            print("No comments found for this video.")
            return

        print(f"\n📝 Top {len(comments)} Comments:")
        for i, comment in enumerate(comments, 1):
            author = comment.get('author', 'Unknown')
            text = comment.get('text', 'No text')
            likes = comment.get('like_count', 0)
            print(f"\n{i}. {author} (👍 {likes})")
            print(f"   {text}")

    def comments(self, url: str, max_results: int = 100,
                 filters: Optional[CommentFilters] = None) -> CommentResult:
        if filters is None:
            filters = CommentFilters(max_results=max_results)
        else:
            filters.max_results = max_results

        # Use existing advanced_get_comments
        raw_result = self.advanced_get_comments(url, filters)

        # Convert raw comments to Comment objects
        comments = []
        raw_comments = raw_result.get('comments', [])

        for raw in raw_comments:
            if isinstance(raw, Comment):
                comments.append(raw)
            elif isinstance(raw, dict):
                author_data = raw.get('author', {})
                metrics_data = raw.get('metrics', {})

                author = CommentAuthor(
                    display_name=author_data.get('display_name', 'Unknown'),
                    channel_id=author_data.get('channel_id'),
                    profile_image_url=author_data.get('profile_image_url'),
                    is_verified=author_data.get('is_verified', False),
                    is_channel_owner=author_data.get('is_channel_owner', False),
                )

                metrics = CommentMetrics(
                    like_count=metrics_data.get('like_count', 0),
                    reply_count=metrics_data.get('reply_count', 0),
                )

                from datetime import datetime
                published_at = raw.get('published_at')
                if isinstance(published_at, str):
                    try:
                        published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    except:
                        published_at = datetime.now()
                elif not isinstance(published_at, datetime):
                    published_at = datetime.now()

                comments.append(Comment(
                    comment_id=raw.get('comment_id', ''),
                    text=raw.get('text', ''),
                    author=author,
                    published_at=published_at,
                    metrics=metrics,
                    parent_id=raw.get('parent_id'),
                ))

        return CommentResult(
            comments=comments,
            total_results=raw_result.get('total_results', len(comments)),
            next_page_token=raw_result.get('next_page_token'),
            filters_applied=filters,
            quota_cost=raw_result.get('quota_cost', 1),
        )

    def get_comments_raw(self, url: str, max_comments: int = 100,
                         sort: str = 'top') -> List[Dict[str, Any]]:
        return self._toolkit.yt_dlp.get_comments(url, max_comments, sort)

    def fetch_replies(self, video_id: str, comment_id: str,
                      max_results: int = 50) -> List[Dict[str, Any]]:
        return self._toolkit.youtube_api.fetch_replies(
            video_id,
            comment_id,
            max_results=max_results
        )

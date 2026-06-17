"""
search.py — search/discovery-domain service.

Holds video search (basic + advanced + boolean + paginated + filtered),
category/trending lookups, scrapetube search, and the clean-API SearchResult
builder, descended out of YouTubeToolkit (api.py). api.py keeps one-line
delegations; bodies are verbatim moves with self.* -> self._toolkit.*.

Reads: youtube_toolkit.api.YouTubeToolkit (back-ref), handlers via toolkit,
youtube_toolkit.core.search.* (filters, results, categories),
youtube_toolkit.handlers.scrapetube_handler (lazy import).
"""

from typing import Optional, List, Dict, Any
from ..core.search import SearchResult, SearchFilters, SearchResultItem


class SearchService:
    def __init__(self, toolkit):
        self._toolkit = toolkit

    def search_videos(self, query: str, filters: Optional[Dict] = None, max_results: int = 20) -> List[Dict[str, Any]]:
        results = []

        # Try pytubefix first
        try:
            pytube_results = self._toolkit.pytubefix.search_videos(query, filters, max_results)
            if pytube_results and len(pytube_results) > 0:
                results.extend(pytube_results)
                print(f"✅ PyTubeFix search returned {len(pytube_results)} results")
            else:
                print("⚠️  PyTubeFix search returned no results")
        except Exception as e:
            print(f"PyTubeFix search failed: {e}")

        # If PyTubeFix failed or returned no results, try simple search
        if not results:
            try:
                print("🔍 Trying PyTubeFix simple search fallback...")
                simple_results = self._toolkit.pytubefix.simple_search(query, max_results)
                if simple_results and len(simple_results) > 0:
                    results.extend(simple_results)
                    print(f"✅ PyTubeFix simple search returned {len(simple_results)} results")
                else:
                    print("⚠️  PyTubeFix simple search returned no results")
            except Exception as e:
                print(f"PyTubeFix simple search failed: {e}")

        # If we don't have enough results, try YouTube API
        if len(results) < max_results:
            try:
                remaining_count = max_results - len(results)
                print(f"🔍 Trying YouTube API for {remaining_count} more results...")
                api_results = self._toolkit.youtube_api.search_videos(query, remaining_count)
                if api_results and len(api_results) > 0:
                    results.extend(api_results)
                    print(f"✅ YouTube API search returned {len(api_results)} additional results")
                else:
                    print("⚠️  YouTube API search returned no results")
            except Exception as e:
                print(f"YouTube API search failed: {e}")

        # If still no results, try yt-dlp as last resort
        if not results:
            try:
                print("Trying yt-dlp search as fallback...")
                # Note: yt-dlp doesn't have built-in search, but we can try to get video info
                # This is a placeholder for future implementation
                print("yt-dlp search not implemented yet")
            except Exception as e:
                print(f"yt-dlp search failed: {e}")

        # Limit results to requested max
        if len(results) > max_results:
            results = results[:max_results]

        if not results:
            print("⚠️  All search methods failed. No results found.")
            print("💡 Try:")
            print("   1. Check your internet connection")
            print("   2. Verify the search query is valid")
            print("   3. Check if YouTube API key is set (for enhanced search)")
            print("   4. Try a different search term")
            return []

        print(f"🎯 Total search results: {len(results)}")
        return results

    def advanced_search(self, query: str, filters: Optional[Dict] = None, max_results: int = 20) -> Dict[str, Any]:
        from ..core.search import SearchFilters

        # Convert dict to SearchFilters if needed
        if isinstance(filters, dict):
            filters = SearchFilters(**filters)
        elif filters is None:
            filters = SearchFilters()

        # Try YouTube API first for advanced search (most comprehensive)
        try:
            print(f"🔍 Advanced search: '{query}' with {filters.type} type, order: {filters.order}")
            api_results = self._toolkit.youtube_api.advanced_search(query, filters, max_results)

            if api_results and not api_results.get('error'):
                print(f"✅ YouTube API advanced search returned {len(api_results.get('items', []))} results")
                return api_results
            else:
                print(f"⚠️  YouTube API advanced search failed: {api_results.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"YouTube API advanced search failed: {e}")

        # Fallback to basic search methods
        print("🔄 Falling back to basic search methods...")
        basic_results = self._toolkit.search_videos(query, filters.__dict__ if filters else None, max_results)

        # Convert basic results to advanced format
        from ..core.search import SearchResult, SearchResultItem, Thumbnails, Thumbnail
        from datetime import datetime

        items = []
        for result in basic_results:
            try:
                # Parse published date
                published_at = None
                if result.get('publish_date'):
                    try:
                        published_at = datetime.fromisoformat(result['publish_date'].replace('Z', '+00:00'))
                    except:
                        pass

                # Create basic thumbnail (we don't have thumbnail data from basic search)
                thumbnails = None

                item = SearchResultItem(
                    kind="youtube#video",
                    etag="",
                    video_id=result.get('video_id'),
                    title=result.get('title', ''),
                    description=result.get('description', ''),
                    channel_title=result.get('author', ''),
                    published_at=published_at,
                    thumbnails=thumbnails,
                    live_broadcast_content="none"  # We don't have this info from basic search
                )
                items.append(item)
            except Exception as item_error:
                print(f"Warning: Failed to convert basic result: {item_error}")
                continue

        # Create search result
        search_result = SearchResult(
            items=items,
            total_results=len(items),
            query=query,
            filters_applied=filters,
            backend_used='fallback',
            next_page_token=None,
            prev_page_token=None
        )

        return search_result.to_dict()

    def search_live_content(self, query: str, event_type: str = "live", max_results: int = 20) -> Dict[str, Any]:
        from ..core.search import SearchFilters

        filters = SearchFilters(
            type="video",
            event_type=event_type,
            order="viewCount"  # Sort by current viewers for live content
        )

        return self._toolkit.advanced_search(query, filters, max_results)

    def search_by_category(self, query: str, category_name: str, max_results: int = 20) -> Dict[str, Any]:
        from ..core.search import SearchFilters, YOUTUBE_CATEGORIES

        category_id = YOUTUBE_CATEGORIES.get(category_name)
        if not category_id:
            available_categories = list(YOUTUBE_CATEGORIES.keys())
            raise ValueError(f"Unknown category '{category_name}'. Available categories: {available_categories}")

        filters = SearchFilters(
            type="video",
            video_category_id=category_id
        )

        return self._toolkit.advanced_search(query, filters, max_results)

    def search_sponsored_content(self, query: str, max_results: int = 20) -> Dict[str, Any]:
        from ..core.search import SearchFilters

        filters = SearchFilters(
            type="video",
            video_paid_product_placement="true"
        )

        return self._toolkit.advanced_search(query, filters, max_results)

    def search_with_boolean_query(self, boolean_query: str, filters: Optional[Dict] = None, max_results: int = 20) -> Dict[str, Any]:
        from ..core.search import SearchFilters, BooleanSearchQuery

        # Parse Boolean query
        boolean_search = BooleanSearchQuery.from_string(boolean_query)
        processed_query = boolean_search.build_query()

        # Apply additional filters
        if isinstance(filters, dict):
            search_filters = SearchFilters(**filters)
        elif filters is None:
            search_filters = SearchFilters()
        else:
            search_filters = filters

        return self._toolkit.advanced_search(processed_query, search_filters, max_results)

    def search_paginated(self, query: str, filters: Optional[Dict] = None,
                        page_token: Optional[str] = None, max_results: int = 20) -> Dict[str, Any]:
        from ..core.search import SearchFilters

        if isinstance(filters, dict):
            search_filters = SearchFilters(**filters)
        elif filters is None:
            search_filters = SearchFilters()
        else:
            search_filters = filters

        # Add pagination
        search_filters.page_token = page_token
        search_filters.max_results = max_results

        return self._toolkit.advanced_search(query, search_filters, max_results)

    def get_search_categories(self) -> Dict[str, str]:
        from ..core.search import YOUTUBE_CATEGORIES
        return YOUTUBE_CATEGORIES.copy()

    def search_with_filters(self, query: str,
                            duration: Optional[str] = None,
                            upload_date: Optional[str] = None,
                            sort_by: Optional[str] = None,
                            features: Optional[List[str]] = None,
                            result_type: str = 'video',
                            max_results: int = 20) -> Dict[str, Any]:
        return self._toolkit.pytubefix.advanced_search(
            query=query,
            duration=duration,
            upload_date=upload_date,
            sort_by=sort_by,
            features=features,
            result_type=result_type,
            max_results=max_results
        )

    def search_without_api(self, query: str,
                           limit: int = 20,
                           sort_by: str = 'relevance') -> List[Dict[str, Any]]:
        try:
            from ..handlers.scrapetube_handler import ScrapeTubeHandler
            scrapetube = ScrapeTubeHandler()
            return scrapetube.search(query, limit=limit, sort_by=sort_by)

        except ImportError:
            if self._toolkit.verbose:
                print("⚠️ scrapetube not installed. Using pytubefix search.")
            return self._toolkit.pytubefix.search_videos(query, max_results=limit)

    def search(self, query: str, max_results: int = 20,
               filters: Optional[SearchFilters] = None) -> SearchResult:
        if filters is None:
            filters = SearchFilters()

        filters.max_results = max_results

        # Use existing advanced_search which returns dict
        raw_result = self._toolkit.advanced_search(query, filters, max_results)

        # If already a SearchResult dict format, convert items
        items = []
        raw_items = raw_result.get('items', [])

        for item in raw_items:
            if isinstance(item, SearchResultItem):
                items.append(item)
            elif isinstance(item, dict):
                items.append(SearchResultItem(
                    kind=item.get('kind', 'youtube#video'),
                    etag=item.get('etag', ''),
                    video_id=item.get('video_id', item.get('id', {}).get('videoId', '')),
                    title=item.get('title', item.get('snippet', {}).get('title', '')),
                    description=item.get('description', item.get('snippet', {}).get('description', '')),
                    channel_title=item.get('channel_title', item.get('snippet', {}).get('channelTitle', '')),
                ))

        return SearchResult(
            items=items,
            total_results=raw_result.get('total_results', len(items)),
            query=query,
            filters_applied=filters,
            backend_used=raw_result.get('backend_used', 'mixed'),
            next_page_token=raw_result.get('next_page_token'),
            prev_page_token=raw_result.get('prev_page_token'),
        )

    def get_video_categories(self, region_code: str = 'US',
                            language: str = 'en') -> List[Dict[str, Any]]:
        return self._toolkit.youtube_api.get_video_categories(region_code, language)

    def get_category_by_id(self, category_id: str,
                          language: str = 'en') -> Dict[str, Any]:
        return self._toolkit.youtube_api.get_category_by_id(category_id, language)

    def get_trending_videos(self, region_code: str = 'US',
                           category_id: str = None,
                           max_results: int = 25,
                           page_token: str = None) -> Dict[str, Any]:
        return self._toolkit.youtube_api.get_trending_videos(region_code, category_id, max_results, page_token)

    def get_trending_by_category(self, region_code: str = 'US',
                                 language: str = 'en') -> Dict[str, List[Dict[str, Any]]]:
        return self._toolkit.youtube_api.get_trending_by_category(region_code, language)

    def search_videos_api(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        return self._toolkit.youtube_api.search_videos(query, max_results=limit)

    def search_videos_pytubefix(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        return self._toolkit.pytubefix.search_videos(query, max_results=limit)

    def advanced_search_native(self, query: str, result_type: str = 'video',
                               limit: int = 20) -> Dict[str, Any]:
        return self._toolkit.pytubefix.advanced_search(
            query, result_type=result_type, max_results=limit
        )

    def get_search_suggestions(self, query: str) -> List[str]:
        return self._toolkit.pytubefix.get_search_suggestions(query)

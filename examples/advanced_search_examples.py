"""
Advanced Search Examples for YouTube Toolkit (2.0 sub-API)

This file demonstrates the search capabilities of the 2.0 search sub-API
(toolkit.search), including advanced filtering and result inspection.

NOTE (2.0 migration): The flat toolkit.advanced_search(...) method was removed.
Searches now go through toolkit.search.with_filters(...) / toolkit.search.videos(...).
The native search result dicts use the keys: 'title', 'watch_url', 'video_id',
'author', 'length', 'views', 'publish_date', 'description'. Several API-based
fields (thumbnails, live_broadcast_content, kind, total_results, quota_cost,
backend_used) are no longer exposed by the native search sub-API.
"""

import os
from youtube_toolkit import YouTubeToolkit
# NOTE (2.0): SearchFilters / SearchResult dataclasses are still importable, but
# the native search sub-API no longer consumes/produces them directly, so the
# examples in this file build filters as keyword arguments to search.with_filters.


def setup_toolkit():
    """Initialize YouTube Toolkit with verbose output."""
    return YouTubeToolkit(verbose=True)


def example_basic_advanced_search():
    """Example 1: Basic advanced search with default settings."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Advanced Search")
    print("="*60)

    toolkit = setup_toolkit()

    # Basic advanced search via the 2.0 search sub-API
    results = toolkit.search.with_filters("python programming tutorial")

    videos = results.get('videos', [])
    print(f"Query: 'python programming tutorial'")
    print(f"Videos found: {len(videos)}")
    # NOTE (2.0): per-item 'kind' / 'live_broadcast_content' / thumbnails removed.

    # Display first few results
    for i, item in enumerate(videos[:3], 1):
        print(f"\n{i}. {item.get('title', 'No title')}")
        print(f"   Channel: {item.get('author', 'Unknown')}")
        print(f"   URL: {item.get('watch_url', 'Unknown')}")
        print(f"   Views: {item.get('views', 'Unknown')}")


def example_search_with_filters():
    """Example 2: Search with advanced filters."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Search with Advanced Filters")
    print("="*60)

    toolkit = setup_toolkit()

    # The 2.0 with_filters API takes keyword filters directly.
    results = toolkit.search.with_filters(
        "machine learning",
        duration="medium",      # Medium length videos
        upload_date="month",    # Last month
        sort_by="views",        # Sort by view count
        features=["hd"],        # High definition only
        max_results=10,
    )

    print(f"Query: 'machine learning' with filters")
    print(f"Filters applied:")
    print(f"  - Duration: medium")
    print(f"  - Upload date: month")
    print(f"  - Sort by: views")
    print(f"  - Features: ['hd']")

    videos = results.get('videos', [])
    print(f"\nResults: {len(videos)} videos found")

    # Display results with additional info
    for i, item in enumerate(videos[:3], 1):
        print(f"\n{i}. {item.get('title', 'No title')}")
        print(f"   Channel: {item.get('author', 'Unknown')}")
        print(f"   Published: {item.get('publish_date', 'Unknown')}")
        print(f"   Video ID: {item.get('video_id', 'Unknown')}")


def example_live_content_search():
    """Example 3: Search for live content."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Live Content Search")
    print("="*60)

    toolkit = setup_toolkit()

    # NOTE (2.0): per-item live_broadcast_content flags were removed. Live content
    # is now filtered at the query level via features=['live'].
    results = toolkit.search.with_filters("gaming live stream", features=["live"])

    videos = results.get('videos', [])
    print(f"Query: 'gaming live stream' (features=['live'])")
    print(f"Live results found: {len(videos)}")

    for i, item in enumerate(videos[:3], 1):
        print(f"\n{i}. {item.get('title', 'No title')}")
        print(f"   Channel: {item.get('author', 'Unknown')}")
        print(f"   Video ID: {item.get('video_id', 'Unknown')}")


def example_channel_search():
    """Example 4: Search for channels."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Channel Search")
    print("="*60)

    toolkit = setup_toolkit()

    # In 2.0, channels come back under the 'channels' key of with_filters,
    # or directly via search.channels(...).
    results = toolkit.search.with_filters(
        "tech review", result_type="channel", max_results=10
    )

    channels = results.get('channels', [])
    print(f"Query: 'tech review' channels")
    print(f"Results: {len(channels)} channels found")

    for i, item in enumerate(channels[:3], 1):
        print(f"\n{i}. {item.get('title', 'No title')}")
        print(f"   Author: {item.get('author', 'Unknown')}")
        print(f"   Description: {item.get('description', 'No description')[:100]}...")


def example_thumbnail_management():
    """Example 5: Thumbnail management and analysis."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Thumbnail Management")
    print("="*60)

    # NOTE (2.0): Thumbnail metadata (default/medium/high/standard/maxres URLs and
    # dimensions) is NOT exposed by the native search sub-API anymore. The previous
    # thumbnail-availability analysis relied on the removed API-based search.
    # Below we just run a normal search so main() stays runnable.
    toolkit = setup_toolkit()

    results = toolkit.search.with_filters("nature documentary")
    videos = results.get('videos', [])
    print(f"Query: 'nature documentary'")
    print(f"Results: {len(videos)} videos found")
    print("Thumbnail metadata is not available via the 2.0 search sub-API.")


def example_date_range_search():
    """Example 6: Search within a recent upload window."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Recent Upload Search")
    print("="*60)

    toolkit = setup_toolkit()

    # NOTE (2.0): explicit published_before/published_after date ranges were
    # replaced by coarse upload_date buckets ('hour'/'today'/'week'/'month'/'year').
    results = toolkit.search.with_filters(
        "news",
        upload_date="week",   # Last week
        sort_by="date",       # Sort by date
        duration="short",     # Short videos only
        max_results=10,
    )

    videos = results.get('videos', [])
    print(f"Query: 'news' from the last week")
    print(f"Results: {len(videos)} videos found")

    for i, item in enumerate(videos[:3], 1):
        print(f"\n{i}. {item.get('title', 'No title')}")
        print(f"   Channel: {item.get('author', 'Unknown')}")
        print(f"   Published: {item.get('publish_date', 'Unknown')}")


def example_comprehensive_search():
    """Example 7: Comprehensive search with multiple filters."""
    print("\n" + "="*60)
    print("EXAMPLE 7: Comprehensive Search")
    print("="*60)

    toolkit = setup_toolkit()

    # Combine several 2.0 filters at once. (Region/language/caption/license-level
    # filters from the old API-based search are not part of the native sub-API;
    # 'cc' and 'creative_commons' features are the closest equivalents.)
    results = toolkit.search.with_filters(
        "educational content",
        duration="long",                         # Long videos
        sort_by="rating",                        # Sort by rating
        features=["hd", "cc", "creative_commons"],  # HD + captions + CC license
        max_results=15,
    )

    print(f"Query: 'educational content' with comprehensive filters")
    print(f"Filters:")
    print(f"  - Duration: long")
    print(f"  - Sort by: rating")
    print(f"  - Features: ['hd', 'cc', 'creative_commons']")

    videos = results.get('videos', [])
    print(f"\nResults: {len(videos)} videos found")

    # Show detailed results
    for i, item in enumerate(videos[:3], 1):
        print(f"\n{i}. {item.get('title', 'No title')}")
        print(f"   Channel: {item.get('author', 'Unknown')}")
        print(f"   Description: {item.get('description', 'No description')[:150]}...")
        print(f"   Video ID: {item.get('video_id', 'Unknown')}")


def example_search_result_analysis():
    """Example 8: Analyze search results."""
    print("\n" + "="*60)
    print("EXAMPLE 8: Search Result Analysis")
    print("="*60)

    toolkit = setup_toolkit()

    # NOTE (2.0): The rich SearchResult analysis (thumbnails summary, live content
    # counts, kind counts, SearchResult.from_dict over an 'items' list) relied on
    # the removed API-based search. Here we analyze the plain list returned by
    # search.videos() directly using len()/simple aggregation.
    videos = toolkit.search.videos("python tutorial", limit=20)

    print(f"Query: 'python tutorial'")
    print(f"Videos found: {len(videos)}")

    # Count items per channel using the native 'author' key.
    by_channel = {}
    for item in videos:
        author = item.get('author', 'Unknown')
        by_channel[author] = by_channel.get(author, 0) + 1

    print(f"Distinct channels: {len(by_channel)}")

    # Show a few of the most prolific channels in this result set.
    top_channels = sorted(by_channel.items(), key=lambda kv: kv[1], reverse=True)[:3]
    print(f"\nTop channels in results:")
    for i, (author, count) in enumerate(top_channels, 1):
        print(f"  {i}. {author}: {count} videos")

    # Show first few titles.
    print(f"\nFirst few results:")
    for i, item in enumerate(videos[:3], 1):
        print(f"  {i}. {item.get('title', 'No title')} ({item.get('publish_date', 'Unknown')})")


def main():
    """Run all examples."""
    print("YouTube Toolkit - Advanced Search Examples")
    print("=" * 60)

    # Check if API key is available
    if not os.getenv("YOUTUBE_API_KEY"):
        print("⚠️  Warning: YOUTUBE_API_KEY not set. Some features may not work.")
        print("   Set your API key: export YOUTUBE_API_KEY='your_api_key_here'")
        print("   Get API key from: https://console.developers.google.com/")
        print()

    try:
        example_basic_advanced_search()
        example_search_with_filters()
        example_live_content_search()
        example_channel_search()
        example_thumbnail_management()
        example_date_range_search()
        example_comprehensive_search()
        example_search_result_analysis()

        print("\n" + "="*60)
        print("All examples completed successfully!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("Make sure you have:")
        print("1. Installed all dependencies: uv add google-api-python-client")
        print("2. Set your YouTube API key: export YOUTUBE_API_KEY='your_key'")
        print("3. Internet connection for API calls")


if __name__ == "__main__":
    main()

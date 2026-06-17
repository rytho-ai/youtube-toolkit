"""
Advanced Features Examples for YouTube Toolkit (2.0 sub-API)

This file demonstrates search features through the 2.0 search sub-API
(toolkit.search). Several API-based capabilities were removed in 2.0; where a
capability no longer has a sub-API equivalent it is replaced with the closest
available call and an inline note.

NOTE (2.0 migration): The flat toolkit.* search methods were removed. Use
toolkit.search.with_filters(...) / toolkit.search.videos(...). Native result
dicts use keys 'title', 'watch_url', 'video_id', 'author', 'length', 'views',
'publish_date', 'description'. The fields quota_cost / api_info / total_results /
next_page_token / live_broadcast_content / thumbnails are no longer exposed.
"""

import os
from youtube_toolkit import YouTubeToolkit, SearchFilters, BooleanSearchQuery, YOUTUBE_CATEGORIES


def setup_toolkit():
    """Initialize YouTube Toolkit with verbose output."""
    return YouTubeToolkit(verbose=True)


def example_event_type_filtering():
    """Example 1: Live content filtering."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Live Content Filtering")
    print("="*70)

    toolkit = setup_toolkit()

    # NOTE (2.0): toolkit.search_live_content(query, event_type=...) was removed.
    # event_type filtering (live / upcoming / completed) is no longer available;
    # the closest equivalent is the 'live' feature filter, which returns currently
    # live results only. Per-item live_broadcast_content status flags were removed.
    print("🔴 Searching for LIVE streams (features=['live'])...")
    live_results = toolkit.search.with_filters("gaming", features=["live"], max_results=10)

    videos = live_results.get('videos', [])
    print(f"Live results found: {len(videos)}")
    for i, item in enumerate(videos[:3], 1):
        print(f"  {i}. {item.get('title', 'No title')}")
        print(f"     Channel: {item.get('author', 'Unknown')}")
        print(f"     URL: {item.get('watch_url', 'Unknown')}")


def example_category_filtering():
    """Example 2: Category awareness."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Category Awareness")
    print("="*70)

    toolkit = setup_toolkit()

    # The old static name->id map is now the YOUTUBE_CATEGORIES constant.
    print("Available YouTube categories (from YOUTUBE_CATEGORIES constant):")
    for name, category_id in list(YOUTUBE_CATEGORIES.items())[:10]:  # Show first 10
        print(f"  {name}: {category_id}")
    print(f"  ... and {len(YOUTUBE_CATEGORIES) - 10} more categories")

    # NOTE (2.0): toolkit.search_by_category(query, category, ...) was removed and
    # has no sub-API equivalent. We demonstrate a plain query search instead; the
    # YOUTUBE_CATEGORIES constant is still useful for mapping names to category ids.
    print("\n🎯 Category-scoped search was removed in 2.0; running a plain search...")
    results = toolkit.search.with_filters("gaming tutorial", max_results=5)
    videos = results.get('videos', [])
    print(f"  Found {len(videos)} results")
    for i, item in enumerate(videos[:2], 1):
        print(f"    {i}. {item.get('title', 'No title')}")
        print(f"       Channel: {item.get('author', 'Unknown')}")


def example_sponsored_content_detection():
    """Example 3: Sponsored content detection (removed in 2.0)."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Sponsored Content Detection")
    print("="*70)

    # NOTE (2.0): toolkit.search_sponsored_content(...) was removed and has no
    # sub-API equivalent. There is no native flag for sponsored content anymore.
    print("Sponsored content detection was removed in 2.0 (no sub-API equivalent).")


def example_boolean_search():
    """Example 4: Boolean query building."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Boolean Query Building")
    print("="*70)

    toolkit = setup_toolkit()

    # NOTE (2.0): toolkit.search_with_boolean_query(...) was removed and native
    # boolean-operator parsing is gone. The BooleanSearchQuery helper still exists
    # to BUILD a plain query string, which we then pass to search.with_filters().
    print("🔧 Building a query with BooleanSearchQuery and passing the string...")
    boolean_query = BooleanSearchQuery()
    boolean_query.add_term("artificial intelligence")
    boolean_query.add_excluded_term("beginner")
    boolean_query.add_or_group(["tutorial", "course", "guide"])

    query_string = boolean_query.build_query()
    print(f"Built query: {query_string}")

    results = toolkit.search.with_filters(query_string, max_results=10)
    videos = results.get('videos', [])
    print(f"Results for built query: {len(videos)}")
    for i, item in enumerate(videos[:3], 1):
        print(f"  {i}. {item.get('title', 'No title')}")
        print(f"     Channel: {item.get('author', 'Unknown')}")


def example_pagination():
    """Example 5: Result count control (pagination removed in 2.0)."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Result Count Control")
    print("="*70)

    toolkit = setup_toolkit()

    # NOTE (2.0): toolkit.search_paginated(...) was removed; there is no
    # next_page_token / pagination sub-API. Use max_results to cap the number of
    # results returned in a single call.
    print("📄 Pagination was removed in 2.0; capping results with max_results...")
    results = toolkit.search.with_filters("python programming", max_results=5)

    videos = results.get('videos', [])
    print(f"Results: {len(videos)} (max_results=5)")
    for i, item in enumerate(videos, 1):
        print(f"  {i}. {item.get('title', 'No title')}")


def example_comprehensive_filtering():
    """Example 6: Comprehensive Filtering with Multiple Criteria."""
    print("\n" + "="*70)
    print("EXAMPLE 6: Comprehensive Filtering")
    print("="*70)

    toolkit = setup_toolkit()

    # Combine several 2.0 keyword filters. (Region/language/caption/license-level
    # API filters were removed; 'cc' and 'creative_commons' features are the
    # closest equivalents.)
    print("🔍 Comprehensive search with multiple filters...")
    print("Filters applied:")
    print(f"  - Duration: medium")
    print(f"  - Upload date: month")
    print(f"  - Sort by: rating")
    print(f"  - Features: ['hd', 'cc', 'creative_commons']")

    results = toolkit.search.with_filters(
        "educational content",
        duration="medium",
        upload_date="month",
        sort_by="rating",
        features=["hd", "cc", "creative_commons"],
        max_results=10,
    )

    videos = results.get('videos', [])
    print(f"\nResults: {len(videos)} videos found")
    # NOTE (2.0): quota_cost / api_info are no longer part of search results.

    for i, item in enumerate(videos[:3], 1):
        print(f"\n{i}. {item.get('title', 'No title')}")
        print(f"   Channel: {item.get('author', 'Unknown')}")
        print(f"   Published: {item.get('publish_date', 'Unknown')}")
        print(f"   Description: {item.get('description', 'No description')[:100]}...")


def example_filter_validation():
    """Example 7: Filter Validation."""
    print("\n" + "="*70)
    print("EXAMPLE 7: Filter Validation")
    print("="*70)

    # This example only constructs SearchFilters and calls validate_filters(),
    # which the dataclass still supports in 2.0.
    print("🧪 Testing filter validation...")

    # Invalid: eventType without video type
    invalid_filters1 = SearchFilters(
        type="channel",  # Wrong type
        event_type="live"  # Requires video type
    )

    errors1 = invalid_filters1.validate_filters()
    print(f"Invalid filters 1 errors: {errors1}")

    # Invalid: forContentOwner with video filters
    invalid_filters2 = SearchFilters(
        type="video",
        for_content_owner=True,
        video_duration="medium"  # Conflicts with forContentOwner
    )

    errors2 = invalid_filters2.validate_filters()
    print(f"Invalid filters 2 errors: {errors2}")

    # Valid filters
    valid_filters = SearchFilters(
        type="video",
        event_type="live",
        order="viewCount"
    )

    errors3 = valid_filters.validate_filters()
    print(f"Valid filters errors: {errors3}")


def example_content_ownership_features():
    """Example 8: Content Ownership Features (Enterprise)."""
    print("\n" + "="*70)
    print("EXAMPLE 8: Content Ownership Features")
    print("="*70)

    print("🏢 Enterprise Content Ownership Features:")
    print("  - forContentOwner: Search only content owner's videos")
    print("  - forDeveloper: Search only developer-uploaded videos")
    print("  - forMine: Search only authenticated user's videos")
    print("  - onBehalfOfContentOwner: Search on behalf of content owner")

    # Note: These features require proper authentication
    print(f"\n⚠️  Note: Content ownership features require:")
    print(f"  - Proper OAuth2 authentication")
    print(f"  - Content owner permissions")
    print(f"  - Developer account setup")

    # Example filter setup (won't work without proper auth)
    enterprise_filters = SearchFilters(
        type="video",
        for_mine=True,  # Would search user's own videos
        order="date"
    )

    print(f"\nExample enterprise filter setup:")
    print(f"  - forMine: {enterprise_filters.for_mine}")
    print(f"  - Type: {enterprise_filters.type}")
    print(f"  - Order: {enterprise_filters.order}")


def main():
    """Run all advanced feature examples."""
    print("YouTube Toolkit - Advanced Features Examples")
    print("=" * 70)

    # Check if API key is available
    if not os.getenv("YOUTUBE_API_KEY"):
        print("⚠️  Warning: YOUTUBE_API_KEY not set. Some features may not work.")
        print("   Set your API key: export YOUTUBE_API_KEY='your_api_key_here'")
        print("   Get API key from: https://console.developers.google.com/")
        print()

    try:
        example_event_type_filtering()
        example_category_filtering()
        example_sponsored_content_detection()
        example_boolean_search()
        example_pagination()
        example_comprehensive_filtering()
        example_filter_validation()
        example_content_ownership_features()

        print("\n" + "="*70)
        print("All advanced feature examples completed successfully!")
        print("="*70)

        print("\n🎯 Key Features Demonstrated:")
        print("  ✅ Live content filtering (features=['live'])")
        print("  ✅ Category awareness (YOUTUBE_CATEGORIES constant)")
        print("  ✅ Boolean query building (BooleanSearchQuery -> query string)")
        print("  ✅ Result count control (max_results)")
        print("  ✅ Comprehensive filtering")
        print("  ✅ Filter validation")
        print("  ✅ Content ownership features (filter setup)")
        print("  ℹ️  Removed in 2.0: event_type / category search / sponsored")
        print("      detection / native boolean parsing / pagination / quota info")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("Make sure you have:")
        print("1. Installed all dependencies: uv add google-api-python-client")
        print("2. Set your YouTube API key: export YOUTUBE_API_KEY='your_key'")
        print("3. Internet connection for API calls")


if __name__ == "__main__":
    main()

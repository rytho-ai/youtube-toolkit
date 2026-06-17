"""
Advanced Comments Examples for YouTube Toolkit

Migrated to the 2.0.0 sub-API surface. The flat ``toolkit.*`` comment methods
were removed; comment retrieval now goes through ``toolkit.analyze.comments``.

``analyze.comments(url, max_comments=100, sort='relevance'|'time')`` returns a
``CommentResult`` dataclass with:
  - ``.comments``      -> list of ``Comment`` objects (attribute access, not dicts)
  - ``.total_results`` -> int
  - ``.quota_cost``    -> int
  - ``.analytics``     -> ``CommentAnalytics`` or ``None``

Each ``Comment`` exposes ``.text``, ``.comment_id``, ``.parent_id``,
``.published_at``, ``.author`` (``.author.display_name``) and
``.metrics`` (``.metrics.like_count`` / ``.metrics.reply_count``), plus
``.replies`` and helper properties (``.is_top_level``, ``.has_replies``).
"""

import os
from datetime import datetime, timedelta
from youtube_toolkit import YouTubeToolkit, CommentSentimentAnalyzer


def setup_toolkit():
    """Initialize YouTube Toolkit with verbose output."""
    return YouTubeToolkit(verbose=True)


def example_basic_advanced_comments():
    """Example 1: Basic Advanced Comment Retrieval."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Advanced Comment Retrieval")
    print("="*70)

    toolkit = setup_toolkit()

    # Basic advanced comment retrieval -> analyze.comments returns CommentResult
    result = toolkit.analyze.comments("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    print(f"Total comments: {result.total_results}")
    print(f"Comments retrieved: {len(result.comments)}")
    print(f"Quota cost: {result.quota_cost} units")

    # Display analytics (CommentAnalytics dataclass, or None)
    analytics = result.analytics
    if analytics:
        print(f"\n📊 Analytics:")
        print(f"  - Total comments: {getattr(analytics, 'total_comments', 0)}")
        print(f"  - Total replies: {getattr(analytics, 'total_replies', 0)}")
        print(f"  - Total likes: {getattr(analytics, 'total_likes', 0)}")
        print(f"  - Unique authors: {getattr(analytics, 'unique_authors', 0)}")

    # Display first few comments (Comment objects -> attribute access)
    for i, comment in enumerate(result.comments[:3], 1):
        print(f"\n{i}. {comment.text[:100]}...")
        print(f"   Author: {comment.author.display_name}")
        print(f"   Likes: {comment.metrics.like_count}")
        print(f"   Replies: {comment.metrics.reply_count}")


def example_comment_filtering():
    """Example 2: Comment Filtering (client-side)."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Comment Filtering")
    print("="*70)

    toolkit = setup_toolkit()

    # NOTE: `get_high_engagement_comments` and `search_comments` were removed in
    # 2.0 with no sub-API equivalent. Fetch via analyze.comments and filter
    # client-side instead.
    result = toolkit.analyze.comments(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        max_comments=50,
    )

    # Filter for high engagement comments (10+ likes)
    print("🔥 High engagement comments (10+ likes)...")
    high_engagement = [c for c in result.comments if c.metrics.like_count >= 10]
    print(f"High engagement comments: {len(high_engagement)}")
    for i, comment in enumerate(high_engagement[:3], 1):
        print(f"  {i}. {comment.text[:80]}...")
        print(f"     Likes: {comment.metrics.like_count}")

    # Search within comments (client-side text match)
    print(f"\n🔍 Searching for 'great' in comments...")
    matches = [c for c in result.comments if 'great' in c.text.lower()]
    print(f"Comments containing 'great': {len(matches)}")
    for i, comment in enumerate(matches[:3], 1):
        print(f"  {i}. {comment.text[:100]}...")


def example_comment_sorting():
    """Example 3: Comment Sorting."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Comment Sorting")
    print("="*70)

    toolkit = setup_toolkit()

    # NOTE: token-based pagination (`get_comments_paginated`) was removed in 2.0.
    # analyze.comments supports sort ('relevance' or 'time') and max_comments.
    print("📄 Top comments by relevance...")
    relevant = toolkit.analyze.comments(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        max_comments=10,
        sort='relevance',
    )
    print(f"Relevance: {len(relevant.comments)} comments")
    print(f"Total results: {relevant.total_results}")

    print(f"\n📄 Newest comments by time...")
    newest = toolkit.analyze.comments(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        max_comments=10,
        sort='time',
    )
    print(f"Time: {len(newest.comments)} comments")
    for i, comment in enumerate(newest.comments[:3], 1):
        print(f"  {i}. {comment.text[:80]}...")


def example_comment_analytics():
    """Example 4: Comment Analytics and Insights."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Comment Analytics and Insights")
    print("="*70)

    toolkit = setup_toolkit()

    # Get comments with analytics
    result = toolkit.analyze.comments(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        max_comments=50,
    )

    analytics = result.analytics
    if analytics:
        print("📊 Comment Analytics:")
        print(f"  - Total comments: {getattr(analytics, 'total_comments', 0)}")
        print(f"  - Total replies: {getattr(analytics, 'total_replies', 0)}")
        print(f"  - Total likes: {getattr(analytics, 'total_likes', 0)}")
        print(f"  - Unique authors: {getattr(analytics, 'unique_authors', 0)}")

        # Top authors
        top_authors = getattr(analytics, 'top_authors', [])
        if top_authors:
            print(f"\n👥 Top Contributors:")
            for i, author in enumerate(top_authors[:5], 1):
                print(f"  {i}. {author.get('name', 'Unknown')}: {author.get('comment_count', 0)} comments")
    else:
        # Fall back to deriving simple stats from the Comment objects directly
        comments = result.comments
        total_likes = sum(c.metrics.like_count for c in comments)
        print("📊 Derived stats (no analytics object returned):")
        print(f"  - Comments: {len(comments)}")
        print(f"  - Total likes: {total_likes}")

    # Most liked comments (derived client-side)
    most_liked = sorted(result.comments, key=lambda c: c.metrics.like_count, reverse=True)
    if most_liked:
        print(f"\n👍 Most Liked Comments:")
        for i, comment in enumerate(most_liked[:3], 1):
            print(f"  {i}. {comment.text[:60]}...")
            print(f"     Likes: {comment.metrics.like_count}")


def example_sentiment_analysis():
    """Example 5: Comment Sentiment Analysis."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Comment Sentiment Analysis")
    print("="*70)

    toolkit = setup_toolkit()

    # Get comments for sentiment analysis
    result = toolkit.analyze.comments(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        max_comments=30,
    )

    # CommentSentimentAnalyzer is still available for manual sentiment scoring.
    print("🔍 Manual Sentiment Analysis:")
    for i, comment in enumerate(result.comments[:5], 1):
        text = comment.text
        sentiment_scores = CommentSentimentAnalyzer.analyze_sentiment(text)
        sentiment_label = CommentSentimentAnalyzer.get_sentiment_label(sentiment_scores)

        print(f"  {i}. {text[:50]}...")
        print(f"     Sentiment: {sentiment_label} (P:{sentiment_scores['positive']:.2f}, N:{sentiment_scores['negative']:.2f})")

    # Aggregate sentiment across the batch
    labels = [
        CommentSentimentAnalyzer.get_sentiment_label(
            CommentSentimentAnalyzer.analyze_sentiment(c.text)
        )
        for c in result.comments
    ]
    if labels:
        positive = labels.count('positive')
        negative = labels.count('negative')
        total = len(labels)
        print(f"\n😊 Aggregate Sentiment ({total} comments):")
        print(f"  - Positive: {positive / total:.2%}")
        print(f"  - Negative: {negative / total:.2%}")


def example_recent_comments():
    """Example 6: Recent Comments."""
    print("\n" + "="*70)
    print("EXAMPLE 6: Recent Comments")
    print("="*70)

    toolkit = setup_toolkit()

    # NOTE: `get_recent_comments(days_back=...)` was removed in 2.0. Use
    # sort='time' to retrieve the newest comments, then filter by date
    # client-side if needed.
    result = toolkit.analyze.comments(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        max_comments=20,
        sort='time',
    )

    print("📅 Newest comments...")
    cutoff = datetime.now() - timedelta(days=7)
    recent = []
    for c in result.comments:
        published = c.published_at
        # published_at is a datetime; tolerate naive/aware comparison failures
        try:
            if published.replace(tzinfo=None) >= cutoff:
                recent.append(c)
        except Exception:
            recent.append(c)

    print(f"Comments in last 7 days (approx): {len(recent)}")
    for i, comment in enumerate(result.comments[:3], 1):
        print(f"  {i}. {comment.text[:60]}...")
        print(f"     Published: {comment.published_at}")
        print(f"     Author: {comment.author.display_name}")


def example_comprehensive_comment_analysis():
    """Example 7: Comprehensive Comment Analysis."""
    print("\n" + "="*70)
    print("EXAMPLE 7: Comprehensive Comment Analysis")
    print("="*70)

    toolkit = setup_toolkit()

    print("🔍 Comprehensive comment analysis...")
    print("Settings applied:")
    print(f"  - Max comments: 100")
    print(f"  - Sort: relevance")

    result = toolkit.analyze.comments(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        max_comments=100,
        sort='relevance',
    )

    print(f"\n📊 Results:")
    print(f"  - Comments found: {len(result.comments)}")
    print(f"  - Total results: {result.total_results}")
    print(f"  - Quota cost: {result.quota_cost} units")

    # Analyze comment structure (Comment objects)
    comments = result.comments
    top_level_count = len([c for c in comments if c.is_top_level])
    reply_count = len([c for c in comments if c.is_reply])

    print(f"\n📝 Comment Structure:")
    print(f"  - Top-level comments: {top_level_count}")
    print(f"  - Replies: {reply_count}")

    # Show sample comments with replies
    comments_with_replies = [c for c in comments if c.has_replies]
    if comments_with_replies:
        print(f"\n💬 Sample comment with replies:")
        sample = comments_with_replies[0]
        print(f"  Main: {sample.text[:80]}...")
        print(f"  Likes: {sample.metrics.like_count}")
        print(f"  Replies ({len(sample.replies)}):")
        for i, reply in enumerate(sample.replies[:3], 1):
            print(f"    {i}. {reply.text[:60]}...")


def example_comment_threading():
    """Example 8: Comment Threading and Reply Management."""
    print("\n" + "="*70)
    print("EXAMPLE 8: Comment Threading and Reply Management")
    print("="*70)

    toolkit = setup_toolkit()

    # Get comments with replies
    result = toolkit.analyze.comments(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        max_comments=20,
    )

    comments = result.comments

    print("🧵 Comment Threading Analysis:")
    print(f"  - Total comments: {len(comments)}")

    # Analyze threading
    threads_with_replies = 0
    total_replies = 0
    max_replies_in_thread = 0

    for comment in comments:
        replies = comment.replies
        if replies:
            threads_with_replies += 1
            total_replies += len(replies)
            max_replies_in_thread = max(max_replies_in_thread, len(replies))

    print(f"  - Threads with replies: {threads_with_replies}")
    print(f"  - Total replies: {total_replies}")
    print(f"  - Max replies in single thread: {max_replies_in_thread}")

    # Show threaded conversation
    print(f"\n💬 Sample Threaded Conversation:")
    for i, comment in enumerate(comments[:2], 1):
        if comment.has_replies:
            print(f"\n{i}. {comment.text[:60]}...")
            print(f"   Author: {comment.author.display_name}")
            print(f"   Likes: {comment.metrics.like_count}")

            replies = comment.replies
            print(f"   Replies ({len(replies)}):")
            for j, reply in enumerate(replies[:3], 1):
                print(f"     {j}. {reply.text[:50]}...")
                print(f"        Author: {reply.author.display_name}")

            if len(replies) > 3:
                print(f"     ... and {len(replies) - 3} more replies")


def main():
    """Run all advanced comment examples."""
    print("YouTube Toolkit - Advanced Comments Examples")
    print("=" * 70)

    # Check if API key is available
    if not os.getenv("YOUTUBE_API_KEY"):
        print("⚠️  Warning: YOUTUBE_API_KEY not set. Some features may not work.")
        print("   Set your API key: export YOUTUBE_API_KEY='your_api_key_here'")
        print("   Get API key from: https://console.developers.google.com/")
        print()

    try:
        example_basic_advanced_comments()
        example_comment_filtering()
        example_comment_sorting()
        example_comment_analytics()
        example_sentiment_analysis()
        example_recent_comments()
        example_comprehensive_comment_analysis()
        example_comment_threading()

        print("\n" + "="*70)
        print("All advanced comment examples completed successfully!")
        print("="*70)

        print("\n🎯 Key Features Demonstrated:")
        print("  ✅ Comment retrieval with analytics (analyze.comments)")
        print("  ✅ Client-side comment filtering (engagement, text search)")
        print("  ✅ Sorting (relevance / time)")
        print("  ✅ Comment analytics and insights")
        print("  ✅ Sentiment analysis (CommentSentimentAnalyzer)")
        print("  ✅ Recent comments (sort='time')")
        print("  ✅ Comprehensive comment analysis")
        print("  ✅ Comment threading and reply management")
        print("\nℹ️  Removed in 2.0 (no sub-API): get_high_engagement_comments,")
        print("   search_comments, get_comments_paginated (token pagination),")
        print("   get_recent_comments(days_back=), export_comments, display_comments.")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("Make sure you have:")
        print("1. Installed all dependencies: uv add google-api-python-client")
        print("2. Set your YouTube API key: export YOUTUBE_API_KEY='your_key'")
        print("3. Internet connection for API calls")


if __name__ == "__main__":
    main()

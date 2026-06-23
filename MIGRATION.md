# Migrating to 2.0.0 — flat methods removed, use the sub-APIs

`youtube-toolkit` 2.0.0 removes the ~100 legacy flat `YouTubeToolkit` methods
(`toolkit.get_video_info(...)`, `toolkit.download_audio(...)`, …). The public
surface is now exactly the **five core sub-APIs**:

```python
toolkit.get        # retrieve information
toolkit.download   # save to disk
toolkit.search     # find content
toolkit.analyze    # analyze content
toolkit.stream     # stream to buffer
```

Plus two bare helpers that have no sub-API home:

- `toolkit.extract_video_id(url)` — **still on the toolkit, unchanged.**
- `toolkit._sanitize_filename(...)` — internal helper (was never public).

If your code already uses only the sub-APIs (the common case), nothing changes.
If you called any flat method, use the table below.

## Why

The flat methods were thin one-line delegations that duplicated the sub-API
surface. They are gone so there is a single canonical public API. The behaviour
behind each sub-API call is identical to the old flat method it replaces.

---

## Flat method → sub-API

### GET — video / metadata / chapters / formats

| Removed flat method | New call |
|---|---|
| `get_video_info(url)` | `toolkit.get.video(url)` |
| `get_video(url)` | `toolkit.get.video(url)` |
| `get_shorts_info(url)` | `toolkit.get.video(url)` |
| `get_full_metadata(url)` | `toolkit.get.metadata(url)` |
| `get_rich_metadata(url)` | `toolkit.get.metadata(url)` |
| `get_video_description(url)` | `toolkit.get.metadata(url)` |
| `get_chapters(url)` | `toolkit.get.chapters(url)` |
| `get_video_chapters(url)` | `toolkit.get.chapters(url)` |
| `get_available_formats(url)` | `toolkit.get.formats(url)` |
| `get_captions(url)` | `toolkit.get.captions(url)` |
| `list_captions(url)` | `toolkit.get.captions(url)` |

### GET — channel

| Removed flat method | New call |
|---|---|
| `get_channel_info(channel)` | `toolkit.get.channel(channel)` |
| `get_channel_info_full(...)` | `toolkit.get.channel(channel)` |
| `get_channel_videos(channel, limit=...)` | `toolkit.get.channel.videos(channel, limit=...)` |
| `get_all_channel_videos(channel)` | `toolkit.get.channel.all_videos(channel)` |
| `get_channel_shorts(channel)` | `toolkit.get.channel.shorts(channel)` |

### GET — playlist

| Removed flat method | New call |
|---|---|
| `get_playlist_info(url)` | `toolkit.get.playlist(url)` |
| `get_playlist_urls(url)` | `toolkit.get.playlist.urls(url)` |
| `playlist(url)` | `toolkit.get.playlist.urls(url)` |

### DOWNLOAD

| Removed flat method | New call |
|---|---|
| `download_audio(url, ...)` | `toolkit.download.audio(url, ...)` |
| `download_video(url, ...)` | `toolkit.download.video(url, ...)` |
| `download(url, type=...)` | `toolkit.download(url, ...)` (sub-API is callable) |
| `download_short(url)` | `toolkit.download.shorts(url)` |
| `download_live_stream(url)` | `toolkit.download.live(url)` |
| `download_captions(url, ...)` | `toolkit.download.captions(url, ...)` |
| `download_thumbnail(url)` | `toolkit.download.thumbnail(url)` |
| `download_with_sponsorblock(url)` | `toolkit.download.with_sponsorblock(url)` |
| `download_with_archive(url, ...)` | `toolkit.download.with_archive(url, ...)` |
| `download_with_filter(url, ...)` | `toolkit.download.with_filter(url, ...)` |
| `download_audio_with_metadata(url, ...)` | `toolkit.download.with_metadata(url, ...)` |
| `download_with_metadata_files(url, ...)` | `toolkit.download.with_metadata(url, ...)` |
| `download_playlist_media(url, ...)` | `toolkit.download.playlist(url, ...)` |
| `download_many(urls, ...)` | `toolkit.download.many(urls, ...)` |

### SEARCH

| Removed flat method | New call |
|---|---|
| `search_videos(query)` | `toolkit.search.videos(query)` |
| `search_without_api(query, limit=, sort_by=)` | `toolkit.search.videos(query, limit=, sort_by=)` (no-API path; the default) |
| `advanced_search(query, ...)` | `toolkit.search.with_filters(query, ...)` |
| `search_with_filters(query, ...)` | `toolkit.search.with_filters(query, ...)` |
| `get_trending_videos(...)` | `toolkit.search.trending(...)` |
| `get_trending_by_category(...)` | `toolkit.search.trending.by_category(...)` |
| `get_search_categories()` | `toolkit.search.categories()` *(see note)* |
| `get_video_categories(...)` | `toolkit.search.categories(...)` |
| `get_supported_regions(...)` | `toolkit.search.regions(...)` |
| `get_supported_languages(...)` | `toolkit.search.languages(...)` |

> Note: the old `get_search_categories()` returned a *static* name→id mapping.
> That static mapping is still available as the public `YOUTUBE_CATEGORIES`
> constant (`from youtube_toolkit import YOUTUBE_CATEGORIES`).
> `toolkit.search.categories()` is the API-based variant (live, region-aware,
> returns a list of category dicts).

### ANALYZE — engagement / sponsorblock / comments

| Removed flat method | New call |
|---|---|
| `get_heatmap(url)` | `toolkit.analyze.engagement(url)` |
| `get_replayed_heatmap(url)` | `toolkit.analyze.engagement(url)` |
| `get_key_moments(url)` | `toolkit.analyze.engagement(url)` |
| `get_sponsorblock_segments(url)` | `toolkit.analyze.sponsorblock(url)` |
| `get_comments(url, ...)` | `toolkit.analyze.comments(url, ...)` |
| `advanced_get_comments(url, ...)` | `toolkit.analyze.comments(url, ...)` |
| `get_comments_paginated(url, ...)` | `toolkit.analyze.comments(url, ...)` |
| `get_recent_comments(url, ...)` | `toolkit.analyze.comments(url, ...)` |

### STREAM — live status / buffers

| Removed flat method | New call |
|---|---|
| `is_live(url)` | `toolkit.stream.live.status(url)` |
| `get_live_status(url)` | `toolkit.stream.live.status(url)` |
| `stream_to_buffer(url, 'audio')` | `toolkit.stream.audio(url)` |
| `stream_to_buffer(url, 'video')` | `toolkit.stream.video(url)` |

### Unchanged

| Still on the toolkit |
|---|
| `toolkit.extract_video_id(url)` |

---

## Removed without a sub-API equivalent (re-add on request)

These flat methods had no corresponding sub-API entry and were removed under
YAGNI. They are preserved in git history and can be re-added (with a proper
sub-API home) on request:

- **Diagnostics / capabilities**: `test_handlers`, `test_search`,
  `test_anti_detection`, `get_anti_detection_status`, `get_supported_browsers`,
  `get_supported_subtitle_formats`.
- **Captions extras**: `advanced_download_captions`, `get_captions_in_format`,
  `search_captions`, `get_caption_analytics`, `export_captions`,
  `get_best_caption_track`.
- **Subtitles**: `download_subtitles`, `convert_subtitles`.
- **Comments extras**: `search_comments`, `get_high_engagement_comments`,
  `get_comments_by_author`, `export_comments`, `display_comments`,
  `get_comments_raw`.
- **Search extras**: `search_live_content`, `search_by_category`,
  `search_sponsored_content`, `search_with_boolean_query`, `search_paginated`,
  `get_category_by_id`.
- **Channel extras**: `get_channel_subscriptions`, `check_subscription`,
  `get_channel_activities`, `get_recent_uploads`, `get_channel_sections`,
  `get_channel_featured_channels`, `get_multiple_channels`.
- **Download / filter extras**: `get_videos_matching_filter`, `filter_playlist`,
  `batch_download_with_filter`, `batch_download_shorts`, `split_by_chapters`,
  `export_metadata_only`, `is_in_archive`, `is_youtube_short`,
  `get_thumbnail_url`, `get_video_info_with_cookies`.

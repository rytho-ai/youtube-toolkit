# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-06-17

### Deep-module refactor — services + 5 sub-APIs (BREAKING)

This release finishes the deep-module decomposition and makes the five sub-APIs
the single public surface.

#### Changed (architecture)

- **api.py is now a composition root.** The `YouTubeToolkit` god class was
  decomposed into 9 domain services under `services/` (get_info, channel,
  playlist, download, search, analyze, comments, captions, system). `api.py`
  `__init__` now only wires handlers + services + the 5 sub-APIs together; the
  only methods left on it are `extract_video_id` and `_sanitize_filename`.
- **Sub-APIs call services directly** (`self._toolkit._<svc>.<method>`); services
  own the handler-fallback. Layers: `sub_apis -> services -> handlers`.
- The fallback decision is a single primitive, `core/fallback.run_with_fallback`.
- `captions.py` was split into the `core/captions/` package (models / convert /
  analytics).

#### Removed (BREAKING)

- **All ~100 flat `YouTubeToolkit` methods were removed** (`get_video_info`,
  `download_audio`, `download_video`, `search_videos`, `advanced_search`,
  `get_channel_info`, `get_sponsorblock_segments`, `get_heatmap`, `list_captions`,
  …). The public API is now exactly the five sub-APIs (`get` / `download` /
  `search` / `analyze` / `stream`) plus `extract_video_id`. See
  [MIGRATION.md](MIGRATION.md) for the full flat-method → sub-API mapping.

#### Added

- **Parallel + async downloads** (opt-in, additive; default stays sequential):
  `download.many(urls, max_workers=N)`, a `concurrent_fragments` option on the
  yt-dlp handler, and async facades `download.audio_async` / `video_async` /
  `many_async`. Parallel paths still respect the thread-safe rate limiter.

## [1.0.0] - 2024-11-27

### Added - Consolidated API with 5 Core Sub-APIs

This is a major release that consolidates all functionality into 5 intuitive core APIs.

#### New APIs

- **AnalyzeAPI** (`toolkit.analyze`) - Content analysis
  - `analyze(url)` / `analyze.metadata(url)` - Get 50+ field metadata
  - `analyze.engagement(url)` - Heatmap and key moments
  - `analyze.comments(url)` - Comment analytics
  - `analyze.captions(url)` - Caption analysis
  - `analyze.sponsorblock(url)` - Sponsor segment detection
  - `analyze.channel(channel)` - Channel analytics
  - `analyze.filesize(url)` - Filesize preview without downloading

- **StreamAPI** (`toolkit.stream`) - Stream to buffer
  - `stream(url)` / `stream.audio(url)` - Stream audio to bytes
  - `stream.video(url)` - Stream video to bytes
  - `stream.live.status(url)` - Live stream status
  - `stream.live.is_live(url)` - Check if currently live
  - `stream.live.download(url)` - Download live stream

#### Enhanced APIs

- **GetAPI** (`toolkit.get`) - New methods
  - `get.keywords(url)` - Get video tags
  - `get.formats(url)` - Get available download formats
  - `get.restriction(url)` - Get age/region restrictions
  - `get.embed_url(url)` - Get embeddable URL

- **DownloadAPI** (`toolkit.download`) - New methods
  - `download.shorts(url)` - Download YouTube Shorts
  - `download.live(url)` - Download live streams
  - `download.with_sponsorblock(url)` - Download with sponsor removal
  - `download.with_metadata(url)` - Download with embedded metadata
  - `download.with_filter(url)` - Download with match filter
  - `download.with_archive(url)` - Download with archive tracking
  - `download.with_cookies(url)` - Download using browser cookies

- **SearchAPI** (`toolkit.search`) - New methods
  - `search.suggestions(query)` - Autocomplete suggestions
  - `search.trending()` - Trending videos
  - `search.trending.by_category()` - Trending by category
  - `search.categories()` - Video categories
  - `search.regions()` - Supported regions
  - `search.languages()` - Supported languages

#### Handler Improvements

- Added `stream_to_buffer()` to PyTubeFixHandler
- Added `get_filesize_preview()` to PyTubeFixHandler
- Added `get_search_suggestions()` to PyTubeFixHandler

### Removed - Legacy Sub-APIs

The following legacy sub-APIs have been removed and consolidated into the 5 core APIs:

| Removed API | Replacement |
|-------------|-------------|
| `toolkit.sponsorblock` | `toolkit.analyze.sponsorblock()` or `toolkit.download.with_sponsorblock()` |
| `toolkit.engagement` | `toolkit.analyze.engagement()` |
| `toolkit.live` | `toolkit.stream.live` |
| `toolkit.archive` | `toolkit.download.with_archive()` |
| `toolkit.cookies` | `toolkit.download.with_cookies()` |
| `toolkit.subtitles` | `toolkit.download.captions()` |
| `toolkit.chapters` | `toolkit.get.chapters()` |
| `toolkit.thumbnail` | `toolkit.download.thumbnail()` |
| `toolkit.filter` | `toolkit.download.with_filter()` |
| `toolkit.metadata` | `toolkit.analyze.metadata()` |
| `toolkit.shorts` | `toolkit.download.shorts()` |
| `toolkit.categories` | `toolkit.search.categories()` |
| `toolkit.i18n` | `toolkit.search.languages()` / `toolkit.search.regions()` |
| `toolkit.trending` | `toolkit.search.trending()` |
| `toolkit.channel_info` | `toolkit.analyze.channel()` |
| `toolkit.subscriptions` | Removed |
| `toolkit.activities` | Removed |
| `toolkit.sections` | Removed |
| `toolkit.audio_enhanced` | `toolkit.download.with_metadata()` |

### Changed

- Updated `sub_apis.py` from ~2500 lines to ~1500 lines
- Simplified API initialization in `api.py`
- Updated README.md with new API documentation
- Development status changed from Alpha to Beta

### Migration Guide

```python
# Before (v0.7.0)
segments = toolkit.sponsorblock.segments(url)
heatmap = toolkit.engagement.heatmap(url)
status = toolkit.live.status(url)
path = toolkit.archive.download(url)

# After (v1.0.0)
segments = toolkit.analyze.sponsorblock(url)
engagement = toolkit.analyze.engagement(url)  # Returns {heatmap, key_moments}
status = toolkit.stream.live.status(url)
path = toolkit.download.with_archive(url)
```

---

## [0.7.0] - 2024-11-26

### Added
- YouTube API analytics features
- SubscriptionsAPI, CategoriesAPI, I18nAPI
- ActivitiesAPI, TrendingAPI, ChannelSectionsAPI, ChannelInfoAPI
- Advanced search with SearchFilters dataclass

## [0.6.0] - 2024-11-25

### Added
- Match Filters API for conditional downloads
- Metadata Export API
- YouTube Shorts support
- FilterAPI, MetadataAPI, ShortsAPI

## [0.5.0] - 2024-11-24

### Added
- SponsorBlock integration
- Live stream support
- Browser cookie authentication
- Archive mode for tracking downloads
- Chapter splitting
- Enhanced audio downloads with metadata
- Thumbnail downloads
- Subtitle conversion

## [0.4.0] - 2024-11-23

### Added
- Action-Based API design
- GetAPI, DownloadAPI, SearchAPI sub-APIs
- Callable sub-APIs with smart defaults

## [0.3.0] - 2024-11-22

### Added
- Channel support (videos, shorts, streams)
- Video chapters and key moments
- Engagement heatmap data
- Advanced search with native filters
- Playlist information
- ScrapeTube integration

## [0.2.0] - 2024-11-21

### Added
- Comments API with CommentResult
- Captions API with CaptionResult
- Rich metadata from YouTube API

## [0.1.0] - 2024-11-20

### Added
- Initial release
- VideoInfo, DownloadResult, SearchResult dataclasses
- PyTubeFix handler (primary)
- YT-DLP handler (fallback)
- YouTube API handler (metadata)
- Automatic fallback between handlers
- Anti-detection measures

# YouTube Toolkit

A robust Python toolkit for YouTube operations with automatic fallback between multiple backends. Built for reliability and ease of use.

## Why YouTube Toolkit?

YouTube libraries break frequently. youtube-toolkit solves this by using **multiple backends** with **automatic fallback**:

- If PyTubeFix fails → tries yt-dlp
- If yt-dlp fails → tries YouTube API
- You get consistent results regardless of which backend succeeds

## Features

- **5 Intuitive APIs** - Get, Download, Search, Analyze, Stream
- **Automatic Fallback** - Multiple backends ensure reliability
- **Type Safety** - Data classes with IDE autocomplete support
- **No API Key Required** - Most features work without YouTube API key
- **Comprehensive** - Videos, playlists, channels, shorts, live streams

## Installation

### Prerequisites

**Python 3.10+** and **FFmpeg** are required.

```bash
# Install FFmpeg
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows - Download from https://ffmpeg.org/download.html
```

### Install the Package

This project uses **[uv](https://docs.astral.sh/uv/) as its primary toolchain** —
prefer it over `pip` for installs and environment management.

```bash
# With uv (preferred)
uv add git+https://github.com/rhythmculture/youtube-toolkit.git
# ...or into an active environment:
uv pip install git+https://github.com/rhythmculture/youtube-toolkit.git

# Specific version
uv add git+https://github.com/rhythmculture/youtube-toolkit.git@v2.0.0

# Fallback, only if uv is unavailable
pip install git+https://github.com/rhythmculture/youtube-toolkit.git
```

### YouTube API Key (Optional)

Most features work without an API key. Only needed for: `search.trending()`, `search.categories()`, `search.regions()`, `search.languages()`, and API-based comments.

```bash
# Set your API key
echo "YOUTUBE_API_KEY=your_key_here" > .env

# Or export directly
export YOUTUBE_API_KEY=your_key_here
```

Get an API key from [Google Cloud Console](https://console.cloud.google.com/) → Enable YouTube Data API v3 → Create Credentials.

## Quick Start

```python
from youtube_toolkit import YouTubeToolkit

toolkit = YouTubeToolkit()
url = "https://youtube.com/watch?v=dQw4w9WgXcQ"

# Get video info
video = toolkit.get(url)
print(f"{video.title} - {video.duration}s")

# Download audio
result = toolkit.download(url, type='audio', format='mp3')
print(f"Downloaded: {result.file_path}")

# Search
results = toolkit.search("python tutorial", max_results=5)
for item in results.items:
    print(f"- {item.title}")
```

## The 5 Core APIs

> **These five sub-APIs (`get` / `download` / `search` / `analyze` / `stream`) are the
> only public API.** The older flat methods (`toolkit.get_video_info()`,
> `toolkit.download_audio()`, …) were **removed in v2.0** (a breaking change).
> If you're upgrading, see [MIGRATION.md](MIGRATION.md) for the
> flat-method → sub-API mapping.

### GET - Retrieve Information

```python
video = toolkit.get(url)                    # Video info
chapters = toolkit.get.chapters(url)        # Chapter timestamps
comments = toolkit.get.comments(url)        # Video comments
formats = toolkit.get.formats(url)          # Available formats

# Channel
videos = toolkit.get.channel.videos("@Fireship", limit=50)
shorts = toolkit.get.channel.shorts("@Fireship")

# Playlist
videos = toolkit.get.playlist.videos(playlist_url)
```

### DOWNLOAD - Save to Disk

```python
result = toolkit.download(url, type='audio', format='mp3')
audio_path = toolkit.download.audio(url, format='mp3')
video_path = toolkit.download.video(url, quality='720p')

# Advanced
toolkit.download.shorts(url)                              # YouTube Shorts
toolkit.download.live(url, from_start=True)               # Live streams
toolkit.download.with_sponsorblock(url, action='remove')  # Skip sponsors
toolkit.download.with_cookies(url, browser='chrome')      # Age-restricted
```

### SEARCH - Find Content

```python
results = toolkit.search("query", max_results=20)
videos = toolkit.search.videos("query")
channels = toolkit.search.channels("query")

# With filters
results = toolkit.search.with_filters(
    "python tutorial",
    duration='medium',      # short, medium, long
    upload_date='month',    # hour, today, week, month, year
    sort_by='views'
)

# Trending (requires API key)
trending = toolkit.search.trending()
```

### ANALYZE - Deep Analysis

```python
metadata = toolkit.analyze(url)             # 50+ fields
engagement = toolkit.analyze.engagement(url) # Heatmap + key moments
segments = toolkit.analyze.sponsorblock(url) # Sponsor segments
filesize = toolkit.analyze.filesize(url)     # Preview sizes
```

### STREAM - Stream to Buffer

```python
audio_bytes = toolkit.stream.audio(url)     # Audio in memory
video_bytes = toolkit.stream.video(url)     # Video in memory

# Live streams
is_live = toolkit.stream.live.is_live(url)
status = toolkit.stream.live.status(url)
```

## Return Types (Dataclasses)

The three primary entry points return typed dataclasses (attribute access, IDE
autocomplete), not raw dicts:

```python
video = toolkit.get(url)        # VideoInfo
print(video.title, video.duration, video.views, video.author, video.video_id, video.url)

result = toolkit.download(url)   # DownloadResult
if result.success:
    print(result.file_path, result.file_size)
else:
    print(result.error_message)

results = toolkit.search(q)      # SearchResult
print(results.query, results.total_results)
for item in results.items:       # items: list[SearchResultItem]
    print(item.title)
```

- `toolkit.get(url)` → **`VideoInfo`** (`.title` / `.duration` / `.views` / `.author` / `.video_id` / `.url` …)
- `toolkit.download(url)` → **`DownloadResult`** (`.success` / `.file_path` / `.error_message` / `.file_size`)
- `toolkit.search(q)` → **`SearchResult`** (`.items` is a list of `SearchResultItem`, plus `.total_results` / `.query`)

> Note: some sub-methods (e.g. `toolkit.get.channel.videos()`, `toolkit.get.playlist.urls()`)
> currently return plain `dict` / `list` rather than dataclasses.

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Architecture & extending guide (layering, adding features)
- **[examples/](examples/)** - Runnable examples
- **[MIGRATION.md](MIGRATION.md)** - v1 → v2 migration
- **[CHANGELOG.md](CHANGELOG.md)** - Version history

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Sub-API Layer (public surface)              │
│     GetAPI │ DownloadAPI │ SearchAPI │ AnalyzeAPI │ StreamAPI│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                          │
│        Business logic + handler-fallback per domain        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Handlers                               │
│   PyTubeFix (primary) │ yt-dlp (fallback) │ YouTube API     │
└─────────────────────────────────────────────────────────────┘

  api.py (YouTubeToolkit) wires the three layers together (composition root).
```

## Dependencies & Acknowledgments

youtube-toolkit is built on top of excellent open-source projects:

### Core Dependencies

| Package | Purpose | License |
|---------|---------|---------|
| [**PyTubeFix**](https://github.com/JuanBindez/pytubefix) | Primary download engine, channel/playlist support, search | MIT |
| [**yt-dlp**](https://github.com/yt-dlp/yt-dlp) | Robust fallback downloader, live streams, SponsorBlock, cookies | Unlicense |
| [**google-api-python-client**](https://github.com/googleapis/google-api-python-client) | Official YouTube Data API v3 for comments, trending, metadata | Apache 2.0 |
| [**MoviePy**](https://github.com/Zulko/moviepy) | Video processing, audio extraction, format conversion | MIT |
| [**FFmpeg**](https://ffmpeg.org/) | Audio/video encoding, format conversion (system dependency) | LGPL/GPL |
| [**requests**](https://github.com/psf/requests) | HTTP requests for thumbnails and API calls | Apache 2.0 |
| [**rich**](https://github.com/Textualize/rich) | Beautiful terminal output and progress bars | MIT |
| [**python-dotenv**](https://github.com/theskumar/python-dotenv) | Environment variable management | BSD |
| [**scrapetube**](https://github.com/dermasmid/scrapetube) | Unlimited channel videos without API limits | MIT |

### Special Thanks

- **pytube** maintainers and contributors - The original inspiration
- **yt-dlp** team - For the most comprehensive YouTube downloader
- **SponsorBlock** - Community-driven sponsor segment database
- All contributors to the open-source packages that make this possible

## Project Structure

```
youtube-toolkit/
├── src/                        # src layout — package lives here, not at repo root
│   └── youtube_toolkit/
│       ├── api.py              # YouTubeToolkit (composition root)
│       ├── sub_apis.py         # 5 Core APIs (public surface)
│       ├── services/           # Business logic + fallback per domain
│       ├── handlers/           # Backend handlers
│       │   ├── pytubefix_handler.py
│       │   ├── yt_dlp_handler.py
│       │   ├── youtube_api_handler.py
│       │   └── scrapetube_handler.py
│       ├── core/               # Data classes + fallback primitive
│       └── utils/              # Utilities
├── docs/                   # Plans + generated codebase map
│   ├── plans/
│   └── codebase-map/
├── examples/               # Runnable examples
├── tests/                  # Test suite (200+ tests)
├── CLAUDE.md               # Architecture & extending guide
├── CONTRIBUTING.md
├── MIGRATION.md            # v1 → v2 migration
├── CHANGELOG.md
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the [architecture guidelines](CLAUDE.md)
4. Add tests for new functionality
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and [CLAUDE.md](CLAUDE.md) for the architecture.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and migration guides.

---

**Made with reliability in mind.**

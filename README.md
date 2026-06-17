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

```bash
# With uv (recommended)
uv pip install git+https://github.com/rhythmculture/youtube-toolkit.git

# With pip
pip install git+https://github.com/rhythmculture/youtube-toolkit.git

# Specific version
uv pip install git+https://github.com/rhythmculture/youtube-toolkit.git@v1.0.0
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
> recommended public API.** The older flat methods (`toolkit.get_video_info()`,
> `toolkit.download_audio()`, …) still work for backward compatibility but are
> **legacy**: calling one directly emits a `DeprecationWarning` pointing at its
> sub-API replacement. New code should use the sub-APIs below.

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

## Documentation

- **[Usage Guide](docs/USAGE.md)** - Comprehensive usage examples
- **[Architecture](docs/ARCHITECTURE.md)** - Design philosophy and decisions
- **[Extending](docs/EXTENDING.md)** - How to add new features

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Sub-API Layer                          │
│     GetAPI │ DownloadAPI │ SearchAPI │ AnalyzeAPI │ StreamAPI│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    YouTubeToolkit                           │
│            Fallback logic, unified interface                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Handlers                               │
│   PyTubeFix (primary) │ yt-dlp (fallback) │ YouTube API     │
└─────────────────────────────────────────────────────────────┘
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
├── youtube_toolkit/
│   ├── api.py              # YouTubeToolkit main class
│   ├── sub_apis.py         # 5 Core APIs
│   ├── handlers/           # Backend handlers
│   │   ├── pytubefix_handler.py
│   │   ├── yt_dlp_handler.py
│   │   ├── youtube_api_handler.py
│   │   └── scrapetube_handler.py
│   ├── core/               # Data classes
│   └── utils/              # Utilities
├── docs/                   # Documentation
│   ├── USAGE.md
│   ├── ARCHITECTURE.md
│   └── EXTENDING.md
├── tests/                  # Test suite (200+ tests)
├── CHANGELOG.md
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the [architecture guidelines](docs/ARCHITECTURE.md)
4. Add tests for new functionality
5. Submit a pull request

See [EXTENDING.md](docs/EXTENDING.md) for detailed contribution guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and migration guides.

---

**Made with reliability in mind.**

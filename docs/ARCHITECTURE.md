# YouTube Toolkit Architecture & Design Philosophy

This document explains the design decisions and philosophy behind youtube-toolkit.

## Table of Contents

- [Design Philosophy](#design-philosophy)
- [Four-Layer Architecture](#four-layer-architecture)
- [The 5 Core APIs](#the-5-core-apis)
- [Handler System](#handler-system)
- [Fallback Strategy](#fallback-strategy)
- [Data Classes](#data-classes)
- [Why This Design?](#why-this-design)

## Design Philosophy

### 1. Reliability Over Speed

YouTube's API and website change frequently. A single library can break at any time. youtube-toolkit solves this by:

- Using **multiple backends** (PyTubeFix, yt-dlp, YouTube API)
- Implementing **automatic fallback** when one method fails
- Providing **consistent interfaces** regardless of which backend succeeds

### 2. Intuitive API Design

APIs should be discoverable and self-documenting:

```python
# Bad: What does this do?
toolkit.gvi(url, True, False, 'en')

# Good: Self-explanatory
toolkit.get.video(url)
toolkit.get.chapters(url)
toolkit.download.audio(url, format='mp3')
```

### 3. Action-Based Organization

Instead of organizing by data type, we organize by **what the user wants to do**:

| Action | API | Purpose |
|--------|-----|---------|
| **Get information** | `toolkit.get` | Retrieve without downloading |
| **Save to disk** | `toolkit.download` | Download files |
| **Find content** | `toolkit.search` | Search and discover |
| **Analyze deeply** | `toolkit.analyze` | Metadata, engagement, etc. |
| **Stream to memory** | `toolkit.stream` | Buffer without saving |

### 4. Progressive Disclosure

Simple things are simple, complex things are possible:

```python
# Simple (most common use case)
toolkit.download(url)

# More control
toolkit.download.audio(url, format='mp3', bitrate='320k')

# Full control
toolkit.download.with_filter(url, match_filter="duration > 600 & view_count > 10000")
```

### 5. Backward Compatibility

Legacy methods continue to work:

```python
# Old way (still works)
toolkit.download_audio(url)
toolkit.get_video_info(url)

# New way (recommended)
toolkit.download.audio(url)
toolkit.get.video(url)
```

## Four-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SUB-API LAYER                            │
│              (sub_apis.py - User Interface)                 │
│                                                             │
│   GetAPI    DownloadAPI    SearchAPI    AnalyzeAPI   StreamAPI│
│                                                             │
│   - User-friendly methods, callable classes, smart defaults │
│   - Delegates to API layer (never directly to handlers)     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     API LAYER (the public contract)         │
│              (api.py - YouTubeToolkit)                      │
│                                                             │
│   - Thin delegation layer: each method is one line to a     │
│     service. Method signatures are FROZEN (external import).│
│   - Owns handlers + anti-detection + the 5 sub-APIs         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   SERVICE LAYER                             │
│              (services/*.py - Business logic)              │
│                                                             │
│   GetInfo  Channel  Playlist  Download  Search  Analyze     │
│   Comments  Captions  System  (each takes a toolkit back-ref)│
│                                                             │
│   - Handler-fallback orchestration (core/fallback.py)       │
│   - Parallel/async download owner (services/download.py)    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   HANDLER LAYER                             │
│              (handlers/*.py - Backends)                     │
│                                                             │
│   PyTubeFixHandler    YTDLPHandler    YouTubeAPIHandler     │
│   - Raw implementation using external packages, no          │
│     cross-handler logic, simple focused methods             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 EXTERNAL PACKAGES                           │
│   pytubefix  │  yt-dlp  │  google-api-python-client        │
└─────────────────────────────────────────────────────────────┘
```

### Why These Layers?

1. **Separation of Concerns**: Each layer has a single responsibility — api.py is
   the stable public contract, services hold the logic, handlers wrap backends
2. **Testability**: Layers can be tested independently
3. **Flexibility**: Swap handlers without changing user-facing APIs
4. **Maintainability**: api.py stays small (a delegation index); a domain's logic
   lives in one service file you can read top-to-bottom

## The 5 Core APIs

### Why 5 APIs?

We consolidated ~20 legacy APIs into 5 based on **user intent**:

| User Intent | API | Old APIs Consolidated |
|-------------|-----|----------------------|
| "I want to know about this video" | `get` | video_info, chapters, metadata |
| "I want to save this" | `download` | audio, video, shorts, live, sponsorblock |
| "I want to find videos" | `search` | videos, channels, trending, categories |
| "I want to analyze this" | `analyze` | engagement, comments, sponsorblock, metadata |
| "I want this in memory" | `stream` | buffer, live status |

### Callable Sub-APIs

Each Sub-API is callable with smart defaults:

```python
class DownloadAPI:
    def __call__(self, url, type='audio', format='mp3'):
        """Smart download with defaults."""
        if type == 'audio':
            return self.audio(url, format=format)
        else:
            return self.video(url)
    
    def audio(self, url, format='mp3'):
        """Explicit audio download."""
        ...
    
    def video(self, url, quality='best'):
        """Explicit video download."""
        ...
```

This allows:
```python
toolkit.download(url)           # Uses defaults
toolkit.download.audio(url)     # Explicit
toolkit.download.video(url)     # Explicit
```

## Handler System

### Handler Responsibilities

| Handler | Package | Primary Use |
|---------|---------|-------------|
| `PyTubeFixHandler` | pytubefix | Downloads, channels, search, chapters |
| `YTDLPHandler` | yt-dlp | Fallback downloads, live streams, SponsorBlock |
| `YouTubeAPIHandler` | google-api | Comments, trending, categories, official search |
| `ScrapeTubeHandler` | scrapetube | Unlimited channel videos |

### Handler Design Principles

1. **Single Package**: Each handler wraps exactly one external package
2. **Stateless Methods**: Methods don't depend on previous calls
3. **Consistent Errors**: All handlers raise `RuntimeError` on failure
4. **Lazy Initialization**: Resources loaded only when needed

## Fallback Strategy

### Automatic Fallback

Fallback lives in the **service layer**, built on the single primitive
`core/fallback.run_with_fallback` (one owner for the "try handlers in order,
log, raise when all fail" decision). api.py just delegates.

```python
# api.py — thin delegation (the public contract)
def get_video_info(self, url: str) -> Dict:
    """Get video info with automatic fallback."""
    return self._get_info.get_video_info(url)

# services/get_info.py — where the fallback decision actually lives
def get_video_info(self, url: str) -> Dict:
    from ..core.fallback import run_with_fallback
    return run_with_fallback(
        [("PyTubeFix", lambda: self._toolkit.pytubefix.get_video_info(url)),
         ("YT-DLP",    lambda: self._toolkit.yt_dlp.get_video_info(url))],
        error_message="All video info extraction methods failed",
        verbose=self._toolkit.verbose,
    )
```

### Why This Order?

1. **PyTubeFix first**: Faster, lighter, sufficient for most cases
2. **yt-dlp second**: More robust, handles edge cases
3. **YouTube API third**: Official but requires API key and has quotas

## Data Classes

### Return Types

All main APIs return dataclasses for consistent attribute access:

```python
# GET API returns VideoInfo dataclass
video = toolkit.get(url)
print(video.title)           # Attribute access
print(video.duration)
print(video.views)

# DOWNLOAD API returns DownloadResult dataclass
result = toolkit.download(url)
print(result.file_path)      # Attribute access
print(result.success)

# SEARCH API returns SearchResult dataclass
results = toolkit.search("query")
for item in results.items:   # items is a list of SearchResultItem
    print(item.title)        # Attribute access

# Note: Some sub-methods return dicts (channel videos, playlist videos)
videos = toolkit.get.channel.videos("@Channel")
for v in videos:             # List of dicts
    print(v['title'])
```

### Core Data Classes

```python
@dataclass
class VideoInfo:
    title: str
    duration: int
    views: int
    author: str
    video_id: str
    url: str
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    # ... more fields

@dataclass
class DownloadResult:
    success: bool
    file_path: str
    error_message: Optional[str] = None
    file_size: Optional[int] = None

@dataclass
class SearchResult:
    items: List[SearchResultItem]
    total_results: int
    query: str

@dataclass
class SearchResultItem:
    title: str
    video_id: Optional[str] = None
    channel_id: Optional[str] = None
    description: str = ""
    # ... more fields
```

## Why This Design?

### Problem: YouTube Libraries Break Frequently

YouTube changes their website/API constantly. Libraries like pytube, youtube-dl frequently break.

**Solution**: Multiple backends with automatic fallback.

### Problem: APIs Are Confusing

20+ methods with unclear names and overlapping functionality.

**Solution**: 5 action-based APIs organized by user intent.

### Problem: Raw Dictionaries Are Error-Prone

No type safety, no IDE support, easy to make typos.

**Solution**: Typed data classes with clear documentation.

### Problem: Hard to Extend

Tightly coupled code makes adding features difficult.

**Solution**: Layered architecture (sub-API -> api -> services -> handlers) with clear boundaries.

---

## Summary

youtube-toolkit is designed around these principles:

1. **Reliability**: Multiple backends with automatic fallback
2. **Simplicity**: 5 intuitive APIs based on user intent
3. **Type Safety**: Data classes instead of raw dictionaries
4. **Extensibility**: Layered architecture (services + handlers)
5. **Compatibility**: Legacy methods still work

The goal is a library that "just works" while remaining maintainable and extensible.

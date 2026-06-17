# CLAUDE.md - Development Principles for youtube-toolkit

This document contains development principles and architecture guidelines for Claude (or any AI assistant) when working on this codebase.

## Architecture Principles

### Four-Layer Architecture

The youtube-toolkit follows a strict layered architecture. `api.py` is the
public contract (a thin delegation layer); the business logic lives in
`services/`; `handlers/` are the swappable backends.

```
┌─────────────────────────────────────────────────────────────┐
│                   sub_apis.py                                │
│   Action facades: toolkit.get / download / search /         │
│   analyze / stream (GetAPI, DownloadAPI, ...).              │
│   Call api.py methods ONLY — never handlers directly.       │
└─────────────────────────────────────────────────────────────┘
                              │  (also: direct toolkit.method() calls)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 api.py (YouTubeToolkit)                      │
│   THE PUBLIC CONTRACT + thin delegation layer.             │
│   Each public method delegates one-line to a service.      │
│   Owns handlers + anti-detection + the 5 sub-APIs.         │
│   Method signatures are FROZEN (other projects import them).│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   services/*.py                             │
│   Business logic per domain (get_info, channel, playlist,  │
│   download, search, analyze, comments, captions, system).  │
│   Hold the handler-fallback orchestration. Each takes a    │
│   toolkit back-ref (self._toolkit), like sub_apis.         │
│   Fallback primitive lives in core/fallback.py.            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   handlers/                                 │
│   Backend implementations                                   │
│   (PyTubeFixHandler, YTDLPHandler, YouTubeAPIHandler)       │
└─────────────────────────────────────────────────────────────┘
```

### CRITICAL: Layer Communication Rules

**Rule 1 — Sub-APIs MUST call api.py methods, NOT handlers directly.**
(Executable guard: `grep -E '_toolkit\.(pytubefix|ytdlp|yt_dlp|youtube_api)\.' youtube_toolkit/sub_apis.py` must return **0**.)

**Rule 2 — api.py methods delegate to a service, NOT to handlers directly.**
api.py is the public contract; the body of each method should be a one-line
delegation to `self._<domain>.<method>(...)`. Handler calls + fallback live in
the service (using `core/fallback.run_with_fallback`). The only retained
exception is the shared util `extract_video_id`.

```python
# ❌ WRONG - Sub-API calling handler directly
class SponsorBlockAPI:
    def segments(self, url: str):
        return self._toolkit.yt_dlp.get_sponsorblock_segments(url)  # BAD!

# ✅ CORRECT - Sub-API -> api.py -> service -> handler
class AnalyzeAPI:
    def sponsorblock(self, url: str):
        return self._toolkit.get_sponsorblock_segments(url)  # GOOD!
```

**Why this matters:**
1. **Fallback Logic**: services implement fallback between handlers (one owner: `core/fallback.py`)
2. **Cross-cutting Concerns**: Logging, caching, rate limiting sit at api/service level
3. **Consistency**: Single point of control for each feature; api.py is the stable contract
4. **Testability**: Easier to mock at api.py level

### Public API: the sub-APIs are canonical; flat methods are legacy

The five sub-APIs (`get` / `download` / `search` / `analyze` / `stream`) are THE
recommended public API. The ~100 flat `YouTubeToolkit` methods
(`get_video_info()`, `download_audio()`, …) remain for backward compatibility but
are **legacy**: each clear duplicate carries `@deprecated("toolkit.x.y()")` from
`utils/deprecation.py`, which emits a `DeprecationWarning` **only when called from
outside the `youtube_toolkit` package**. This means internal callers (the
sub-APIs and the services, which still route cross-domain calls through these
methods) never self-warn, while external users get a runtime nudge. When adding a
new capability, expose it on a sub-API; only add a flat method if a legacy-style
entry point is genuinely needed, and decorate it if it duplicates a sub-API.

The 14 internal plumbing delegators that sub_apis needs (e.g.
`_get_video_info_pytubefix`, `_stream_to_buffer`) are `_`-prefixed private — keep
new internal-only delegators private too, so the public surface stays small.

### Parallel / async downloads (conservative by design)

Multi-video parallelism, fragment concurrency, and an async facade are all
**opt-in and additive** — default behavior is sequential and unchanged.
The single owner of parallel orchestration (thread pool, worker cap,
rate-limit coordination) is `services/download.py` (`download_many`); the
fragment param lands in the yt-dlp handler; async methods are thin
`run_in_executor` wrappers in `DownloadAPI`. Parallel paths still go through
`@rate_limit` (made thread-safe), so they respect the anti-detection budget.

### Adding New Features

When adding a new feature, follow this pattern:

1. **Handler Layer** (`handlers/*.py`): Implement the raw functionality
   ```python
   # handlers/yt_dlp_handler.py
   def get_new_feature(self, url: str) -> Dict:
       # Raw implementation using yt-dlp
       ...
   ```

2. **Service Layer** (`services/<domain>.py`): Add the orchestration + fallback
   ```python
   # services/get_info.py
   def get_new_feature(self, url: str) -> Dict:
       from ..core.fallback import run_with_fallback
       return run_with_fallback(
           [("PyTubeFix", lambda: self._toolkit.pytubefix.get_new_feature(url)),
            ("YT-DLP",    lambda: self._toolkit.yt_dlp.get_new_feature(url))],
           error_message="All get_new_feature methods failed",
           verbose=self._toolkit.verbose,
       )
   ```

3. **API Layer** (`api.py`): Add a one-line delegation (the public contract)
   ```python
   # api.py
   def get_new_feature(self, url: str) -> Dict:
       return self._get_info.get_new_feature(url)
   ```

4. **Sub-API Layer** (`sub_apis.py`): Add user-friendly interface
   ```python
   # sub_apis.py
   class NewFeatureAPI:
       def get(self, url: str) -> Dict:
           return self._toolkit.get_new_feature(url)  # Calls api.py, never the handler!
   ```

5. **Initialize in api.py** (services are wired in `__init__` before sub-APIs)
   ```python
   # api.py __init__
   self._get_info = GetInfoService(self)   # service
   from .sub_apis import NewFeatureAPI
   self.new_feature = NewFeatureAPI(self)  # sub-API
   ```

## Code Organization

### File Structure

```
youtube_toolkit/
├── api.py                 # Public contract: YouTubeToolkit, thin delegation layer
├── sub_apis.py            # Action facades (GetAPI, DownloadAPI, ...) -> call api.py
├── services/              # Business logic per domain (the api.py bodies live here)
│   ├── get_info.py        #   GetInfoService, ChannelService, PlaylistService,
│   ├── channel.py         #   DownloadService, SearchService, AnalyzeService,
│   ├── playlist.py        #   CommentsService, CaptionsService, SystemService.
│   ├── download.py        #   download.py also owns parallel/async download.
│   ├── search.py
│   ├── analyze.py
│   ├── comments.py
│   ├── captions.py
│   └── system.py
├── handlers/
│   ├── pytubefix_handler.py    # Primary handler
│   ├── yt_dlp_handler.py       # Fallback handler
│   ├── youtube_api_handler.py  # Official API handler
│   └── scrapetube_handler.py   # Optional scraping handler
├── core/                  # Data classes + the fallback primitive
│   ├── fallback.py        #   run_with_fallback: single owner of fallback decision
│   ├── captions/          #   caption models / convert / analytics (was captions.py)
│   └── ...                #   video_info, download, search, comments, post_processors
└── utils/                 # Utility functions (anti_detection, request_interceptor, ...)
```

### Naming Conventions

- **api.py methods**: Use descriptive names like `get_video_info()`, `download_audio()`
- **services/ classes**: Use `*Service` suffix like `GetInfoService`, `DownloadService`
- **sub_apis.py classes**: Use `*API` suffix like `GetAPI`, `DownloadAPI`, `SponsorBlockAPI`
- **handlers**: Use `*Handler` suffix like `YTDLPHandler`, `PyTubeFixHandler`

## Testing

- Tests are in `tests/` directory
- Run tests with: `uv run pytest tests/ -v`
- When adding new features, add corresponding tests
- Mock at the handler level for unit tests

## Version History

- **v0.3**: Added channel support, chapters, advanced search
- **v0.4**: Added Action-Based API (get, download, search sub-APIs)
- **v0.5**: Added advanced yt-dlp features (SponsorBlock, live streams, engagement data, etc.)
- **v1.0**: Deep-module refactor — api.py god class decomposed into `services/`
  (api.py becomes a thin delegation layer / public contract); fallback extracted
  to `core/fallback.py`; `captions.py` split into `core/captions/`; sub_apis
  routed through api.py (no handler-direct calls). Added opt-in parallel +
  async downloads (`download_many`, `concurrent_fragments`, `*_async`).
  Public API contract unchanged.

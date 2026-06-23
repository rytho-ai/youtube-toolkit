# CLAUDE.md - Development Principles for youtube-toolkit

This document contains development principles and architecture guidelines for Claude (or any AI assistant) when working on this codebase.

## Architecture Principles

### Three-Layer Architecture

The youtube-toolkit follows a strict layered architecture. `sub_apis.py` is the
**only public surface** (5 action facades); the business logic + handler fallback
live in `services/`; `handlers/` are the swappable backends. `api.py`
(`YouTubeToolkit`) is the **composition root**: its `__init__` wires handlers +
services + sub-APIs together, and it keeps just two bare helpers.

```
┌─────────────────────────────────────────────────────────────┐
│                   sub_apis.py  (the public surface)         │
│   Action facades: toolkit.get / download / search /         │
│   analyze / stream (GetAPI, DownloadAPI, ...).              │
│   Call the matching SERVICE directly (self._toolkit._<svc>),│
│   never handlers.                                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 api.py (YouTubeToolkit) = COMPOSITION ROOT   │
│   __init__ builds handlers + anti-detection, the 9 domain   │
│   services, and the 5 sub-APIs — that's its whole job.      │
│   Only two methods stay on it: extract_video_id and the     │
│   shared helper _sanitize_filename. It is NOT a delegation  │
│   layer — the ~100 legacy flat methods were REMOVED in 2.0. │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   services/*.py                             │
│   Business logic per domain (get_info, channel, playlist,  │
│   download, search, analyze, comments, captions, system).  │
│   Own the handler-fallback orchestration. Each takes a     │
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

**Rule 1 — Sub-APIs call the matching SERVICE directly, NOT handlers.**
A sub-API method body calls `self._toolkit._<svc>.<method>(...)` (e.g.
`self._toolkit._get_info.get_video_info_pytubefix(url)`). It never reaches into a
handler — neither via `self._toolkit.<handler>` nor by importing/instantiating a
handler class inline. (Executable guard — both must return **0** over
`src/youtube_toolkit/sub_apis.py`:
`grep -E '_toolkit\.(pytubefix|ytdlp|yt_dlp|youtube_api)\.'` **and**
`grep -E 'import .*Handler|[A-Za-z]+Handler\('` — the second catches the
`from .handlers... import XxxHandler; XxxHandler()` end-run the first misses.)

**Rule 2 — Services own the handler-fallback.**
A service is where handlers actually get called and where fallback is decided,
using `core/fallback.run_with_fallback`. Services hold a toolkit back-ref so they
can reach the handlers (`self._toolkit.pytubefix`, `self._toolkit.yt_dlp`, ...).

**Rule 3 — api.py is a composition root, not a method layer.**
Do NOT add delegation methods to `api.py`. Its body is `__init__` (wiring) plus
the two retained helpers `extract_video_id` and `_sanitize_filename`. New
capabilities are exposed on a sub-API, not on `YouTubeToolkit`.

```python
# ❌ WRONG - Sub-API calling handler directly
class SponsorBlockAPI:
    def segments(self, url: str):
        return self._toolkit.yt_dlp.get_sponsorblock_segments(url)  # BAD!

# ✅ CORRECT - Sub-API -> service -> handler (service owns fallback)
class AnalyzeAPI:
    def sponsorblock(self, url: str):
        return self._toolkit._analyze.get_sponsorblock_segments(url)  # GOOD!
```

**Why this matters:**
1. **Fallback Logic**: services implement fallback between handlers (one owner: `core/fallback.py`)
2. **Cross-cutting Concerns**: Logging, caching, rate limiting sit at the service level
3. **Consistency**: Single point of control for each feature, inside the service
4. **Testability**: Mock at the handler (or service) level

### Public API: the 5 sub-APIs (flat methods removed in 2.0)

The public API is **exactly** the five sub-APIs — `get` / `download` / `search` /
`analyze` / `stream` (plus `toolkit.extract_video_id`). There are no flat methods:
the ~100 historical `YouTubeToolkit` flat methods (`get_video_info()`,
`download_audio()`, …) were **removed in 2.0** (a breaking change). Anyone
migrating off them should consult the root `MIGRATION.md` for the
flat-method → sub-API mapping.

### Parallel / async downloads (conservative by design)

Multi-video parallelism, fragment concurrency, and an async facade are all
**opt-in and additive** — default behavior is sequential and unchanged.
The single owner of parallel orchestration (thread pool, worker cap,
rate-limit coordination) is `services/download.py` (`download_many`); the
fragment param lands in the yt-dlp handler; async methods are thin
`run_in_executor` wrappers in `DownloadAPI`. Parallel paths still go through
`@rate_limit` (made thread-safe), so they respect the anti-detection budget.

### Adding New Features

When adding a new feature, follow this three-step pattern (no api.py step):

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

3. **Sub-API Layer** (`sub_apis.py`): Expose it, calling the service directly
   ```python
   # sub_apis.py
   class GetAPI:
       def new_feature(self, url: str) -> Dict:
           return self._toolkit._get_info.get_new_feature(url)  # service, never the handler!
   ```

If the feature warrants an **entirely new** service or sub-API, wire it once in
the `api.py` composition root (`__init__`):
```python
# api.py __init__
self._get_info = GetInfoService(self)   # service (already exists for this domain)
self.get = GetAPI(self)                 # sub-API
```
This is the only thing api.py does — it never grows a delegation method.

## Code Organization

### File Structure

```
src/youtube_toolkit/       # src layout: the package lives under src/, never at repo root
├── api.py                 # Composition root: YouTubeToolkit.__init__ wires it all
├── sub_apis.py            # Action facades (GetAPI, DownloadAPI, ...) -> call services
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

- **services/ methods**: Use descriptive names like `get_video_info()`, `download_audio()`
- **services/ classes**: Use `*Service` suffix like `GetInfoService`, `DownloadService`
- **sub_apis.py classes**: Use `*API` suffix like `GetAPI`, `DownloadAPI`, `SponsorBlockAPI`
- **handlers**: Use `*Handler` suffix like `YTDLPHandler`, `PyTubeFixHandler`

## Environment & Tooling

- **src layout (required).** The package lives at `src/youtube_toolkit/`, never at
  the repo root. This forces tests/examples to run against the *installed* package
  rather than the cwd source tree, closing the class of "passes locally,
  `ImportError` after install" packaging bugs. `pyproject.toml` declares
  `packages = ["src/youtube_toolkit"]` (wheel) and `/src/youtube_toolkit` (sdist).
- **`uv` first, `pip` only as fallback.** Use `uv` for all dependency and
  environment work — `uv sync`, `uv run …`, `uv add …`, `uv build`. Reach for
  `pip`/`uv pip install` only when something genuinely can't be expressed through
  `uv` (e.g. installing the built wheel into a foreign environment). Do not add
  bare `pip install` steps to docs, CI, or scripts when a `uv` equivalent exists.

## Testing

- Tests are in `tests/` directory
- Run tests with: `uv run pytest tests/ -v`
- When adding new features, add corresponding tests
- Mock at the handler level for unit tests

<!-- shape:dev-workflow start -->
## Dev workflow

This project is driven by the **shape / nav** skill workflow. The planning board lives in `docs/blueprints/`; the codebase map and grounded plans already live under `docs/`.

| You want to… | Verb |
|---|---|
| Decide what to work on next / refresh the board | `/shape:align` → `docs/blueprints/plan.md` + `overview.html` |
| Scope a feature against the actual code | `/nav:plan` → `docs/plans/` |
| Implement a small decided change | `/nav:do` |
| Drive the in-progress board to done | `/shape:build` |
| Behaviour-preserving structural move | `/nav:refactor` |
| Re-sync file-top headers after restructuring | `/nav:sync` |
| Regenerate the repo map | `/nav:map` → `docs/codebase-map/index.html` |
| Audit architecture against the layer rules above | `/nav:audit` |

**Standing pointers:** plan board = `docs/blueprints/plan.md` (agent) + `overview.html` (human) · grounded plans = `docs/plans/` · repo map = `docs/codebase-map/index.html`.

**Communication:** converse with the user in **Traditional Chinese (Taiwanese phrasing)**, plain and direct, with concrete analogies; keep code, identifiers, and commit messages in English.
<!-- shape:dev-workflow end -->

## Version History

- **v0.3**: Added channel support, chapters, advanced search
- **v0.4**: Added Action-Based API (get, download, search sub-APIs)
- **v0.5**: Added advanced yt-dlp features (SponsorBlock, live streams, engagement data, etc.)
- **v1.0**: Deep-module refactor — api.py god class decomposed into `services/`;
  fallback extracted to `core/fallback.py`; `captions.py` split into
  `core/captions/`. Added opt-in parallel + async downloads (`download_many`,
  `concurrent_fragments`, `*_async`).
- **v2.0**: **Breaking change** — all ~100 flat `YouTubeToolkit` methods removed;
  api.py is now a pure composition root (`__init__` wiring + `extract_video_id` +
  `_sanitize_filename`). The public API is exactly the 5 sub-APIs, which now call
  their services directly. See `MIGRATION.md` for the flat-method → sub-API map.

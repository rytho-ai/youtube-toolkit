# youtube-toolkit — plan

> 2026-06-23 · status index (one layer, by status). Only "what to do + which doc".
> grounded plans in `../plans/`, repo map in `../codebase-map/index.html`. design notes (if any) in `thoughts/`.
> Seeded by a workflow-priming experiment (CLAUDE.md `## Dev workflow` + this tree); fill on the first real `/shape:align`.

## 🚧 In progress —— v2.0 convergence in review
> plans `../plans/2026-06-17-nav-deep-module-refactor.md`, `../plans/2026-06-17-tier3-api-convergence-and-typing.md`
- **v2.0 deep-module refactor + src layout + uv-first** — shipped on branch `refactor/nav-deep-module`, open as **PR #1**, awaiting review/merge.

## ▶ Next —— packaging/lint modernization (flagged by the setup `python-lib` archetype)
- **Lint → ruff, line-100** — drop legacy `[tool.black]` + `flake8` + `[tool.mypy]@88`.
- **Ship `py.typed`** — this is a typed library; the marker is currently missing.
- **Collapse dual dev-dep tables** — keep `[dependency-groups].dev` only; drop the legacy `[project.optional-dependencies].dev`.

## ▶ Next —— audit follow-ups (surfaced 2026-07-11 by the youtube-cli audit)
- **CI (GitHub Actions)** — repo is on GitHub with 303 tests but has NO CI; a
  push that breaks the suite goes unnoticed. Add a minimal `uv run pytest`
  workflow on push/PR. (Highest value.)
- **Finish the error-hygiene pass** — the 2026-07-11 work redacted the
  YouTube-API handler's key-leaking prints and added `RateLimitedError` for the
  transcript path, but the library still has many bare `print()`s in the other
  handlers and collapses most failures into a generic `RuntimeError` via
  `run_with_fallback`. Route handler logging through the existing
  `verbose`-gated logger (`core/fallback.log_failure`) and widen the typed
  exception seam (`core/exceptions.py`) to a small NotFound / Private / Network
  taxonomy so callers can classify failures instead of string-matching.
- **Real smoke of `playlist --download`** — the `output_path` TypeError is fixed
  (facade→service signature now binds) but `download_playlist_media`'s full path
  has never been run end-to-end; do one real playlist download to validate it.

## ⏸ Future —— deferred
> build when a real consumer needs it
- **Async facade beyond downloads** — only `DownloadAPI` has `*_async` today; widen only if asked.

## ✅ Shipped
v1.0 deep-module refactor (services/ + `core/fallback.py` + `core/captions/` split), v2.0 flat-method removal → 5 sub-APIs, dict-compatible dataclass returns, opt-in parallel/async downloads, **src layout + uv-first toolchain (2026-06-23)**。(detail in git log + CHANGELOG.md)
- **2026-07-11 audit fixes** — API-key redaction on the Data-API handler,
  comment-fetch errors propagated (`CommentResult.error`), `transcript(lang=)`
  threaded through all three layers, `comments(order='rating')` reachable,
  `RateLimitedError` typed exception for transcript IP-blocks, `playlist`
  `output_path` honored, `channel.shorts/streams` gained `sort_by`,
  `get_playlist_videos` always returns dicts. (303 tests; commits `15f74ae`,
  `c0ad5f5`, `55dae8a`.)

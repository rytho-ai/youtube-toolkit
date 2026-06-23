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

## ⏸ Future —— deferred
> build when a real consumer needs it
- **Async facade beyond downloads** — only `DownloadAPI` has `*_async` today; widen only if asked.

## ✅ Shipped
v1.0 deep-module refactor (services/ + `core/fallback.py` + `core/captions/` split), v2.0 flat-method removal → 5 sub-APIs, dict-compatible dataclass returns, opt-in parallel/async downloads, **src layout + uv-first toolchain (2026-06-23)**。(detail in git log + CHANGELOG.md)

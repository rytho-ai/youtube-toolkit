# PO token setup (optional) — when yt-dlp downloads hit YouTube's bot-check

## What this solves

YouTube can require a Proof-of-Origin (PO) token for certain client/format
combinations. When it's missing, yt-dlp fails with a bot-check-style error
("Sign in to confirm you're not a bot", HTTP 403). `download_audio`/
`download_video`/`get_video_info` in `handlers/yt_dlp_handler.py` now detect
this failure shape (`utils/po_token_diagnostics.py`) and append a pointer to
this doc — but they do **not** generate PO tokens themselves. This package
doesn't implement PO-token generation; it recognizes when you need a
provider plugin and tells you so instead of surfacing a cryptic error alone.

## Why not built-in

Every real option for minting a PO token needs *something* beyond pure
Python — either a real/headless browser or a JS runtime emulating Google's
BotGuard attestation. Making that a hard dependency of youtube-toolkit would
force it on everyone, including the common case (no bot-check hit) where
it's dead weight. It's opt-in, matching the package's existing "swappable
handler backend" philosophy.

## Recommended fix: `bgutil-ytdlp-pot-provider`

Reverse-engineered/verified 2026-07-10 (yt-dlp's own PO-Token-Guide wiki +
the plugin's README). **Not** browser automation (no Puppeteer/Playwright) —
it runs Google's own BotGuard-interfacing JS ("BgUtils") under Node.js or
Deno. yt-dlp auto-detects it via its plugin framework once installed; no
`extractor_args` wiring needed in this codebase for the default case.

### Setup

```bash
# 1. Install the pip plugin (yt-dlp finds it automatically)
uv pip install "youtube-toolkit[po-token]"
# or directly: pip install bgutil-ytdlp-pot-provider

# 2. Run its token-generation server (simplest: Docker)
docker run --name bgutil-provider -d --init --restart unless-stopped \
    -p 4416:4416 brainicism/bgutil-ytdlp-pot-provider

# 3. Verify yt-dlp sees it
yt-dlp -v <any-youtube-url> 2>&1 | grep "PO Token Providers"
```

Without Docker: clone the repo, `npm ci && npx tsc` (or `deno`) under
`server/`, run it — needs Node.js ≥20 or Deno ≥2.0. See the plugin's own
README for the script-mode alternative (spawns a process per call; the
README itself says it's not recommended for anything but low-frequency use).

### Caveats (from the plugin's own docs — not a silver bullet)

- Providing a token does **not guarantee** bypassing bot-checks — it makes
  traffic look more legitimate, nothing more.
- Requires the `canvas` npm package; known friction on some platforms
  (e.g. Termux) — see the plugin's FAQ if the server fails to start.
- Token TTL defaults to 6 hours (`TOKEN_TTL` env var to change it).
- This is a *different* endpoint/mechanism than `get.transcript()`'s
  caption-fetch calls (that goes through `youtube-transcript-api`, not
  yt-dlp's player API) — a PO token here does not necessarily fix a
  transcript-fetch IP-block. Treat them as separate failure modes.

## If you'd rather not run a Node/Deno service at all

Two lighter but weaker options:
- **Cookies**: `YOUTUBE_COOKIES_FILE` (already supported, see the handler)
  — a logged-in session's cookies satisfy some of the same checks. Doesn't
  help every case; PO tokens and cookies address overlapping but not
  identical restrictions.
- **Wait and retry later** — some bot-checks are IP-reputation-based and
  transient, not permanent for that video.

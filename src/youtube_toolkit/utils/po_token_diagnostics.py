"""PO token failure diagnostics — recognize the error, point at the fix.

YouTube can require a Proof-of-Origin token (PO token) for certain
client/format combinations; when it's missing, yt-dlp raises a bot-check /
403-style error that reads like an opaque extraction failure. This module
does NOT generate PO tokens itself — that's the job of the community
`bgutil-ytdlp-pot-provider` plugin (auto-detected by yt-dlp's own plugin
framework once installed + its Node/Deno server is running; see
docs/po-token-setup.md). This module's only job is recognizing when a
failure is *shaped like* a missing-PO-token error, so we can append an
actionable hint instead of surfacing yt-dlp's raw, cryptic message alone.
"""

from __future__ import annotations

_PO_TOKEN_ERROR_MARKERS = (
    "sign in to confirm",
    "not a bot",
    "http error 403",
    "403: forbidden",
    "the following content is not available",
    "po token",
    "po_token",
)

PO_TOKEN_HINT = (
    "This looks like YouTube's bot-check / missing PO-token error, not a "
    "code bug. yt-dlp can need a Proof-of-Origin token for some "
    "clients/formats; see docs/po-token-setup.md for the (opt-in) fix — "
    "installing `bgutil-ytdlp-pot-provider` and running its token server. "
    "Retrying immediately won't help if the token is genuinely missing."
)


def is_po_token_related(exc: BaseException) -> bool:
    """Heuristic: does this exception look like a missing-PO-token failure?

    Deliberately conservative (substring match on yt-dlp's own wording) —
    false negatives (missed detection) are safer than false positives
    (blaming PO tokens for an unrelated failure).
    """
    text = str(exc).lower()
    return any(marker in text for marker in _PO_TOKEN_ERROR_MARKERS)


def augment(message: str, exc: BaseException) -> str:
    """Append the PO-token hint to an error message, only if it applies."""
    if is_po_token_related(exc):
        return f"{message}\n\n{PO_TOKEN_HINT}"
    return message

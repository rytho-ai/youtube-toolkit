"""Typed exceptions for youtube_toolkit.

Kept deliberately small: this is NOT the start of a general exception
taxonomy for the whole library. It exists so the transcript path (the one
place today that needs it — see the yt-dlp transcript handler) can
distinguish "YouTube is rate-limiting/blocking this IP" from "this video
genuinely has no captions", both of which used to collapse into a bare
``None`` return.

Reads: nothing (stdlib-free).
"""


class TranscriptError(RuntimeError):
    """Base class for transcript-fetch failures that are NOT "no captions".

    Genuinely-absent captions should still be represented as ``None`` —
    this is only for failures that mean "we don't actually know whether
    captions exist" (e.g. the request itself was blocked).
    """


class RateLimitedError(TranscriptError):
    """Raised when YouTube is rate-limiting or IP-blocking transcript requests.

    Callers can catch this specifically to show a "try again later /
    you're being rate-limited" message instead of a misleading "no
    transcript available".
    """

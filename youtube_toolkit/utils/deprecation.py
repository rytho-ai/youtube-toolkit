"""
utils/deprecation.py — caller-aware @deprecated decorator for legacy api.py methods.

Marks a flat YouTubeToolkit method as legacy: it still works and still delegates
to its service, but a DeprecationWarning is emitted **only when the caller is
outside the youtube_toolkit package**. This lets the recommended sub-API path
(toolkit.get/download/...) and the services keep calling these methods
internally without self-warning, while external users get a runtime nudge toward
the sub-API. No call-graph rewrite needed — the guard is the caller's module.

Reads: stdlib functools / warnings / sys only.
"""

import functools
import sys
import warnings

_PKG = "youtube_toolkit"


def deprecated(alternative: str):
    """
    Mark a public method as deprecated in favour of a sub-API.

    Args:
        alternative: The recommended replacement, e.g. "toolkit.get.video()".
            Shown in the warning message.

    The warning fires only for calls originating outside the youtube_toolkit
    package (so internal sub-API / service delegation stays quiet). DeprecationWarning
    is silent by default in Python, so library output is unaffected unless the
    consumer opts in (`-W` / warnings filters).
    """
    def decorator(func):
        message = (
            f"YouTubeToolkit.{func.__name__}() is a legacy method and will be "
            f"de-emphasised in a future release; prefer {alternative}."
        )

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            caller = sys._getframe(1).f_globals.get("__name__", "") or ""
            if not (caller == _PKG or caller.startswith(_PKG + ".")):
                warnings.warn(message, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        wrapper.__deprecated_alternative__ = alternative
        return wrapper

    return decorator

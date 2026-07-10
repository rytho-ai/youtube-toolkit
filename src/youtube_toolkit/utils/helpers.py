import os
import re

def ensure_directory(directory_path: str):
    """Ensure that the specified directory exists."""
    os.makedirs(directory_path, exist_ok=True)


# Matches `key=<value>` case-insensitively, stopping at the next query-string
# delimiter. This single pattern also catches `developerKey=`, `api_key=`,
# and `apiKey=` — they all contain the substring `key=`, so the match starts
# partway through the parameter name and only the secret *value* gets
# redacted (e.g. "developerKey=SECRET" -> "developerKey=***REDACTED***").
_SECRET_VALUE_PATTERN = re.compile(r'(?i)(key=)([^&\s"\'<>]*)')


def redact_secrets(value) -> str:
    """Scrub API-key-like query-string values out of an error/string.

    ``googleapiclient.errors.HttpError`` (and similar client errors) embed the
    full request URI — including ``key=<YOUTUBE_API_KEY>`` — in their string
    representation. Printing or logging such an exception verbatim leaks the
    API key in plaintext. Call this on any error/string that might have come
    from the YouTube Data API client before it is printed, logged, or stored.

    Args:
        value: An exception, string, or anything ``str()``-able (None is
            passed through unchanged).

    Returns:
        The stringified value with any ``key=...`` parameter value replaced
        by ``***REDACTED***``.
    """
    if value is None:
        return value
    text = str(value)
    return _SECRET_VALUE_PATTERN.sub(lambda m: f"{m.group(1)}***REDACTED***", text)

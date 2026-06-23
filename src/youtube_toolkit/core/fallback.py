"""
core/fallback.py — the single owner of the codebase's one fallback decision.

Captures the pattern hand-written ~69 times in api.py: try handlers in order,
log and move on when one raises, and raise RuntimeError once every attempt has
failed. `run_with_fallback` is the primitive; `log_failure` + the module logger
are the logging seam that replaces bare `print()`, gated by a `verbose` flag.
Lives in core/ so any service can reach it without an upward dependency.

Reads: nothing (pure stdlib logging + callables passed in by callers).
"""

import logging
from typing import Callable, Iterable, Optional, Tuple, TypeVar

# Module-level logger; callers may pass their own logger instead.
logger = logging.getLogger("youtube_toolkit")

T = TypeVar("T")

# An attempt is a (label, zero-arg callable) pair. The label identifies the
# handler in log output (e.g. "PyTubeFix", "YT-DLP", "YouTube API"), mirroring
# the prefixes used by the existing print() statements.
Attempt = Tuple[str, Callable[[], T]]


def log_failure(
    label: str,
    error: Exception,
    *,
    logger: Optional[logging.Logger] = None,
    verbose: bool = False,
) -> None:
    """
    Report that a handler attempt failed.

    This is the unified replacement for the bare ``print(f"<Label> failed: {e}")``
    calls. When ``verbose`` is True the failure is surfaced; otherwise it is kept
    quiet (logged at debug level). Faithfully preserves the existing "<label>
    failed: <error>" message shape.

    Args:
        label: Human-readable name of the handler that failed.
        error: The exception that was raised.
        logger: Logger to use; defaults to the module logger.
        verbose: When True, log at WARNING; when False, log at DEBUG (quiet).
    """
    log = logger if logger is not None else globals()["logger"]
    message = f"{label} failed: {error}"
    if verbose:
        log.warning(message)
    else:
        log.debug(message)


def run_with_fallback(
    attempts: Iterable[Attempt],
    *,
    error_message: str,
    logger: Optional[logging.Logger] = None,
    verbose: bool = False,
) -> T:
    """
    Try each attempt in order; return the first success, raise if all fail.

    This is the single owner of the "try primary handler -> log -> fall back ->
    raise RuntimeError if everything failed" decision that api.py currently
    hand-rolls everywhere. The first attempt that returns without raising wins,
    and no later attempt is invoked. Each failure is reported via ``log_failure``.

    Args:
        attempts: Ordered iterable of ``(label, callable)`` pairs. Each callable
            takes no arguments and performs one handler attempt.
        error_message: Message for the RuntimeError raised when every attempt
            fails (e.g. "All video info extraction methods failed").
        logger: Logger to use for failure reporting; defaults to module logger.
        verbose: Whether failures are surfaced loudly (see ``log_failure``).

    Returns:
        The return value of the first attempt that succeeds.

    Raises:
        RuntimeError: If every attempt fails.
    """
    for label, call in attempts:
        try:
            return call()
        except Exception as error:
            log_failure(label, error, logger=logger, verbose=verbose)
    raise RuntimeError(error_message)

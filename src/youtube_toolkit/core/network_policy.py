"""
network_policy.py — RequestPolicy + the transport seam for the official API client.

Owns every piece of "how do official-API HTTP requests behave on the wire"
knowledge: the RequestPolicy dataclass (timeout / transport retries / backoff),
which exceptions count as transient transport failures (SSL, socket timeout,
connection reset, DNS) versus application errors (quota, auth, validation —
never retried here), and the two factories the handler injects into
googleapiclient.discovery.build: a policy-carrying httplib2.Http (optionally
OAuth-wrapped) and a retrying HttpRequest subclass. Retries happen on the RAW
exception, before the handler's RuntimeError wrapping, so callers can still
rely on the handler's uniform error surface.

Reads: httplib2 · google_auth_httplib2 · googleapiclient.http (all lazily, to
preserve the handler's "google client not installed" ImportError path)
"""

import socket
import ssl
import time
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RequestPolicy:
    """Network behavior for official YouTube Data API requests.

    timeout_sec: per-socket-operation timeout handed to httplib2.Http.
        None (the default) keeps the platform default — no timeout — which
        preserves pre-2.1 behavior for existing consumers.
    transport_retries: how many times a request is re-sent after a transient
        TRANSPORT failure (SSL error, socket timeout, connection reset, DNS).
        Application-level errors (quota, auth, validation → HttpError) are
        never retried. 0 (the default) means fail on first error, as before.
    retry_backoff_sec: base sleep between retries, doubled each attempt
        (0.15 → 0.15s, 0.3s, 0.6s, ...).
    """

    timeout_sec: Optional[float] = None
    transport_retries: int = 0
    retry_backoff_sec: float = 0.15

    def __post_init__(self):
        if self.timeout_sec is not None and self.timeout_sec <= 0:
            raise ValueError(f"timeout_sec must be positive or None, got {self.timeout_sec}")
        if self.transport_retries < 0:
            raise ValueError(f"transport_retries must be >= 0, got {self.transport_retries}")
        if self.retry_backoff_sec < 0:
            raise ValueError(f"retry_backoff_sec must be >= 0, got {self.retry_backoff_sec}")


def _transient_transport_errors():
    """Exceptions worth a transport-level retry. Lazily built: httplib2 is
    only guaranteed present when google-api-python-client is installed."""
    import httplib2

    return (
        ssl.SSLError,
        socket.timeout,  # alias of TimeoutError on 3.10+
        ConnectionError,  # ConnectionResetError / BrokenPipeError / ...
        httplib2.ServerNotFoundError,  # transient DNS
    )


def build_policy_http(policy: RequestPolicy, credentials=None):
    """Build the httplib2 transport carrying the policy's timeout.

    With credentials, wraps it in google_auth_httplib2.AuthorizedHttp — the
    same wrapper discovery.build would apply internally — so the OAuth and
    API-key paths get identical timeout behavior.
    """
    import httplib2

    http = httplib2.Http(timeout=policy.timeout_sec)
    if credentials is not None:
        import google_auth_httplib2

        http = google_auth_httplib2.AuthorizedHttp(credentials, http=http)
    return http


def build_request_builder(policy: RequestPolicy):
    """Build the requestBuilder class for discovery.build.

    Returns an HttpRequest subclass whose execute() retries transient
    transport failures per the policy, re-raising the last raw exception
    untouched once retries are exhausted. HttpError never enters the retry
    loop, so quota / auth / validation errors surface on the first call.
    """
    from googleapiclient.http import HttpRequest

    transient = _transient_transport_errors()

    class _RetryingHttpRequest(HttpRequest):
        def execute(self, http=None, num_retries=0):
            last_exc = None
            for attempt in range(policy.transport_retries + 1):
                try:
                    return super().execute(http=http, num_retries=num_retries)
                except transient as e:
                    last_exc = e
                    if attempt < policy.transport_retries:
                        time.sleep(policy.retry_backoff_sec * (2 ** attempt))
            raise last_exc

    return _RetryingHttpRequest

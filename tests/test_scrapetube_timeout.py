"""scrapetube's HTTP calls must carry a timeout.

scrapetube passes none, and `requests` without one waits forever. Callers
reach this handler from async code by putting it on a thread, and a thread
cannot be cancelled — so one unresponsive endpoint holds a worker for good
and enough of them exhaust the pool. The handler is the only place that can
supply the argument scrapetube never does.
"""

import requests

from youtube_toolkit.handlers.scrapetube_handler import (
    DEFAULT_TIMEOUT_SEC,
    ScrapeTubeHandler,
    _apply_default_timeout,
)


class _FakeSession:
    def __init__(self):
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append(kwargs)
        return "response"


class _FakeScrapetube:
    def __init__(self):
        self.built = 0

    def get_session(self, proxies=None):
        self.built += 1
        return _FakeSession()


def test_a_default_timeout_reaches_every_request():
    module = _FakeScrapetube()

    _apply_default_timeout(module, 12.5)
    session = module.get_session()
    session.request("GET", "https://youtube.invalid")

    assert session.calls == [{"timeout": 12.5}]


def test_an_explicit_timeout_still_wins():
    """Filling in a default must never override a caller who asked for something."""
    module = _FakeScrapetube()

    _apply_default_timeout(module, 12.5)
    session = module.get_session()
    session.request("GET", "https://youtube.invalid", timeout=1.0)

    assert session.calls == [{"timeout": 1.0}]


def test_patching_twice_does_not_stack_wrappers():
    module = _FakeScrapetube()

    _apply_default_timeout(module, 12.5)
    _apply_default_timeout(module, 99.0)
    session = module.get_session()
    session.request("GET", "https://youtube.invalid")

    # The second call must be a no-op, not another layer — a stacked wrapper
    # would have the inner default win and make the knob silently useless.
    assert session.calls == [{"timeout": 12.5}]


def test_timeout_none_restores_the_old_wait_forever_behaviour():
    module = _FakeScrapetube()

    _apply_default_timeout(module, None)
    session = module.get_session()
    session.request("GET", "https://youtube.invalid")

    # No timeout injected — the caller explicitly asked to keep waiting forever.
    assert session.calls == [{}]


def test_a_module_without_get_session_is_left_alone():
    """If upstream refactors the factory away, losing a timeout is a better
    failure than crashing on import."""

    class _Changed:
        pass

    changed = _Changed()
    _apply_default_timeout(changed, 12.5)  # must not raise

    assert not hasattr(changed, "get_session")


def test_the_handler_installs_the_default_on_a_real_scrapetube_session():
    """End to end against the real package: the session scrapetube hands back
    must carry the timeout into `requests`' own call signature."""
    import scrapetube.scrapetube as st

    ScrapeTubeHandler()._ensure_initialized()

    seen = {}
    original_send = requests.Session.send

    def _capture(self, request, **kwargs):
        seen.update(kwargs)
        raise requests.exceptions.ConnectionError("stopped before leaving the machine")

    requests.Session.send = _capture
    try:
        session = st.get_session()
        try:
            session.get("https://youtube.invalid")
        except requests.exceptions.ConnectionError:
            pass
    finally:
        requests.Session.send = original_send

    assert seen.get("timeout") == DEFAULT_TIMEOUT_SEC

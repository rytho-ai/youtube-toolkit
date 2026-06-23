"""
DictAccessMixin — read-only dict-style access bridge for result dataclasses.

Lets a dataclass be used both as an object (``x.title``) and as a read-only
mapping (``x['title']``, ``x.get('title')``, ``'title' in x``, ``dict(x)``), so
returns that were previously plain dicts can become typed dataclasses without
breaking existing dict-style consumers.

Requirement: the host class must define ``to_dict()`` — keys()/values()/items()/
iteration are sourced from it. Only read access is covered; mutating/unpacking
semantics (pop/update/del/len) are intentionally NOT provided.

Reads: nothing (stdlib-free mixin).
"""


class DictAccessMixin:
    """Mixin granting read-only dict-style access on top of attribute access.

    The host dataclass must implement ``to_dict()``.
    """

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __contains__(self, key):
        return hasattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def keys(self):
        return self.to_dict().keys()

    def values(self):
        return self.to_dict().values()

    def items(self):
        return self.to_dict().items()

    def __iter__(self):
        return iter(self.to_dict())

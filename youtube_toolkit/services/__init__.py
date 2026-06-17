"""
services/ — home for business logic descending out of the api.py god class.

This package is the new home for the orchestration/business logic currently
living inside YouTubeToolkit (api.py). Each future module groups methods by
domain (get_info, channel, download, search, ...) so api.py can shrink to a
thin delegation layer while handlers stay pluggable backends. Empty for now —
this is the skeleton; services are filled in by the next refactor phase.

Reads: nothing yet (barrel only). Future services will read youtube_toolkit.handlers.* and youtube_toolkit.core.fallback.
"""

__all__: list = []

"""Web search backends."""

from neteyes.backends.search.ddg_backend import DuckDuckGoBackend
from neteyes.backends.search.searxng_backend import SearxngBackend

__all__ = ["DuckDuckGoBackend", "SearxngBackend"]
